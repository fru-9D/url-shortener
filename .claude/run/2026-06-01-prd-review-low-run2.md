# PRD Review — 2026-06-01 (low effort, run 2)

**File reviewed:** `docs/prd.md` (v3)
**Effort:** low
**Run:** 2 of 2 at this effort level
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 2  **Gate 3:** 5

## Lookup

| PRD location | Defect | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/prd.md:107 | "interpreted in the viewer's browser timezone" — ambiguous whether frontend or backend performs conversion | PRD-006 | 2 | blocker |
| docs/prd.md:50 | Flow A lacks a failure branch for network/transport failure during link creation | PRD-007 | 2 | blocker |
| docs/prd.md:238 | "Mid-tier mobile over 4G" — no reference device or Lighthouse profile | PRD-010 | 3 | warning |
| docs/prd.md:240 | "OWASP Top-10 baseline" — no edition, controls, or verification mechanism | PRD-010 | 3 | warning |
| docs/prd.md:141 | Admin demoting another Admin to last-admin state — user-visible error unstated | PRD-011 | 3 | warning |
| docs/prd.md:144 | "Re-inviting" — actor unnamed (Admin clicking Resend? new invite? auto-retry?) | PRD-012 | 3 | warning |
| docs/prd.md:8,135 | "Teams" section heading + "team" vs "Workspace" drift bleeds into API resource naming | PRD-013 | 3 | warning |

## Comparison vs run 1 (low effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 0 | 2 | +2 |
| Gate 3 | 0 | 5 | +5 |
| Verdict | PASS | FAIL_BLOCKER | **flipped** |

Run 1 returned a clean PASS at low effort. Run 2 — same effort, same artifacts — returned FAIL_BLOCKER with two genuine Gate 2 blockers and five Gate 3 warnings. Every finding is real:

- **PRD-006 (line 107):** the timezone-conversion responsibility is genuinely unspecified (frontend or backend?). Different query implementations result.
- **PRD-007 (Flow A):** the link-creation flow has no network-failure UX branch.

This is a significant intra-effort variance. Low-effort PRD review is unstable — it can go PASS or FAIL_BLOCKER on the same document in successive runs.
