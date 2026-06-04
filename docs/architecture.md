# Snip — Architecture (v1)

**Status:** Draft v3
**Author:** Engineering
**Derived from:** PRD v5, ERD v5 (2026-06-04)

## Overview

Snip is split into three deployment tiers chosen for the per-tier latency and scale targets in the PRD:

1. **Edge** — the redirect service runs on Cloudflare Workers at every POP. Its sole job is `GET /<short-code>` → `302`. It owns the redirect-path SLO (p95 < 100ms global, 99.95% monthly).
2. **Regional** — the dashboard (Next.js), the link API (FastAPI/Python), the Mixpanel forwarder, and the email worker run in a single AWS region (us-east-1 in v1). These tiers hold all stateful concerns: Postgres for the OLTP store, Redis for cache + rate-limit counters, SQS for async pipelines.
3. **Async** — the click pipeline, Mixpanel forwarder, and SES mail-events worker consume from SQS queues and run as ECS Fargate services.

Every component is workspace-scoped at the data layer (`workspace_id` carried directly on every row per ERD v2) and at the request layer (auth middleware injects the active workspace context).

## Component diagram

```
                    ┌──────────────────┐
   Anonymous GET ───┤ Cloudflare Worker│── 302 ──► destination
                    │  (redirect)      │
                    └────────┬─────────┘
                             │ ClickEvent
                             ▼
                    ┌──────────────────┐
                    │  SQS: clicks     │
                    └────────┬─────────┘
                             │
                             ▼
   ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
   │  Postgres   │◄───┤  Click consumer  ├───►│ SQS:mixpanel│
   │ (workspace- │    └──────────────────┘    └──────┬──────┘
   │  scoped)    │                                   │
   └──────┬──────┘                                   ▼
          │                                  ┌──────────────────┐
          ▲                                  │ Mixpanel fwdr    │
          │                                  └──────────────────┘
   ┌──────┴──────┐    ┌──────────────────┐
   │  Dashboard  │───►│   Link API       │
   │  (Next.js)  │    │   (FastAPI)      │
   └─────────────┘    └────────┬─────────┘
                               │
                       ┌───────┴──────────┐
                       ▼                  ▼
                ┌────────────┐    ┌────────────────┐
                │   Redis    │    │   SES + SNS    │
                │ (cache,    │    │ + mail worker  │
                │  rate-lim) │    └────────────────┘
                └────────────┘
```

## Authentication and authorization

- **Identity.** Sessions are server-issued via HTTP-only, Secure, SameSite=Lax cookies. Cookie carries a signed session id (HMAC-SHA256) that references a Redis-backed session record. 30-day absolute, 7-day idle.
- **Session revocation.** Sessions reference `USER.session_version`. Auth middleware compares the cookie's `session_version` against the row; mismatch → 401. Bumped on logout, password change, and admin removal of the user (per PRD §Teams "lose access immediately").
- **Authorization model.** Role-based, two roles in v1: `admin` and `editor`. Permission checks are middleware-level — every API request resolves `(user, active_workspace_id)` and a `role`, then route handlers declare required role via a FastAPI dependency.
- **Multi-tenant enforcement.** Every query that touches workspace-scoped tables passes through a base repository class that automatically AND'es `workspace_id = <active>` into every SELECT / UPDATE / DELETE. Routes that need to bypass this (none in v1) must explicitly opt out. This is structural defense-in-depth on top of the per-row `workspace_id` FK in the ERD.

## Secrets management

- **Provider.** AWS Secrets Manager for production. All non-public config (DB credentials, KMS key ARNs, Mixpanel project token, SES SMTP credentials, Cloudflare API token, signing secrets) lives there.
- **Distribution.** ECS services read secrets at task-start via the standard ECS Secrets Manager integration. No secrets in container images, no secrets in environment variables baked into builds.
- **Cloudflare Workers** read secrets via the Workers Secrets binding, populated from CI using the Cloudflare API token (which itself lives in Secrets Manager and is fetched by the deploy job at deploy time).
- **Rotation.** DB credentials rotate every 30 days via Secrets Manager's RDS rotation Lambda. Signing secrets rotate quarterly; both old and new are accepted during a 7-day overlap window via key id in the signed cookie payload.

## Data and storage

### Primary store — Postgres

- Single primary in us-east-1, two read replicas (analytics queries route to replicas; OLTP to primary).
- ERD v2 drives the schema. All workspace-scoped tables carry `workspace_id` directly; the base repository enforces tenant filtering.
- **Encryption.** Email `email_ciphertext` columns are encrypted application-layer with AES-256-GCM. The DEK is generated per-row, sealed by a KMS CMK, and stored alongside the ciphertext. `email_search_hash` is HMAC-SHA256 over the lowercased email with a key from Secrets Manager — used for uniqueness and lookup, irreversible.
- **Migrations.** Alembic. Every schema change ships as a migration file in the same PR as the code. CI runs migrations against a fresh DB in test. Production migrations run as a separate deploy step gated on manual approval. Migrations must be forward-compatible (old code can run against the new schema for at least one deploy) to allow zero-downtime deploys.
- **Connection pool.** SQLAlchemy `pool_size=10, max_overflow=5` per ECS task. Aggregate connection counts at autoscale ceilings:

  | Service | Max tasks | Pool per task | Max connections |
  |---|---|---|---|
  | Link API | 50 | 15 | 750 |
  | Click consumer | 50 | 5 (pool=3, overflow=2) | 250 |
  | Mixpanel forwarder | 10 | 5 | 50 |
  | Mail worker | 5 | 5 | 25 |
  | **Total** | | | **1 075** |

  Total (1 075) exceeds `db.r6g.large` `max_connections ≈ 1000`. **PgBouncer** runs in transaction-mode pooling as a sidecar on the primary (targeting 700 pooled server connections), multiplexing all application connections. Application services connect to PgBouncer on port 5433; PgBouncer connects to Postgres on 5432. Pool-leak detection via Postgres `idle_in_transaction_session_timeout = 30s` and `statement_timeout = 30s` on the application role.
- **Transaction boundaries.** Every API request opens exactly one database transaction via a FastAPI dependency-injected unit of work. Service-layer code never calls `commit()` or `rollback()` directly — the handler commits on successful return; the dependency rolls back on any exception. For operations that also publish to SQS (link create → Mixpanel enqueue), the SQS publish happens after the DB commit; a crash between commit and publish loses the event, with the Mixpanel dead-letter store as the recovery path. Member removal's atomic `owner_id` reassignment is a single multi-row UPDATE inside the transaction before commit.

### Cache / rate limiting — Redis

- AWS ElastiCache (single-AZ in v1, multi-AZ in a future hardening pass).
- Carries: session records, rate-limit counters (`link-create:<user_id>`, `login-attempts:<email_hash>`), Pwned Passwords result cache (none in v1 per PRD, but the key exists for v2).
- **Persistence.** AOF persistence enabled (fsync: `everysec`) to survive node restarts. Daily automatic backups via ElastiCache with a 7-day retention window.
- **Failure posture.** ElastiCache is single-AZ in v1. A node or AZ failure forces session loss (all users are signed out) and resets login-lockout counters. Session loss is an acceptable inconvenience (users re-authenticate). Lockout counter reset is a known, low-frequency security tradeoff: it allows a burst of additional login attempts until the counter rebuilds. Both risks are acknowledged in §Open questions. Login lockout failing open (allowing attempts) is preferred over the alternative of denying all logins while Redis is unavailable.

### Click event store — Postgres CLICK table

- CLICK lives in the same Postgres cluster. `workspace_id` is indexed; the redirect-emission write path is a single insert.
- 13-month rolling retention is enforced by a scheduled job (pg_cron) that deletes `WHERE clicked_at < NOW() - INTERVAL '13 months'`.

### Scheduled maintenance jobs

Two pg_cron jobs run on the Postgres primary daily during low-traffic hours:

| Job | Query | Purpose |
|---|---|---|
| CLICK retention | `DELETE FROM click WHERE clicked_at < NOW() - INTERVAL '13 months'` | PRD §Data retention 13-month rolling window |
| LINK hard-delete | `DELETE FROM link WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days'` | PRD §Data retention — soft-deleted links hard-deleted after 30 days, freeing the short code for reuse |

Both jobs write a completion row to a `maintenance_run` log table for ops monitoring.

### Backups and recovery

- **RPO target:** 5 minutes. Postgres uses continuous WAL archiving to S3.
- **RTO target:** 1 hour. Restore-from-snapshot drills run quarterly.
- **Retention.** Daily snapshots for 30 days; weekly snapshots for 90 days; quarterly archives for 7 years (compliance hedge — no specific regulation today).

## Async work

| Pipeline | Trigger | Queue | Workers | Purpose |
|---|---|---|---|---|
| Clicks | Redirect Worker publishes a `ClickEvent` to **Cloudflare Queue** `cf-clicks`; a Cloudflare Queue consumer forwards to SQS `clicks` | SQS `clicks` | Click consumer (ECS Fargate, autoscaled on queue depth) | Persist to Postgres CLICK; emit downstream `link_clicked` Mixpanel event |
| Mixpanel | Click consumer + link/account API publish | SQS `mixpanel` | Mixpanel forwarder (ECS Fargate) | POST events to `/track`, retry per PRD §Mixpanel, write failures to `mixpanel_dead_letter` |
| Mail events | SES bounce/complaint → SNS → SQS | SQS `mail-events` | Mail worker (ECS Fargate) | Insert / update `email_suppression` |

All SQS queues have DLQs configured (max 5 receive attempts).

**Click pipeline durable buffering.** Cloudflare Workers are stateless V8 isolates with no local persistent storage — the Worker cannot buffer events locally when SQS is unavailable. The PRD requirement ("click event is durably queued locally") is satisfied by placing a **Cloudflare Queue** between the Worker and SQS: the Worker publishes to Cloudflare Queue (an atomic, durable edge write); a Cloudflare Queue consumer forwards messages to SQS `clicks`. If SQS is temporarily unavailable, Cloudflare Queue holds the events and retries delivery; the 302 redirect is already complete. Cloudflare Queue provides at-least-once delivery with built-in retry and a DLQ for persistent failures.

## External integrations and resilience

- **Mixpanel** — per PRD §Mixpanel: server-side `/track`, in-process retry 3× exponential, dead-letter to Postgres. Mixpanel forwarder is fully decoupled from request path. Every event includes `$insert_id` set to the source entity UUID (e.g. `CLICK.id` for `link_clicked`, `LINK.id` for `link_created`). Mixpanel deduplicates on `$insert_id` within a 7-day window, preventing duplicate analytics from SQS at-least-once redelivery. **Crash window:** if the click consumer crashes after persisting the CLICK row but before publishing to SQS:mixpanel, the `link_clicked` event is lost; recovery relies on a periodic reconciliation job that replays CLICK rows with no corresponding dead-letter entry.
- **Pwned Passwords** — k-anonymity API on sign-up / password change. 500ms timeout, 1 retry. Fail-open per PRD; the skip is logged with `pwned_check_skipped=true` and the daily ops review catches anomalies.
- **AWS SES** — SDK calls from Link API for invite emails and from Account API for verify / reset emails. boto3 configured with `connect_timeout=3s`, `read_timeout=10s`. Send failures are retried 3× in-process with exponential backoff; persistent failure surfaces per PRD's per-context UX.
- **Google Safe Browsing v4** — Link API calls on link create and link edit. 800ms timeout, fail-open per PRD. No retry on timeout (latency budget). One retry on transient network error with immediate backoff. API key from Secrets Manager.
- **MaxMind GeoLite2** — local `.mmdb` distributed to every Cloudflare Worker POP via the deploy pipeline. Twice-weekly DB pull job (CodeBuild) signs the mmdb and uploads to a worker-secret binding. Stale > 30 days → country falls back to `Unknown`; > 21 days → ops alert.

## Observability

- **Logging.** Structured JSON logs to AWS CloudWatch via the ECS log driver and the Cloudflare Workers Logpush integration. Every log line carries `request_id`, `workspace_id` (when known), and `member_id` (when known). **request_id generation:** the ALB injects a UUID-v4 as `X-Request-Id` on every inbound request to the Link API (ALB attribute: custom request header injection); the FastAPI middleware trusts this header only when the source IP is the ALB. The Cloudflare Worker generates a UUID-v4 at the start of each `fetch` handler. `request_id` is propagated as the `X-Request-Id` header on all outbound HTTP calls (Google Safe Browsing, Pwned Passwords API, SES, Mixpanel `/track`) and as an SQS message attribute for cross-service correlation alongside `X-Amzn-Trace-Id`.
- **Metrics.** CloudWatch metrics emitted by each service: request rate, error rate, p50/p95/p99 latency. Custom metrics for `redirect_p95`, `click_pipeline_depth`, `pwned_check_skipped_count`, `mail_send_failures`.
- **Tracing.** AWS X-Ray on the regional services. Trace context is propagated from edge → SQS → consumer via the `X-Amzn-Trace-Id` message attribute.
- **Error tracking.** Sentry for both the Next.js dashboard (client + SSR) and the FastAPI backend. Each release is tagged.
- **Alerts.** PagerDuty rotation. Pages on: redirect p95 > 150ms for 5 min, redirect error rate > 1% for 5 min, click pipeline depth > 100k, mail-events DLQ depth > 0, mixpanel_dead_letter inserts > 100/hour, DB primary replication lag > 60s, KMS errors any.

## Scaling

- **Redirect.** Cloudflare Workers — no capacity planning beyond paying for the request volume. The Worker is stateless; the `.mmdb` is the only large local asset and is shipped at deploy.
- **Link API.** ECS Fargate behind an ALB. Autoscale on CPU > 60% and request count per target. Concrete v1 capacity target: sustain 200 link-create RPS with bursts to 1000. (PRD does not state a peak; this number was chosen as 10× expected steady-state at month-6 paid traffic.)
- **Dashboard.** Separate ECS Fargate service from the Link API, behind the same ALB (different target group). Static assets (JS bundles, CSS) are hashed at build time and served from S3 via CloudFront with immutable cache headers (`Cache-Control: public, immutable, max-age=31536000`). Next.js SSR responses for the `/links` page are cached at CloudFront with a 10s TTL (fast staleness acceptable; link list has a Retry button). The p95 < 2s on slow 4G NFR is enforced in CI via Lighthouse CI on a representative simulated throttle profile.
- **Click pipeline.** ECS Fargate autoscaled on SQS queue depth. Target depth ≤ 1000 messages, autoscale to ≤ 50 consumer tasks.
- **Database.** Single primary; read traffic offloaded to replicas. Vertical scale path to `db.r6g.4xlarge` (current `db.r6g.large` in v1) before considering sharding.
- **Health check endpoints.** Each ECS service exposes:
  - `GET /healthz` — liveness: returns 200 if the process responds (no dependency checks). ECS uses this to detect crashed containers.
  - `GET /readyz` — readiness: returns 200 only when the process can reach the Postgres primary and Redis within 2 s each. The ALB uses this to gate traffic routing; a failing task is drained before replacement. ALB config: path `/readyz`, interval 15 s, healthy threshold 2, unhealthy threshold 3.

## Rate limiting and abuse

- **Link creation:** Redis-backed sliding window. 60 / minute / user per PRD.
- **Login:** 5 failed attempts / 15 min / email per PRD. Counter and lockout end-time both in Redis. Lockout counter fails open when Redis is unavailable (see §Cache / rate limiting — Redis failure posture).
- **Sign-up:** Redis-backed token bucket. 5 accounts per IP per hour and 3 accounts per email domain per hour. Prevents bot account creation; enforcement is fail-closed (if Redis is unreachable, sign-up is rejected with a 503).
- **Password reset:** Redis-backed, 3 reset emails per email address per hour and 10 per originating IP per hour. Prevents SES quota exhaustion and email enumeration amplification.
- **Redirect path:** Cloudflare WAF rules — per-IP global rate-limit (1000 req/s/IP) and bot-traffic mitigation rules at the edge. Per-short-code rate limiting is not implemented in v1; if a viral link causes hot-key pressure, the Worker's regional cache absorbs it. *(Note: PRD Gate 3 finding flagged this; v1 accepts the edge / WAF coverage.)*

## Caching

- **Edge.** Cloudflare's regional cache stores `short_code → destination_url` lookups with a 5-min TTL. Cache key includes `deleted_at` is null; deletes purge via Cloudflare's API. Cache miss → fetch from Link API → return 302 and populate.
- **Application.** None in v1. Workspace membership, role, and link list rely on Postgres + index quality. Revisit if dashboard p95 exceeds target.

## Environments

| Environment | Purpose | Hosts | Data |
|---|---|---|---|
| `dev` | Engineer-local | Docker Compose | Seeded test data |
| `staging` | Pre-prod integration | Same shape as prod, smaller capacity | Anonymized subset of prod (daily refresh — see note below) |
| `prod` | Live | us-east-1 | Real data |

All environments share the same migration tooling; promotions are migration-first.

**Staging anonymization.** The staging environment uses a **separate AWS KMS CMK** from production. The daily refresh pipeline does not copy production `email_ciphertext` fields — it generates synthetic email addresses for every USER, INVITE, and EMAIL_SUPPRESSION row, re-encrypts them with the staging CMK, and writes staging-specific `email_search_hash` values. All destination URLs and short codes are copied as-is (not PII). Session data, login-attempt counters, and rate-limit state are not copied. The anonymization pipeline runs as a CodeBuild job; its IAM role has cross-account read access to a prod S3 export (never direct Postgres access).

## CI/CD

- **CI.** GitHub Actions. Per-PR: type check (Mypy + tsc), lint (Ruff, ESLint), unit + integration tests, OpenAPI diff, Alembic check (no naked DDL, no destructive operations without explicit annotation), **SAST** (Bandit for Python with HIGH/MEDIUM severity gate; semgrep with `python.security` and `javascript.react.security` rulesets), **dependency vulnerability scan** (`pip-audit` for Python and `npm audit --audit-level=high` for Node — covers OWASP A06: Vulnerable and Outdated Components), **Lighthouse CI** for dashboard performance (p95 load time threshold on slow 4G).
- **Deploys.** Trunk-based. Merge to `main` → CI builds container images → `staging` deploy is automatic → manual promotion to `prod` via a GitHub Actions workflow gated on approval. Edge Worker has the same shape but is deployed via Cloudflare's API.
- **Graceful shutdown.** All ECS Fargate services handle SIGTERM with a two-phase drain:
  - HTTP services (Link API): stop accepting new connections immediately; drain in-flight requests with a 30 s timeout; exit.
  - Queue consumers (click consumer, Mixpanel forwarder, mail worker): finish processing the current message batch (SQS visibility timeout: 90 s); stop polling; exit. ECS task `stopTimeout` is set to 120 s (drain window + safety margin) to prevent SIGKILL mid-message.

## Frontend/backend contract

- **Transport.** REST over HTTPS with JSON bodies.
- **Schema source of truth.** FastAPI's auto-generated OpenAPI document. The Next.js dashboard consumes generated TypeScript types via `openapi-typescript` on every dashboard deploy.
- **Auth transport.** Session cookie (HTTP-only). The dashboard sends fetch requests with `credentials: 'include'`; CSRF tokens are required on mutating endpoints (double-submit cookie pattern).
- **API versioning.** All Link API routes are prefixed `/v1/` (e.g. `/v1/links`, `/v1/workspaces`). Breaking changes require a new version prefix and a minimum 90-day deprecation window; deprecated versions respond with `Deprecation` and `Sunset` headers. Non-breaking additive changes (new optional fields, new endpoints) ship without a version bump.
- **CORS.** Allowed origins (v1): `https://app.snip.io` only. No wildcard origins. `Access-Control-Allow-Credentials: true` (required for the session cookie). Allowed methods: `GET, POST, PUT, PATCH, DELETE, OPTIONS`. Enforced via FastAPI `CORSMiddleware`; the ALB does not add CORS headers independently. Branded-domain origins are out of scope for v1 (PRD §Out of scope); the allowlist will expand when that feature ships.
- **TLS enforcement.** TLS 1.2 is the minimum at every HTTPS termination point: Cloudflare (SSL/TLS mode "Full (strict)", minimum TLS version 1.2 in the SSL settings), ALB (security policy `ELBSecurityPolicy-TLS13-1-2-2021-06`), ElastiCache in-transit encryption (TLS 1.2+), RDS encryption in transit enforced via the `rds.force_ssl=1` parameter group setting. ECS-internal traffic stays within the VPC private subnet (no TLS required for same-region service-to-service calls).
- **HTTP security headers.** Applied on every response via FastAPI middleware (Link API) and Next.js `headers()` config (Dashboard). Canonical production values: `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` · `X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` · `Referrer-Policy: strict-origin-when-cross-origin` · `Permissions-Policy: geolocation=(), camera=()`. `Content-Security-Policy` is set per surface: dashboard allows `'self'` plus the CDN asset origin; API responses carry `default-src 'none'`. In local dev only, the dashboard CSP adds `'unsafe-eval'` for hot-reload.
- **Request body limits.** Default JSON body limit: 1 MB, enforced by FastAPI middleware and an ALB 1 MB request-body limit on the Link API target group. No file upload endpoints in v1. The Cloudflare redirect Worker accepts GET requests only; no body limit applies.
- **Error envelope.** Every Link API 4xx/5xx response is JSON: `{ "error": { "code": "<machine-code>", "message": "<human>", "request_id": "<uuid>" } }`. A global FastAPI exception handler catches all unhandled exceptions and wraps them in this shape. Stack traces are never included in HTTP responses — they are forwarded to Sentry and CloudWatch only. Common exception-to-status-code mappings: `EntityNotFound` → 404 · `PermissionDenied` → 403 · Pydantic `ValidationError` → 422 · unhandled → 500.
- **Cloudflare Worker error handling.** The redirect Worker wraps the entire `fetch` handler in a try-catch. On a Postgres/KV lookup failure, the Worker returns `503 Service Unavailable` with a plain-text body (the Worker cannot render the full app shell without a DB connection, consistent with PRD Flow B "503 page"). On any other unhandled exception, the Worker returns `503`. All Worker errors are reported to Sentry via the Sentry Cloudflare Workers SDK and to Cloudflare Logpush.
- **Payload compression.** Responses ≥ 1 KB are gzip-compressed via FastAPI `GZipMiddleware`; Brotli is used where the client signals `br` in `Accept-Encoding`. Cloudflare applies Brotli automatically on edge-cached redirect responses. Analytics time-series and paginated link-list responses are the primary beneficiaries.

## API design

### Input validation and DTO boundary

All request bodies are declared as Pydantic `BaseModel` subclasses on every endpoint. ORM model instances are never returned directly from handlers — every response uses an explicit `response_model` schema to prevent accidental field leakage (e.g. `password_hash`, `email_ciphertext`). Partial-update endpoints use dedicated `Update<X>` schemas with all fields optional and at least one present required.

### Pagination

All list endpoints use cursor-based pagination. Default page size: 50 (matching PRD §Link list). Maximum page size: 200. The cursor is an opaque base64-encoded composite of `(created_at DESC, id DESC)` passed as the `after` query parameter. Response envelope: `{ "items": [...], "next_cursor": "<string> | null" }`. Offset-based pagination is not used — it produces inconsistent results under concurrent inserts and degrades as the CLICK table grows.

### Analytics query bounds

All click time-series queries are bounded: `WHERE link_id = :link_id AND clicked_at >= NOW() - INTERVAL '30 days'`. The analytics API endpoint enforces a maximum lookback of 13 months (the retention window); requests exceeding this are clamped server-side. Partial indexes on `(link_id, clicked_at)` and `(workspace_id, clicked_at)` support these queries. No unbounded `SELECT COUNT(*)` is permitted in the analytics path.

### Idempotency

POST endpoints that create resources (`POST /v1/links`, `POST /v1/workspaces/invites`) accept an optional `Idempotency-Key` request header. The server stores the `(Idempotency-Key, user_id, endpoint)` → serialised response in Redis with a 24-hour TTL and replays the cached response on retry without re-executing the handler. Endpoints that are naturally idempotent by domain semantics (PATCH invite-accept on a token hash, DELETE link) are marked as such in the OpenAPI spec and do not require a key. Endpoints where the PRD explicitly allows duplicates (link creation — two requests with the same destination produce two distinct short codes) are also documented so callers know that retry behaviour is intentional.

## Compliance

PRD does not name a specific compliance regime (GDPR, HIPAA, etc.) as a hard requirement; the only PII handled is email addresses (encrypted at rest per PRD NFR). GDPR-style user-data export and delete are explicitly out of scope per PRD (handled manually via support). The architecture preserves the *capability* to add automated export/delete later — single `workspace_id` join out from USER reaches all owned data, and `email_search_hash` allows targeted lookup without holding plaintext.

## Open questions

These items are flagged for follow-up before architectural finalization or known v1 limitations to revisit post-launch:

- **Workspace deletion lifecycle** — PRD has no `Workspace.deleted_at` requirement in v1; a deletion path (cascade vs. retain) needs a PRD decision before architecture can declare an implementation.
- **email_search_hash key rotation** — rotation would require re-hashing every email address in USER, INVITE, and EMAIL_SUPPRESSION. This must be coordinated with KMS DEK rotation (potentially online re-encryption). Strategy TBD post-v1.
- **ElastiCache multi-AZ** — v1 accepts single-AZ (session loss + lockout reset on AZ failure). Post-launch hardening: enable multi-AZ replication group and automatic failover.
- **Mixpanel crash-window reconciliation** — the click consumer crash window (CLICK persisted but link_clicked not published) has no automated reconciler in v1. Add a scheduled replay job in the first hardening sprint.
- **PgBouncer operations** — PgBouncer is added to address the connection count ceiling but adds an operational component. Statement-mode vs. transaction-mode tradeoffs for long-running analytics queries should be validated under load.
