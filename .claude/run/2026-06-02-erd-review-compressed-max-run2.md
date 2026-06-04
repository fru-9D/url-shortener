# ERD Review — Compressed Agent — Max Effort — Run 2
**Date:** 2026-06-02
**Agent:** erd-review-compressed
**Effort:** max
**Project:** Snip (url-shortener)

---

## STEP C — Summary Verdict

```json
{
  "domain": "erd-review",
  "gate1_count": 5,
  "gate2_count": 11,
  "gate3_count": 7,
  "verdict": "FAIL_CRITICAL"
}
```

---

## Gate 1 — Critical (5)

| ID | Rule | Entity | Finding |
|---|---|---|---|
| F-01 | ERD-PRD-001 | missing | No LOGIN_ATTEMPT or FAILED_LOGIN_THROTTLE entity. Failed-login throttling state (per-email, 5/15min, 15-min lockout) must survive process restarts. USER has no throttle columns. |
| F-02 | ERD-PRD-001 | missing SESSION | No SESSION entity. Per-session 7-day idle expiry and immediate invalidation-on-removal require per-session last_activity_at. USER.session_version only supports global invalidation. |
| F-03 | ERD-PRD-001 | missing RESERVED_SLUG_PREFIX | 12 reserved slug prefixes have no ERD entity, column, or Notes documentation of data-layer enforcement. |
| F-04 | ERD-PRD-001 | LINK | LINK.owner_id is mutable (reassigned on member removal). No immutable created_by_id FK. Link list must display creator — original creator is permanently lost after reassignment. |
| F-05 | ERD-PRD-002 | EMAIL_SUPPRESSION | EMAIL_SUPPRESSION has no FK relationship or relationship lines to USER or INVITE, despite cross-referencing their email_search_hash values. Structurally orphaned suppression lookup. |

---

## Gate 2 — Blockers (11)

| ID | Rule | Entity | Finding |
|---|---|---|---|
| F-06 | ERD-PRD-004 | INVITE (USER→INVITE) | `USER ||--o{ INVITE` mandatory USER side contradicts nullable inviter_id after inviter removal. Correct: `USER o|--o{ INVITE`. |
| F-07 | ERD-PRD-004 | CLICK (WORKSPACE→CLICK) | `WORKSPACE ||--o{ CLICK` allows CLICK without WORKSPACE; workspace_id is mandatory at click-emission time. Correct: `||--|{`. |
| F-08 | ERD-PRD-004 | ABUSE_REVIEW (USER→ABUSE_REVIEW) | `USER ||--o{ ABUSE_REVIEW` mandatory USER side contradicts nullable reviewer_id until reviewer acts. Correct: `USER o|--o{ ABUSE_REVIEW`. |
| F-09 | ERD-PRD-007 | INVITE | INVITE.status missing 'cancelled' value; PRD requires cancellation as explicit lifecycle state when inviter is removed. |
| F-10 | ERD-PRD-006 | ABUSE_REVIEW | ABUSE_REVIEW has no workspace_id column. Reviewer ops queries are workspace-scoped. ERD Notes provide no justification. |
| F-11 | ERD-PRD-006 | MIXPANEL_DEAD_LETTER | MIXPANEL_DEAD_LETTER has no workspace_id column. workspace_id is in opaque JSON payload, not queryable. ERD Notes provide no justification. |
| F-12 | ERD-PRD-003 | EMAIL_SUPPRESSION | EMAIL_SUPPRESSION missing email_ciphertext. USER and INVITE both use (email_ciphertext, email_search_hash) split. ERD Notes §Email encryption do not explain this asymmetry. |
| F-13 | ERD-PRD-009 | LINK | LINK.destination_url has no length constraint annotation (PRD requires ≤ 2048 chars). |
| F-14 | ERD-PRD-009 | LINK | LINK.short_code inline UK contradicts Notes partial UK (WHERE deleted_at IS NULL). Global UK would block slug reuse after deletion. |
| F-15 | ERD-PRD-009 | WORKSPACE_MEMBER | WORKSPACE_MEMBER.user_id inline UK contradicts Notes partial UK (WHERE removed_at IS NULL). Global UK prevents re-membership. |
| F-16 | ERD-PRD-009 | CLICK | No composite unique constraint on (link_id, clicked_at). PRD-mandated idempotency has no DB-layer enforcement. |

---

## Gate 3 — Warnings (7)

| ID | Rule | Entity | Finding |
|---|---|---|---|
| F-17 | ERD-PRD-007 | WORKSPACE | No lifecycle/status field; PRD defers this to post-v1. ERD Out of Scope section acknowledges it. |
| F-18 | ERD-PRD-010 | LINK | Relationship label "created by" on LINK misrepresents mutable owner_id semantics |
| F-19 | ERD-PRD-010 | WORKSPACE | WORKSPACE.owner_id relationship to WORKSPACE_MEMBER admin role undocumented in Notes |
| F-20 | ERD-PRD-011 | MIXPANEL_DEAD_LETTER | No relationship lines (orphan); PRD-justified but structurally isolated |
| F-21 | ERD-PRD-020 | CLICK | Unbounded append-only high-throughput table with no partitioning/archival strategy in Notes |
| F-22 | ERD-PRD-017 | LINK | LINK has created_at but no immutable created_by_id; original creator lost after owner reassignment |
| F-23 | ERD-PRD-012 | INVITE | INVITE.email_search_hash has no inline UK marker, unlike USER and EMAIL_SUPPRESSION — inconsistent documentation pattern |

---

## STEP A-bis — Rule Coverage

| Rule ID | Result |
|---|---|
| ERD-PRD-001 | FINDINGS: F-01 (throttle state), F-02 (SESSION), F-03 (reserved prefix), F-04 (created_by_id) |
| ERD-PRD-002 | FINDING: F-05 (EMAIL_SUPPRESSION orphaned) |
| ERD-PRD-003 | FINDING: F-12 (EMAIL_SUPPRESSION missing email_ciphertext) |
| ERD-PRD-004 | FINDINGS: F-06 (INVITE inviter_id), F-07 (CLICK workspace_id), F-08 (ABUSE_REVIEW reviewer_id) |
| ERD-PRD-005 | PASS: All 11 entities checked. CLICK append-only justified in Notes. |
| ERD-PRD-006 | FINDINGS: F-10 (ABUSE_REVIEW no workspace_id), F-11 (MIXPANEL_DEAD_LETTER no workspace_id) |
| ERD-PRD-007 | FINDINGS: F-09 (INVITE missing 'cancelled'), F-17 (WORKSPACE lifecycle acknowledged) |
| ERD-PRD-008 | DISMISSED: No monetary columns |
| ERD-PRD-009 | FINDINGS: F-13 (destination_url length), F-14 (LINK.short_code UK contradiction), F-15 (WORKSPACE_MEMBER.user_id UK contradiction), F-16 (CLICK idempotency UK) |
| ERD-PRD-010 | FINDINGS: F-18 (LINK label), F-19 (WORKSPACE.owner_id undocumented) |
| ERD-PRD-011 | FINDING: F-20 (MIXPANEL_DEAD_LETTER orphan) |
| ERD-PRD-012 | FINDING: F-23 (INVITE email_search_hash inline UK inconsistency) |
| ERD-PRD-013 | CHECKED: No additional nullable FK violations beyond those captured in ERD-PRD-004 findings |
| ERD-PRD-014 | DISMISSED: No many-to-many lines |
| ERD-PRD-015 | DISMISSED: No multi-currency |
| ERD-PRD-016 | DISMISSED: All PKs are uuid |
| ERD-PRD-017 | FINDING: F-22 (LINK missing immutable created_by_id) |
| ERD-PRD-018 | DISMISSED: No concurrent editing in PRD |
| ERD-PRD-019 | DISMISSED: No cascade delete requirement in PRD v1 |
| ERD-PRD-020 | FINDING: F-21 (CLICK no partitioning strategy) |
| ERD-PRD-021 | DISMISSED: MIXPANEL_DEAD_LETTER.payload intentionally opaque |
