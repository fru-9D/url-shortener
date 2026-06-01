# Architecture Review — 2026-06-01 (max effort, run 2)

**Architecture:** `docs/architecture.md` (v1)
**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** max
**Run:** 2 of 2 at this effort level
**Spec version:** 34 rules
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 8  **Gate 3:** 7

## Lookup

| Location | Coverage gap | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/architecture.md | CORS allowlist policy not declared | ARCH-019 | 2 | blocker |
| docs/architecture.md | HTTP security headers strategy not declared | ARCH-020 | 2 | blocker |
| docs/architecture.md | API versioning strategy not declared | ARCH-022 | 2 | blocker |
| docs/architecture.md | Health check endpoints not declared | ARCH-023 | 2 | blocker |
| docs/architecture.md | Request body / payload size limits not declared | ARCH-024 | 2 | blocker |
| docs/architecture.md | Input validation / DTO boundary policy not declared | ARCH-025 | 2 | blocker |
| docs/architecture.md:156 | Global exception handler + stack-trace policy + status mapping not declared | ARCH-026 | 2 | blocker |
| docs/architecture.md | SSRF defense for Safe Browsing call path not declared | ARCH-027 | 2 | blocker |
| docs/architecture.md | Failure-mode / runbook scaffolding not declared | ARCH-017 | 3 | warning |
| docs/architecture.md | DB connection pool strategy not declared | ARCH-028 | 3 | warning |
| docs/architecture.md | Idempotency policy for mutating endpoints not declared | ARCH-029 | 3 | warning |
| docs/architecture.md | Pagination scheme not declared | ARCH-030 | 3 | warning |
| docs/architecture.md | Transaction boundary / unit-of-work pattern not declared | ARCH-031 | 3 | warning |
| docs/architecture.md | Graceful shutdown / draining strategy not declared | ARCH-033 | 3 | warning |
| docs/architecture.md | Payload compression strategy not declared | ARCH-034 | 3 | warning |

## Notable dismissals at max effort

- **ARCH-012 (tech justification):** PASS — max effort accepted the tier-level rationale (edge/regional/async splits justified by PRD latency targets). Run 1 also accepted this.
- **ARCH-032 (correlation IDs):** PASS — the agent credited X-Ray + `X-Amzn-Trace-Id` SQS propagation + `request_id` in all log lines as adequate. Run 1 also accepted this.
- **ARCH-021 (cookie flags):** PASS — HttpOnly/Secure/SameSite=Lax with TTLs declared inline in auth section.

## Comparison vs run 1 (max effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 7 | 8 | +1 (ARCH-027) |
| Gate 3 | 7 | 7 | 0 |
| Total | 14 | 15 | +1 |
| Verdict | FAIL_BLOCKER | FAIL_BLOCKER | **stable** |

Run 1 dismissed ARCH-027 (SSRF) as exempt. Run 2 flagged it, citing the GSB call accepts user-supplied URL host+path and an attacker could use a metadata endpoint. Both readings are defensible — the rule's "exempt if pure redirect, never fetch" clause applies to the redirect path but not the GSB lookup path.

Gate 3 count exactly matches (7/7). All 7 findings identical between runs. This is the strongest consistency in the entire test — max-effort architecture review at Gate 3 is fully deterministic.
