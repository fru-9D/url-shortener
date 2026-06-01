# Architecture Review — 2026-06-01 (low effort, 34-rule spec)

**Architecture:** `docs/architecture.md` (v1)
**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** low
**Spec version:** 34 rules (ARCH-001..034, expanded with be-* upstream coverage)
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 7  **Gate 3:** 8

## Lookup

| Location | Coverage gap | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/architecture.md | CORS allowlist policy not stated (Next.js dashboard calls FastAPI cross-origin with credentials) | ARCH-019 | 2 | blocker |
| docs/architecture.md | HTTP security headers (CSP, HSTS, X-Frame-Options, etc.) not declared | ARCH-020 | 2 | blocker |
| docs/architecture.md | API versioning scheme not declared | ARCH-022 | 2 | blocker |
| docs/architecture.md | Health / readiness / liveness endpoint strategy not declared | ARCH-023 | 2 | blocker |
| docs/architecture.md | Request body / payload size limits not declared globally | ARCH-024 | 2 | blocker |
| docs/architecture.md | Input validation / DTO boundary policy (Pydantic schemas, response_model) not declared | ARCH-025 | 2 | blocker |
| docs/architecture.md | Global exception handler + stack-trace policy + status-code mapping not declared | ARCH-026 | 2 | blocker |
| docs/architecture.md | Failure-mode runbook scaffolding not enumerated | ARCH-017 | 3 | warning |
| docs/architecture.md | Connection pool sizing vs Postgres max_connections not declared | ARCH-028 | 3 | warning |
| docs/architecture.md | Idempotency policy for mutating endpoints not declared | ARCH-029 | 3 | warning |
| docs/architecture.md | Pagination scheme details not declared at architecture level | ARCH-030 | 3 | warning |
| docs/architecture.md | Transaction boundary / unit-of-work pattern not declared | ARCH-031 | 3 | warning |
| docs/architecture.md | Correlation/request-id propagation into SQS attributes / outbound calls not declared | ARCH-032 | 3 | warning |
| docs/architecture.md | Graceful shutdown / draining strategy for ECS + SQS not declared | ARCH-033 | 3 | warning |
| docs/architecture.md | Payload compression strategy not declared | ARCH-034 | 3 | warning |

## Rules that PASSED

ARCH-001 (auth), ARCH-002 (secrets), ARCH-003 (backup/recovery), ARCH-004 (compliance), ARCH-005 (no PRD contradiction), ARCH-006 (observability), ARCH-007 (async boundary), ARCH-008 (scaling), ARCH-009 (external API resilience), ARCH-010 (multi-tenant isolation), ARCH-011 (migrations), ARCH-012 (tech stack justification), ARCH-013 (rate limiting), ARCH-014 (caching), ARCH-015 (environments), ARCH-016 (CI/CD), ARCH-018 (FE/BE contract), ARCH-021 (cookie flags — HttpOnly/Secure/SameSite explicit), ARCH-027 (SSRF — N/A, no server-side user-URL fetch).

## Comparison vs previous run (2026-05-25-architecture-review.md, 18-rule spec)

Previous: 0/0/4 PASS_WITH_RISK (3 × ARCH-012 stack justification + 1 × ARCH-017 runbooks). Today: 0/7/8 FAIL_BLOCKER. The change is dominated by the 16 newly-added rules (ARCH-019..034) — most fire because the architecture doc was written against the original 18-rule spec and didn't proactively address the be-* upstreamed concerns. Notably:

- ARCH-012 (stack justification × 3) **no longer fires** in this run — the low-effort pass apparently accepted the per-tier rationale as sufficient. Previous higher-effort run was more demanding.
- ARCH-017 (runbooks) still fires.
- All 7 new Gate 2 + 7 of 7 new Gate 3 rules fire — the architecture genuinely doesn't address them.
- ARCH-027 (SSRF) correctly recognized as N/A because the redirect path doesn't fetch user URLs server-side.
