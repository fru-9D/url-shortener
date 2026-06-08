# Migration Review — 2026-06-04

**File reviewed:** `c:\Users\faraz\Desktop\Code\url-shortener\backend\alembic\versions\0001_initial_schema.py`
**ERD context:** `c:\Users\faraz\Desktop\Code\url-shortener\docs\erd.md`
**ORM models:** `c:\Users\faraz\Desktop\Code\url-shortener\backend\app\models\`

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `0001_initial_schema.py:84–88` | `op.execute()` used for partial unique index on `workspace_member` — Alembic cannot express partial indexes via `op.create_index()` in standard dialect-agnostic form (PostgreSQL `WHERE` clause); this is a legitimate PostgreSQL-specific operation. See dismissal. | — | — | dismissed |
| `0001_initial_schema.py:155` | `server_default="'Unknown'"` on `click.country_code` is a business-logic sentinel value, not a DB-generated value | MIG-011 | 3 | warning |
| `0001_initial_schema.py:222–224` | `server_default="pending_review"` on `abuse_review.status` is a business-logic default, not a DB-generated value | MIG-011 | 3 | warning |
| `0001_initial_schema.py:100–104` | `server_default="pending"` on `invite.status` is a business-logic default, not a DB-generated value | MIG-011 | 3 | warning |

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| MIG-001 | Yes | `downgrade()` is fully implemented — drops all tables in correct dependency order, then drops all enum types. This is the very first migration (`down_revision = None`) and the downgrade is a complete teardown. Not flagged. |
| MIG-002 | Yes | `downgrade()` contains `op.drop_table()` calls, but this is the initial schema migration. Dropping all tables in `downgrade()` is the only correct reversal of `upgrade()` creating all tables. No data-loss risk beyond what is inherent in rolling back the initial schema. Not flagged. |
| MIG-003 | Yes | Every `NOT NULL` column added across all `op.create_table()` calls either (a) carries a `server_default`, or (b) is in a freshly created table (no pre-existing rows to backfire on). `user.created_at`, `user.updated_at`, `user.password_hash`, etc. are all new tables. Not flagged. |
| MIG-004 | Yes | All FK columns are either (a) part of a newly created table where no separate index is strictly required at table-creation time and are covered by the PK, or (b) covered by explicit indexes. Specific analysis: `workspace.owner_id` (FK to `user.id`) — no explicit index created. This is a moderate concern but the table is workspace-level, not high-volume, and the FK is only exercised for ownership checks. `workspace_member.workspace_id` and `workspace_member.user_id` — no explicit indexes beyond the partial unique on `user_id`. `invite.workspace_id`, `invite.inviter_id` — no explicit indexes. `link.workspace_id`, `link.owner_id`, `link.created_by_id` — `workspace_id` is covered by `ix_link_workspace_created`; `owner_id` and `created_by_id` have no standalone indexes. `click.link_id` — covered by `ix_click_link_clicked_at`. `click.workspace_id` — covered by `ix_click_workspace_clicked_at`. `password_reset_token.user_id`, `email_verification_token.user_id` — no explicit indexes. `abuse_review.link_id` — covered by `ix_abuse_review_link_flagged`. `abuse_review.reviewer_id` — no explicit index. These absences are noted under MIG-004 findings below. |
| MIG-005 | Yes | Three `op.execute()` calls at lines 84–88, 116–120, and 141–145 all create partial unique indexes using PostgreSQL's `WHERE` clause. Alembic's `op.create_index()` does support partial indexes via the `postgresql_where` keyword argument (as confirmed by the ORM models at `link.py:47–51` and `invite.py:56–62`). Therefore these `op.execute()` calls for partial index DDL **could** have been expressed structurally. However, the migration was written before this pattern was settled in the ORM, and the SQL is correct. This is flagged as MIG-005 below. |
| MIG-006 | Yes | All operations in `upgrade()` are DDL only — no DML (`UPDATE`, `INSERT`, `bulk_insert`). Not flagged. |
| MIG-007 | Yes | Enums are created using `postgresql.ENUM(...).create(op.get_bind(), checkfirst=True)` outside of `op.create_table()`, not via `ALTER TYPE ... ADD VALUE`. No enum values are being added to an existing type. Not flagged. |
| MIG-008 | Yes | The `click` table is high-volume (ERD notes: "append-only", "consider range-partitioning CLICK at high traffic volumes", "13-month rolling-delete"). Two indexes are created on it: `ix_click_workspace_clicked_at` and `ix_click_link_clicked_at`. However, these indexes are created at table-creation time (the table is new, zero rows), so `ACCESS EXCLUSIVE` lock has no operational impact — there is no existing data to scan. `CREATE INDEX CONCURRENTLY` is only meaningful when adding an index to a populated table. Not flagged. |
| MIG-009 | Yes | Revision message is `"initial schema"` — descriptive and unambiguous. Not flagged. |
| MIG-010 | Yes | All tables in this migration are part of the initial schema introduction. All are inter-related (user → workspace → workspace_member → invite → link → click → abuse_review, plus token and suppression tables). This is a single-feature "create the whole schema" migration. Not flagged. |
| MIG-012 | Yes | Only one migration file provided. `down_revision = None` correctly marks this as the root. Chain branching not checkable across multiple files. Not flagged. |

---

## Detailed findings

### MIG-004 — FK columns added without accompanying indexes

**Gate 2 — blocker**

The following FK columns are created in `upgrade()` with no corresponding `op.create_index()` in the same migration. FK columns without indexes cause full-table scans on every join or cascade operation.

**Finding 4a — `workspace.owner_id`**

```python
# 0001_initial_schema.py:63–66
sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
...
sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="RESTRICT"),
```

No index on `workspace.owner_id`. Any query joining workspace to user by owner, or cascading from user to workspace, will full-scan. At workspace scale this is low severity in practice, but the rule requires an index.

**Finding 4b — `workspace_member.workspace_id` and `workspace_member.user_id`**

```python
# 0001_initial_schema.py:73–81
sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
...
sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="RESTRICT"),
sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="RESTRICT"),
```

The partial unique index `uq_workspace_member_active_user` on `(user_id) WHERE removed_at IS NULL` covers active-member lookup on `user_id` but does NOT cover lookups where `removed_at IS NOT NULL` (historical members), and does not cover `workspace_id` at all. Any `SELECT * FROM workspace_member WHERE workspace_id = $1` requires a full-table scan.

**Finding 4c — `invite.workspace_id` and `invite.inviter_id`**

```python
# 0001_initial_schema.py:92–113
sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
...
sa.Column("inviter_id", postgresql.UUID(as_uuid=True), nullable=True),
...
sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"], ondelete="RESTRICT"),
sa.ForeignKeyConstraint(["inviter_id"], ["user.id"], ondelete="SET NULL"),
```

The partial unique on `(workspace_id, email_search_hash) WHERE status = 'pending'` covers active-invite lookups by workspace but only for the partial condition. A plain `workspace_id` index is absent. `inviter_id` has no index at all.

**Finding 4d — `link.owner_id` and `link.created_by_id`**

```python
# 0001_initial_schema.py:127–138
sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
...
sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="RESTRICT"),
sa.ForeignKeyConstraint(["created_by_id"], ["user.id"], ondelete="RESTRICT"),
```

`ix_link_workspace_created` covers `(workspace_id, created_at)`, not `owner_id` or `created_by_id`. Both are non-nullable FK columns queried in permission checks and attribution lookups. Neither has an index.

**Finding 4e — `password_reset_token.user_id` and `email_verification_token.user_id`**

```python
# 0001_initial_schema.py:170–177
sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
...
sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
```

Token lookup by `user_id` (e.g. "does this user have a pending token?") and cascade deletes on user removal require full-table scans without an index. Same pattern for `email_verification_token.user_id` at lines 183–191.

**Finding 4f — `abuse_review.workspace_id` and `abuse_review.reviewer_id`**

```python
# 0001_initial_schema.py:214–231
sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
...
sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"], ondelete="SET NULL"),
```

`ix_abuse_review_link_flagged` covers `(link_id, flagged_at)`. `ix_abuse_review_status` covers `status`. Neither covers `workspace_id` (needed for workspace-scoped ops queries per ERD notes) or `reviewer_id`. The ERD explicitly notes: "`ABUSE_REVIEW.workspace_id` enables workspace-scoped ops queries without a join to LINK" — but no index is created to support that access pattern.

**Effort:** low for each (add `op.create_index()` lines)

---

### MIG-005 — Raw `op.execute()` for DDL Alembic can express structurally

**Gate 2 — blocker**

Three partial unique indexes are created via raw `op.execute()` SQL:

```python
# 0001_initial_schema.py:84–88
op.execute(
    """CREATE UNIQUE INDEX uq_workspace_member_active_user
       ON workspace_member (user_id)
       WHERE removed_at IS NULL"""
)
```

```python
# 0001_initial_schema.py:116–120
op.execute(
    """CREATE UNIQUE INDEX uq_invite_pending_workspace_email
       ON invite (workspace_id, email_search_hash)
       WHERE status = 'pending'"""
)
```

```python
# 0001_initial_schema.py:141–145
op.execute(
    """CREATE UNIQUE INDEX uq_link_short_code_active
       ON link (short_code)
       WHERE deleted_at IS NULL"""
)
```

Alembic's `op.create_index()` supports the `postgresql_where` keyword argument for partial indexes. The ORM models for the same tables use this pattern correctly (e.g. `link.py:47–51`: `Index("uq_link_short_code_active", "short_code", unique=True, postgresql_where=text("deleted_at IS NULL"))`). The raw SQL bypasses Alembic's `--sql` dry-run mode and cross-dialect safety net.

The correct structural form is:

```python
op.create_index(
    "uq_workspace_member_active_user",
    "workspace_member",
    ["user_id"],
    unique=True,
    postgresql_where="removed_at IS NULL",
)
```

**Effort:** low (three `op.execute()` calls replaced with `op.create_index()`)

---

### MIG-011 — `server_default` set to business-logic values

**Gate 3 — warning**

**Finding 11a — `click.country_code`**

```python
# 0001_initial_schema.py:155
sa.Column("country_code", sa.String(8), nullable=False, server_default="'Unknown'"),
```

`"Unknown"` is a sentinel value meaningful to the application's geo-enrichment logic (per ERD: "ISO 3166-1 alpha-2 or Unknown"). It is not a database-generated value. The ORM model at `click.py:19` correctly uses `default="Unknown"` (application-layer default). The `server_default` here creates a dual-ownership situation — if the sentinel string changes, the migration must be amended as well as the ORM. Server defaults are appropriate for timestamps and sequences; application-layer sentinels belong in `default=` only.

**Finding 11b — `invite.status`**

```python
# 0001_initial_schema.py:100–104
sa.Column(
    "status",
    sa.Enum(..., name="invite_status"),
    nullable=False,
    server_default="pending",
),
```

`"pending"` is the initial state in the invite state machine. The ORM model at `invite.py:38` uses `default=InviteStatus.pending`. Having both a `server_default` and an ORM `default` is redundant and can produce divergent behaviour if the default ever changes and one side is updated but not the other.

**Finding 11c — `abuse_review.status`**

```python
# 0001_initial_schema.py:222–224
sa.Column(
    "status",
    sa.Enum(..., name="abuse_review_status"),
    nullable=False,
    server_default="pending_review",
),
```

Same pattern. `"pending_review"` is the initial state of the abuse review state machine. ORM model at `abuse_review.py:30` uses `default=AbuseReviewStatus.pending_review`. Dual defaults on a state-machine column.

**Effort:** low (remove `server_default` from the three columns; ORM `default=` already handles application-layer insertion)

---

## Step B — JSON findings array

```json
[
  {
    "domain": "migration-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "MIG-004",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 63,
    "snippet": "sa.Column(\"owner_id\", postgresql.UUID(as_uuid=True), nullable=False),\n...\nsa.ForeignKeyConstraint([\"owner_id\"], [\"user.id\"], ondelete=\"RESTRICT\"),",
    "message": "workspace.owner_id is a FK column with no accompanying index. Joins from workspace to user by owner_id will full-scan the workspace table.",
    "fix": "Add op.create_index(\"ix_workspace_owner_id\", \"workspace\", [\"owner_id\"]) after the create_table call.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "MIG-004",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 73,
    "snippet": "sa.Column(\"workspace_id\", postgresql.UUID(as_uuid=True), nullable=False),\nsa.ForeignKeyConstraint([\"workspace_id\"], [\"workspace.id\"], ondelete=\"RESTRICT\"),",
    "message": "workspace_member.workspace_id is a FK column with no covering index. Listing members of a workspace requires a full-table scan. The partial unique index on user_id does not cover workspace_id.",
    "fix": "Add op.create_index(\"ix_workspace_member_workspace_id\", \"workspace_member\", [\"workspace_id\"]) after the create_table call.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "MIG-004",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 98,
    "snippet": "sa.Column(\"inviter_id\", postgresql.UUID(as_uuid=True), nullable=True),\nsa.ForeignKeyConstraint([\"inviter_id\"], [\"user.id\"], ondelete=\"SET NULL\"),",
    "message": "invite.inviter_id is a FK column with no index. When an inviter is removed and their pending invites are cancelled atomically (PRD §Teams member removal), a full-scan of the invite table by inviter_id is required.",
    "fix": "Add op.create_index(\"ix_invite_inviter_id\", \"invite\", [\"inviter_id\"]) after the create_table call.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "MIG-004",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 127,
    "snippet": "sa.Column(\"owner_id\", postgresql.UUID(as_uuid=True), nullable=False),\nsa.Column(\"created_by_id\", postgresql.UUID(as_uuid=True), nullable=False),\nsa.ForeignKeyConstraint([\"owner_id\"], [\"user.id\"], ondelete=\"RESTRICT\"),\nsa.ForeignKeyConstraint([\"created_by_id\"], [\"user.id\"], ondelete=\"RESTRICT\"),",
    "message": "link.owner_id and link.created_by_id are FK columns with no indexes. Permission checks (owner_id) and attribution queries (created_by_id) will full-scan the link table. ix_link_workspace_created does not cover either column.",
    "fix": "Add op.create_index(\"ix_link_owner_id\", \"link\", [\"owner_id\"]) and op.create_index(\"ix_link_created_by_id\", \"link\", [\"created_by_id\"]) after the create_table call.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "MIG-004",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 170,
    "snippet": "sa.Column(\"user_id\", postgresql.UUID(as_uuid=True), nullable=False),\nsa.ForeignKeyConstraint([\"user_id\"], [\"user.id\"], ondelete=\"CASCADE\"),",
    "message": "password_reset_token.user_id and email_verification_token.user_id are FK columns with no indexes. Token lookups by user and cascade deletes on user removal require full-table scans.",
    "fix": "Add op.create_index(\"ix_password_reset_token_user_id\", \"password_reset_token\", [\"user_id\"]) and op.create_index(\"ix_email_verification_token_user_id\", \"email_verification_token\", [\"user_id\"]) after each respective create_table call.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "MIG-004",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 214,
    "snippet": "sa.Column(\"workspace_id\", postgresql.UUID(as_uuid=True), nullable=False),\nsa.Column(\"reviewer_id\", postgresql.UUID(as_uuid=True), nullable=True),\nsa.ForeignKeyConstraint([\"reviewer_id\"], [\"user.id\"], ondelete=\"SET NULL\"),",
    "message": "abuse_review.workspace_id and abuse_review.reviewer_id lack indexes. The ERD notes workspace_id enables workspace-scoped ops queries without joining LINK, but no index exists to serve that access pattern. reviewer_id full-scans on SET NULL cascade.",
    "fix": "Add op.create_index(\"ix_abuse_review_workspace_id\", \"abuse_review\", [\"workspace_id\"]) and op.create_index(\"ix_abuse_review_reviewer_id\", \"abuse_review\", [\"reviewer_id\"]) after the create_table call.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "MIG-005",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 84,
    "snippet": "op.execute(\n    \"\"\"CREATE UNIQUE INDEX uq_workspace_member_active_user\n       ON workspace_member (user_id)\n       WHERE removed_at IS NULL\"\"\"\n)",
    "message": "Three partial unique indexes are created via raw op.execute() SQL at lines 84, 116, and 141. Alembic's op.create_index() supports the postgresql_where keyword for partial indexes — the ORM models for the same tables already use this structured form. Raw SQL bypasses --sql dry-run mode.",
    "fix": "Replace each op.execute() partial index with op.create_index(..., postgresql_where=\"<condition>\"). Corresponding downgrade() already uses op.drop_index() which is consistent with the structured form.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 3,
    "severity": "warning",
    "rule": "MIG-011",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 155,
    "snippet": "sa.Column(\"country_code\", sa.String(8), nullable=False, server_default=\"'Unknown'\"),",
    "message": "server_default='Unknown' on click.country_code is a business-logic sentinel, not a DB-generated value. The ORM model already has default=\"Unknown\". Having both creates dual ownership: if the sentinel changes, the migration must also be updated.",
    "fix": "Remove server_default from this column. The ORM default= is sufficient for application-layer inserts.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 3,
    "severity": "warning",
    "rule": "MIG-011",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 100,
    "snippet": "sa.Column(\n    \"status\",\n    sa.Enum(..., name=\"invite_status\"),\n    nullable=False,\n    server_default=\"pending\",\n),",
    "message": "server_default='pending' on invite.status is a business-logic state-machine initial value. The ORM model already has default=InviteStatus.pending. Dual defaults on a state-machine column create a risk of divergence if the default ever changes.",
    "fix": "Remove server_default from this column. The ORM default= is sufficient.",
    "effort": "low"
  },
  {
    "domain": "migration-review",
    "gate": 3,
    "severity": "warning",
    "rule": "MIG-011",
    "file": "backend/alembic/versions/0001_initial_schema.py",
    "line": 222,
    "snippet": "sa.Column(\n    \"status\",\n    sa.Enum(..., name=\"abuse_review_status\"),\n    nullable=False,\n    server_default=\"pending_review\",\n),",
    "message": "server_default='pending_review' on abuse_review.status is a business-logic state-machine initial value. The ORM model already has default=AbuseReviewStatus.pending_review. Same dual-ownership concern as invite.status.",
    "fix": "Remove server_default from this column. The ORM default= is sufficient.",
    "effort": "low"
  }
]
```

---

## Step C — Domain summary

```json
{
  "domain": "migration-review",
  "gate1_count": 0,
  "gate2_count": 7,
  "gate3_count": 3,
  "verdict": "FAIL_BLOCKER"
}
```

---

## Summary

**Verdict: FAIL_BLOCKER**

The migration creates the correct schema — the tables, types, constraints, and partial unique indexes all match the ERD and ORM models. The `downgrade()` is complete and correct. No Gate 1 issues exist.

The two Gate 2 blockers are:

1. **MIG-004 (6 findings):** Nine FK columns across seven tables have no covering index. The most operationally significant are `workspace_member.workspace_id` (member-list queries), `link.owner_id` and `link.created_by_id` (permission and attribution lookups on the highest-volume write table), `abuse_review.workspace_id` (ops dashboard queries the ERD explicitly calls out), and `invite.inviter_id` (atomically cancelled on member removal). All fixes are one-line `op.create_index()` additions — effort is low per finding.

2. **MIG-005 (1 finding):** Three partial unique indexes use raw `op.execute()` SQL even though `op.create_index(..., postgresql_where=...)` is the supported structured form. The inconsistency is highlighted by the fact that the ORM `__table_args__` for the same tables use the structured Alembic form correctly.

The Gate 3 warnings are dual `server_default` / ORM `default=` declarations on three state-machine status columns — correctness risk is low now, but is a maintenance hazard if defaults change in future migrations.

All issues have **low** estimated fix effort. The migration should not be applied to staging or CI until the missing FK indexes and the `op.execute()` partial-index calls are addressed in the same migration file (since this is the initial schema and no data exists yet, editing this file directly before first apply is the cleanest resolution).
