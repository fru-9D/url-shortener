# ERD Review — 2026-05-25 (v1)

**PRD:** `docs/prd.md` (v3, PASS_WITH_RISK)
**ERD:** `docs/erd.md` (v1)
**Verdict:** FAIL_CRITICAL
**Gate 1 (Critical):** 4 findings
**Gate 2 (Blockers):** 3 findings
**Gate 3 (Warnings):** 3 findings

## Lookup

| Location | ERD ↔ PRD mismatch | Rule ID | Gate | Severity |
|----------|-------------------|---------|------|----------|
| docs/erd.md (no entity) | PRD §Account requires single-use reset tokens with 60-min TTL; no entity | ERD-PRD-001 | 1 | critical |
| docs/erd.md (no entity) | PRD §Account requires email verification gate; no verification-token entity | ERD-PRD-001 | 1 | critical |
| docs/erd.md:22 | USER.email / INVITE.email / EMAIL_SUPPRESSION.email — PRD NFR says "encrypted at rest"; no marker | ERD-PRD-003 | 1 | critical |
| docs/erd.md:34 | WORKSPACE.owner_id FK exists but no USER→WORKSPACE relationship line drawn | ERD-PRD-002 | 1 | critical |
| docs/erd.md:77 | CLICK has no workspace_id; violates ERD's own stated multi-tenant policy | ERD-PRD-006 | 2 | blocker |
| docs/erd.md:39 | WORKSPACE_MEMBER lacks UK on (workspace_id, user_id); PRD: "one Workspace per user in v1" | ERD-PRD-009 | 2 | blocker |
| docs/erd.md:50 | INVITE lacks uniqueness on (workspace_id, email) for pending; PRD: "re-inviting replaces existing" | ERD-PRD-009 | 2 | blocker |
| docs/erd.md:56 | INVITE.status plain `string`; PRD enumerates pending/accepted/declined/expired/failed | ERD-PRD-012 | 3 | warning |
| docs/erd.md:43 | WORKSPACE_MEMBER.role plain `string`; PRD enumerates Admin/Editor | ERD-PRD-012 | 3 | warning |
| docs/erd.md:54 | INVITE.role plain `string`; PRD enumerates Admin/Editor | ERD-PRD-012 | 3 | warning |

## Gate 1 — Critical (ERD not safe to derive ORM models from)

### [ERD-PRD-001] — Password reset token entity missing
**Location:** `docs/erd.md` (no entity)
**Finding:** PRD §Account describes a single-use reset token with 60-min TTL, mailed on demand, invalidated after use. ERD's "Out of ERD scope" note (line 116) admits it's TBD. But the PRD treats the token as a stored, time-bounded, single-use object — that's a first-class entity. Without it in the diagram, ORM code may collapse the token onto USER (one slot, no audit) and silently violate the single-use guarantee under concurrent resets.
**Fix:** Add a `PASSWORD_RESET_TOKEN` entity: `id PK, user_id FK, token_hash UK (store hash not raw), expires_at, consumed_at (nullable), created_at`. Link `USER ||--o{ PASSWORD_RESET_TOKEN`.
**Effort:** low

### [ERD-PRD-001] — Email verification token entity missing
**Location:** `docs/erd.md` (no entity)
**Finding:** PRD §Account requires verification before link creation, and §Account error scenarios describe the verification link expiring with a resend path. Implies a stored token with TTL — not just the `email_verified_at` flag the ERD records on USER. Without the entity: can't model resend, can't enforce single-use, can't audit issue-vs-consume.
**Fix:** Add `EMAIL_VERIFICATION_TOKEN`: `id PK, user_id FK, token_hash UK, expires_at, consumed_at, created_at`. Link `USER ||--o{ EMAIL_VERIFICATION_TOKEN`.
**Effort:** low

### [ERD-PRD-003] — Email encryption-at-rest boundary not signaled
**Location:** `docs/erd.md:22, 53, 89`
**Finding:** PRD NFR (line 240) requires "Email addresses encrypted at rest." ERD declares `USER.email`, `INVITE.email`, and `EMAIL_SUPPRESSION.email` as plain `string` with no marker. ORM models will use a plain string column and inherit no encryption awareness. The `UK` on `USER.email` further implies a deterministic encryption / blind-index strategy is needed (a plain encrypted column cannot be uniquely indexed) — the ERD gives no signal of this.
**Fix:** Either (a) split into a sensitive table — `USER_EMAIL { ciphertext, search_hash UK }` — or (b) annotate columns explicitly: `string email_ciphertext` + `string email_search_hash UK`. Apply consistently across all three entities. Document in the ERD Notes section.
**Effort:** medium

### [ERD-PRD-002] — USER → WORKSPACE relationship line missing
**Location:** `docs/erd.md:34`
**Finding:** `WORKSPACE.owner_id` is declared as FK but the relationships block (lines 12-18) draws no `USER → WORKSPACE` line. PRD §Teams: "The Workspace's creator is the first Admin." Without the line, readers cannot tell whether `owner_id` points at USER or at `WORKSPACE_MEMBER.id`.
**Fix:** Add `USER ||--o{ WORKSPACE : "owns"`. Also reconsider whether `owner_id` should point at USER directly or at WORKSPACE_MEMBER — the latter survives the original creator leaving the workspace.
**Effort:** low

## Gate 2 — Blockers

### [ERD-PRD-006] — CLICK missing workspace_id
**Location:** `docs/erd.md:77`
**Finding:** CLICK carries `link_id` and `short_code` but no `workspace_id`. PRD describes analytics as workspace-scoped. Without `workspace_id` on CLICK, every analytics query must join LINK to filter — a leak primitive. The ERD's own Notes (line 108) state the policy: "Every Workspace-scoped row carries `workspace_id` directly." CLICK violates the stated policy.
**Fix:** Add `uuid workspace_id FK` to CLICK. Add relationship `WORKSPACE ||--o{ CLICK`. Index on `(workspace_id, clicked_at)` for time-range queries.
**Effort:** low

### [ERD-PRD-009] — WORKSPACE_MEMBER lacks (workspace_id, user_id) uniqueness
**Location:** `docs/erd.md:39`
**Finding:** PRD §Teams: "Every Member belongs to exactly one Workspace in v1." Plus the invite-collision rule reinforces user_id uniqueness across the table. ERD has no UK on user_id and no composite UK on (workspace_id, user_id). With `removed_at` present, the right shape is likely a partial unique on `user_id WHERE removed_at IS NULL`.
**Fix:** Add UK on (workspace_id, user_id), and document the partial-unique-on-user_id-where-active in Notes.
**Effort:** low

### [ERD-PRD-009] — INVITE lacks (workspace_id, email) pending uniqueness
**Location:** `docs/erd.md:50`
**Finding:** PRD §Teams: "Re-inviting a still-pending email replaces the existing invite." Implies at most one pending invite per (workspace_id, email). ERD declares only `token` as unique. Nothing prevents duplicate pending rows.
**Fix:** Add partial unique index on (workspace_id, email) WHERE status = 'pending'. Acknowledge in ERD Notes since Mermaid can't natively express partial uniqueness.
**Effort:** low

## Gate 3 — Warnings

(Three — `INVITE.status`, `WORKSPACE_MEMBER.role`, `INVITE.role` all plain `string` instead of signaled enums. See lookup table.)

## Summary

The ERD's most expensive defects are the two missing token entities (ERD-PRD-001 × 2) — the ERD's "Out of ERD scope" note acknowledges them but the PRD treats them as first-class stored objects with single-use TTL semantics, and that means they belong in the schema. The email encryption boundary (ERD-PRD-003) is the second-most-expensive: it propagates straight into ORM column types and migration design, and the `UK` constraint on encrypted email forces a search-hash pattern that nothing in the ERD signals. Multi-tenant scoping on CLICK (ERD-PRD-006) is the sharpest catch — the ERD's own policy statement contradicts its own diagram. Not safe to start ORM model code or architecture decisions on this version.
