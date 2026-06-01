# PRD Review — 2026-06-01 (medium effort, run 2)

**File reviewed:** `docs/prd.md` (v3)
**Effort:** medium
**Run:** 2 of 2 at this effort level
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 2  **Gate 3:** 6

## Lookup

| PRD location | Defect | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/prd.md:139 | "Every Member belongs to exactly one Workspace in v1" — no AC on whether sign-up auto-creates a Workspace | PRD-006 | 2 | blocker |
| docs/prd.md:50 | All three user flows A/B/C are pure happy-path — no failure branch woven into any flow | PRD-007 | 2 | blocker |
| docs/prd.md:238 | "Mid-tier mobile over 4G" — no reference device or throttle profile | PRD-010 | 3 | warning |
| docs/prd.md:240 | "OWASP Top-10 baseline" — no edition, scope, or verification mechanism | PRD-010 | 3 | warning |
| docs/prd.md:107 | Date filter upper bound unspecified (today? latest link created_at? rolling 365 days?) | PRD-011 | 3 | warning |
| docs/prd.md:106 | Deep pagination at scale — no Workspace link cap, no max-page-count or cursor strategy | PRD-011 | 3 | warning |
| docs/prd.md:63 | "redirect service emits a click event synchronously" vs error table "durably queued" — fire-and-forget or blocking? | PRD-012 | 3 | warning |
| docs/prd.md:143 | "owner_id reassigned to the removing Admin" — actor, timing, atomicity unstated | PRD-012 | 3 | warning |

## Comparison vs run 1 (medium effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 2 | 2 | 0 |
| Gate 3 | 6 | 6 | 0 |
| Verdict | FAIL_BLOCKER | FAIL_BLOCKER | **stable** |

Verdict and finding-count are identical. The two Gate 2 items changed:
- **Run 1:** Safe Browsing contract gap + click pipeline contract gap
- **Run 2:** Workspace sign-up flow ambiguity + user flows lack failure branches

Different findings at the same count. Both are genuine Gate 2 defects — neither run is wrong.

**Implication:** Medium-effort PRD review has stable verdict and stable finding-count, but the specific Gate 2 findings vary between runs. The reviewer is reliably finding two real blockers each time, but not the same two blockers. The PRD has more than 2 Gate 2-level gaps and each run surfaces a different subset.
