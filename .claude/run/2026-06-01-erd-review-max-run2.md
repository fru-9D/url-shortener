# ERD Review — 2026-06-01 (max effort, run 2)

**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** max
**Run:** 2 of 2 at this effort level
**Verdict:** PASS_WITH_RISK
**Gate 1:** 0  **Gate 2:** 0  **Gate 3:** 4

## Lookup

| Location | ERD ↔ PRD mismatch | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/erd.md:48 | WORKSPACE_MEMBER.role plain `string` — enum `admin\|editor` not co-located in diagram | ERD-PRD-012 | 3 | warning |
| docs/erd.md:60 | INVITE.role plain `string` — enum `admin\|editor` not co-located | ERD-PRD-012 | 3 | warning |
| docs/erd.md:62 | INVITE.status plain `string` — enum `pending\|accepted\|declined\|expired\|failed` not co-located | ERD-PRD-012 | 3 | warning |
| docs/erd.md:115 | EMAIL_SUPPRESSION.reason plain `string` — enum `bounce\|complaint` not co-located | ERD-PRD-012 | 3 | warning |

## Agent's deliberation on borderline cases

The max-effort agent explicitly worked through and dismissed several borderline findings:

- **ERD-PRD-005 (audit columns):** CLICK has `clicked_at` but no `created_at`/`updated_at`. Agent concluded CLICK is an immutable append-only event log — `clicked_at` is the event timestamp, and audit fields are not required for immutable records. Token tables with `consumed_at` accepted as single-mutation pattern. **Dismissed.**
- **ERD-PRD-009 (INVITE pending uniqueness):** INVITE.email_search_hash has no UK marker in the entity block. Agent noted the ERD notes explicitly document the partial unique constraint with PRD line reference. Because the notes are part of the same file and serve as the enum signal, **dismissed** (unlike medium run 2 which flagged this as Gate 2).
- **ERD-PRD-011 (orphan entities):** EMAIL_SUPPRESSION and MIXPANEL_DEAD_LETTER have no relationship lines. Agent accepted both as intentionally unlinked — EMAIL_SUPPRESSION is a hash-keyed lookup table (no FK appropriate), MIXPANEL_DEAD_LETTER is an ops-only event log. **Dismissed.**
- **ERD-PRD-004 (cardinality):** `USER ||--o{ WORKSPACE_MEMBER` allows zero-or-more memberships. PRD says "exactly one in v1." Agent accepted the partial-UK-in-Notes as adequate. **Dismissed.**

## Comparison vs run 1 (max effort)

| Counter | Run 1 | Run 2 | Delta |
|---|---|---|---|
| Gate 1 | 0 | 0 | 0 |
| Gate 2 | 0 | 0 | 0 |
| Gate 3 | 0 | 4 | +4 |
| Verdict | PASS | PASS_WITH_RISK | **changed** |

Run 1 returned a clean PASS. Run 2 found 4 Gate 3 warnings on enum hints — the same ERD-PRD-012 findings that appear in virtually every run at every effort level. Run 1 apparently accepted the Notes-table-as-hint as meeting the rule's requirement; run 2 applied a stricter reading (the hint should be co-located with the column in the diagram body).

**Verdict shifted PASS → PASS_WITH_RISK, but the findings are Gate 3 only — non-blocking.** Both runs agree there are no Gate 1 or Gate 2 defects.
