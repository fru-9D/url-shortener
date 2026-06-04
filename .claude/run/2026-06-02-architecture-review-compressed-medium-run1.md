# Architecture Review — Compressed Agent — Medium Effort — Run 1
**Date:** 2026-06-02
**Agent:** architecture-review-compressed
**Effort:** medium
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| Architecture §CI/CD; PRD NFR §Security | PRD requires "OWASP Top-10 2021 baseline, verified by SAST tooling on every release." The CI pipeline declares type-check, lint, unit/integration tests, OpenAPI diff, and Alembic check but names no SAST tool (Semgrep, Bandit, CodeQL, Snyk). The security control is structurally absent. | ARCH-005 | G1 | Critical |
| Architecture — no section; PRD §Click pipeline "Failure" | PRD states: "If the queue is unavailable at emit time, the redirect service falls back to local durable buffering and retries when the queue recovers." The redirect service runs on Cloudflare Workers, which are stateless with no persistent local storage. No mechanism (Cloudflare Queues, Durable Objects, graceful degradation) is declared. The PRD-required failure behavior is architecturally impossible on the chosen platform as described. | ARCH-005 | G1 | Critical |
| Architecture §Caching; PRD NFR §Performance | PRD hard NFR: dashboard p95 < 2s on mid-tier mobile 4G. Architecture declares no application-level caching and defers it to a post-breach revisit. No analysis demonstrates the target is achievable via index quality alone. NFR left unvalidated at architecture stage. | ARCH-017 | G3 | Warning |
| Architecture §Rate limiting and abuse | Architecture declares rate limits for login (5/15min) and link-create (60/min) but is silent on signup and password-reset-request endpoints — common targets for credential-stuffing, enumeration, and SES-cost abuse. | ARCH-013 | G3 | Warning |

---

## STEP A-bis — Dismissal Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ARCH-001 | Dismissed | Auth fully declared: HMAC-signed HTTP-only cookie, Redis-backed session, session_version revocation, RBAC two-role model, FastAPI dependency. |
| ARCH-002 | Dismissed | AWS Secrets Manager, ECS integration, Workers Secrets binding, 30-day DB rotation, quarterly signing-secret rotation with overlap window. |
| ARCH-003 | Dismissed | RPO 5 min WAL archiving, RTO 1 hour with quarterly drills, tiered snapshot retention. |
| ARCH-004 | Dismissed | PRD names no hard compliance regime. Architecture §Compliance acknowledges and documents manual GDPR path. |
| ARCH-005 | Flagged (2 findings) | SAST absence (G1) and Cloudflare Worker stateless-buffering contradiction (G1). |
| ARCH-006 | Dismissed | Structured JSON logs (CloudWatch + Logpush), CloudWatch metrics with named custom metrics, AWS X-Ray tracing with SQS propagation, Sentry, PagerDuty. |
| ARCH-007 | Dismissed | Click pipeline, Mixpanel forwarder, mail-events all behind SQS queues with Fargate consumers. |
| ARCH-008 | Dismissed | Cloudflare Workers, ECS Fargate autoscale with concrete RPS targets, click pipeline autoscale on queue depth, DB vertical scale path. |
| ARCH-009 | Dismissed | All five external APIs have declared timeout, retry, and fail-open/fail-closed policies. |
| ARCH-010 | Dismissed | Base repository class AND'es workspace_id; auth middleware injects workspace context; opt-out requires explicit declaration. |
| ARCH-011 | Dismissed | Alembic, forward-compat requirement, CI validation, manual prod gate. |
| ARCH-012 | Dismissed | Tier-level rationale ("chosen for the per-tier latency and scale targets") names the driving constraint. Tier-level adequacy satisfied per rule definition. |
| ARCH-013 | Flagged | Login and link-create declared; signup and password-reset-request absent (G3). |
| ARCH-014 | Dismissed | "Application: None in v1" is explicit; the rule accepts an explicit statement. Dashboard NFR gap captured under ARCH-017. |
| ARCH-015 | Dismissed | dev/staging/prod with purpose, host shape, and data policy declared. |
| ARCH-016 | Dismissed | GitHub Actions pipeline declared with test, lint, type-check gates. SAST absence captured under ARCH-005. |
| ARCH-017 | Flagged | Dashboard p95 target unvalidated without caching analysis (G3). |
| ARCH-018 | Dismissed | REST+JSON, OpenAPI source-of-truth, generated TypeScript types, cookie auth transport, CSRF, error envelope all declared. |
| ARCH-019 | Dismissed | Allowed origins (app.snip.io), credentials true, allowed methods enumerated, FastAPI CORSMiddleware. |
| ARCH-020 | Dismissed | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, and CSP per surface with canonical values. |
| ARCH-021 | Dismissed | HttpOnly, Secure, SameSite=Lax, 30-day absolute, 7-day idle. |
| ARCH-022 | Dismissed | /v1/ prefix, 90-day deprecation window, Deprecation/Sunset headers, additive-change policy. |
| ARCH-023 | Dismissed | /healthz liveness and /readyz readiness with ALB interval, threshold config. |
| ARCH-024 | Dismissed | 1 MB JSON limit via FastAPI middleware and ALB. |
| ARCH-025 | Dismissed | Pydantic BaseModel on every endpoint, explicit response_model, Update<X> schemas. |
| ARCH-026 | Dismissed | Global FastAPI exception handler, canonical JSON error envelope, no stack traces in responses, exception-to-status mappings. |
| ARCH-028 | Dismissed | pool_size=10, max_overflow=5 per task; sizing math against db.r6g.large; Postgres session/statement timeouts. |
| ARCH-029 | Dismissed | Idempotency-Key on POST /v1/links and POST /v1/workspaces/invites; Redis 24h TTL; naturally-idempotent endpoints annotated. |
| ARCH-030 | Dismissed | Cursor-based pagination, default 50, max 200, opaque cursor, response envelope. |
| ARCH-031 | Dismissed | Unit-of-work per request, service layer never commits directly, SQS publish after DB commit, dead-letter recovery. |
| ARCH-032 | Dismissed | request_id in every log line and error envelope; X-Amzn-Trace-Id propagated from edge to SQS to consumer. All three propagation requirements met. |
| ARCH-033 | Dismissed | SIGTERM two-phase drain for HTTP (30s) and queue consumers (SQS 90s + ECS stopTimeout 120s). |
| ARCH-034 | Dismissed | GZipMiddleware ≥1 KB, Brotli on br, Cloudflare Brotli on edge; analytics and list responses named as beneficiaries. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-005",
    "gate": 1,
    "severity": "critical",
    "title": "SAST tooling required by PRD NFR is absent from CI pipeline",
    "location": "Architecture §CI/CD",
    "line": 153,
    "snippet": "Per-PR: type check (Mypy + tsc), lint (Ruff, ESLint), unit + integration tests, OpenAPI diff, Alembic check",
    "prd_passage": "OWASP Top-10 2021 baseline, verified by SAST tooling on every release.",
    "description": "The PRD names SAST tooling as a mandatory security control. The architecture's CI pipeline lists five gate types but includes no SAST tool. The control is structurally absent — code reviewers and runtime are the only remaining defenses against OWASP Top-10 class vulnerabilities.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-005",
    "gate": 1,
    "severity": "critical",
    "title": "PRD-required click-event local durable buffering is architecturally impossible on stateless Cloudflare Workers",
    "location": "Architecture — no section; PRD §Click pipeline 'Failure'",
    "line": 0,
    "snippet": "",
    "prd_passage": "If the queue is unavailable at emit time, the redirect service falls back to local durable buffering and retries when the queue recovers.",
    "description": "The architecture deploys the redirect service on Cloudflare Workers, which are stateless with no persistent local storage between invocations. No mechanism is declared to implement local durable buffering — not Cloudflare Queues, not Durable Objects, not a documented graceful degradation. Without a declared mechanism the PRD failure behaviour cannot be implemented.",
    "effort": "medium"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-017",
    "gate": 3,
    "severity": "warning",
    "title": "Dashboard p95 NFR left unvalidated — no analysis confirming target achievable without application caching",
    "location": "Architecture §Caching",
    "line": 139,
    "snippet": "Application. None in v1. Workspace membership, role, and link list rely on Postgres + index quality. Revisit if dashboard p95 exceeds target.",
    "prd_passage": "dashboard initial-render p95 < 2s on mid-tier mobile over 4G",
    "description": "The PRD sets a hard p95 dashboard NFR. The architecture explicitly declines application-level caching for v1 and defers it to a post-breach revisit. No analysis is cited to demonstrate the target is achievable via index quality alone. The revisit trigger is post-failure, meaning the NFR could be breached before caching is considered.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-013",
    "gate": 3,
    "severity": "warning",
    "title": "Rate limits not declared for signup and password-reset-request endpoints",
    "location": "Architecture §Rate limiting and abuse",
    "line": 132,
    "snippet": "Link creation: Redis-backed sliding window. 60 / minute / user per PRD. Login: 5 failed attempts / 15 min / email per PRD.",
    "description": "Signup and password-reset-request endpoints have no declared rate limit. Both are common targets for credential-stuffing, enumeration, and SES-cost abuse. Not even 'handled at edge via Cloudflare WAF' is stated for these endpoints.",
    "effort": "low"
  }
]
```

---

## STEP C — Summary Verdict

```json
{
  "domain": "architecture-review",
  "gate1_count": 2,
  "gate2_count": 0,
  "gate3_count": 2,
  "verdict": "FAIL_CRITICAL",
  "note": "Two Gate 1 findings: (1) SAST tooling absent from CI pipeline; (2) PRD-required local durable buffering for click events is architecturally impossible on stateless Cloudflare Workers. Two Gate 3 warnings: dashboard p95 NFR unvalidated without caching; signup/password-reset endpoints lack rate-limit declarations."
}
```
