# Architecture Review — Compressed Agent — Medium Effort — Run 2
**Date:** 2026-06-02
**Agent:** architecture-review-compressed
**Effort:** medium
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| Architecture §CI/CD; PRD NFR §Security | PRD: "OWASP Top-10 2021 baseline, verified by SAST tooling on every release." CI/CD lists Mypy, tsc, Ruff, ESLint, unit/integration tests, OpenAPI diff, Alembic check. No SAST tool (Bandit, Semgrep, CodeQL, Snyk) named. Hard PRD NFR not satisfied by architecture. | ARCH-004 | G1 | Critical |
| Architecture — no section; PRD §Click pipeline "Failure" | PRD: "redirect service falls back to local durable buffering and retries when the queue recovers." Cloudflare Workers are stateless isolates with no persistent local storage. No mechanism declared (Cloudflare Durable Objects, Workers KV, secondary queue, in-memory with bounded loss). PRD durability guarantee has no architectural implementation. | ARCH-005 | G1 | Critical |
| Architecture §Frontend/backend contract — CORS | CORS allowlist includes "any branded-domain origins registered per Workspace." PRD §Out of scope explicitly excludes "Custom branded domains" from v1. Architecture declares a CORS policy for a feature that does not exist, which either silently includes out-of-scope work or creates a permissive default with no registered origins in practice. | ARCH-005 | G1 | Critical |
| Architecture — no section; PRD NFR §Security | PRD: "TLS 1.2+ everywhere." Architecture never declares a TLS version floor or where it is enforced (Cloudflare TLS settings, ALB security policy, ElastiCache in-transit, RDS TLS). "Everywhere" in the PRD names this as a hard NFR but the architecture provides no policy. | ARCH-005 | G1 | Critical |
| Architecture §Caching; PRD NFR §Performance | PRD hard NFR: dashboard p95 < 2s on mid-tier mobile 4G. Application caching: "None in v1. Revisit if dashboard p95 exceeds target." No analysis presented that target is achievable without caching. Deferred with no evidence. | ARCH-014 | G3 | Warning |
| Architecture §API design / Idempotency | Idempotency section covers only HTTP POST endpoints via Idempotency-Key headers. SQS click consumer dedup mechanism — whether ON CONFLICT DO NOTHING, SELECT-before-INSERT, Redis seen-set, or other — is never declared. Code reviewers have no policy to verify. | ARCH-029 | G3 | Warning |
| Architecture §Data / Transaction boundaries | Architecture explicitly acknowledges crash window between DB commit and SQS publish for link-create Mixpanel event, then says "Mixpanel dead-letter store as the recovery path." But if the crash occurs before the SQS message is ever emitted, no forwarder retry cycle fires and no dead-letter row is ever created. The recovery path does not cover the stated failure mode. | ARCH-031 | G3 | Warning |
| Architecture §Observability | Logs carry `request_id` but: (a) the named HTTP header carrying the correlation ID on inbound Link API requests is not declared; (b) where the ID is generated for requests originating at the Cloudflare Worker is not stated; (c) propagation into outbound SES and Pwned Passwords calls is not addressed. X-Ray covers the SQS leg only. | ARCH-032 | G3 | Warning |

---

## STEP A-bis — Dismissal Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ARCH-001 | Dismissed | Auth: HTTP-only Secure SameSite=Lax cookie, HMAC-signed session ID, Redis-backed session, session_version revocation, RBAC two-role, FastAPI dependency. |
| ARCH-002 | Dismissed | Secrets: AWS Secrets Manager, ECS integration, Workers Secrets binding, rotation schedule with overlap window. |
| ARCH-003 | Dismissed | Backup: RPO 5 min WAL archiving, RTO 1 hour quarterly drills, tiered snapshot retention. |
| ARCH-004 (GDPR/compliance) | Dismissed | PRD names no hard compliance regime. Architecture §Compliance acknowledges and documents manual GDPR path. SAST gap filed separately. |
| ARCH-005 (non-TLS/CORS/buffer) | Dismissed | See specific findings above for TLS, CORS, durable buffer. No other PRD contradictions found. |
| ARCH-006 | Dismissed | Structured JSON logs (CloudWatch + Logpush), CloudWatch metrics + custom metrics, AWS X-Ray tracing, Sentry, PagerDuty alerts. |
| ARCH-007 | Dismissed | Click pipeline, Mixpanel forwarder, mail-events all behind SQS queues. |
| ARCH-008 | Dismissed | Cloudflare Workers, ECS Fargate autoscale, click pipeline autoscale on queue depth, DB vertical scale path. |
| ARCH-009 | Dismissed | All five external APIs have timeout, retry, and fail-open/fail-closed. |
| ARCH-010 | Dismissed | Base repository class AND'es workspace_id; auth middleware injects workspace context. |
| ARCH-011 | Dismissed | Alembic, forward-compat, CI validation, manual prod gate. |
| ARCH-012 | Dismissed | Tier-level rationale covers choices. Per-technology ADRs not required. |
| ARCH-013 | Dismissed | Login (5/15min/email Redis), link-create (60/min/user Redis), redirect (Cloudflare WAF per-IP). Note: signup/password-reset endpoints lack explicit rate-limit declarations but PRD doesn't set targets for them; run 1 found this as G3 but at medium effort the WAF coverage is an implicit defense. |
| ARCH-014 | Flagged | Dashboard p95 target unvalidated without caching analysis. |
| ARCH-015 | Dismissed | dev/staging/prod with purpose, host shape, and data policy. |
| ARCH-016 | Dismissed | GitHub Actions per-PR gates. SAST absence captured under ARCH-004. |
| ARCH-017 | Dismissed | Key failure modes addressed: DB unreachable (503), click pipeline unavailable (durable buffer — gap noted in ARCH-005), Mixpanel exhaustion (dead-letter), SES failure (per-context UX). Architecture is not purely happy-path. |
| ARCH-018 | Dismissed | REST/JSON, OpenAPI source-of-truth, session cookie auth, CSRF, versioning, CORS, security headers, body limits, error envelope all declared. |
| ARCH-019 | Dismissed | CORS: allowed origins, no wildcard, credentials true, methods enumerated, FastAPI CORSMiddleware. Branded-domain inconsistency filed under ARCH-005. |
| ARCH-020 | Dismissed | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP per surface with canonical values. |
| ARCH-021 | Dismissed | HttpOnly, Secure, SameSite=Lax, 30-day absolute, 7-day idle. CSRF double-submit declared. |
| ARCH-022 | Dismissed | /v1/ prefix, 90-day deprecation window, Deprecation/Sunset headers, additive-change policy. |
| ARCH-023 | Dismissed | /healthz liveness and /readyz readiness with ALB config parameters. |
| ARCH-024 | Dismissed | 1 MB JSON body limit via FastAPI middleware and ALB. |
| ARCH-025 | Dismissed | Pydantic BaseModel on every endpoint, explicit response_model, Update<X> schemas. |
| ARCH-026 | Dismissed | Global FastAPI exception handler, canonical JSON error envelope, no stack traces, exception-to-status mappings. |
| ARCH-028 | Dismissed | pool_size=10, max_overflow=5 per task; sizing math against db.r6g.large; leak detection via Postgres timeouts. |
| ARCH-029 | Flagged | SQS consumer dedup mechanism undeclared. |
| ARCH-030 | Dismissed | Cursor-based pagination, default 50, max 200, opaque cursor, response envelope. |
| ARCH-031 | Flagged | Commit/publish crash window acknowledged; recovery path does not cover the failure mode it describes. |
| ARCH-032 | Flagged | HTTP correlation-id header name and generation point for inbound requests and outbound calls not declared. |
| ARCH-033 | Dismissed | SIGTERM two-phase drain: HTTP services 30s, queue consumers SQS 90s + ECS stopTimeout 120s. |
| ARCH-034 | Dismissed | GZipMiddleware ≥1 KB, Brotli on br, Cloudflare Brotli; analytics and list responses named. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-004",
    "gate": 1,
    "severity": "critical",
    "title": "SAST tooling required by PRD NFR absent from CI pipeline",
    "snippet": "Per-PR: type check (Mypy + tsc), lint (Ruff, ESLint), unit + integration tests, OpenAPI diff, Alembic check",
    "prd_quote": "OWASP Top-10 2021 baseline, verified by SAST tooling on every release.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-005",
    "gate": 1,
    "severity": "critical",
    "title": "PRD 'local durable buffering' for click events has no viable mechanism on stateless Cloudflare Workers",
    "snippet": "",
    "prd_quote": "If the queue is unavailable at emit time, the redirect service falls back to local durable buffering and retries when the queue recovers.",
    "effort": "medium"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-005",
    "gate": 1,
    "severity": "critical",
    "title": "CORS allowlist includes branded domains explicitly excluded from v1 scope",
    "snippet": "Allowed origins: `https://app.snip.io` and any branded-domain origins registered per Workspace.",
    "prd_quote": "Custom branded domains. (explicitly excluded from v1)",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-005",
    "gate": 1,
    "severity": "critical",
    "title": "TLS 1.2+ floor declared in PRD NFR but absent from architecture",
    "snippet": "",
    "prd_quote": "TLS 1.2+ everywhere.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-014",
    "gate": 3,
    "severity": "warning",
    "title": "Application cache deferred with no performance argument for dashboard p95 target",
    "snippet": "Application. None in v1. Revisit if dashboard p95 exceeds target.",
    "prd_quote": "dashboard initial-render p95 < 2s on mid-tier mobile over 4G",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-029",
    "gate": 3,
    "severity": "warning",
    "title": "SQS click consumer idempotency enforcement mechanism not declared",
    "snippet": "",
    "prd_quote": "The ingest consumer is idempotent on (link_id, clicked_at).",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-031",
    "gate": 3,
    "severity": "warning",
    "title": "Acknowledged publish-after-commit crash window has a recovery path that does not cover the failure mode",
    "snippet": "a crash between commit and publish loses the event, with the Mixpanel dead-letter store as the recovery path.",
    "effort": "medium"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-032",
    "gate": 3,
    "severity": "warning",
    "title": "HTTP correlation-id header name and generation point not declared for inbound requests and outbound calls",
    "snippet": "Every log line carries `request_id`",
    "effort": "low"
  }
]
```

---

## STEP C — Summary Verdict

```json
{
  "domain": "architecture-review",
  "gate1_count": 4,
  "gate2_count": 0,
  "gate3_count": 4,
  "verdict": "FAIL_CRITICAL",
  "note": "Four Gate 1 findings: SAST absent from CI, Cloudflare Worker stateless/durable-buffer contradiction, CORS branded-domain out-of-scope inconsistency, TLS 1.2+ floor undeclared. Four Gate 3 warnings: dashboard p95 unvalidated without caching, SQS consumer dedup mechanism undeclared, publish-after-commit recovery path incorrect, HTTP correlation-id header undeclared."
}
```
