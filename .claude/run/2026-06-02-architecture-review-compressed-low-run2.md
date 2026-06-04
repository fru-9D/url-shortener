# Architecture Review — Compressed Agent — Low Effort — Run 2
**Date:** 2026-06-02
**Agent:** architecture-review-compressed
**Effort:** low
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| CI/CD section (absent — no SAST step) | PRD NFR §Security mandates "OWASP Top-10 2021 baseline, verified by SAST tooling on every release." CI/CD section lists type check, lint, unit/integration tests, OpenAPI diff, and Alembic check — no SAST tool (Bandit, Semgrep, Snyk, etc.) is named or declared. | ARCH-004 | G1 | Critical |
| No dedicated section | Architecture has no failure-mode enumeration. Document is written almost entirely in happy-path terms. Known failure modes — Redis unavailable (session/rate-limit path), DB primary down, SQS unavailable at click-emit time (local durable buffering mechanism unspecified), connection-pool exhaustion, cache stampede on cold-start — are not enumerated with degradation behavior. | ARCH-017 | G3 | Warning |

---

## STEP A-bis — Dismissal Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ARCH-001 | Dismissed | Auth/authorization fully declared: HTTP-only Secure SameSite=Lax cookie, HMAC-signed session id, Redis-backed session, `session_version` revocation, RBAC with admin/editor roles, FastAPI dependency. |
| ARCH-002 | Dismissed | AWS Secrets Manager; ECS Secrets Manager integration; Workers Secrets binding; rotation cadences stated. |
| ARCH-003 | Dismissed | RPO 5 min (WAL archiving), RTO 1 hour with quarterly drills, tiered snapshot retention. |
| ARCH-004 | **FLAGGED** | See finding above. |
| ARCH-005 | Dismissed | No direct contradiction found between architecture and PRD requirements. |
| ARCH-006 | Dismissed | Structured JSON logs (CloudWatch), CloudWatch metrics with named custom metrics, AWS X-Ray tracing with SQS propagation, Sentry, PagerDuty. All four pillars covered. |
| ARCH-007 | Dismissed | Click pipeline (SQS + ECS), Mixpanel forwarding (SQS), SES mail-events (SNS→SQS→worker) all behind queues. |
| ARCH-008 | Dismissed | Cloudflare Workers (stateless), ECS Fargate autoscale, click consumer autoscale on queue depth, DB read replicas, vertical scale path. Concrete RPS targets stated. |
| ARCH-009 | Dismissed | All five external integrations have timeout + failure behavior declared. |
| ARCH-010 | Dismissed | Base repository class auto-ANDs workspace_id; auth middleware injects active workspace context. |
| ARCH-011 | Dismissed | Alembic, same-PR migration, CI fresh-DB test, manual-approval prod gating, forward-compatibility requirement. |
| ARCH-012 | Dismissed | Major stack choices justified with per-tier latency/scale constraints. Tier-level rationale covers choices. |
| ARCH-013 | Dismissed | Link creation (60/min/user Redis), login (5 attempts/15 min/email), redirect (Cloudflare WAF per-IP). |
| ARCH-014 | Dismissed | Edge cache (Cloudflare 5-min TTL). Application cache: "None in v1" explicitly stated with revisit condition. |
| ARCH-015 | Dismissed | dev/staging/prod environments declared with purpose, hosts, data. |
| ARCH-016 | Dismissed | GitHub Actions per-PR gates; trunk-based deploys; manual-approval prod promotion. |
| ARCH-017 | **FLAGGED** | No failure-mode enumeration. |
| ARCH-018 | Dismissed | REST/JSON transport, FastAPI OpenAPI source-of-truth, session cookie auth, CSRF, versioning, CORS, security headers, body limits, error envelope all declared. |
| ARCH-019 | Dismissed | CORS: allowed origins list, no wildcard, credentials true, methods enumerated, FastAPI CORSMiddleware. |
| ARCH-020 | Dismissed | HTTP security headers with production values: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP per surface. |
| ARCH-021 | Dismissed | Cookie flags: HTTP-only, Secure, SameSite=Lax, 30-day absolute TTL, 7-day idle TTL. |
| ARCH-022 | Dismissed | /v1/ URI prefix, 90-day deprecation window, Deprecation/Sunset headers. |
| ARCH-023 | Dismissed | /healthz (liveness) and /readyz (readiness) with ALB config parameters. |
| ARCH-024 | Dismissed | Default JSON body limit 1 MB enforced by FastAPI middleware and ALB. |
| ARCH-025 | Dismissed | Pydantic BaseModel on every endpoint; explicit response_model; Update<X> schemas. |
| ARCH-026 | Dismissed | Global FastAPI exception handler; canonical JSON error envelope; stack traces excluded; exception-to-status mappings listed. |
| ARCH-028 | Dismissed | pool_size=10, max_overflow=5 per ECS task; sizing math against db.r6g.large; leak detection via session/statement timeouts. |
| ARCH-029 | Dismissed | Idempotency-Key header; Redis store keyed on (key, user_id, endpoint) with 24h TTL; naturally-idempotent endpoints annotated. |
| ARCH-030 | Dismissed | Cursor-based pagination; default 50; max 200; offset-based explicitly rejected with rationale. |
| ARCH-031 | Dismissed | Unit-of-work per request; service layer prohibited from calling commit/rollback; SQS publish after DB commit with dead-letter recovery. |
| ARCH-032 | Dismissed | request_id in every log line and error envelope; propagated into SQS via X-Amzn-Trace-Id; X-Ray edge→SQS→consumer. All three propagation requirements met. |
| ARCH-033 | Dismissed | SIGTERM handler; HTTP services 30s drain; queue consumers finish current batch (90s visibility timeout); ECS stopTimeout=120s. |
| ARCH-034 | Dismissed | GZip ≥ 1 KB via GZipMiddleware; Brotli where client signals br; Cloudflare automatic Brotli on edge-cached responses. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-004",
    "gate": 1,
    "severity": "critical",
    "title": "OWASP SAST tooling required by PRD not declared in CI pipeline",
    "location": "architecture.md — CI/CD section",
    "line": 0,
    "snippet": "Per-PR: type check (Mypy + tsc), lint (Ruff, ESLint), unit + integration tests, OpenAPI diff, Alembic check",
    "prd_passage": "OWASP Top-10 2021 baseline, verified by SAST tooling on every release",
    "description": "PRD NFR §Security mandates SAST tooling on every release. The CI/CD section enumerates five per-PR gates but names no SAST scanner (e.g. Bandit, Semgrep, Snyk). This is a direct omission of a declared PRD requirement.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "rule_id": "ARCH-017",
    "gate": 3,
    "severity": "warning",
    "title": "No failure-mode enumeration — architecture is happy-path only",
    "location": "architecture.md — no dedicated section",
    "line": 0,
    "snippet": "",
    "description": "The architecture describes the happy path for each component but does not enumerate known failure modes or degradation behavior. Specific gaps: (1) Redis unavailable — session reads and rate-limit counters both depend on Redis; fail-open vs fail-closed policy is unstated. (2) DB primary down — architecture declares read replicas but does not state whether writes hard-fail or queue. (3) 'Local durable buffering' on SQS unavailability (mentioned in PRD) — the buffering mechanism is never specified in the architecture. (4) Connection-pool exhaustion — no queue-full or shed-load behavior declared. (5) Cloudflare cache stampede on cold-start after purge event.",
    "effort": "medium"
  }
]
```

---

## STEP C — Summary Verdict

```json
{"domain":"architecture-review","gate1_count":1,"gate2_count":0,"gate3_count":1,"verdict":"FAIL_CRITICAL"}
```

**Remediation for ARCH-004 (low effort):** Add a named SAST tool (Bandit for Python, Semgrep with `p/owasp-top-ten` ruleset, or Snyk Code) to the per-PR CI gate list in the CI/CD section.
