# ORM Review — Run 4 — 2026-06-05

**ERD:** `c:\Users\faraz\Desktop\Code\url-shortener\docs\erd.md`
**Models reviewed:** `backend/app/models/base.py`, `user.py`, `workspace.py`, `invite.py`, `link.py`, `click.py`, `tokens.py`, `abuse_review.py`, `email_suppression.py`, `mixpanel_dead_letter.py`
**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 4 findings
**Gate 3 (Warnings):** 0 findings

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `backend/app/models/click.py:31-33` | ERD documents CLICK idempotency as composite UNIQUE index on `(link_id, clicked_at)`; model omits it and substitutes a non-ERD `event_id` column with `UniqueConstraint("event_id")`. The `(link_id, clicked_at)` index present is non-unique. | ORM-ERD-006 | 2 | blocker |
| `backend/app/models/user.py:14` | `email_ciphertext` declared as plain `String` with no TypeDecorator/encryption wrapper/comment acknowledging the AES-256-GCM strategy from ERD Notes. | ORM-ERD-008 | 2 | blocker |
| `backend/app/models/invite.py` | `email_ciphertext` declared as plain `String` with no protection acknowledgment per ERD Notes §Email encryption. | ORM-ERD-008 | 2 | blocker |
| `backend/app/models/email_suppression.py` | `email_ciphertext` declared as plain `String` with no protection acknowledgment; ERD Notes mark it "AES-256-GCM encrypted". | ORM-ERD-008 | 2 | blocker |

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ORM-ERD-001 | Yes | All 11 Postgres ERD entities have model classes. SESSION and LOGIN_ATTEMPT are explicitly Redis-backed with no ORM model per ERD Notes §Session and login-attempt state. |
| ORM-ERD-002 | Yes | Every model class maps to an ERD entity. No orphan model classes. Click.event_id is an orphan *column*, not a class — captured under ORM-ERD-006, not 002. |
| ORM-ERD-003 | Yes | All types are ERD-equivalent: uuid→`UUID(as_uuid=True)`, string→`String`, int→`Integer`, boolean→`Boolean`, datetime→`DateTime`, json→`JSONB`. |
| ORM-ERD-004 | Yes | Every entity declares `uuid id PK` and every model uses `UUID(as_uuid=True), primary_key=True, default=uuid.uuid4`. No composite-PK entities. |
| ORM-ERD-005 | Yes | All ERD relationship FKs present and correctly targeted. EmailSuppression correctly has no USER FK per ERD Notes. |
| ORM-ERD-006 | Yes (FLAGGED) | Global UKs present. Partial UKs implemented with `postgresql_where` (workspace_member active, invite pending, link short_code active). FAILS for CLICK `(link_id, clicked_at)` — see flag. |
| ORM-ERD-007 | Yes | TimestampMixin supplies `created_at` + `updated_at` to all mutable models. Click correctly omits `updated_at` (append-only per ERD Notes §Click table). Token tables' `updated_at` justified by ERD Notes §Token tables. |
| ORM-ERD-008 | Yes (FLAGGED) | email_search_hash is a keyed HMAC and correctly stored plaintext. `email_ciphertext` columns on User/Invite/EmailSuppression are plain `String` with no decorator/comment — FLAGGED. |
| ORM-ERD-009 | Yes | All cardinalities correct. WORKSPACE_MEMBER is a modeled associative entity with its own PK, consistent with `||--|{`. |
| ORM-ERD-010 | Yes | All relationships bidirectional with `back_populates`; multi-FK paths to User disambiguated with explicit `foreign_keys`. |
| ORM-ERD-011 | Yes | Parent→child cascades present where intended (Link→clicks/abuse_reviews, User→tokens). Workspace→Link uses RESTRICT intentionally; workspace deletion deferred post-v1 per ERD §Out of scope. |
| ORM-ERD-012 | Yes | Every FK column is indexed — standalone or as the leading column of a composite index. |
| ORM-ERD-013 | Yes | ERD UPPER_SNAKE singular maps cleanly to snake_case singular `__tablename__`. Convention consistent. |
| ORM-ERD-014 | Yes | Nullable matches cardinality: optional FK sides nullable=True; mandatory FKs nullable=False. |

---

## Gate 1 — Critical (models not safe to generate migrations from)

_No Gate 1 findings._

---

## Gate 2 — Blockers (will produce incorrect or unsafe schema)

### [ORM-ERD-006] — CLICK idempotency key diverges from ERD
**Location:** `backend/app/models/click.py:31`
**Finding:** The ERD declares the CLICK idempotency key as a composite UNIQUE index on `(link_id, clicked_at)` so the at-least-once SQS ingest consumer silently discards duplicates on insert conflict. The model does not implement this unique constraint — the `(link_id, clicked_at)` index it declares is NON-unique — and instead introduces an `event_id` UUID column (absent from the ERD) carrying a `UniqueConstraint`. This substitutes an unauthorized, differently-keyed idempotency mechanism: duplicate `(link_id, clicked_at)` events with distinct `event_id`s will both insert, defeating the documented idempotency guarantee. The dismissal carve-out for partial/conditional uniques does not apply because the model implements a *different* constraint, not the documented one.
**Fix:** Either add a composite `UniqueConstraint`/unique `Index` on `(link_id, clicked_at)` as the ERD specifies (and remove or justify `event_id`), or raise an ERD amendment to make `event_id` the contracted idempotency key before generating a migration. Do not generate a migration while the model and ERD disagree on the idempotency key.
**Effort:** low

### [ORM-ERD-008] — User.email_ciphertext lacks encryption acknowledgment
**Location:** `backend/app/models/user.py:14`
**Finding:** The ERD documents `email_ciphertext` as application-layer AES-256-GCM encrypted PII (per-row DEK sealed by AWS KMS), but the User model declares it as a plain `String` with no TypeDecorator/EncryptedType, no encryption wrapper, and no comment acknowledging the protection strategy. A migration generator or downstream developer cannot distinguish this from a plaintext column.
**Fix:** Wrap `email_ciphertext` in a TypeDecorator that performs the KMS-sealed AES-256-GCM encrypt/decrypt, or add an explicit comment documenting that ciphertext is produced at the service layer and the column stores opaque ciphertext.
**Effort:** low

### [ORM-ERD-008] — Invite.email_ciphertext lacks encryption acknowledgment
**Location:** `backend/app/models/invite.py`
**Finding:** `Invite.email_ciphertext` stores AES-256-GCM encrypted PII per the ERD Notes but is declared as a plain `String` with no TypeDecorator, encryption wrapper, or acknowledging comment. Same protection gap as `User.email_ciphertext`.
**Fix:** Apply the same encryption TypeDecorator used project-wide for `email_ciphertext`, or add a comment acknowledging the service-layer encryption contract.
**Effort:** low

### [ORM-ERD-008] — EmailSuppression.email_ciphertext lacks encryption acknowledgment
**Location:** `backend/app/models/email_suppression.py`
**Finding:** `EmailSuppression.email_ciphertext` is annotated "AES-256-GCM encrypted; for ops/audit use" in the ERD but is declared as a plain `String` with no TypeDecorator, encryption wrapper, or acknowledging comment.
**Fix:** Apply the project's email encryption TypeDecorator, or add a comment acknowledging the service-layer AES-256-GCM encryption contract.
**Effort:** low

---

## Gate 3 — Warnings

_No Gate 3 findings._

---

## Summary

The structural and relationship issues from prior runs are resolved — Gate 1 is clean (every entity, PK, FK, type, cardinality, and back_populates is correct) and there are no Gate 3 warnings. Two Gate-2 blockers remain. The highest-confidence and most impactful is the **CLICK idempotency divergence (ORM-ERD-006)**: the model never implements the ERD-contracted composite *unique* index on `(link_id, clicked_at)` and instead substitutes a non-ERD `event_id` unique column — so the schema this model generates would not enforce the documented duplicate-discard guarantee, the single mismatch most likely to cause a production incident (double-counted clicks) if it reaches migration. The remaining three are lower-confidence `email_ciphertext` PII findings (ORM-ERD-008). The models are **not safe to generate migrations from** until the model and ERD agree on the CLICK idempotency key.
