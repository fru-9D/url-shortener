# ORM Review — Run 3
**Date:** 2026-06-05
**ERD:** `docs/erd.md` (Draft v5, derived from PRD v5 2026-06-04)
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
- `backend/app/models/base.py` (TimestampMixin, read for audit-column analysis)

---

## Entity-to-Model Mapping

| ERD Entity | ORM Model Class | File | Disposition |
|---|---|---|---|
| USER | User | user.py | Mapped |
| SESSION | — | — | ERD Notes: Redis-backed, no ORM model generated |
| LOGIN_ATTEMPT | — | — | ERD Notes: Redis-backed, no ORM model generated |
| WORKSPACE | Workspace | workspace.py | Mapped |
| WORKSPACE_MEMBER | WorkspaceMember | workspace.py | Mapped |
| INVITE | Invite | invite.py | Mapped |
| LINK | Link | link.py | Mapped |
| CLICK | Click | click.py | Mapped |
| PASSWORD_RESET_TOKEN | PasswordResetToken | tokens.py | Mapped |
| EMAIL_VERIFICATION_TOKEN | EmailVerificationToken | tokens.py | Mapped |
| EMAIL_SUPPRESSION | EmailSuppression | email_suppression.py | Mapped |
| MIXPANEL_DEAD_LETTER | MixpanelDeadLetter | mixpanel_dead_letter.py | Mapped |
| ABUSE_REVIEW | AbuseReview | abuse_review.py | Mapped |

---

## STEP A — Lookup Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `backend/app/models/click.py:22` | `event_id` column present in Click model but not declared in the ERD CLICK entity; the ERD Notes mandate a composite unique index on `(link_id, clicked_at)` for idempotency — that index is absent from the model | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/user.py:14` | `email_ciphertext: Mapped[str] = mapped_column(String, nullable=False)` — plain String type, no TypeDecorator or encryption wrapper; ERD Notes §Email encryption mandates AES-256-GCM application-layer encryption for this column | ORM-ERD-008 | 2 | blocker |
| `backend/app/models/invite.py:32` | `email_ciphertext: Mapped[str] = mapped_column(String, nullable=False)` — plain String type, no TypeDecorator or encryption wrapper; ERD Notes §Email encryption mandates AES-256-GCM encryption for all email_ciphertext columns | ORM-ERD-008 | 2 | blocker |
| `backend/app/models/mixpanel_dead_letter.py:14` | `workspace_id: Mapped[uuid.UUID \| None] = mapped_column(UUID(as_uuid=True), nullable=True)` — no Index declared on this FK-like column; the ERD Notes §Multi-tenant scoping identifies workspace_id as a query dimension on this table | ORM-ERD-012 | 3 | warning |

---

## STEP A-bis — Dismissed Rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ORM-ERD-001 | Yes | All ERD entities have a corresponding model class. SESSION and LOGIN_ATTEMPT are explicitly documented in ERD Notes §Session and login-attempt state as Redis-backed — no ORM model or migration is generated for them. |
| ORM-ERD-002 | Yes | All model classes (User, Workspace, WorkspaceMember, Invite, Link, Click, PasswordResetToken, EmailVerificationToken, EmailSuppression, MixpanelDeadLetter, AbuseReview) map to declared ERD entities. No orphan models found. |
| ORM-ERD-003 | Yes | All column types are equivalent to ERD declarations. MixpanelDeadLetter.payload uses JSONB (equivalent to ERD `json`). Click.is_bot uses Boolean (equivalent to ERD `boolean`). No Float/Double used for decimal columns. No Integer used for uuid PK. |
| ORM-ERD-004 | Yes | All entities use `uuid id PK`; all models use `UUID(as_uuid=True)` as primary key. No composite PK entities exist in the ERD. No mismatches found. |
| ORM-ERD-005 | Yes | All ERD-implied FKs are present and point to correct tables. LINK has workspace_id→workspace.id, owner_id→user.id, created_by_id→user.id. CLICK has link_id→link.id, workspace_id→workspace.id. WORKSPACE_MEMBER has workspace_id→workspace.id, user_id→user.id. INVITE has workspace_id→workspace.id, inviter_id→user.id. ABUSE_REVIEW has link_id→link.id, workspace_id→workspace.id, reviewer_id→user.id. Token tables have user_id→user.id. MixpanelDeadLetter.workspace_id carries no FK marker in the ERD and no relationship line to WORKSPACE — not flagged. |
| ORM-ERD-006 (partial) | Yes | ORM-ERD-006 is fired for the CLICK entity's missing `(link_id, clicked_at)` unique index. All other ERD-declared UK constraints are satisfied: USER.email_search_hash (UniqueConstraint), INVITE.token_hash (UniqueConstraint), PASSWORD_RESET_TOKEN.token_hash (UniqueConstraint), EMAIL_VERIFICATION_TOKEN.token_hash (UniqueConstraint), EMAIL_SUPPRESSION.email_search_hash (UniqueConstraint), LINK.short_code (partial unique Index with postgresql_where), WORKSPACE_MEMBER.user_id (partial unique Index with postgresql_where), INVITE.(workspace_id, email_search_hash) WHERE status='pending' (partial unique Index). |
| ORM-ERD-007 | Yes | TimestampMixin (base.py) provides created_at with server_default=func.now() and updated_at with onupdate=func.now(). All models use TimestampMixin except Click. Click is explicitly documented in ERD Notes §Click table as "append-only — no field mutates after insert; updated_at is intentionally omitted." Click.created_at has server_default=func.now(). No audit column violations found. |
| ORM-ERD-008 (partial) | Yes | ORM-ERD-008 is fired for User.email_ciphertext and Invite.email_ciphertext. EmailSuppression.email_ciphertext has an inline comment "Encrypted for ops/audit use" acknowledging the protection strategy — dismissed per rule exception ("or comment acknowledging the protection strategy"). |
| ORM-ERD-009 | Yes | All relationship() declarations use correct cardinality. One-to-many relationships use list-typed Mapped (uselist=True by inference). ABUSE_REVIEW.reviewer uses `Mapped["User \| None"]` (uselist=False) matching the `USER o\|--o{` optional-one cardinality. No many-to-many entities exist in the ERD. No mismatches found. |
| ORM-ERD-010 | Yes | All bidirectional relationships declare back_populates on both sides. Checked: User↔WorkspaceMember, User↔Workspace (owner), User↔Link (owner and creator), User↔Invite (inviter), User↔AbuseReview (reviewer), Workspace↔WorkspaceMember, Workspace↔Link, Workspace↔Click, Workspace↔Invite, Workspace↔AbuseReview, Link↔Click, Link↔AbuseReview. No missing back_populates found. |
| ORM-ERD-011 | Yes | Cascade is declared where ERD/PRD describes deletion cascades. Link.clicks has cascade="all, delete-orphan" with ondelete="CASCADE" on FK. Link.abuse_reviews has cascade="all, delete-orphan". User.password_reset_tokens and User.email_verification_tokens have cascade="all, delete-orphan". Workspace deletion is explicitly out of scope for v1 per ERD Notes §"Workspace deletion lifecycle" — absence of cascade on Workspace.members, Workspace.links, Workspace.invites is therefore justified. |
| ORM-ERD-012 (partial) | Yes | ORM-ERD-012 is fired for MixpanelDeadLetter.workspace_id. All other FK columns have corresponding indexes: Link (workspace_id composite, owner_id, created_by_id), Click (workspace_id composite, link_id composite), WorkspaceMember (workspace_id, user_id), Invite (workspace_id, inviter_id), AbuseReview (link_id, workspace_id, reviewer_id), PasswordResetToken (user_id), EmailVerificationToken (user_id), Workspace (owner_id via inline index=True). |
| ORM-ERD-013 | Yes | All __tablename__ values use lowercase snake_case singular form matching the evident project convention derived from ERD entity names. No naming drift found. |
| ORM-ERD-014 | Yes | Nullable settings are consistent with ERD relationship cardinality. Mandatory FK sides (LINK.workspace_id, LINK.owner_id, LINK.created_by_id, CLICK.workspace_id, CLICK.link_id, WORKSPACE_MEMBER.workspace_id, WORKSPACE_MEMBER.user_id, INVITE.workspace_id, ABUSE_REVIEW.link_id, ABUSE_REVIEW.workspace_id) are nullable=False. Optional sides (ABUSE_REVIEW.reviewer_id, INVITE.inviter_id) are nullable=True, matching the `o\|` zero-or-one ERD notation and explicit ERD Notes justifications. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/click.py",
    "line": 38,
    "snippet": "ERD Notes §Uniqueness constraints: `CLICK | Composite unique index on (link_id, clicked_at) | Idempotency for the at-least-once SQS ingest consumer`. Model declares UniqueConstraint(\"event_id\") on a column not in the ERD; the ERD-mandated (link_id, clicked_at) unique index is absent.",
    "message": "The ERD Notes mandate a composite unique index on (link_id, clicked_at) for CLICK idempotency. The model instead declares a UniqueConstraint on event_id, a column that does not appear in the ERD CLICK entity. The ERD-specified uniqueness shape is not implemented.",
    "fix": "Replace UniqueConstraint(\"event_id\") with UniqueConstraint(\"link_id\", \"clicked_at\", name=\"uq_click_link_clicked_at\") — or confirm with the ERD owner that event_id is an approved ERD amendment and update the ERD accordingly. If event_id is kept, the ERD CLICK entity must also declare it.",
    "effort": "medium"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-008",
    "file": "backend/app/models/user.py",
    "line": 14,
    "snippet": "`email_ciphertext: Mapped[str] = mapped_column(String, nullable=False)`",
    "message": "ERD Notes §Email encryption states email_ciphertext is encrypted with AES-256-GCM using a per-row DEK sealed by AWS KMS — plaintext is never persisted. The User model stores this column as plain String with no TypeDecorator, encryption wrapper, or comment acknowledging the protection strategy. If a developer queries this column without knowing about the encryption convention, they will read or write plaintext.",
    "fix": "Wrap the column type in an EncryptedType (or equivalent TypeDecorator) that performs AES-256-GCM encryption/decryption transparently, or add a prominent inline comment (e.g. # AES-256-GCM via app-layer KMS DEK; never store plaintext) to document the protection contract until the TypeDecorator is implemented.",
    "effort": "medium"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-008",
    "file": "backend/app/models/invite.py",
    "line": 32,
    "snippet": "`email_ciphertext: Mapped[str] = mapped_column(String, nullable=False)`",
    "message": "Same PII protection gap as User.email_ciphertext. The ERD Notes §Email encryption mandates AES-256-GCM application-layer encryption for all email_ciphertext columns. The Invite model uses a plain String column with no encryption wrapper or acknowledging comment.",
    "fix": "Apply the same EncryptedType or inline acknowledgment comment as User.email_ciphertext.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/mixpanel_dead_letter.py",
    "line": 14,
    "snippet": "`workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)`",
    "message": "MixpanelDeadLetter.workspace_id has no index. The ERD Notes §Multi-tenant scoping and §Mixpanel dead letter document that workspace_id is a query dimension for replaying workspace-scoped events. Without an index, filtering dead-letter rows by workspace_id produces a full-table scan.",
    "fix": "Add Index(\"ix_mixpanel_dead_letter_workspace_id\", \"workspace_id\") to __table_args__ (nullable columns are still worth indexing in PostgreSQL — NULL values are indexed and can be excluded with IS NOT NULL predicates).",
    "effort": "low"
  }
]
```

---

## STEP C — Domain Summary

```json
{
  "domain": "orm-review",
  "gate1_count": 0,
  "gate2_count": 3,
  "gate3_count": 1,
  "verdict": "FAIL_BLOCKER"
}
```

---

## Summary

**Verdict: FAIL_BLOCKER** — 3 Gate 2 blockers, 1 Gate 3 warning, 0 Gate 1 criticals.

This is a significant improvement over prior runs. Gate 1 is now clean: every ERD entity is accounted for (SESSION and LOGIN_ATTEMPT correctly absent as Redis-backed), and no orphan models exist. Audit columns, PK types, FK targets, relationship cardinalities, back_populates coverage, and most unique constraints are all correct.

Three blockers remain:

1. **ORM-ERD-006 / CLICK idempotency key** — The CLICK model replaced the ERD-mandated `(link_id, clicked_at)` composite unique index with a non-ERD `event_id` column. Whether `event_id` is a deliberate improvement or an accidental deviation, it requires either an ERD amendment or a model correction before migrations are generated.

2. **ORM-ERD-008 / User.email_ciphertext** — Plain `String` column with no encryption wrapper or comment. This is the highest-risk gap: a developer who reads or writes this column without knowing the convention will persist plaintext PII.

3. **ORM-ERD-008 / Invite.email_ciphertext** — Same gap, lower impact (invites are shorter-lived than user records), but the same protection is mandated by the ERD.

The one warning (missing index on MixpanelDeadLetter.workspace_id) is a performance concern, not a correctness issue, and can be addressed in a follow-up migration.
