# ERD Review — 2026-06-01 (max effort)

**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** max
**Verdict:** PASS
**Gate 1:** 0  **Gate 2:** 0  **Gate 3:** 0

## Findings

None.

## Notable considerations the max-effort agent worked through and dismissed

- **ERD-PRD-004 (cardinality):** `USER ||--o{ WORKSPACE_MEMBER` is permissive vs PRD's v1 "exactly one workspace per user." Considered as a Gate 2 candidate; concluded that the partial UK on `user_id WHERE removed_at IS NULL` documented in Notes correctly enforces the constraint at active-row level, and the `o{` permissively models historical removed rows. Defensible.
- **ERD-PRD-001 (failed-login throttling state):** PRD §Account requires per-email lockout tracking (5 attempts / 15 min). No `LOGIN_ATTEMPT` entity in ERD. Considered as missing; concluded that this is typically Redis-backed and the PRD doesn't require persistent storage or audit. Not first-class data per the rule's definition.
- **ERD-PRD-009 (invite pending uniqueness):** Partial UK on `(workspace_id, email_search_hash) WHERE status='pending'` is documented in Notes but no `UK` marker on the `email_search_hash` column. The Notes section explicitly addresses Mermaid's inability to express partial uniqueness with PRD line references — the constraint is captured in the artifact even if not in the diagram. Not a defect.
- **ERD-PRD-012 (string enums):** Plain `string` columns on `role`, `status`, `reason`, `country_code` — but the ERD has a comprehensive Enums table with PRD line references. The "no comment/no enum hint" condition is not met.

## Comparison vs other effort levels

| Effort | Findings (G1/G2/G3) | Verdict |
|---|---|---|
| Original (high) | 0 / 0 / 0 | PASS |
| Low | 0 / 1 / 3 | FAIL_BLOCKER |
| Medium | 0 / 0 / 0 | PASS |
| **Max** | **0 / 0 / 0** | **PASS** |

**Headline:** Low effort was the outlier. At medium and above, every walk through credits the Notes section's documented mitigations and concludes PASS. The ERD is genuinely clean.
