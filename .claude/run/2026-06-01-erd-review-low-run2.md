# ERD Review — 2026-06-01 (low effort, run 2)

**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** low
**Run:** 2 of 2 at this effort level
**Verdict:** PASS_WITH_RISK
**Gate 1:** 0  **Gate 2:** 0  **Gate 3:** 6

## Lookup

| Location | ERD ↔ PRD mismatch | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/erd.md:120 | MIXPANEL_DEAD_LETTER has no relationship line — workspace context not signaled | ERD-PRD-011 | 3 | warning |
| docs/erd.md:112 | EMAIL_SUPPRESSION has no relationship line — lookup pattern on sign-up/invite not visible | ERD-PRD-011 | 3 | warning |
| docs/erd.md:48 | WORKSPACE_MEMBER.role plain `string` — enum `admin\|editor` not inline | ERD-PRD-012 | 3 | warning |
| docs/erd.md:62 | INVITE.role plain `string` — enum `admin\|editor` not inline | ERD-PRD-012 | 3 | warning |
| docs/erd.md:63 | INVITE.status plain `string` — enum `pending\|accepted\|declined\|expired\|failed` not inline | ERD-PRD-012 | 3 | warning |
| docs/erd.md:88 | CLICK.country_code plain `string` — ISO 3166-1 alpha-2 closed set not inline | ERD-PRD-012 | 3 | warning |

## Comparison vs run 1 (low effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 1 (cardinality) | 0 | -1 |
| Gate 3 | 3 (enum hints) | 6 (enum hints + 2 orphan entity) | +3 |
| Verdict | FAIL_BLOCKER | PASS_WITH_RISK | **changed** |

Run 1 flagged visual cardinality as Gate 2 (FAIL_BLOCKER). Run 2 accepted cardinality as adequate and found no Gate 2 — but surfaced 6 Gate 3 items including two new ERD-PRD-011 findings about orphan entities (EMAIL_SUPPRESSION and MIXPANEL_DEAD_LETTER having no relationship lines).

Both runs flagged the same enum-hint concern (ERD-PRD-012) but the count differs (3 vs 4 columns). Run 2 is more thorough here — it caught CLICK.country_code in addition to the three role/status columns.

Verdict moved FAIL_BLOCKER → PASS_WITH_RISK, but finding count increased 4 → 6. The two runs disagree on verdict while agreeing on the underlying issues.
