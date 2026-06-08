# ORM Review — Run 2
**Date:** 2026-06-04
**ERD:** `docs/erd.md` (Draft v5, derived from PRD v5)
**Models reviewed:**
- `backend/app/models/user.py`
- `backend/app/models/link.py`
- `backend/app/models/workspace.py`
- `backend/app/models/tokens.py`
- `backend/app/models/click.py`
- `backend/app/models/abuse_review.py`
- `backend/app/models/email_suppression.py`
- `backend/app/models/invite.py`
- `backend/app/models/mixpanel_dead_letter.py`
- `backend/app/models/base.py` (TimestampMixin)

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `backend/app/models/workspace.py:50-51` | `joined_at` and `removed_at` on WorkspaceMember declared with no explicit `DateTime(timezone=True)` — SQLAlchemy infers `DateTime` without timezone from the annotation, producing `TIMESTAMP WITHOUT TIME ZONE` while the rest of the codebase uses `TIMESTAMP WITH TIME ZONE` | ORM-ERD-003 | 2 | blocker |
| `backend/app/models/user.py:15` and `user.py:47` | `email_search_hash` carries both `unique=True` on the column definition and `UniqueConstraint("email_search_hash", ...)` in `__table_args__` — Alembic will emit two unique indexes on the same column | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/tokens.py:16` and `tokens.py:25` | `PasswordResetToken.token_hash` carries both `unique=True` on the column and `UniqueConstraint("token_hash", ...)` in `__table_args__` — duplicate unique index | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/tokens.py:40` and `tokens.py:49` | `EmailVerificationToken.token_hash` same duplication as above | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/email_suppression.py:21` and `email_suppression.py:28` | `EmailSuppression.email_search_hash` carries both `unique=True` on the column and `UniqueConstraint(...)` in `__table_args__` — duplicate unique index | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/invite.py:40` and `invite.py:52` | `Invite.token_hash` carries both `unique=True` on the column and `UniqueConstraint(...)` in `__table_args__` — duplicate unique index | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/click.py:21` and `click.py:38` | `Click.event_id` carries both `unique=True` on the column and `UniqueConstraint("event_id", ...)` in `__table_args__` — duplicate unique index | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/click.py:9` | Click model defines no `workspace` relationship back to Workspace; ERD `WORKSPACE \|\|--o{ CLICK` implies bidirectional navigability | ORM-ERD-010 | 3 | warning |
| `backend/app/models/abuse_review.py:17` | AbuseReview model defines no `workspace` relationship back to Workspace; ERD `WORKSPACE \|\|--o{ ABUSE_REVIEW` implies bidirectional navigability | ORM-ERD-010 | 3 | warning |
| `backend/app/models/invite.py:28-29` | `Invite.workspace_id` FK is only covered by a partial unique index (`WHERE status = 'pending'`) — non-pending workspace_id lookups (e.g., listing all invites for a workspace) have no index | ORM-ERD-012 | 3 | warning |

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ORM-ERD-001 | Yes | All 11 non-Redis ERD entities have corresponding model classes. SESSION and LOGIN_ATTEMPT are explicitly documented as Redis-backed in ERD Notes §Session — no ORM model expected. |
| ORM-ERD-002 | Yes | All 11 model classes (User, Workspace, WorkspaceMember, Invite, Link, Click, PasswordResetToken, EmailVerificationToken, EmailSuppression, MixpanelDeadLetter, AbuseReview) map to ERD entities. No orphan models found. |
| ORM-ERD-003 (all columns except WorkspaceMember.joined_at/removed_at) | Yes | All other columns use correct SQLAlchemy types matching ERD declarations. UUID columns use `UUID(as_uuid=True)`; string columns use `String`/`String(n)`; boolean columns use `Boolean`; datetime columns use `DateTime(timezone=True)`; integer columns use `Integer`; JSONB payload matches ERD `json` (JSONB is the preferred PostgreSQL supertype). |
| ORM-ERD-004 | Yes | Every model uses `UUID(as_uuid=True)` as primary key, matching `uuid id PK` in all ERD entities. No composite PK mismatches. |
| ORM-ERD-005 | Yes | All FK columns present and pointing to correct tables. MixpanelDeadLetter.workspace_id has no `ForeignKey()` — ERD body does not mark it as `FK` and Notes document it as nullable context field; this matches the model. All other FK relationships verified. |
| ORM-ERD-007 | Yes | All models using TimestampMixin have `created_at` with `server_default=func.now()` and `updated_at` with `onupdate=func.now()`. Click intentionally omits `updated_at` — documented in ERD Notes §Click table ("CLICK is append-only — no field mutates after insert; updated_at is intentionally omitted") and in the model's class docstring. |
| ORM-ERD-008 | Yes | ERD Notes §Email encryption documents email storage as application-layer AES-256-GCM encryption — the ORM stores the already-encrypted ciphertext string. The Notes do not require a TypeDecorator or ORM-level wrapper; plaintext is never passed to the ORM. Plain `String` columns for `email_ciphertext` are consistent with the documented strategy. |
| ORM-ERD-009 | Yes | All `relationship()` declarations use correct cardinality: one-to-many relationships use the default `uselist=True` via `list[...]` mapped types; the nullable reviewer relationship on AbuseReview uses `User | None` typed mapping (uselist=False). All FK-side cardinalities match ERD notation. |
| ORM-ERD-010 (User ↔ Workspace, User ↔ WorkspaceMember, etc.) | Yes | All explicitly navigated bidirectional pairs use `back_populates` correctly. Only the Workspace ↔ Click and Workspace ↔ AbuseReview pairs are missing back_populates — flagged above. |
| ORM-ERD-011 | Yes | Parent-child cascades are correctly configured where documented: `LINK → CLICK` and `LINK → ABUSE_REVIEW` both use `cascade="all, delete-orphan"` on the ORM side with `ondelete="CASCADE"` on the FK. `USER → PasswordResetToken` and `USER → EmailVerificationToken` same. Workspace relationships intentionally use `ondelete="RESTRICT"` — no workspace deletion in v1 (ERD Notes §Out of ERD scope). |
| ORM-ERD-012 (all FK columns except Invite.workspace_id) | Yes | All other FK columns are covered by explicit `Index(...)` declarations or are leading columns in composite indexes. See Lookup table for the one gap on Invite.workspace_id. |
| ORM-ERD-013 | Yes | All `__tablename__` values follow snake_case singular convention consistent with all ERD entity names lowercased. |
| ORM-ERD-014 | Yes | All nullable/non-nullable declarations are consistent with ERD cardinality notation. Mandatory FKs (`||` on the owning side) are `nullable=False`; optional FKs (`o|`) are `nullable=True`. WorkspaceMember.joined_at and removed_at nullable=True is correct — ERD has no mandatory-presence marker on those columns. |

---

## JSON findings

```json
[
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-003",
    "file": "backend/app/models/workspace.py",
    "line": 50,
    "snippet": "joined_at: Mapped[\"datetime | None\"] = mapped_column(nullable=True)  # type: ignore[assignment]\n    removed_at: Mapped[\"datetime | None\"] = mapped_column(nullable=True)  # type: ignore[assignment]",
    "message": "WorkspaceMember.joined_at and removed_at are declared with no explicit SQLAlchemy type. SQLAlchemy 2.x infers bare DateTime (TIMESTAMP WITHOUT TIME ZONE) from the Python annotation, diverging from the rest of the codebase which consistently uses DateTime(timezone=True) (TIMESTAMP WITH TIME ZONE). The ERD declares these as datetime columns, which in this codebase means timezone-aware.",
    "fix": "Add explicit DateTime(timezone=True) to both mapped_column declarations, matching the pattern used by every other datetime column in the codebase.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/user.py",
    "line": 15,
    "snippet": "email_search_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  [line 15]\n    __table_args__ = (UniqueConstraint(\"email_search_hash\", name=\"uq_user_email_search_hash\"),)  [line 47]",
    "message": "User.email_search_hash declares the unique constraint twice: once via unique=True on the column definition (which Alembic emits as an inline unique index) and once via an explicit UniqueConstraint in __table_args__. Alembic autogenerate will emit two separate unique indexes on the same column, making the migration incorrect. The same duplication exists in PasswordResetToken.token_hash, EmailVerificationToken.token_hash, EmailSuppression.email_search_hash, Invite.token_hash, and Click.event_id.",
    "fix": "Remove unique=True from the column definition on all six affected columns and keep only the named UniqueConstraint in __table_args__. The named constraint is preferable as it produces a deterministic migration name.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/tokens.py",
    "line": 16,
    "snippet": "token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  [line 16]\n    __table_args__ = (UniqueConstraint(\"token_hash\", name=\"uq_password_reset_token_hash\"), ...)  [line 25]",
    "message": "PasswordResetToken.token_hash duplicates its unique constraint via both column-level unique=True and an explicit UniqueConstraint in __table_args__. Alembic will generate two unique indexes for this column.",
    "fix": "Remove unique=True from the token_hash mapped_column definition; keep the named UniqueConstraint.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/tokens.py",
    "line": 40,
    "snippet": "token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  [line 40]\n    __table_args__ = (UniqueConstraint(\"token_hash\", name=\"uq_email_verification_token_hash\"), ...)  [line 49]",
    "message": "EmailVerificationToken.token_hash has the same duplicate unique constraint issue as PasswordResetToken.",
    "fix": "Remove unique=True from the token_hash mapped_column definition; keep the named UniqueConstraint.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/email_suppression.py",
    "line": 21,
    "snippet": "email_search_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  [line 21]\n    __table_args__ = (UniqueConstraint(\"email_search_hash\", name=\"uq_email_suppression_search_hash\"),)  [line 28]",
    "message": "EmailSuppression.email_search_hash duplicates its unique constraint via column-level unique=True and an explicit UniqueConstraint in __table_args__.",
    "fix": "Remove unique=True from the email_search_hash mapped_column definition; keep the named UniqueConstraint.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/invite.py",
    "line": 40,
    "snippet": "token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  [line 40]\n    __table_args__ = (UniqueConstraint(\"token_hash\", name=\"uq_invite_token_hash\"), ...)  [line 52]",
    "message": "Invite.token_hash duplicates its unique constraint via column-level unique=True and an explicit UniqueConstraint in __table_args__.",
    "fix": "Remove unique=True from the token_hash mapped_column definition; keep the named UniqueConstraint.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/click.py",
    "line": 21,
    "snippet": "event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)  [line 21]\n    UniqueConstraint(\"event_id\", name=\"uq_click_event_id\"),  [line 38]",
    "message": "Click.event_id duplicates its unique constraint via column-level unique=True and an explicit UniqueConstraint in __table_args__.",
    "fix": "Remove unique=True from the event_id mapped_column definition; keep the named UniqueConstraint.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-010",
    "file": "backend/app/models/click.py",
    "line": 9,
    "snippet": "ERD: `WORKSPACE ||--o{ CLICK` — Click model has no `workspace` relationship; Workspace model has no `clicks` collection.",
    "message": "The ERD declares WORKSPACE has many CLICKs. The Click model has no relationship() to Workspace and Workspace has no clicks collection. Traversal from a Workspace instance to its clicks (e.g. for workspace analytics) silently produces an extra query rather than using a mapped relationship.",
    "fix": "Add relationship('Workspace', back_populates='clicks') to Click and a clicks collection relationship to Workspace, or at minimum add back_populates if the workspace-side collection is useful.",
    "effort": "medium"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-010",
    "file": "backend/app/models/abuse_review.py",
    "line": 17,
    "snippet": "ERD: `WORKSPACE ||--o{ ABUSE_REVIEW` — AbuseReview model has no `workspace` relationship; Workspace model has no `abuse_reviews` collection.",
    "message": "The ERD declares WORKSPACE has many ABUSE_REVIEWs. AbuseReview has no relationship() to Workspace and Workspace has no abuse_reviews collection. Workspace-scoped ops queries (ERD Notes §Abuse review: 'workspace_id enables workspace-scoped ops queries') cannot navigate from a Workspace ORM instance without an extra query.",
    "fix": "Add relationship('Workspace', back_populates='abuse_reviews') to AbuseReview and an abuse_reviews collection to Workspace.",
    "effort": "medium"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/invite.py",
    "line": 28,
    "snippet": "workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"workspace.id\", ondelete=\"RESTRICT\"), nullable=False)",
    "message": "Invite.workspace_id has no standalone index. The only index covering this column is the partial unique index uq_invite_pending_workspace_email (WHERE status = 'pending'). Queries that list all invites for a workspace regardless of status (e.g., invite history, expired invite display) will fall back to a full-table scan. The ERD Notes §Multi-tenant scoping states workspace_id should be directly queryable.",
    "fix": "Add Index('ix_invite_workspace_id', 'workspace_id') to Invite.__table_args__.",
    "effort": "low"
  }
]
```

---

## Domain summary

```json
{
  "domain": "orm-review",
  "gate1_count": 0,
  "gate2_count": 7,
  "gate3_count": 3,
  "verdict": "FAIL_BLOCKER"
}
```

---

## Notes on improvements since Run 1

Significant progress was made between runs. The following previously-flagged issues have been resolved:

- `CLICK.updated_at` absence is now correctly justified in both the ERD Notes and the model's class docstring.
- `Click.event_id` unique constraint is now present (the ERD Notes §Click table documents idempotency keying on event_id).
- `LINK.short_code` partial unique index is correctly implemented with `postgresql_where=text("deleted_at IS NULL")`.
- `WORKSPACE_MEMBER` partial unique index on `user_id WHERE removed_at IS NULL` is correctly implemented.
- All audit columns (TimestampMixin) are consistently applied except where explicitly excluded.
- `back_populates` is now declared on nearly all bidirectional relationship pairs.
- `MixpanelDeadLetter.updated_at` is now present (ERD v5 added it to reflect that `attempts` and `last_error` mutate).
- Cascade semantics on token and review child tables are correctly configured.

The 7 Gate 2 blockers remaining are all in the same category (duplicate unique constraint declarations) plus one timezone-type omission — all are low-effort, mechanical fixes before migration generation.
