# Snip — Architecture (v1)

**Status:** Draft v1
**Author:** Engineering
**Derived from:** PRD v3, ERD v2 (2026-05-25)

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

### Cache / rate limiting — Redis

- AWS ElastiCache (single-AZ in v1, multi-AZ in a future hardening pass).
- Carries: session records, rate-limit counters (`link-create:<user_id>`, `login-attempts:<email_hash>`), Pwned Passwords result cache (none in v1 per PRD, but the key exists for v2).

### Click event store — Postgres CLICK table

- CLICK lives in the same Postgres cluster. `workspace_id` is indexed; the redirect-emission write path is a single insert.
- 13-month rolling retention is enforced by a scheduled job (pg_cron) that deletes `WHERE clicked_at < NOW() - INTERVAL '13 months'`.

### Backups and recovery

- **RPO target:** 5 minutes. Postgres uses continuous WAL archiving to S3.
- **RTO target:** 1 hour. Restore-from-snapshot drills run quarterly.
- **Retention.** Daily snapshots for 30 days; weekly snapshots for 90 days; quarterly archives for 7 years (compliance hedge — no specific regulation today).

## Async work

| Pipeline | Trigger | Queue | Workers | Purpose |
|---|---|---|---|---|
| Clicks | Redirect Worker emits a `ClickEvent` | SQS `clicks` | Click consumer (ECS Fargate, autoscaled on queue depth) | Persist to Postgres CLICK; emit downstream `link_clicked` Mixpanel event |
| Mixpanel | Click consumer + link/account API publish | SQS `mixpanel` | Mixpanel forwarder (ECS Fargate) | POST events to `/track`, retry per PRD §Mixpanel, write failures to `mixpanel_dead_letter` |
| Mail events | SES bounce/complaint → SNS → SQS | SQS `mail-events` | Mail worker (ECS Fargate) | Insert / update `email_suppression` |

All queues have DLQs configured (max 5 receive attempts).

## External integrations and resilience

- **Mixpanel** — per PRD §Mixpanel: server-side `/track`, in-process retry 3× exponential, dead-letter to Postgres. Mixpanel forwarder is fully decoupled from request path.
- **Pwned Passwords** — k-anonymity API on sign-up / password change. 500ms timeout, 1 retry. Fail-open per PRD; the skip is logged with `pwned_check_skipped=true` and the daily ops review catches anomalies.
- **AWS SES** — SDK calls from Link API for invite emails and from Account API for verify / reset emails. Send failures are retried 3× in-process; persistent failure surfaces per PRD's per-context UX.
- **Google Safe Browsing v4** — Link API calls on link create. 800ms timeout, fail-open per PRD. No retry on timeout (latency budget).
- **MaxMind GeoLite2** — local `.mmdb` distributed to every Cloudflare Worker POP via the deploy pipeline. Twice-weekly DB pull job (CodeBuild) signs the mmdb and uploads to a worker-secret binding. Stale > 30 days → country falls back to `Unknown`; > 21 days → ops alert.

## Observability

- **Logging.** Structured JSON logs to AWS CloudWatch via the ECS log driver and the Cloudflare Workers Logpush integration. Every log line carries `request_id`, `workspace_id` (when known), and `member_id` (when known).
- **Metrics.** CloudWatch metrics emitted by each service: request rate, error rate, p50/p95/p99 latency. Custom metrics for `redirect_p95`, `click_pipeline_depth`, `pwned_check_skipped_count`, `mail_send_failures`.
- **Tracing.** AWS X-Ray on the regional services. Trace context is propagated from edge → SQS → consumer via the `X-Amzn-Trace-Id` message attribute.
- **Error tracking.** Sentry for both the Next.js dashboard (client + SSR) and the FastAPI backend. Each release is tagged.
- **Alerts.** PagerDuty rotation. Pages on: redirect p95 > 150ms for 5 min, redirect error rate > 1% for 5 min, click pipeline depth > 100k, mail-events DLQ depth > 0, mixpanel_dead_letter inserts > 100/hour, DB primary replication lag > 60s, KMS errors any.

## Scaling

- **Redirect.** Cloudflare Workers — no capacity planning beyond paying for the request volume. The Worker is stateless; the `.mmdb` is the only large local asset and is shipped at deploy.
- **Link API and Dashboard.** ECS Fargate behind an ALB. Autoscale on CPU > 60% and request count per target. Concrete v1 capacity target: sustain 200 link-create RPS with bursts to 1000. (PRD does not state a peak; this number was chosen as 10× expected steady-state at month-6 paid traffic.)
- **Click pipeline.** ECS Fargate autoscaled on SQS queue depth. Target depth ≤ 1000 messages, autoscale to ≤ 50 consumer tasks.
- **Database.** Single primary; read traffic offloaded to replicas. Vertical scale path to `db.r6g.4xlarge` (current `db.r6g.large` in v1) before considering sharding.

## Rate limiting and abuse

- **Link creation:** Redis-backed sliding window. 60 / minute / user per PRD.
- **Login:** 5 failed attempts / 15 min / email per PRD. Counter and lockout end-time both in Redis.
- **Redirect path:** Cloudflare WAF rules — per-IP global rate-limit (1000 req/s/IP) and bot-traffic mitigation rules at the edge. Per-short-code rate limiting is not implemented in v1; if a viral link causes hot-key pressure, the Worker's regional cache absorbs it. *(Note: PRD Gate 3 finding flagged this; v1 accepts the edge / WAF coverage.)*

## Caching

- **Edge.** Cloudflare's regional cache stores `short_code → destination_url` lookups with a 5-min TTL. Cache key includes `deleted_at` is null; deletes purge via Cloudflare's API. Cache miss → fetch from Link API → return 302 and populate.
- **Application.** None in v1. Workspace membership, role, and link list rely on Postgres + index quality. Revisit if dashboard p95 exceeds target.

## Environments

| Environment | Purpose | Hosts | Data |
|---|---|---|---|
| `dev` | Engineer-local | Docker Compose | Seeded test data |
| `staging` | Pre-prod integration | Same shape as prod, smaller capacity | Anonymized subset of prod (daily refresh) |
| `prod` | Live | us-east-1 | Real data |

All environments share the same migration tooling; promotions are migration-first.

## CI/CD

- **CI.** GitHub Actions. Per-PR: type check (Mypy + tsc), lint (Ruff, ESLint), unit + integration tests, OpenAPI diff, Alembic check (no naked DDL, no destructive operations without explicit annotation).
- **Deploys.** Trunk-based. Merge to `main` → CI builds container images → `staging` deploy is automatic → manual promotion to `prod` via a GitHub Actions workflow gated on approval. Edge Worker has the same shape but is deployed via Cloudflare's API.

## Frontend/backend contract

- **Transport.** REST over HTTPS with JSON bodies.
- **Schema source of truth.** FastAPI's auto-generated OpenAPI document. The Next.js dashboard consumes generated TypeScript types via `openapi-typescript` on every dashboard deploy.
- **Auth transport.** Session cookie (HTTP-only). The dashboard sends fetch requests with `credentials: 'include'`; CSRF tokens are required on mutating endpoints (double-submit cookie pattern).
- **Error envelope.** Every 4xx/5xx response is JSON: `{ "error": { "code": "<machine-code>", "message": "<human>" } }`.

## Compliance

PRD does not name a specific compliance regime (GDPR, HIPAA, etc.) as a hard requirement; the only PII handled is email addresses (encrypted at rest per PRD NFR). GDPR-style user-data export and delete are explicitly out of scope per PRD (handled manually via support). The architecture preserves the *capability* to add automated export/delete later — single `workspace_id` join out from USER reaches all owned data, and `email_search_hash` allows targeted lookup without holding plaintext.

## Open questions

These items are flagged for follow-up before architectural finalization. They surfaced from the PRD's remaining Gate 3 warnings and from architectural choices that the PRD does not constrain:

- Workspace deletion lifecycle (PRD Gate 3 — needs PRD decision before architecture can declare a path).
- Whether email_search_hash key rotation needs to be online-only (rotation would re-hash every email — coordinate with KMS DEK rotation cadence).
- Multi-AZ posture for ElastiCache in v1 vs accept downside on cache cold-starts during AZ outage.
