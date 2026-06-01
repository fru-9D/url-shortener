# Architecture Review — 2026-06-01 (medium effort, run 2)

**Architecture:** `docs/architecture.md` (v1)
**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** medium
**Run:** 2 of 2 at this effort level
**Spec version:** 34 rules
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 8  **Gate 3:** 8

## Lookup

| Location | Coverage gap | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/architecture.md | CORS allowlist policy not declared | ARCH-019 | 2 | blocker |
| docs/architecture.md | HTTP security headers strategy not declared | ARCH-020 | 2 | blocker |
| docs/architecture.md:154 | API versioning scheme not declared | ARCH-022 | 2 | blocker |
| docs/architecture.md | Health check endpoints not declared | ARCH-023 | 2 | blocker |
| docs/architecture.md | Request body / payload size limits not declared | ARCH-024 | 2 | blocker |
| docs/architecture.md | Input validation / DTO boundary policy not declared | ARCH-025 | 2 | blocker |
| docs/architecture.md:156 | Global exception handler + stack-trace policy + status mapping not declared (envelope shape is) | ARCH-026 | 2 | blocker |
| docs/architecture.md | SSRF defense posture not declared for user-submitted URL path | ARCH-027 | 2 | blocker |
| docs/architecture.md | Failure-mode / runbook scaffolding not declared | ARCH-017 | 3 | warning |
| docs/architecture.md | DB connection pool strategy not declared | ARCH-028 | 3 | warning |
| docs/architecture.md | Idempotency policy for SQS consumers and mutating endpoints not declared | ARCH-029 | 3 | warning |
| docs/architecture.md | Pagination strategy not declared | ARCH-030 | 3 | warning |
| docs/architecture.md | Transaction boundary / unit-of-work pattern not declared | ARCH-031 | 3 | warning |
| docs/architecture.md:112 | Correlation/request-ID propagation contract not fully declared | ARCH-032 | 3 | warning |
| docs/architecture.md | Graceful shutdown / draining strategy not declared | ARCH-033 | 3 | warning |
| docs/architecture.md | Payload compression strategy not declared | ARCH-034 | 3 | warning |

## Comparison vs run 1 (medium effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 8 | 8 | 0 |
| Gate 3 | 9 | 8 | -1 |
| Total | 17 | 16 | -1 |
| Verdict | FAIL_BLOCKER | FAIL_BLOCKER | **stable** |

Gate 2 findings are identical between runs (all 8 matched). Gate 3 shows 1 finding difference — run 1 raised ARCH-012 (tech-stack justification), run 2 accepted the tier-level rationale as adequate. The verdict is stable.

**Architecture review at medium effort is the most consistent reviewer** — verdict stable, Gate 2 set fully stable, only minor Gate 3 judgment variance.
