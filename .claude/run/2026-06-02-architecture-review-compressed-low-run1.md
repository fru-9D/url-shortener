# Architecture Review — Compressed Agent — Low Effort — Run 1
**Date:** 2026-06-02
**Agent:** architecture-review-compressed
**Effort:** low
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| CI/CD section (absent — no SAST step) | PRD NFR §Security states "OWASP Top-10 2021 baseline, verified by SAST tooling on every release." The CI/CD section lists type check, lint, and tests but does not mention SAST tooling (e.g. Bandit, Semgrep, Trivy, Snyk). Architecture is silent on which tool satisfies this requirement. | ARCH-005 | G1 | Critical |

---

## STEP A-bis — Dismissal Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ARCH-001 | Dismissed | Auth/authorization fully declared: HTTP-only Secure SameSite=Lax session cookies, HMAC-signed session ID, Redis-backed session, RBAC with admin/editor roles, middleware-level permission checks. |
| ARCH-002 | Dismissed | AWS Secrets Manager, ECS Secrets Manager integration, Workers Secrets binding, 30-day DB credential rotation, quarterly signing-secret rotation with overlap window. |
| ARCH-003 | Dismissed | RPO 5 min (continuous WAL archiving), RTO 1 hour, quarterly restore drills, snapshot retention schedule stated. |
| ARCH-004 | Dismissed | PRD does not name GDPR/HIPAA/PCI/SOC2 as hard requirements. GDPR self-serve explicitly out of scope. |
| ARCH-005 | **FLAGGED** | See finding above. |
| ARCH-006 | Dismissed | Structured JSON logging to CloudWatch, CloudWatch metrics, AWS X-Ray tracing, Sentry error tracking, PagerDuty alerting. All four pillars covered. |
| ARCH-007 | Dismissed | All long-running operations (click ingest, Mixpanel forwarding, SES bounce processing) are behind SQS queues. |
| ARCH-008 | Dismissed | Cloudflare Workers (stateless), ECS Fargate autoscale with concrete RPS targets, click pipeline autoscale on queue depth, DB vertical scale path, read replicas. |
| ARCH-009 | Dismissed | All external APIs have resilience strategies: Mixpanel (retry 3×, dead-letter), Pwned Passwords (timeout, retry, fail-open), SES (retry 3×), Google Safe Browsing (timeout, fail-open), MaxMind (local mmdb, stale fallback). |
| ARCH-010 | Dismissed | Base repository class AND'es `workspace_id = <active>` into every query; auth middleware injects active workspace context; explicit opt-out required. |
| ARCH-011 | Dismissed | Alembic, migration shipped in same PR, CI runs migrations, production migrations gated on manual approval, forward-compatible requirement stated. |
| ARCH-012 | Dismissed | Major tech choices justified with tier-level rationale covering constraints and alternatives. |
| ARCH-013 | Dismissed | Link creation: Redis sliding window. Login: 5 attempts/15 min/email. Redirect: Cloudflare WAF per-IP. |
| ARCH-014 | Dismissed | Edge cache: Cloudflare 5-min TTL with purge. Application cache: "None in v1" explicitly stated with reason. |
| ARCH-015 | Dismissed | dev/staging/prod declared with purpose, hosts, data. |
| ARCH-016 | Dismissed | GitHub Actions CI with per-PR checks. Trunk-based deploys with manual-approval prod promotion. |
| ARCH-017 | Dismissed | Key failure modes documented (Redis single-AZ, click pipeline fallback, Mixpanel dead-letter, DB replication lag alert). |
| ARCH-018 | Dismissed | REST/JSON transport, OpenAPI source of truth, session cookie auth, CSRF double-submit, error envelope all declared. |
| ARCH-019 | Dismissed | CORS: allowed origins list, no wildcard, credentials true, methods enumerated, FastAPI CORSMiddleware. |
| ARCH-020 | Dismissed | HTTP security headers with production values: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP per surface. |
| ARCH-021 | Dismissed | Cookie flags: HTTP-only, Secure, SameSite=Lax, 30-day absolute TTL, 7-day idle TTL. |
| ARCH-022 | Dismissed | /v1/ URI prefix, 90-day deprecation window, Deprecation and Sunset headers. |
| ARCH-023 | Dismissed | /healthz (liveness) and /readyz (readiness) declared for each ECS service with ALB config parameters. |
| ARCH-024 | Dismissed | Default JSON body limit 1 MB enforced by FastAPI middleware and ALB limit. |
| ARCH-025 | Dismissed | All request bodies as Pydantic BaseModel; ORM instances never returned directly; explicit response_model on every handler. |
| ARCH-026 | Dismissed | Global FastAPI exception handler; canonical JSON error envelope; stack traces never in HTTP responses; exception-to-status-code mappings listed. |
| ARCH-028 | Dismissed | pool_size=10, max_overflow=5 per ECS task; sizing math against db.r6g.large max_connections; leak detection via session/statement timeouts. |
| ARCH-029 | Dismissed | Idempotency-Key header for POST resource-creation endpoints; stored in Redis 24h TTL; naturally-idempotent endpoints annotated. |
| ARCH-030 | Dismissed | Cursor-based pagination; default page size 50; max 200; cursor format specified; response envelope specified. |
| ARCH-031 | Dismissed | Unit-of-work per request via FastAPI DI; service layer prohibited from calling commit/rollback; SQS publish after DB commit. |
| ARCH-032 | Dismissed | request_id in every log line; propagation into SQS via X-Amzn-Trace-Id; AWS X-Ray edge→SQS→consumer. All three propagation requirements met. |
| ARCH-033 | Dismissed | SIGTERM handler; HTTP services 30s drain; queue consumers finish current batch (90s visibility timeout); ECS stopTimeout=120s. |
| ARCH-034 | Dismissed | GZip for responses ≥ 1 KB; Brotli where client signals br; Cloudflare applies Brotli on edge-cached responses. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "architecture-review",
    "id": "ARCH-005",
    "rule": "ARCH-005",
    "gate": 1,
    "severity": "critical",
    "title": "SAST tooling requirement from PRD not addressed in CI/CD section",
    "location": {
      "section": "CI/CD",
      "line": 0
    },
    "snippet": "",
    "detail": "PRD NFR §Security states: 'OWASP Top-10 2021 baseline, verified by SAST tooling on every release.' The CI/CD section lists: 'type check (Mypy + tsc), lint (Ruff, ESLint), unit + integration tests, OpenAPI diff, Alembic check' — no SAST tool is named. The architecture directly contradicts the PRD's 'on every release' requirement by omitting SAST from the per-PR and deploy gate steps.",
    "effort": "low",
    "downstream": []
  }
]
```

---

## STEP C — Summary Verdict

```json
{
  "domain": "architecture-review",
  "gate1_count": 1,
  "gate2_count": 0,
  "gate3_count": 0,
  "verdict": "FAIL_CRITICAL",
  "note": "One Gate 1 finding: PRD requires SAST tooling on every release (OWASP Top-10 2021) but the CI/CD section names no SAST tool. All other 33 rules dismissed — the architecture document is otherwise thorough."
}
```
