# ERD Review — 2026-06-01 (low effort)

**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** low
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 1  **Gate 3:** 3

## Lookup

| Location | ERD ↔ PRD mismatch | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/erd.md:12 | `USER ||--o{ WORKSPACE_MEMBER` doesn't visually express v1 single-Workspace constraint | ERD-PRD-004 | 2 | blocker |
| docs/erd.md:47 | WORKSPACE_MEMBER.role plain string — enum hint not inline (only in Notes table) | ERD-PRD-012 | 3 | warning |
| docs/erd.md:60 | INVITE.role/status plain string — enum hint not inline | ERD-PRD-012 | 3 | warning |
| docs/erd.md:115 | EMAIL_SUPPRESSION.reason plain string — enum hint not inline | ERD-PRD-012 | 3 | warning |

## Gate 2 — Blocker

### [ERD-PRD-004] — Single-Workspace cardinality not visually enforced
**Location:** `docs/erd.md:12`
**Finding:** PRD §Teams line 139 states "Every Member belongs to exactly one Workspace in v1." The ERD draws `USER ||--o{ WORKSPACE_MEMBER` (zero-or-many memberships per user), with the v1 1:1 constraint only documented as a partial UK in the Notes table. The diagram itself does not visually enforce the strict 1:1 rule — an ORM-deriver could legitimately produce a many-to-many model.
**Fix:** Tighten cardinality to `USER ||--o|` (one-to-zero-or-one) OR add a clarifying comment on the relationship line. Make the v1 constraint visible on the diagram, not only in a notes table.
**Effort:** low

## Gate 3 — Warnings

Three ERD-PRD-012 findings (enum hints only in separate Notes table, not at attribute site). See lookup table.

## Comparison vs previous higher-effort run (2026-05-25-erd-review-v2.md)

Previous run scored PASS (0/0/0). At low effort, the reviewer became *stricter* — re-flagging the enum-hint findings even though they're documented in the Notes section, AND raising a new Gate 2 about visual cardinality (the previous run accepted the partial-UK-in-Notes pattern with PRD line reference as adequate). Different effort level surfaced different concerns rather than fewer.
