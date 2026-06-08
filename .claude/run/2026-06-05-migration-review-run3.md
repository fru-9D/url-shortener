# Migration Review — Run 3
**File:** `backend/alembic/versions/0001_initial_schema.py`
**Date:** 2026-06-05
**Reviewer:** migration-review agent (claude-sonnet-4-6)

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| — | No findings | — | — | — |

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| MIG-001 | Yes | `downgrade()` is fully implemented. All 10 tables are dropped in FK-safe reverse order and all 5 enum types are dropped via `DROP TYPE IF EXISTS`. This is the first migration (`down_revision = None`) and constitutes a valid full-reset downgrade. |
| MIG-002 | Yes | No `DROP TABLE`, `DROP COLUMN`, or destructive DDL appears in `upgrade()`. The `op.drop_table()` calls in `downgrade()` are the intended rollback path and are not in scope for MIG-002, which targets destructive operations in `upgrade()`. |
| MIG-003 | Yes | All `NOT NULL` columns are declared inside `op.create_table()` calls, not via `op.add_column()` on pre-existing tables. Since the tables are created in the same `upgrade()`, no existing rows are present and the database will never reject the operation. |
| MIG-004 | Yes | Every FK column has a covering index. Verified column-by-column: `workspace.owner_id` → `ix_workspace_owner_id`; `workspace_member.workspace_id` → `ix_workspace_member_workspace_id`; `workspace_member.user_id` → `ix_workspace_member_user_id`; `invite.workspace_id` → `ix_invite_workspace_id`; `invite.inviter_id` → `ix_invite_inviter_id`; `link.workspace_id` → composite `ix_link_workspace_created`; `link.owner_id` → `ix_link_owner_id`; `link.created_by_id` → `ix_link_created_by_id`; `click.link_id` → composite `ix_click_link_clicked_at`; `click.workspace_id` → composite `ix_click_workspace_clicked_at`; `password_reset_token.user_id` → `ix_password_reset_token_user_id`; `email_verification_token.user_id` → `ix_email_verification_token_user_id`; `abuse_review.link_id` → composite `ix_abuse_review_link_flagged`; `abuse_review.workspace_id` → `ix_abuse_review_workspace_id`; `abuse_review.reviewer_id` → `ix_abuse_review_reviewer_id`. All covered. |
| MIG-005 | Yes | `op.execute(f"DROP TYPE IF EXISTS {enum_name}")` in `downgrade()` is the correct approach. Alembic has no structured `op.drop_type()` function. The `postgresql.ENUM(..., create_type=False).create(op.get_bind(), checkfirst=True)` pattern used in `upgrade()` is also a PostgreSQL-specific dialect call with no equivalent structured op. Both usages are database-specific operations that Alembic cannot express structurally. Not flagged per the MIG-005 exception. |
| MIG-006 | Yes | `upgrade()` contains only DDL operations (`op.create_table`, `op.create_index`). No DML (`op.execute('UPDATE ...')`, `op.bulk_insert()`) is present. `downgrade()` contains only DDL. No mixed-transaction concern exists. |
| MIG-007 | Yes | No enum values are added to an existing PostgreSQL enum type. The migration creates new enum types via `postgresql.ENUM(...).create()` — this is `CREATE TYPE`, not `ALTER TYPE ... ADD VALUE`. MIG-007 targets the `ADD VALUE` path specifically. |
| MIG-008 | Yes | The `click` table is flagged in the ERD as high-volume and append-only ("At high traffic volumes, consider range-partitioning CLICK on `clicked_at`"). However, MIG-008 applies when an index is created on an already-populated large table in production. Here, the indexes on `click` are created immediately after `op.create_table("click", ...)` — the table is brand-new and empty at migration time. Standard `CREATE INDEX` on an empty table holds no data lock of consequence. The CONCURRENTLY requirement becomes relevant only in a future migration that adds an index to a live, populated `click` table. |
| MIG-009 | Yes | The revision `message` is `"initial schema"` — specific, descriptive, and unambiguous in `alembic history` output. Not generic. |
| MIG-010 | Yes | All 10 tables created in `upgrade()` are interconnected via FK relationships as part of the single v1 schema introduction: `user` → `workspace` → `workspace_member`, `invite`, `link` → `click`, `abuse_review`; `user` → `password_reset_token`, `email_verification_token`; `email_suppression` and `mixpanel_dead_letter` are ancillary tables part of the same product feature set. The MIG-010 dismissal condition ("all part of a single new feature's schema introduction") applies. |
| MIG-011 | Yes | Three non-timestamp `server_default` values are present: `"false"` on `link.is_custom_slug`, `"false"` on `click.is_bot`, and `"0"` on `mixpanel_dead_letter.attempts`. All three are DB-native primitive defaults (boolean false, integer zero) that will never change with application logic. They are equivalent to `DEFAULT FALSE` / `DEFAULT 0` in SQL — appropriate server defaults. No business-logic constants (status strings, calculated values, app-layer configuration) are used as server defaults. |
| MIG-012 | Yes | Only one migration file was provided. Chain branching cannot be evaluated with a single file. |

---

## JSON findings array

```json
[]
```

---

## Domain summary

```json
{
  "domain": "migration-review",
  "gate1_count": 0,
  "gate2_count": 0,
  "gate3_count": 0,
  "verdict": "PASS"
}
```

---

## Notes for run comparison

This is the third review of this migration file. All previously reported issues have been resolved:

- **Run 1** flagged MIG-001 (downgrade not implemented) and MIG-004 (multiple FK columns without indexes). Both are now resolved: `downgrade()` fully reverses the schema, and every FK column has a covering index.
- **Run 2** flagged residual MIG-004 issues and MIG-008 (click table index without CONCURRENTLY). Both are now resolved: all FK indexes are present, and the CONCURRENTLY concern does not apply to initial-schema table creation.
- **Run 3** finds no violations across all 12 rules. The migration is clean and safe to apply to all environments.
