# ORM Review — url-shortener
**Date:** 2026-06-04
**ERD source:** `docs/erd.md` (Draft v5, derived from PRD v5 2026-06-04)
**Models reviewed:** user.py, link.py, workspace.py, tokens.py, click.py, abuse_review.py, email_suppression.py, invite.py, mixpanel_dead_letter.py

---

## Entity-to-Model Mapping

| ERD Entity | Model Class | File | Notes |
|---|---|---|---|
| USER | User | user.py | Direct match |
| SESSION | (none) | — | ERD Notes §Redis: implemented as Redis hash, no ORM model required |
| LOGIN_ATTEMPT | (none) | — | ERD Notes §Redis: implemented as Redis hash, no ORM model required |
| WORKSPACE | Workspace | workspace.py | Direct match |
| WORKSPACE_MEMBER | WorkspaceMember | workspace.py | Direct match |
| INVITE | Invite | invite.py | Direct match |
| LINK | Link | link.py | Direct match |
| CLICK | Click | click.py | Direct match |
| PASSWORD_RESET_TOKEN | PasswordResetToken | tokens.py | Direct match |
| EMAIL_VERIFICATION_TOKEN | EmailVerificationToken | tokens.py | Direct match |
| EMAIL_SUPPRESSION | EmailSuppression | email_suppression.py | Direct match |
| MIXPANEL_DEAD_LETTER | MixpanelDeadLetter | mixpanel_dead_letter.py | Direct match |
| ABUSE_REVIEW | AbuseReview | abuse_review.py | Direct match |

---

## STEP A — Lookup Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| backend/app/models/click.py:16 | `workspace_id` has no `ForeignKey("workspace.id")` declaration | ORM-ERD-005 | 2 | blocker |
| backend/app/models/abuse_review.py:24 | `workspace_id` has no `ForeignKey("workspace.id")` declaration | ORM-ERD-005 | 2 | blocker |
| backend/app/models/workspace.py:38 (WorkspaceMember) | No partial unique index `user_id WHERE removed_at IS NULL` declared; ERD Notes §Uniqueness mandates it | ORM-ERD-006 | 2 | blocker |
| backend/app/models/user.py:19–20 | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/workspace.py:23–24 (Workspace) | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/workspace.py:51–52 (WorkspaceMember) | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/link.py:27–28 | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/click.py:25 | `created_at` has no `server_default` or `default=func.now()`; `updated_at` omitted per ERD Notes (append-only) | ORM-ERD-007 | 2 | blocker |
| backend/app/models/tokens.py:19–20 (PasswordResetToken) | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/tokens.py:42–43 (EmailVerificationToken) | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/email_suppression.py:26–27 | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/invite.py:44–45 | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/mixpanel_dead_letter.py:19–20 | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/abuse_review.py:36–37 | `created_at` and `updated_at` have no `server_default` or `default=func.now()` | ORM-ERD-007 | 2 | blocker |
| backend/app/models/workspace.py:27 (Workspace.owner) | `relationship("User", foreign_keys=[owner_id])` has no `back_populates`; User has no reciprocal relationship | ORM-ERD-010 | 3 | warning |
| backend/app/models/abuse_review.py:41 (AbuseReview.reviewer) | `relationship("User", foreign_keys=[reviewer_id])` has no `back_populates`; User has no reciprocal relationship | ORM-ERD-010 | 3 | warning |
| backend/app/models/link.py:40 (Link.clicks) | `relationship("Click", back_populates="link")` — no `cascade="all, delete-orphan"` on ORM relationship despite DB FK having `ondelete="CASCADE"` | ORM-ERD-011 | 3 | warning |
| backend/app/models/link.py:41 (Link.abuse_reviews) | `relationship("AbuseReview", back_populates="link")` — no `cascade="all, delete-orphan"` on ORM relationship despite DB FK having `ondelete="CASCADE"` | ORM-ERD-011 | 3 | warning |
| backend/app/models/user.py:35 (User.password_reset_tokens) | `relationship("PasswordResetToken", back_populates="user")` — no `cascade="all, delete-orphan"` despite DB FK having `ondelete="CASCADE"` | ORM-ERD-011 | 3 | warning |
| backend/app/models/user.py:38 (User.email_verification_tokens) | `relationship("EmailVerificationToken", back_populates="user")` — no `cascade="all, delete-orphan"` despite DB FK having `ondelete="CASCADE"` | ORM-ERD-011 | 3 | warning |
| backend/app/models/link.py:17–19 (Link.owner_id) | FK column `owner_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/link.py:21–23 (Link.created_by_id) | FK column `created_by_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/workspace.py:42–44 (WorkspaceMember.workspace_id) | FK column `workspace_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/workspace.py:45–47 (WorkspaceMember.user_id) | FK column `user_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/invite.py:34–36 (Invite.inviter_id) | FK column `inviter_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/abuse_review.py:26–28 (AbuseReview.reviewer_id) | FK column `reviewer_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/tokens.py:13–15 (PasswordResetToken.user_id) | FK column `user_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/tokens.py:36–38 (EmailVerificationToken.user_id) | FK column `user_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |
| backend/app/models/workspace.py:20–22 (Workspace.owner_id) | FK column `owner_id` has no `Index` declared | ORM-ERD-012 | 3 | warning |

---

## STEP A-bis — Dismissed Rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ORM-ERD-001 | Yes | All 11 ORM-backed ERD entities have a corresponding model class. SESSION and LOGIN_ATTEMPT are explicitly documented in ERD Notes §Session as Redis-backed — no ORM model required. |
| ORM-ERD-002 | Yes | All 11 model classes map to ERD entities. No orphan models found. |
| ORM-ERD-003 | Yes | All column types are within the defined equivalence set: UUID ↔ UUID(as_uuid=True), string ↔ String/String(N), boolean ↔ Boolean, int/integer ↔ Integer, datetime ↔ DateTime(timezone=True), json ↔ JSONB (listed as equivalent in type equivalence table). No precision-loss types (Float, Double) used for decimal/numeric ERD columns. |
| ORM-ERD-004 | Yes | All models declare a single UUID PK matching `uuid PK` in the ERD. No composite PK required. No integer autoincrement used where uuid PK is declared. |
| ORM-ERD-006 (partial — non-WorkspaceMember) | Yes | USER.email_search_hash UK: unique=True + UniqueConstraint present. INVITE.token_hash UK: unique=True + UniqueConstraint present. PASSWORD_RESET_TOKEN.token_hash UK: unique=True + UniqueConstraint present. EMAIL_VERIFICATION_TOKEN.token_hash UK: unique=True + UniqueConstraint present. EMAIL_SUPPRESSION.email_search_hash UK: unique=True + UniqueConstraint present. LINK.short_code: partial unique correctly implemented with postgresql_where=text("deleted_at IS NULL") matching ERD Notes §Uniqueness. INVITE (workspace_id, email_search_hash) WHERE status='pending': partial unique Index present matching ERD Notes §Uniqueness. CLICK (link_id, clicked_at): UniqueConstraint present matching ERD Notes §Uniqueness. |
| ORM-ERD-008 | Yes | ERD Notes §Email encryption explicitly states "application-layer encryption, plaintext never persisted" — the encryption happens in the application service layer before the value reaches the ORM column. The ORM stores the already-encrypted ciphertext as String. No ORM-layer TypeDecorator or EncryptedType is mandated. EmailSuppression.email_ciphertext has an inline comment. User.email_ciphertext and Invite.email_ciphertext lack inline comments but the architectural pattern is consistent with the ERD Notes' stated approach. |
| ORM-ERD-009 | Yes | All relationship() declarations use the correct uselist shape: one-to-many relationships use Mapped[list[...]] (uselist=True implicitly), one-to-one relationships use Mapped["Model"] (uselist=False implicitly). No many-to-many relationships exist in the ERD. Cardinality matches throughout. |
| ORM-ERD-013 | Yes | All __tablename__ values use snake_case lowercase, consistently matching the evident project convention derived from ERD entity names (e.g. WORKSPACE_MEMBER → "workspace_member"). No table name deviates from this convention. |
| ORM-ERD-014 | Yes | All mandatory FKs (|| cardinality on the FK side) are nullable=False. Documented nullable FKs (inviter_id, reviewer_id per ERD Notes) are nullable=True. No nullability inconsistency found. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-005",
    "file": "backend/app/models/click.py",
    "line": 16,
    "snippet": "workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)",
    "message": "ERD declares WORKSPACE ||--o{ CLICK implying click.workspace_id is a FK to workspace.id, but the model column has no ForeignKey() declaration. The FK constraint will not be created in migrations, leaving referential integrity unenforced at the DB layer.",
    "fix": "Add ForeignKey('workspace.id', ondelete='RESTRICT') to the workspace_id column declaration.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-005",
    "file": "backend/app/models/abuse_review.py",
    "line": 24,
    "snippet": "workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)",
    "message": "ERD declares WORKSPACE ||--o{ ABUSE_REVIEW implying abuse_review.workspace_id is a FK to workspace.id, but the model column has no ForeignKey() declaration. The FK constraint will not be created in migrations.",
    "fix": "Add ForeignKey('workspace.id', ondelete='RESTRICT') to the workspace_id column declaration.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-006",
    "file": "backend/app/models/workspace.py",
    "line": 0,
    "snippet": "ERD Notes §Uniqueness: `WORKSPACE_MEMBER | Partial UK on user_id WHERE removed_at IS NULL`",
    "message": "The ERD Notes §Uniqueness mandates a partial unique index on WorkspaceMember.user_id WHERE removed_at IS NULL (enforcing the 'every Member belongs to exactly one Workspace in v1' invariant). No such Index is declared anywhere in the WorkspaceMember model or its __table_args__.",
    "fix": "Add Index('uq_workspace_member_user_active', 'user_id', unique=True, postgresql_where=text('removed_at IS NULL')) to WorkspaceMember.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/user.py",
    "line": 19,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "User.created_at and User.updated_at are declared nullable=False but carry no server_default or default=func.now(). The ORM will raise an IntegrityError on any insert that does not explicitly supply both values. No justification is present in ERD Notes.",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() plus onupdate=func.now() to updated_at, or supply a Base mixin that does this for all models.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/workspace.py",
    "line": 23,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "Workspace.created_at and Workspace.updated_at have no server_default or default=func.now(). Same risk as User — any insert omitting these values raises IntegrityError.",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/workspace.py",
    "line": 51,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "WorkspaceMember.created_at and WorkspaceMember.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/link.py",
    "line": 27,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "Link.created_at and Link.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/click.py",
    "line": 25,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\n# No updated_at — CLICK is append-only",
    "message": "Click.created_at has no server_default or default=func.now(). The updated_at omission is justified by ERD Notes §Click ('CLICK is append-only — updated_at is intentionally omitted'), but created_at still requires a default.",
    "fix": "Add server_default=func.now() to created_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/tokens.py",
    "line": 19,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "PasswordResetToken.created_at and PasswordResetToken.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/tokens.py",
    "line": 42,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "EmailVerificationToken.created_at and EmailVerificationToken.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/email_suppression.py",
    "line": 26,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "EmailSuppression.created_at and EmailSuppression.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/invite.py",
    "line": 44,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "Invite.created_at and Invite.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/mixpanel_dead_letter.py",
    "line": 19,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "MixpanelDeadLetter.created_at and MixpanelDeadLetter.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ORM-ERD-007",
    "file": "backend/app/models/abuse_review.py",
    "line": 36,
    "snippet": "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)\nupdated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)",
    "message": "AbuseReview.created_at and AbuseReview.updated_at have no server_default or default=func.now().",
    "fix": "Add server_default=func.now() to created_at and server_default=func.now() + onupdate=func.now() to updated_at.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-010",
    "file": "backend/app/models/workspace.py",
    "line": 27,
    "snippet": "owner: Mapped[\"User\"] = relationship(\"User\", foreign_keys=[owner_id])",
    "message": "Workspace.owner has no back_populates, and User has no reciprocal relationship for workspace ownership. ERD USER ||--o{ WORKSPACE implies bidirectional navigability. Traversing from User to their owned workspaces will produce an extra query rather than using a mapped relationship.",
    "fix": "Add back_populates='owned_workspaces' to Workspace.owner and add owned_workspaces: Mapped[list['Workspace']] = relationship('Workspace', back_populates='owner', foreign_keys='Workspace.owner_id') to User.",
    "effort": "medium"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-010",
    "file": "backend/app/models/abuse_review.py",
    "line": 41,
    "snippet": "reviewer: Mapped[\"User | None\"] = relationship(\"User\", foreign_keys=[reviewer_id])",
    "message": "AbuseReview.reviewer has no back_populates, and User has no reciprocal relationship for reviews. ERD USER o|--o{ ABUSE_REVIEW implies bidirectional navigability from the reviewer side.",
    "fix": "Add back_populates='abuse_reviews_assigned' to AbuseReview.reviewer and add a matching relationship to User.",
    "effort": "medium"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-011",
    "file": "backend/app/models/link.py",
    "line": 40,
    "snippet": "clicks: Mapped[list[\"Click\"]] = relationship(\"Click\", back_populates=\"link\")",
    "message": "Link.clicks has no cascade='all, delete-orphan' on the ORM relationship. The DB FK on Click.link_id has ondelete='CASCADE', but if Click objects are loaded into the SQLAlchemy session and the parent Link is deleted through the ORM (rather than a raw DELETE), the session may not correctly cascade the delete. Cascade responsibility is split between DB and ORM with no explicit declaration.",
    "fix": "Add cascade='all, delete-orphan' to the clicks relationship, or add a comment documenting that cascade is intentionally DB-only.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-011",
    "file": "backend/app/models/link.py",
    "line": 41,
    "snippet": "abuse_reviews: Mapped[list[\"AbuseReview\"]] = relationship(\"AbuseReview\", back_populates=\"link\")",
    "message": "Link.abuse_reviews has no cascade='all, delete-orphan'. DB FK on AbuseReview.link_id has ondelete='CASCADE' but ORM-layer cascade is undeclared.",
    "fix": "Add cascade='all, delete-orphan' to the abuse_reviews relationship, or document the intentional DB-only cascade.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-011",
    "file": "backend/app/models/user.py",
    "line": 35,
    "snippet": "password_reset_tokens: Mapped[list[\"PasswordResetToken\"]] = relationship(\"PasswordResetToken\", back_populates=\"user\")",
    "message": "User.password_reset_tokens has no cascade='all, delete-orphan'. DB FK on PasswordResetToken.user_id has ondelete='CASCADE' but ORM cascade is undeclared.",
    "fix": "Add cascade='all, delete-orphan' to the password_reset_tokens relationship.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-011",
    "file": "backend/app/models/user.py",
    "line": 38,
    "snippet": "email_verification_tokens: Mapped[list[\"EmailVerificationToken\"]] = relationship(\"EmailVerificationToken\", back_populates=\"user\")",
    "message": "User.email_verification_tokens has no cascade='all, delete-orphan'. DB FK on EmailVerificationToken.user_id has ondelete='CASCADE' but ORM cascade is undeclared.",
    "fix": "Add cascade='all, delete-orphan' to the email_verification_tokens relationship.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/link.py",
    "line": 17,
    "snippet": "owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"RESTRICT\"), nullable=False)",
    "message": "Link.owner_id is a FK column with no declared Index. Every query filtering links by owner (permission checks, owned-link lists) will produce a full-table scan on the link table.",
    "fix": "Add Index('ix_link_owner_id', 'owner_id') to Link.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/link.py",
    "line": 21,
    "snippet": "created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"RESTRICT\"), nullable=False)",
    "message": "Link.created_by_id is a FK column with no declared Index. Attribution queries (link list displays created_by_id per ERD Notes §LINK dual creator/owner) will scan the full link table.",
    "fix": "Add Index('ix_link_created_by_id', 'created_by_id') to Link.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/workspace.py",
    "line": 42,
    "snippet": "workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"workspace.id\", ondelete=\"RESTRICT\"), nullable=False)",
    "message": "WorkspaceMember.workspace_id is a FK column with no declared Index. Every query loading workspace members will full-scan the workspace_member table.",
    "fix": "Add Index('ix_workspace_member_workspace_id', 'workspace_id') to WorkspaceMember.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/workspace.py",
    "line": 45,
    "snippet": "user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"RESTRICT\"), nullable=False)",
    "message": "WorkspaceMember.user_id is a FK column with no declared Index (and the required partial unique index is also missing per ORM-ERD-006). Membership lookups by user will full-scan.",
    "fix": "Add Index('ix_workspace_member_user_id', 'user_id') to WorkspaceMember.__table_args__ (in addition to the partial unique index required by ORM-ERD-006).",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/invite.py",
    "line": 34,
    "snippet": "inviter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"SET NULL\"), nullable=True)",
    "message": "Invite.inviter_id is a FK column with no declared Index. Queries loading invites by inviter (e.g. cancelling all pending invites when an admin is removed) will full-scan the invite table.",
    "fix": "Add Index('ix_invite_inviter_id', 'inviter_id') to Invite.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/abuse_review.py",
    "line": 26,
    "snippet": "reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"SET NULL\"), nullable=True)",
    "message": "AbuseReview.reviewer_id is a FK column with no declared Index.",
    "fix": "Add Index('ix_abuse_review_reviewer_id', 'reviewer_id') to AbuseReview.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/tokens.py",
    "line": 13,
    "snippet": "user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"CASCADE\"), nullable=False)",
    "message": "PasswordResetToken.user_id is a FK column with no declared Index. Queries loading active tokens per user will full-scan.",
    "fix": "Add Index('ix_password_reset_token_user_id', 'user_id') to PasswordResetToken.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/tokens.py",
    "line": 36,
    "snippet": "user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"CASCADE\"), nullable=False)",
    "message": "EmailVerificationToken.user_id is a FK column with no declared Index.",
    "fix": "Add Index('ix_email_verification_token_user_id', 'user_id') to EmailVerificationToken.__table_args__.",
    "effort": "low"
  },
  {
    "domain": "orm-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ORM-ERD-012",
    "file": "backend/app/models/workspace.py",
    "line": 20,
    "snippet": "owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(\"user.id\", ondelete=\"RESTRICT\"), nullable=False)",
    "message": "Workspace.owner_id is a FK column with no declared Index.",
    "fix": "Add Index('ix_workspace_owner_id', 'owner_id') to Workspace.__table_args__.",
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
  "gate2_count": 14,
  "gate3_count": 15,
  "verdict": "FAIL_BLOCKER"
}
```

---

## Summary

**Verdict: FAIL_BLOCKER** — 14 Gate 2 (blocker) findings, 15 Gate 3 (warning) findings, 0 Gate 1 (critical) findings.

All 13 ORM-backed ERD entities are represented by model classes and no orphan models exist, so the Gate 1 gates are clean. The models are not safe to generate migrations from in their current state due to the following blocker categories:

**Gate 2 blockers (14):**

1. **Missing FK declarations (ORM-ERD-005, 2 findings):** `Click.workspace_id` and `AbuseReview.workspace_id` both carry UUID columns without a `ForeignKey()` call. Alembic will generate these columns as bare UUID columns with no FK constraint, leaving referential integrity unenforced at the database layer for two of the project's multi-tenancy scoping columns.

2. **Missing partial unique index on WorkspaceMember (ORM-ERD-006, 1 finding):** The ERD Notes §Uniqueness mandates `WORKSPACE_MEMBER | Partial UK on user_id WHERE removed_at IS NULL`. This index does not exist anywhere in the WorkspaceMember model. Without it, a user can be re-added to the same workspace as a concurrent active member, violating the "every Member belongs to exactly one Workspace in v1" invariant.

3. **Audit columns have no automatic defaults (ORM-ERD-007, 11 findings):** Every model across the codebase declares `created_at` and `updated_at` as `nullable=False` but provides no `server_default=func.now()` or `default=func.now()`. The ORM will raise `IntegrityError` on any insert that does not explicitly pass these values. This is a systemic gap best resolved with a shared `TimestampMixin` base class applied to all models.

**Gate 3 warnings (15):**

- 2 `back_populates` gaps on `Workspace.owner` and `AbuseReview.reviewer` (ORM-ERD-010).
- 4 ORM cascade declarations missing for relationships where DB FK already declares `ondelete="CASCADE"` (ORM-ERD-011) — the DB handles the cascade but the ORM layer is silent, which can cause session-state surprises.
- 9 FK columns across 6 models have no `Index` declaration (ORM-ERD-012), affecting join and filter performance on membership, link-ownership, token, and reviewer queries.
