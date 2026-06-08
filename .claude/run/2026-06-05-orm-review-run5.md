# ORM Review — Run 5 — 2026-06-05

**ERD:** `c:\Users\faraz\Desktop\Code\url-shortener\docs\erd.md`
**Models reviewed:** `backend/app/models/base.py`, `user.py`, `workspace.py`, `invite.py`, `link.py`, `click.py`, `tokens.py`, `abuse_review.py`, `email_suppression.py`, `mixpanel_dead_letter.py`
**Verdict:** PASS
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 0 findings

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|----------|---------|---------|------|----------|
| — | No findings | — | — | — |

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---------|-------------|------------------|
| ORM-ERD-001 | Yes | All 11 Postgres ERD entities map to a model class. SESSION and LOGIN_ATTEMPT are Redis-backed per ERD Notes — correctly no model. |
| ORM-ERD-002 | Yes | Every model class maps to an ERD entity; no orphan models. |
| ORM-ERD-003 | Yes | All types match the equivalence table (uuid→UUID, string→String, int→Integer, boolean→Boolean, datetime→DateTime(tz), json→JSONB). |
| ORM-ERD-004 | Yes | Every model PK is `uuid id` matching the ERD. No composite PKs. |
| ORM-ERD-005 | Yes | All ERD relationship FKs present and correctly targeted. EmailSuppression and MixpanelDeadLetter correctly omit a USER FK per ERD Notes. |
| ORM-ERD-006 | Yes | **PRIOR BLOCKER RESOLVED.** ERD now declares `uuid event_id UK` inline (line 111) and the Uniqueness table reads `CLICK | Global unique index on event_id` (line 217); `click.py:39` declares `UniqueConstraint("event_id", name="uq_click_event_id")`. Model and ERD agree. Partial UKs (WorkspaceMember, Invite pending, Link short_code) implemented with `postgresql_where`. |
| ORM-ERD-007 | Yes | Mutable tables use TimestampMixin; Click is documented append-only (created_at only); tokens carry updated_at per ERD Notes. |
| ORM-ERD-008 | Yes | **PRIOR BLOCKER RESOLVED.** User (user.py:14-15), Invite (invite.py:32), and EmailSuppression (email_suppression.py:20-21) now carry explicit comments acknowledging the service-layer AES-256-GCM / KMS-sealed-DEK strategy — satisfies the dismissal bar. |
| ORM-ERD-009 | Yes | All cardinalities match; WORKSPACE_MEMBER is a proper associative entity with its own PK. |
| ORM-ERD-010 | Yes | All relationships bidirectional with `back_populates`; multi-FK paths disambiguated with `foreign_keys`. |
| ORM-ERD-011 | Yes | Parent→child cascades present (Link→clicks/abuse_reviews, User→tokens); Workspace FKs intentionally RESTRICT (deletion deferred post-v1). |
| ORM-ERD-012 | Yes | Every FK column is indexed (standalone or as leading column of a composite). |
| ORM-ERD-013 | Yes | Every `__tablename__` matches the ERD entity in snake_case singular. |
| ORM-ERD-014 | Yes | Nullable matches cardinality: optional FK sides nullable=True; mandatory FKs nullable=False. |

---

## Gate 1 — Critical

_No Gate 1 findings._

## Gate 2 — Blockers

_No Gate 2 findings._

## Gate 3 — Warnings

_No Gate 3 findings._

---

## Summary

**PASS.** Both prior FAIL_BLOCKER items are resolved. **ORM-ERD-006 (CLICK idempotency):** the ERD was amended so CLICK declares `event_id` as a global UK (and the old `(link_id, clicked_at)` composite is gone from both ERD and model) — model and ERD now agree on the idempotency key. **ORM-ERD-008 (email_ciphertext PII ×3):** User, Invite, and EmailSuppression now carry comments documenting the service-layer AES-256-GCM/KMS encryption, meeting the rule's acknowledgment bar. A fresh full pass of all 14 rules found no regressions. The models are safe to generate migrations from.
