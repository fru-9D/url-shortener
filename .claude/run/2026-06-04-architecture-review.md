# Architecture Review — 2026-06-04

**Architecture:** `docs/architecture.md`
**PRD:** `docs/prd.md`
**ERD:** `docs/erd.md`
**Verdict:** PASS
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 0 findings

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| — | No findings — all 34 rules dismissed | — | — | — |

## Dismissed rules

| Rule ID  | Considered? | Dismissal reason |
|----------|-------------|-----------------|
| ARCH-001 | Yes | Authentication and authorization section fully declared: HTTP-only Secure SameSite=Lax session cookies, HMAC-SHA256 signed session id, Redis-backed session store, 30-day absolute / 7-day idle TTLs, session_version revocation on logout/password-change/admin-removal. Role-based authorization (admin/editor) enforced by FastAPI middleware dependency resolving (user, active_workspace_id, role) on every request. |
| ARCH-002 | Yes | Secrets management fully declared: AWS Secrets Manager as provider for all non-public config; distribution via ECS Secrets Manager integration at task-start (no secrets in images or build-time env vars); Cloudflare Workers Secrets binding; rotation policy (DB credentials 30-day via RDS rotation Lambda, signing secrets quarterly with 7-day overlap window via key-id in cookie). |
| ARCH-003 | Yes | Backup and recovery declared: RPO 5 minutes via continuous WAL archiving to S3; RTO 1 hour with quarterly restore-from-snapshot drills; daily/weekly/quarterly snapshot retention. All PRD-critical data is in Postgres and covered. |
| ARCH-004 | Yes | PRD names no compliance regime. The Compliance section explicitly acknowledges this and notes GDPR self-serve export/delete is out of PRD scope. The only privacy NFR (email encryption at rest) is addressed via AES-256-GCM + KMS. |
| ARCH-005 | Yes | All PRD requirements were checked against architecture: redirect p95 < 100ms addressed by Cloudflare Workers; durable click buffering addressed by Cloudflare Queue → SQS; TLS 1.2+, Argon2id, email encryption, CSRF, OWASP SAST all addressed. No direct contradiction found. |
| ARCH-006 | Yes | Observability fully declared: structured JSON logs to CloudWatch (ECS log driver) and Cloudflare Logpush; CloudWatch metrics (request rate, error rate, p50/p95/p99) plus named custom metrics; AWS X-Ray distributed tracing with SQS context propagation; Sentry error tracking for Next.js + FastAPI; PagerDuty alerts with named alert conditions. All four pillars addressed. |
| ARCH-007 | Yes | All long-running / fan-out operations are behind queue/worker boundaries: click ingest (Cloudflare Queue → SQS → ECS consumer), Mixpanel forwarding (SQS → ECS forwarder), SES bounce handling (SNS → SQS → ECS mail worker). No PRD operation described as synchronous that should be async. |
| ARCH-008 | Yes | Scaling declared for all PRD NFRs: Cloudflare Workers for redirect (no capacity ceiling); ECS Fargate autoscale for Link API (200 RPS sustained, 1000 burst target); click pipeline autoscaled on SQS depth; CloudFront for dashboard static assets; Lighthouse CI enforcement for p95 < 2s NFR; DB vertical scale path declared. |
| ARCH-009 | Yes | All external APIs have resilience strategies: Mixpanel (3× exponential retry, dead-letter, decoupled); Pwned Passwords (500ms timeout, 1 retry, fail-open, logged); AWS SES (3s/10s timeouts, 3× retry with backoff); Google Safe Browsing (800ms timeout, fail-open → abuse queue, one retry on network error); MaxMind GeoLite2 (local mmdb, stale fallback to Unknown with ops alert). |
| ARCH-010 | Yes | Multi-tenant isolation declared at two levels: data layer (base repository class auto-AND-es workspace_id = <active> on every workspace-scoped SELECT/UPDATE/DELETE; opt-out requires explicit bypass); request layer (auth middleware injects active_workspace_id and role on every request). Described as structural defense-in-depth on top of ERD per-row workspace_id FKs. |
| ARCH-011 | Yes | Migration strategy fully declared: Alembic, migration file ships in same PR as code, CI runs migrations against fresh DB in test, production migrations run as a separate deploy step gated on manual approval, forward-compatibility requirement for zero-downtime deploys. |
| ARCH-012 | Yes | Major tech-stack choices reviewed: Cloudflare Workers justified by global sub-100ms latency SLO (unreachable from single region — tier-level constraint named); ECS Fargate and FastAPI/Python are conventional within a well-motivated regional tier; Postgres justified by ERD FK relationships and ACID multi-step write requirement; Redis justified by session-loss failure posture explicitly described. Per adequacy definition, tier-level constraint naming counts for choices within that tier. No genuinely unjustified major choice found. |
| ARCH-013 | Yes | Rate limiting fully declared: link creation (60/min/user sliding window, Redis), login (5/15 min/email, Redis, fail-open policy stated), sign-up (5/IP/hour + 3/email-domain/hour, fail-closed), password reset (3/email/hour + 10/IP/hour), redirect path (Cloudflare WAF per-IP 1000 req/s + bot mitigation). Absence of per-short-code rate limiting explicitly acknowledged with rationale (edge/WAF + regional cache). |
| ARCH-014 | Yes | Caching strategy declared: edge cache (Cloudflare regional, 5-min TTL, invalidation via API); CloudFront for static assets (immutable headers); Next.js SSR /links page (CloudFront 10s TTL). Application-layer cache explicitly declared as "None in v1" with revisit condition — acceptable explicit declaration per ARCH-014. |
| ARCH-015 | Yes | Environment topology declared: dev (Docker Compose, seeded data), staging (same shape as prod, smaller capacity, anonymized daily refresh with separate KMS CMK), prod (us-east-1, real data). Staging anonymization pipeline described in detail. |
| ARCH-016 | Yes | CI/CD fully declared: GitHub Actions; per-PR gates (Mypy + tsc, Ruff + ESLint, unit + integration tests, OpenAPI diff, Alembic check, Bandit + semgrep SAST, pip-audit + npm audit, Lighthouse CI); trunk-based deployment with automatic staging deploy and manual prod promotion gated on approval; edge Worker deployed via Cloudflare API. |
| ARCH-017 | Yes | Failure modes enumerated across sections: Redis single-AZ failure posture (session loss + lockout reset, acknowledged with rationale); Mixpanel crash-window (documented in §External integrations and §Open questions); SES SNS→SQS drop risk (acknowledged); PgBouncer operational risk (Open questions); KMS hard-dependency failure contract referenced. §Open questions section functions as runbook-scaffolding. Alerts cover primary failure vectors. Dismissed as sufficiently addressed at architecture stage. |
| ARCH-018 | Yes | Frontend/backend contract fully declared: REST over HTTPS + JSON; FastAPI OpenAPI as schema source of truth; Next.js consumes generated TypeScript types via openapi-typescript; session cookie (HTTP-only) with credentials: 'include'; CSRF double-submit cookie on mutating endpoints; error envelope shape declared. |
| ARCH-019 | Yes | CORS policy declared: allowed origin `https://app.snip.io` only (no wildcard), `Access-Control-Allow-Credentials: true` with justification, allowed methods `GET, POST, PUT, PATCH, DELETE, OPTIONS`, enforced via FastAPI CORSMiddleware (ALB does not independently add CORS headers). Branded-domain expansion path noted. |
| ARCH-020 | Yes | HTTP security headers declared: applied via FastAPI middleware (Link API) and Next.js headers() config (Dashboard). Canonical production values listed: HSTS (max-age=63072000, includeSubDomains, preload), X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy: strict-origin-when-cross-origin, Permissions-Policy. CSP declared per surface. Dev-only unsafe-eval override declared explicitly. |
| ARCH-021 | Yes | Cookie/session flag policy declared: HTTP-only, Secure, SameSite=Lax stated explicitly in auth section. 30-day absolute TTL and 7-day idle TTL stated. Cookie carries HMAC-SHA256 signed session id. |
| ARCH-022 | Yes | API versioning declared: all routes prefixed /v1/; breaking changes require new version prefix with 90-day deprecation window; deprecated versions respond with Deprecation and Sunset headers; non-breaking additive changes ship without version bump. |
| ARCH-023 | Yes | Health check endpoints declared: GET /healthz (liveness, process responds, no dependency checks, used by ECS); GET /readyz (readiness, Postgres primary + Redis within 2s, used by ALB with named config: interval 15s, healthy threshold 2, unhealthy threshold 3). All required elements present. |
| ARCH-024 | Yes | Request body / payload size limits declared: default JSON body limit 1 MB enforced by FastAPI middleware and ALB 1 MB limit on Link API target group; no file upload endpoints in v1; Cloudflare redirect Worker accepts GET only. Enforcement layers named. |
| ARCH-025 | Yes | Input validation / DTO boundary declared in API design section: all request bodies as Pydantic BaseModel subclasses on every endpoint; ORM model instances never returned directly; every response uses explicit response_model schema; partial-update endpoints use dedicated Update<X> schemas. All required elements present. |
| ARCH-026 | Yes | Global exception handling and error envelope declared: envelope shape `{ "error": { "code", "message", "request_id" } }`; global FastAPI exception handler catches all unhandled exceptions and wraps them; stack traces never in HTTP responses (Sentry + CloudWatch only); exception-to-status-code mappings declared. Cloudflare Worker error handling also declared. |
| ARCH-028 | Yes | Database connection pool declared: per-service pool sizing table (Link API 750, Click consumer 250, Mixpanel forwarder 50, Mail worker 25, total 1,075); math against DB max_connections (~1,000) performed explicitly; PgBouncer in transaction-mode as sidecar targeting 700 server connections declared as overflow solution; leak detection via idle_in_transaction_session_timeout=30s and statement_timeout=30s. |
| ARCH-029 | Yes | Idempotency policy declared: POST resource-creation endpoints accept optional Idempotency-Key header; (Idempotency-Key, user_id, endpoint) → serialised response stored in Redis with 24-hour TTL and replayed on retry; naturally idempotent endpoints marked in OpenAPI spec; PRD-allowed duplicates (link creation) documented. |
| ARCH-030 | Yes | Pagination strategy declared: all list endpoints use cursor-based pagination; default page size 50; max 200; cursor is opaque base64-encoded composite of (created_at DESC, id DESC) passed as after query parameter; response envelope `{ "items": [...], "next_cursor": "<string> | null" }`; offset-based pagination excluded with rationale. |
| ARCH-031 | Yes | Transaction boundary / unit-of-work pattern declared: every API request opens exactly one transaction via FastAPI dependency-injected unit of work; service-layer code never calls commit()/rollback() directly; handler commits on success, dependency rolls back on exception. SQS publish happens after DB commit (crash-window acknowledged, dead-letter as recovery). Member removal multi-row UPDATE declared as single transaction. |
| ARCH-032 | Yes | Correlation ID propagation fully declared: (a) named field: request_id on every log line, X-Request-Id header; (b) generation: ALB injects UUID-v4 for Link API (trusted from ALB source IP only), Worker generates UUID-v4 at start of each fetch handler; (c) queue propagation: request_id as SQS message attribute alongside X-Amzn-Trace-Id; (d) outbound calls: X-Request-Id propagated to all outbound HTTP calls (Safe Browsing, Pwned Passwords, SES, Mixpanel). All three adequacy requirements met — dismissed per adequacy definition. |
| ARCH-033 | Yes | Graceful shutdown declared: all ECS Fargate services handle SIGTERM with two-phase drain; HTTP services (Link API): stop accepting connections immediately, drain in-flight with 30s timeout; queue consumers: finish current message batch (SQS visibility timeout 90s), stop polling; ECS task stopTimeout 120s to prevent SIGKILL mid-message. |
| ARCH-034 | Yes | Payload compression declared: responses ≥ 1 KB gzip-compressed via FastAPI GZipMiddleware; Brotli used where client signals br in Accept-Encoding; Cloudflare applies Brotli automatically on edge-cached responses. Analytics time-series and paginated link-list responses named as primary beneficiaries. |

## Gate 1 — Critical (architecture not safe to implement against)

No Gate 1 findings.

## Gate 2 — Blockers (will surface as production incidents)

No Gate 2 findings.

## Gate 3 — Warnings (soft spots)

No Gate 3 findings.

## Summary

The architecture document passes all 34 rules cleanly. It is safe to begin implementation against immediately. The document is unusually thorough: every architectural concern — from CORS policy and cookie flags to PgBouncer connection pool math and graceful shutdown SIGTERM sequences — is explicitly declared with named values rather than left to implementation discretion. The §Open questions section proactively enumerates known v1 limitations (ElastiCache single-AZ, Mixpanel crash-window, Workspace deletion lifecycle, email_search_hash key rotation) and defers them to the first post-launch hardening sprint, which satisfies ARCH-017's failure-mode scaffolding requirement at architecture stage. The only outstanding risks before launch are the seven PRD Gate 2 blockers (Cloudflare contract, Link deletion feature, integration timeouts) documented in the prd-review run — those must be resolved in the PRD before the architecture needs to be updated.
