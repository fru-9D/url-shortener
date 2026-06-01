# Architecture Review — 2026-06-01 (low effort, run 2)

**Architecture:** `docs/architecture.md` (v1)
**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** low
**Run:** 2 of 2 at this effort level
**Spec version:** 34 rules
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 8  **Gate 3:** 8

## Lookup

| Location | Coverage gap | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/architecture.md | CORS allowlist policy not declared | ARCH-019 | 2 | blocker |
| docs/architecture.md | HTTP security headers strategy not declared | ARCH-020 | 2 | blocker |
| docs/architecture.md | API versioning strategy not declared | ARCH-022 | 2 | blocker |
| docs/architecture.md | Health check endpoints not declared | ARCH-023 | 2 | blocker |
| docs/architecture.md | Request body / payload size limits not declared | ARCH-024 | 2 | blocker |
| docs/architecture.md | Input validation / DTO boundary policy not declared | ARCH-025 | 2 | blocker |
| docs/architecture.md:156 | Error envelope shape declared but no global exception handler, stack-trace policy, or exception→status mapping | ARCH-026 | 2 | blocker |
| docs/architecture.md:107 | SSRF protection not declared for user-supplied URL ingestion path | ARCH-027 | 2 | blocker |
| docs/architecture.md | Failure-mode / runbook scaffolding not declared | ARCH-017 | 3 | warning |
| docs/architecture.md | DB connection pool strategy not declared | ARCH-028 | 3 | warning |
| docs/architecture.md | Idempotency policy for mutating endpoints not declared | ARCH-029 | 3 | warning |
| docs/architecture.md | Pagination strategy not declared | ARCH-030 | 3 | warning |
| docs/architecture.md | Transaction boundary / unit-of-work pattern not declared | ARCH-031 | 3 | warning |
| docs/architecture.md:112 | Correlation / request ID outbound forwarding and Worker→SQS propagation not declared | ARCH-032 | 3 | warning |
| docs/architecture.md | Graceful shutdown / draining strategy not declared | ARCH-033 | 3 | warning |
| docs/architecture.md | Payload compression strategy not declared | ARCH-034 | 3 | warning |

## Comparison vs run 1 (low effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 7 | 8 | +1 (ARCH-027 SSRF) |
| Gate 3 | 8 | 8 | 0 |
| Total | 15 | 16 | +1 |
| Verdict | FAIL_BLOCKER | FAIL_BLOCKER | stable |

**Key differences:**
- **ARCH-027 (SSRF):** Run 1 dismissed as N/A; run 2 flagged it explicitly, citing that the system accepts user URLs and makes outbound calls involving them (Safe Browsing lookup). Both readings are defensible given the exemption clause.
- **ARCH-032 (correlation IDs):** Run 1 flagged as warning; run 2 also flagged as warning — this finding was consistent but with different articulation (run 2 more specific about Worker→SQS and outbound HTTP forwarding gaps).
- **ARCH-012 (tech-stack):** Run 1 flagged as warning; run 2 accepted as PASS. Same reversal as medium-effort runs — the architecture document's tier-level rationale is enough for some runs, not others.

Verdict stable at FAIL_BLOCKER. Finding set has ~6% variance on borderline rules.
