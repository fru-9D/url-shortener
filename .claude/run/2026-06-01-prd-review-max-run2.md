# PRD Review — 2026-06-01 (max effort, run 2)

**File reviewed:** `docs/prd.md` (v3)
**Effort:** max
**Run:** 2 of 2 at this effort level
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 3 (+1 for PRD-007 sub-finding)  **Gate 3:** 8

## Lookup

| PRD location | Defect | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/prd.md:85 | Abuse-review queue referenced as safety net but never specified as a feature | PRD-005 | 2 | blocker |
| docs/prd.md:139 | "Exactly one Workspace in v1" — no AC or error scenario for second-Workspace attempt | PRD-005 | 2 | blocker |
| docs/prd.md:62,123 | Dual freshness specs: "≤ 60 seconds" (one-sided) vs "± 1 minute" (symmetric) | PRD-006 | 2 | blocker |
| docs/prd.md:59 | Flow B missing error scenarios for redirect-datastore failure and click-pipeline unavailability | PRD-007 | 2 | blocker |
| docs/prd.md:238 | "Mid-tier mobile over 4G" — no reference device or throttle profile | PRD-010 | 3 | warning |
| docs/prd.md:241 | "Email addresses encrypted at rest" — no algorithm, key-management, or column scope | PRD-010 | 3 | warning |
| docs/prd.md:79 | Case-near slug collision boundary (e.g. "Abc" vs "abc") — behavior unstated | PRD-011 | 3 | warning |
| docs/prd.md:106 | Pagination controls visibility at ≤50 links unstated | PRD-011 | 3 | warning |
| docs/prd.md:84 | Passive: deduplication constraint — system vs Member as actor | PRD-012 | 3 | warning |
| docs/prd.md:143 | Passive: "owner_id reassigned" — automatic vs manual, atomicity unstated | PRD-012 | 3 | warning |
| docs/prd.md:29 | "User" vs "Member" — no Glossary entry for "User" as pre-membership state | PRD-013 | 3 | warning |

## Comparison vs run 1 (max effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 5 | 4 | -1 |
| Gate 3 | 9 | 8 | -1 |
| Verdict | FAIL_BLOCKER | FAIL_BLOCKER | **stable** |

Run 1 Gate 2 findings: abuse queue, invite decline missing, freshness inconsistency, member removal cascade, SES backpressure.
Run 2 Gate 2 findings: abuse queue, second-Workspace AC missing, freshness inconsistency, Flow B error scenarios.

**Overlap:** 2 of 5 findings match exactly (abuse queue + freshness inconsistency). 3 findings per run are different but all genuine.

**Verdict stable. Finding-count stable. Finding-identity moderate — max effort finds 4-5 real Gate 2 issues per run but samples different subsets.**

This confirms the PRD has more Gate 2 defects than any single run surfaces. The full set across both max runs is at least 7 distinct Gate 2 issues.
