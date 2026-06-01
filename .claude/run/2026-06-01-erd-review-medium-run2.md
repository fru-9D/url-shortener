# ERD Review — 2026-06-01 (medium effort, run 2)

**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** medium
**Run:** 2 of 2 at this effort level
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 5  **Gate 3:** 5

## Lookup

| Location | ERD ↔ PRD mismatch | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/erd.md:59 | INVITE.email_search_hash has no UK marker; PRD implies partial unique on (workspace_id, email_search_hash) WHERE pending | ERD-PRD-009 | 2 | blocker |
| docs/erd.md:83 | CLICK missing created_at and updated_at — PRD NFR §Data retention requires audit fields indefinitely | ERD-PRD-005 | 2 | blocker |
| docs/erd.md:94 | PASSWORD_RESET_TOKEN missing updated_at — row is mutable (consumed_at set) | ERD-PRD-005 | 2 | blocker |
| docs/erd.md:103 | EMAIL_VERIFICATION_TOKEN missing updated_at — row is mutable (consumed_at set) | ERD-PRD-005 | 2 | blocker |
| docs/erd.md:112 | EMAIL_SUPPRESSION missing updated_at — reason could be corrected | ERD-PRD-005 | 2 | blocker |
| docs/erd.md:48 | WORKSPACE_MEMBER.role plain `string` — enum admin\|editor not inline | ERD-PRD-012 | 3 | warning |
| docs/erd.md:61 | INVITE.role plain `string` — enum admin\|editor not inline | ERD-PRD-012 | 3 | warning |
| docs/erd.md:62 | INVITE.status plain `string` — enum pending\|accepted\|declined\|expired\|failed not inline | ERD-PRD-012 | 3 | warning |
| docs/erd.md:120 | MIXPANEL_DEAD_LETTER orphan entity — no relationship lines, no workspace_id FK | ERD-PRD-011 | 3 | warning |
| docs/erd.md:112 | EMAIL_SUPPRESSION orphan entity — no relationship lines, no logical hash-join note | ERD-PRD-011 | 3 | warning |

## Comparison vs run 1 (medium effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 0 | 5 | **+5** |
| Gate 3 | 0 | 5 | **+5** |
| Verdict | PASS | FAIL_BLOCKER | **verdict flipped** |

Run 1 returned a clean PASS. Run 2 found 5 Gate 2 blockers and 5 Gate 3 warnings — **verdict flipped from PASS to FAIL_BLOCKER**.

The Gate 2 findings are all genuine:
- **ERD-PRD-009:** INVITE.email_search_hash has no UK marker in the entity block — the partial-unique constraint is only in prose. A real gap that ORM generators would miss.
- **ERD-PRD-005 × 4:** CLICK, PASSWORD_RESET_TOKEN, EMAIL_VERIFICATION_TOKEN, EMAIL_SUPPRESSION all missing `updated_at`. The PRD NFR explicitly states "Audit fields (created_at, updated_at): indefinite." CLICK is also missing `created_at`.

**This is the most significant variance finding of the entire test.** The same ERD at the same effort level produced PASS and FAIL_BLOCKER. The findings are not invented — run 2 caught real defects that run 1 genuinely missed. The ERD reviewer at medium effort is unstable on whether it applies the PRD NFR data-retention clause to all entity types.
