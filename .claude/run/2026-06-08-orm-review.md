# ORM Review — 2026-06-08

**ERD:** `docs/erd.md`
**Models reviewed:** `backend/app/models/{base,user,workspace,invite,link,click,tokens,abuse_review,email_suppression,mixpanel_dead_letter}.py`
**Reconciled from:** 2 independent reviewer runs (one track — standard)
**Authority:** ADVISORY — a single track catches only ~half the defect union, so this is not a standalone gate decision. Run `/cross-reconcile orm` to union both tracks into the authoritative, confidence-tiered worklist.
**Verdict:** PASS
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 0 findings

## Lookup
| Location | Finding | Rule ID | Gate | Severity |
|----------|---------|---------|------|----------|
| _(none)_ | No findings — the ORM models faithfully implement every ERD entity, type, and constraint | — | — | — |

## Dismissed rules
| Rule ID | Considered? | Dismissal reason |
|---------|-------------|------------------|
| ORM-ERD-001 | Yes | All 11 Postgres ERD entities map to model classes; SESSION & LOGIN_ATTEMPT correctly Redis-only per ERD Notes. |
| ORM-ERD-002 | Yes | Every model class maps to an ERD entity; no orphans. |
| ORM-ERD-003 | Yes | Types match: uuid→`UUID(as_uuid=True)`, string→`String(n)`, int→`Integer`, boolean→`Boolean`, datetime→`DateTime(timezone=True)`, json→`JSONB`. |
| ORM-ERD-004 | Yes | Every PK is `UUID(as_uuid=True), primary_key=True, default=uuid.uuid4`; no composite-PK entities. |
| ORM-ERD-005 | Yes | All ERD FKs present and correctly targeted; `MixpanelDeadLetter.workspace_id` correctly a plain column (no FK marker in ERD). |
| ORM-ERD-006 | Yes | Inline UKs enforced (email_search_hash, token_hash ×2, event_id) + all three partial UKs via `postgresql_where`. |
| ORM-ERD-007 | Yes | Audit columns via `TimestampMixin`; Click's `updated_at` omission is the ERD-documented append-only exception. |
| ORM-ERD-008 | Yes | PII `email_ciphertext` columns carry AES-256-GCM/KMS comments; `email_search_hash` plaintext HMAC is correct per ERD Notes. |
| ORM-ERD-009 | Yes | One-to-many relationships use `relationship(list[...])` + FK on child; no `||--||`/`}o--o{` shapes. |
| ORM-ERD-010 | Yes | All bidirectional relationships declare `back_populates`; `foreign_keys=` disambiguates dual User↔Link / reviewer pairs. |
| ORM-ERD-011 | Yes | Link→Click and Link→AbuseReview cascade at both layers (`delete-orphan` + FK `ondelete=CASCADE`); workspace children `RESTRICT`. |
| ORM-ERD-012 | Yes | Every FK column is indexed (inline or leading column of a composite index). |
| ORM-ERD-013 | Yes | All `__tablename__` match ERD entity names (singular snake_case). |
| ORM-ERD-014 | Yes | FK nullability matches cardinality: optional `o\|--o{` FKs (inviter_id, reviewer_id) nullable; mandatory FKs `nullable=False`. |

## Gate 1 — Critical (models not safe to generate migrations from)
_None._

## Gate 2 — Blockers (will produce incorrect or unsafe schema)
_None._

## Gate 3 — Warnings
_None._

## Reconciliation (reflexion)
- **Runs usable:** 2 (both `[]` findings / PASS).
- **Consensus:** 0 findings — empty union, nothing to adjudicate.
- **Consensus — dropped (failed artifact check):** none.
- **Divergent — kept / dropped:** 0 / 0.
- **Spot-checks:** ORM-ERD-011 cascade (link.py:41,44 + click.py:16 + abuse_review.py:23), ORM-ERD-006 partial uniques (link.py:49-54, invite.py:56-62, click.py:39), ORM-ERD-014 nullability (abuse_review.py:29-31, invite.py:36-38) — all verified against the models; consensus is genuine, not a shared misread.
- **Verdict:** PASS — recomputed from 0/0/0 reconciled findings.

## Summary
The SQLAlchemy models are a faithful, complete realization of the ERD — confirmed by unanimous consensus across both standard runs plus ground-truth spot-checks. The models are safe to generate migrations from.

Report saved to c:\Users\faraz\Desktop\Code\url-shortener\.claude\run\2026-06-08-orm-review.md
