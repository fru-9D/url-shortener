# ERD Review — Compressed Agent — Low Effort — Run 1
**Date:** 2026-06-02
**Agent:** erd-review-compressed
**Effort:** low
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| ERD: no failed_login_attempt or lockout entity | PRD §Account: "5 failed attempts per email per 15 minutes triggers a 15-minute lockout. Lockout is per-email." No ERD entity or column captures this (USER has no `failed_login_count`, `lockout_until`, or equivalent; no LOGIN_ATTEMPT table exists). | ERD-PRD-001 | G1 | Critical |
| ERD: CLICK — no `user_agent` column | PRD §Click analytics: "Bot User-Agents matching the IAB/ABC International Spiders & Bots List are excluded from the displayed count, but raw counts are still stored." ERD has `is_bot` (the result) but no `user_agent` storage. If classification needs to be re-run or audited, no raw signal exists. | ERD-PRD-011 | G3 | Warning |

---

## STEP A-bis — Rule Disposition Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ERD-PRD-001 | YES — partial finding | Failed login lockout tracking has no ERD entity (filed as G1). All other PRD nouns are represented. |
| ERD-PRD-002 | YES — no finding | All PRD relationships have ERD lines. |
| ERD-PRD-003 | YES — no finding | Email PII: ERD Notes §"Email encryption at rest" documents AES-256-GCM + HMAC-SHA256 split. Fully satisfied. |
| ERD-PRD-004 | YES — no finding | All reviewed cardinalities match PRD verbs. |
| ERD-PRD-005 | YES — no finding (except CLICK exemption) | All entities have `created_at` + `updated_at` except CLICK, which is documented as append-only in Notes. |
| ERD-PRD-006 | YES — no finding | All workspace-scoped entities (LINK, INVITE, WORKSPACE_MEMBER, CLICK) carry `workspace_id` FK. |
| ERD-PRD-007 | YES — no finding | LINK has `deleted_at` and `disabled_at`. WORKSPACE omission explicitly justified. WORKSPACE_MEMBER has `removed_at`. INVITE has `status` with lifecycle states. |
| ERD-PRD-008 | YES — no finding | No monetary amounts in v1 (no billing). |
| ERD-PRD-009 | YES — no finding | All PRD uniqueness requirements covered or Notes-documented. |
| ERD-PRD-010 | YES — no finding | ERD vocabulary matches PRD glossary exactly. |
| ERD-PRD-011 | YES — G3 warning filed | CLICK lacks raw `user_agent` column. |
| ERD-PRD-012 | YES — no finding | All enumerable status/role fields documented with closed value sets in ERD Notes §Enums. |
| ERD-PRD-013 | YES — no finding | No nullable FK on clearly mandatory relationships. Nullable FKs (INVITE.inviter_id, ABUSE_REVIEW.reviewer_id) are documented in Notes. |
| ERD-PRD-014 | YES — no finding | No bare many-to-many lines; WORKSPACE_MEMBER is an explicit junction entity. |
| ERD-PRD-015 | YES — no finding | No multi-currency scope in v1. |
| ERD-PRD-016 | YES — no finding | All PKs are `uuid` type. |
| ERD-PRD-017 | YES — no finding | PRD does not describe user-visible attribution feeds. Link list "creator" served by `LINK.owner_id FK`. |
| ERD-PRD-018 | YES — no finding | PRD does not describe concurrent collaborative editing. |
| ERD-PRD-019 | YES — no finding | PRD §Teams: Workspace deletion not described. Member removal is a soft operation. |
| ERD-PRD-020 | YES — no finding | 13-month rolling delete is a scheduled job per Out of ERD scope. |
| ERD-PRD-021 | YES — no finding | No multi-valued columns detected. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-001",
    "gate": 1,
    "severity": "CRITICAL",
    "entity": null,
    "line": 0,
    "prd_section": "Features > Account — Failed-login throttling",
    "finding": "PRD requires per-email failed-login attempt counting and a 15-minute lockout. No ERD entity or column tracks this state — USER has no failed_login_count, lockout_until, or equivalent, and no LOGIN_ATTEMPT or RATE_LIMIT table exists."
  },
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-011",
    "gate": 3,
    "severity": "WARNING",
    "entity": "CLICK",
    "line": 0,
    "prd_section": "Features > Click analytics — bot exclusion",
    "finding": "CLICK stores is_bot (the computed classification result) but not the raw user_agent string. If bot classification must be re-run or audited, there is no raw signal to reprocess. Not documented in ERD Notes."
  }
]
```

---

## STEP C — Summary Verdict

```json
{
  "domain": "erd-review",
  "gate1_count": 1,
  "gate2_count": 0,
  "gate3_count": 1,
  "verdict": "FAIL_CRITICAL",
  "note": "One Gate 1 finding: failed-login throttling state has no ERD representation. One Gate 3 warning: raw user_agent not stored on CLICK."
}
```
