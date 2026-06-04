# ERD Review — Compressed Agent — Low Effort — Run 2
**Date:** 2026-06-02
**Agent:** erd-review-compressed
**Effort:** low
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| CLICK entity | PRD §Click pipeline: "The ingest consumer is idempotent on `(link_id, clicked_at)`." No unique constraint on `(link_id, clicked_at)` is declared in the ERD or ERD Notes. At-least-once SQS delivery means duplicate messages are expected; without this constraint, duplicate click rows can silently inflate analytics counts. | ERD-PRD-009 | G2 | Blocker |
| MIXPANEL_DEAD_LETTER entity | MIXPANEL_DEAD_LETTER has no ERD relationship line to any other entity, making it a diagram-orphan. Its purpose is justified by the PRD Mixpanel integration section, but the absence of any relationship link may cause confusion. Could be intentional for a pure-log table but is not documented as such. | ERD-PRD-011 | G3 | Warning |

---

## STEP A-bis — Rule Disposition Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ERD-PRD-001 | Yes — no finding | All PRD nouns (User, Workspace, Member/WORKSPACE_MEMBER, Invite, Link, Click, Password reset token, Email verification token, Abuse review queue, Suppression list, Mixpanel dead-letter) have corresponding ERD entities. |
| ERD-PRD-002 | Yes — no finding | All PRD-described relationships are represented. |
| ERD-PRD-003 | Yes — no finding | Email PII: ERD Notes §"Email encryption at rest" fully documents the email_ciphertext / email_search_hash split. |
| ERD-PRD-004 | Yes — no finding | All cardinalities checked. No contradictions found. |
| ERD-PRD-005 | Yes — no finding (CLICK exemption) | All entities have `created_at` + `updated_at` except CLICK, documented as append-only in Notes. |
| ERD-PRD-006 | Yes — no finding | LINK, INVITE, WORKSPACE_MEMBER, CLICK all carry `workspace_id`. USER/token/suppression entities are system-wide — no workspace scope needed. |
| ERD-PRD-007 | Yes — no finding | LINK has `deleted_at` and `disabled_at`. WORKSPACE_MEMBER has `removed_at`. INVITE has `status`. WORKSPACE omission explicitly justified. |
| ERD-PRD-008 | Yes — no finding | No monetary amounts in v1 schema (billing out of scope). |
| ERD-PRD-009 | Yes — G2 finding filed | CLICK idempotency key `(link_id, clicked_at)` has no unique constraint in ERD or Notes. |
| ERD-PRD-010 | Yes — no finding | Vocabulary aligns: USER, WORKSPACE, WORKSPACE_MEMBER, INVITE, LINK, CLICK, ABUSE_REVIEW. No significant divergence. |
| ERD-PRD-011 | Yes — G3 warning filed | MIXPANEL_DEAD_LETTER is a diagram-orphan. Justified by PRD text but not documented as intentional. |
| ERD-PRD-012 | Yes — no finding | All enumerable status/role fields documented with closed value sets in ERD Notes §Enums. Skip condition satisfied. |
| ERD-PRD-013 | Yes — no finding | No nullable FK on clearly mandatory relationships. Nullable FKs (INVITE.inviter_id, ABUSE_REVIEW.reviewer_id) are documented in Notes. |
| ERD-PRD-014 | Yes — no finding | No many-to-many lines. WORKSPACE_MEMBER is an explicit junction entity. |
| ERD-PRD-015 | Yes — no finding | No multi-currency requirement in PRD v1. |
| ERD-PRD-016 | Yes — no finding | All PKs are `uuid` type. |
| ERD-PRD-017 | Yes — no finding | PRD does not describe user-visible attribution feeds. Link list "creator" served by `LINK.owner_id FK`. |
| ERD-PRD-018 | Yes — no finding | PRD does not describe concurrent collaborative editing. |
| ERD-PRD-019 | Yes — no finding | Member removal handled at app layer. No structural cascade strategy needed beyond what exists. |
| ERD-PRD-020 | Yes — no finding | Retention is a scheduled job per Out of ERD scope. Trigger keywords not present in PRD. |
| ERD-PRD-021 | Yes — no finding | No multi-valued columns detected. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "erd-review",
    "id": "F1",
    "rule": "ERD-PRD-009",
    "gate": 2,
    "severity": "BLOCKER",
    "entity": "CLICK",
    "line": 0,
    "prd_section": "External integrations / Click pipeline — 'The ingest consumer is idempotent on (link_id, clicked_at)'",
    "finding": "No unique constraint on (link_id, clicked_at) is declared in the ERD or ERD Notes. At-least-once SQS delivery means duplicate messages are expected; without this constraint, duplicate click rows can silently inflate analytics counts.",
    "recommendation": "Add a composite unique index on CLICK(link_id, clicked_at) in the ERD Notes under 'Uniqueness constraints not natively expressible in Mermaid'."
  },
  {
    "domain": "erd-review",
    "id": "F2",
    "rule": "ERD-PRD-011",
    "gate": 3,
    "severity": "WARNING",
    "entity": "MIXPANEL_DEAD_LETTER",
    "line": 0,
    "prd_section": "External integrations / Mixpanel — failure handling",
    "finding": "MIXPANEL_DEAD_LETTER has no ERD relationship line to any other entity, making it a diagram-orphan. Its purpose is justified by PRD text but the absence of documentation as an intentionally unrelated log table may cause confusion.",
    "recommendation": "Add a prose note in the ERD confirming MIXPANEL_DEAD_LETTER is an intentionally unrelated log table."
  }
]
```

---

## STEP C — Summary Verdict

```json
{
  "domain": "erd-review",
  "gate1_count": 0,
  "gate2_count": 1,
  "gate3_count": 1,
  "verdict": "FAIL_BLOCKER",
  "note": "One Gate 2 blocker: CLICK table is missing a documented unique constraint on (link_id, clicked_at), which the PRD explicitly requires for idempotent at-least-once click pipeline ingestion. One Gate 3 warning: MIXPANEL_DEAD_LETTER is an ERD orphan with no relationship lines."
}
```
