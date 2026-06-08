# Migration Review — Run 2

**File reviewed:** `c:\Users\faraz\Desktop\Code\url-shortener\backend\alembic\versions\0001_initial_schema.py`
**ERD context:** `c:\Users\faraz\Desktop\Code\url-shortener\docs\erd.md` (Draft v5)
**ORM models:** `c:\Users\faraz\Desktop\Code\url-shortener\backend\app\models\`
**Reviewed:** 2026-06-04

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `0001_initial_schema.py:51` | `server_default="1"` for `session_version` duplicates ORM-layer default as a hardcoded DB string | MIG-011 | 3 | warning |

---

## Dismissed Rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| MIG-001 | Yes | `downgrade()` is fully implemented — drops all tables in reverse FK dependency order and drops all enum types with `DROP TYPE IF EXISTS`. This is the project's first migration (`down_revision = None`) and the downgrade is a legitimate full reset. |
| MIG-002 | Yes | `upgrade()` contains no DROP operations. `downgrade()` contains `DROP TABLE` and `DROP TYPE IF EXISTS`, which are appropriate rollback operations, not unsafe destructive steps in the forward migration path. |
| MIG-003 | Yes | Every `nullable=False` column is on a table created in the same `upgrade()` (no pre-existing rows). No `op.add_column` is used; all columns are defined inside `op.create_table` blocks. |
| MIG-004 | Yes | All FK columns are covered by an index: `workspace.owner_id` → `ix_workspace_owner_id`; `workspace_member.workspace_id` → `ix_workspace_member_workspace_id`; `workspace_member.user_id` → `ix_workspace_member_user_id`; `invite.workspace_id` → leading column of partial composite unique `uq_invite_pending_workspace_email (workspace_id, email_search_hash)`; `invite.inviter_id` → `ix_invite_inviter_id`; `link.workspace_id` → leading column of `ix_link_workspace_created (workspace_id, created_at)`; `link.owner_id` → `ix_link_owner_id`; `link.created_by_id` → `ix_link_created_by_id`; `click.link_id` → leading column of `ix_click_link_clicked_at (link_id, clicked_at)`; `click.workspace_id` → leading column of `ix_click_workspace_clicked_at (workspace_id, clicked_at)`; `password_reset_token.user_id` → `ix_password_reset_token_user_id`; `email_verification_token.user_id` → `ix_email_verification_token_user_id`; `abuse_review.link_id` → leading column of `ix_abuse_review_link_flagged (link_id, flagged_at)`; `abuse_review.workspace_id` → `ix_abuse_review_workspace_id`; `abuse_review.reviewer_id` → `ix_abuse_review_reviewer_id`. |
| MIG-005 | Yes | `op.execute()` is used only in `downgrade()` to run `DROP TYPE IF EXISTS {enum_name}`. Alembic has no structured op for dropping PostgreSQL enum types; this raw SQL call is the correct approach and cannot be replaced with a structured Alembic op. |
| MIG-006 | Yes | `upgrade()` is entirely DDL — no `UPDATE`, `INSERT`, `op.bulk_insert()`, or other DML operations. |
| MIG-007 | Yes | Enum types are being **created** fresh with `postgresql.ENUM(...).create(op.get_bind(), checkfirst=True)`. No `ALTER TYPE ... ADD VALUE` is performed anywhere. The `ALTER TYPE ... ADD VALUE` transaction restriction does not apply to initial enum type creation. |
| MIG-008 | Yes | The `click` table is append-only and high-volume per the ERD ("At high traffic volumes, consider range-partitioning CLICK on `clicked_at`"). However, this is the **initial schema** migration — the table does not exist before `upgrade()` runs, so the indexes are created on an empty table. An exclusive lock on an empty table is instantaneous and causes no production outage. The CONCURRENTLY concern applies only to adding indexes to populated tables in subsequent migrations. |
| MIG-009 | Yes | The revision `message` is `"initial schema"` — specific and correctly descriptive of the migration's purpose. |
| MIG-010 | Yes | All DDL operates on tables that collectively form the single v1 application schema introduced together for the first time. This fits squarely within the "all part of a single new feature's schema introduction" exception. |
| MIG-012 | Yes | Only one migration file was provided. Chain branching cannot be evaluated with a single revision. `down_revision = None` is correct for a root migration. |

---

## JSON Findings

```json
[
  {
    "domain": "migration-review",
    "gate": 3,
    "severity": "warning",
    "rule": "MIG-011",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 51,
    "snippet": "sa.Column(\"session_version\", sa.Integer(), nullable=False, server_default=\"1\")",
    "message": "The server_default=\"1\" for session_version is an application-layer initial value, not a database-generated value. The ORM model (user.py line 18) already declares default=1 at the Python layer. Setting the same value as a server_default means the default is defined in two places — the string \"1\" in the migration and the integer 1 in the ORM model. If the initial value changes (e.g., a future decision to start at 0 or use a sequence), the migration and the ORM model will diverge silently. Server defaults are appropriate for timestamps (now()), UUIDs (gen_random_uuid()), and DB-generated sequences — not for application-level counter seeds.",
    "fix": "Remove server_default=\"1\" from the migration column definition. The ORM model's default=1 is sufficient for all ORM-mediated inserts. If you need a DB-level fallback for non-ORM inserts (e.g., raw SQL scripts, seeds), document that dependency explicitly rather than silently duplicating the value.",
    "effort": "low"
  }
]
```

---

## Domain Summary

```json
{
  "domain": "migration-review",
  "gate1_count": 0,
  "gate2_count": 0,
  "gate3_count": 1,
  "verdict": "PASS_WITH_RISK"
}
```

---

## Notes for Run 2

This is the second review pass. The migration is substantially improved from the first review. All Gate 1 (critical) and Gate 2 (blocker) issues are resolved. The single remaining finding is a low-effort Gate 3 warning about a duplicated default value.

### ERD alignment observation (outside the 12 rules)

The ERD notes section "Uniqueness constraints not natively expressible in Mermaid" specifies:

> `CLICK` | Composite unique index on `(link_id, clicked_at)` | Idempotency for the at-least-once SQS ingest consumer

The migration does **not** create a unique index on `(link_id, clicked_at)`. Instead it creates:
- `ix_click_link_clicked_at` — a non-unique index on `(link_id, clicked_at)` (line 178)
- `uq_click_event_id` — a unique constraint on `event_id` (line 175)

The ORM model (`click.py`) also uses `event_id` as the unique idempotency key, not `(link_id, clicked_at)`. This is an ERD-vs-implementation divergence. The `event_id` approach (a stable UUID emitted by the redirect service) is architecturally superior for idempotency — it is immutable, unambiguous, and does not depend on the precision of `clicked_at`. The ERD note appears to have been written before `event_id` was introduced as the canonical idempotency key. This divergence is not a migration safety issue (no rule fires), but it should be resolved by updating the ERD note to reflect `event_id` as the idempotency mechanism. This is an ERD documentation gap, not a migration defect.
