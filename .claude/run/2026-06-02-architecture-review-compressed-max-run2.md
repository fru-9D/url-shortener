# Architecture Review — Compressed Agent — Max Effort — Run 2
**Date:** 2026-06-02
**Agent:** architecture-review-compressed
**Effort:** max
**Project:** Snip (url-shortener)

---

## STEP C — Summary Verdict

```json
{
  "domain": "architecture-review",
  "gate1_count": 4,
  "gate2_count": 0,
  "gate3_count": 5,
  "verdict": "FAIL_CRITICAL"
}
```

---

## Gate 1 — Critical (4)

| ID | Rule | Finding |
|---|---|---|
| ARCH-005-a | ARCH-005 | SAST tooling mandated by PRD NFR ("OWASP Top-10 2021 baseline, verified by SAST tooling on every release") is absent from the declared CI pipeline (type check, lint, tests, OpenAPI diff, Alembic check — no SAST scanner). |
| ARCH-005-b | ARCH-005 | PRD §Click pipeline requires redirect service to "fall back to local durable buffering" when SQS is unavailable. Cloudflare Workers are stateless V8 isolates with no local persistent storage. Architecture never declares how this is implemented (no Durable Objects, no secondary queue, no local ring buffer). PRD and architecture are in direct contradiction. |
| ARCH-005-c | ARCH-005 | Architecture declares pg_cron for 13-month CLICK retention but is entirely silent on the required 30-day hard-delete scheduled job for soft-deleted LINKs ("Deleted links: soft-delete for 30 days, then hard-delete" — explicit PRD data-retention requirement). |
| ARCH-003-a | ARCH-003 | Redis (ElastiCache) is the authoritative session store. Architecture's backup/recovery section covers only Postgres. No Redis persistence configuration (RDB/AOF), no ElastiCache backup, and no session-loss posture declared. Given session availability directly determines dashboard availability (≥ 99.5% NFR), this is a business-critical data backup gap. |

---

## Gate 3 — Warnings (5)

| ID | Rule | Finding |
|---|---|---|
| ARCH-013-a | ARCH-013 | Password-reset initiation (POST /v1/auth/reset) and signup (POST /v1/auth/signup) endpoints have no declared rate-limiting policy. Both are public unauthenticated endpoints that can be abused for email enumeration and SES quota exhaustion. Architecture only declares rate limits for login and link creation. |
| ARCH-028-a | ARCH-028 | Connection pool math covers Link API only (50 tasks × 15 = 750 connections). Three additional Postgres-connected ECS services (click consumer, Mixpanel forwarder, mail worker) are omitted. At even modest pool sizes, aggregate could exceed db.r6g.large max_connections ≈ 1000. |
| ARCH-029-a | ARCH-029 | Mixpanel forwarder consumes SQS at-least-once with 3× retries but no idempotency mechanism declared. If Mixpanel accepts an event but the ACK is lost, the event is re-delivered and duplicate analytics events appear in Mixpanel. Architecture is silent on whether `$insert_id` deduplication is used. |
| ARCH-032-a | ARCH-032 | `request_id` is named in log lines and error envelope, and X-Amzn-Trace-Id propagates via SQS. However: (1) the component generating `request_id` is never declared; (2) propagation of `request_id` to outbound HTTP calls (Safe Browsing, Pwned Passwords, SES SDK, Mixpanel /track) is not addressed. Two of three ARCH-032 prongs are unmet. |
| ARCH-017-a | ARCH-017 | Staging uses "anonymized subset of prod (daily refresh)" but the anonymization pipeline is not described. Given email_ciphertext uses KMS-managed per-row DEKs and email_search_hash is a stable keyed HMAC, naive data copying brings production-encrypted PII into staging. KMS key separation between prod and staging is not declared. |

---

## STEP A-bis — Dismissal Table (all non-flagged rules)

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ARCH-001 | Dismissed | HTTP-only Secure SameSite=Lax cookies, HMAC-signed session id, Redis-backed session, session_version revocation, RBAC two-role, FastAPI dependency. |
| ARCH-002 | Dismissed | AWS Secrets Manager, ECS integration, Workers Secrets binding, rotation schedule with overlap. |
| ARCH-003 | **Flagged** | Postgres backup fully declared. Redis session store backup gap flagged. |
| ARCH-004 | Dismissed | PRD names no hard compliance regime. GDPR self-serve out of scope. |
| ARCH-005 | **Flagged** (×3) | SAST absence, Cloudflare Worker durable buffer, LINK hard-delete scheduled job. |
| ARCH-006 | Dismissed | Structured JSON logs, CloudWatch metrics, X-Ray tracing, Sentry, PagerDuty. All four pillars. |
| ARCH-007 | Dismissed | All long-running work (click pipeline, Mixpanel, mail events) behind SQS queues. |
| ARCH-008 | Dismissed | Cloudflare Workers stateless, ECS Fargate autoscale with concrete RPS targets, DB vertical scale path, click pipeline queue-depth autoscale. |
| ARCH-009 | Dismissed | All five external APIs have timeout, retry, fallback, or fail-open strategies. |
| ARCH-010 | Dismissed | Base repository auto-AND on workspace_id. |
| ARCH-011 | Dismissed | Alembic, same-PR migration, CI fresh-DB run, manual prod gate, forward-compat requirement. |
| ARCH-012 | Dismissed | All major tech choices trace to named constraints. Three-tier split rationale meets adequacy threshold. |
| ARCH-013 | **Flagged** | Login and link-create declared. Password-reset and signup absent. |
| ARCH-014 | Dismissed | Edge cache declared. Application cache "None in v1" explicitly stated. |
| ARCH-015 | Dismissed | dev/staging/prod declared with purpose, hosts, data. |
| ARCH-016 | Dismissed | GitHub Actions per-PR gates, trunk-based deploys, manual prod approval. |
| ARCH-017 | **Flagged** | Staging anonymization pipeline undescribed; PII/KMS key separation unaddressed. |
| ARCH-018 | Dismissed | REST/JSON, OpenAPI source-of-truth, session cookie auth, CSRF, error envelope. |
| ARCH-019 | Dismissed | CORS allowed origins, credentials, methods, CORSMiddleware. |
| ARCH-020 | Dismissed | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP per surface. |
| ARCH-021 | Dismissed | HttpOnly, Secure, SameSite=Lax, 30-day absolute, 7-day idle. |
| ARCH-022 | Dismissed | /v1/ prefix, 90-day deprecation, Deprecation/Sunset headers. |
| ARCH-023 | Dismissed | /healthz liveness and /readyz readiness with ALB config. |
| ARCH-024 | Dismissed | 1 MB JSON body limit via FastAPI middleware and ALB. |
| ARCH-025 | Dismissed | Pydantic BaseModel, explicit response_model, Update<X> schemas. |
| ARCH-026 | Dismissed | Global FastAPI exception handler, canonical JSON error envelope, no stack traces in responses. |
| ARCH-028 | **Flagged** | Link API pool math declared. Consumer services omitted. |
| ARCH-029 | **Flagged** | HTTP POST idempotency declared. Mixpanel forwarder deduplication absent. |
| ARCH-030 | Dismissed | Cursor-based pagination, default 50, max 200, opaque cursor. |
| ARCH-031 | Dismissed | Single unit-of-work per request, SQS publish post-commit, atomic member removal UPDATE. |
| ARCH-032 | **Flagged** | request_id named. Generation point and outbound-call propagation absent. |
| ARCH-033 | Dismissed | SIGTERM two-phase drain, 30s HTTP, 90s SQS visibility, 120s stopTimeout. |
| ARCH-034 | Dismissed | GZip ≥ 1KB, Brotli on br, Cloudflare Brotli, analytics/list responses named. |
