# ERD Review — Compressed Agent — Max Effort — Run 1
**Date:** 2026-06-02
**Agent:** erd-review-compressed
**Effort:** max
**Project:** Snip (url-shortener)

---

## STEP C — Summary Verdict

```json
{
  "domain": "erd-review",
  "gate1_count": 3,
  "gate2_count": 13,
  "gate3_count": 14,
  "verdict": "FAIL_CRITICAL"
}
```

---

## Gate 1 — Critical (3)

| ID | Rule | Entity | Finding |
|---|---|---|---|
| F01 | ERD-PRD-001 | N/A (missing) | Failed-login throttle state entity missing — no LOGIN_ATTEMPT_THROTTLE or equivalent; USER has no throttle columns |
| F02 | ERD-PRD-001 | N/A (missing) | SESSION entity missing — per-session 7-day idle expiry cannot be enforced; USER.session_version is bulk-invalidation only |
| F03 | ERD-PRD-002 | WORKSPACE / WORKSPACE_MEMBER | No ERD relationship or Notes annotation linking WORKSPACE.owner_id to a WORKSPACE_MEMBER admin row; ≥1 Admin invariant has no structural linkage |

---

## Gate 2 — Blockers (13)

| ID | Rule | Entity | Finding |
|---|---|---|---|
| F04 | ERD-PRD-004 | USER → WORKSPACE | Cardinality one-to-many; PRD v1 allows at most one workspace per user (should be `||--o|`) |
| F05 | ERD-PRD-004 | USER → ABUSE_REVIEW | Reviewer cardinality drawn as mandatory USER left-side; reviewer_id is nullable (should be `o|--o{`) |
| F06 | ERD-PRD-003 | EMAIL_SUPPRESSION | Missing email_ciphertext; all other email-bearing entities use (email_ciphertext, email_search_hash) split; inconsistency not documented |
| F07 | ERD-PRD-009 | CLICK | (link_id, clicked_at) composite unique key missing; idempotency constraint has no DB-level enforcement |
| F08 | ERD-PRD-007 | INVITE | INVITE.status enum missing 'cancelled' value; PRD requires cancellation as explicit lifecycle event |
| F09 | ERD-PRD-007 | INVITE | INVITE missing cancelled_at timestamp (accepted_at and declined_at exist; no parallel for cancellation) |
| F10 | ERD-PRD-007 | INVITE | INVITE.inviter_id nullable status undocumented; implementors will apply NOT NULL, breaking inviter-removal flow |
| F11 | ERD-PRD-009 | LINK | LINK.short_code inline UK marker implies full unique; Notes documents partial UK WHERE deleted_at IS NULL — conflicting signals |
| F12 | ERD-PRD-009 | WORKSPACE_MEMBER | WORKSPACE_MEMBER.user_id inline UK implies full unique; Notes documents partial UK WHERE removed_at IS NULL — conflicting signals |
| F13 | ERD-PRD-009 | LINK | LINK.destination_url has no length constraint annotation (PRD requires ≤ 2048 chars) |
| F14 | ERD-PRD-006 | ABUSE_REVIEW | ABUSE_REVIEW missing direct workspace_id FK; Multi-tenant scoping Notes lists LINK/INVITE/WORKSPACE_MEMBER/CLICK but not ABUSE_REVIEW |
| F15 | ERD-PRD-006 | MIXPANEL_DEAD_LETTER | MIXPANEL_DEAD_LETTER missing workspace_id column; payloads include workspace_id but not as indexed column |
| F16 | ERD-PRD-009 | N/A (missing) | Reserved slug prefix list (12 items) has no ERD representation — no RESERVED_SLUG table, no Notes, no is_reserved column |

---

## Gate 3 — Warnings (14)

| ID | Rule | Entity | Finding |
|---|---|---|---|
| F17 | ERD-PRD-010 | WORKSPACE_MEMBER | Name diverges from PRD primary vocabulary "Member" |
| F18 | ERD-PRD-004 | USER → WORKSPACE_MEMBER | Zero-or-many cardinality imprecise for v1 (at-most-one active); `||--o|` would be more accurate |
| F19 | ERD-PRD-010 | LINK | destination_url punycode normalisation requirement not annotated |
| F20 | ERD-PRD-020 | CLICK | Unbounded append-only log with no partitioning or archival strategy in Notes |
| F21 | ERD-PRD-017 | LINK | LINK.owner_id is mutable (reassigned on member removal); original creator lost for display |
| F22 | ERD-PRD-017 | WORKSPACE_MEMBER | Missing invited_by_id FK for post-acceptance attribution |
| F23 | ERD-PRD-010 | WORKSPACE | WORKSPACE.owner_id relationship to WORKSPACE_MEMBER admin role undocumented |
| F24 | ERD-PRD-011 | MIXPANEL_DEAD_LETTER | Structurally orphaned in diagram — no relationship lines to any other entity |
| F25 | ERD-PRD-012 | INVITE | Re-invite replace semantics (update vs delete+insert) undocumented |
| F26 | ERD-PRD-007 | INVITE | Missing expired_at transition timestamp (accepted_at and declined_at exist; no parallel) |
| F27 | ERD-PRD-009 | LINK | LINK.short_code has no length annotation (max 32 chars for custom slug) |
| F28 | ERD-PRD-019 | CLICK / LINK | Cascade strategy for CLICK rows on LINK hard-delete undocumented; CLICK has 13-month retention but LINK is hard-deleted at 30 days |
| F29 | ERD-PRD-019 | ABUSE_REVIEW / LINK | Cascade strategy for ABUSE_REVIEW rows on LINK hard-delete undocumented |
| F30 | ERD-PRD-019 | INVITE | INVITE cancellation cascade on member removal undocumented in ERD Notes |

---

## STEP A-bis — Rule Coverage

| Rule ID | Result |
|---|---|
| ERD-PRD-001 | FINDINGS: SESSION entity missing (F02); failed-login throttle entity missing (F01) |
| ERD-PRD-002 | FINDING: WORKSPACE.owner_id not linked to WORKSPACE_MEMBER admin row (F03) |
| ERD-PRD-003 | FINDING: EMAIL_SUPPRESSION missing email_ciphertext (F06) |
| ERD-PRD-004 | FINDINGS: USER→WORKSPACE cardinality (F04); ABUSE_REVIEW reviewer cardinality (F05); USER→WORKSPACE_MEMBER warning (F18) |
| ERD-PRD-005 | All 11 entities checked — PASS (CLICK append-only justified in Notes) |
| ERD-PRD-006 | FINDINGS: ABUSE_REVIEW no workspace_id (F14); MIXPANEL_DEAD_LETTER no workspace_id (F15) |
| ERD-PRD-007 | FINDINGS: INVITE missing 'cancelled' status (F08); missing cancelled_at (F09); inviter_id nullable undocumented (F10); expired_at missing (F26) |
| ERD-PRD-008 | DISMISSED: No money/financial columns |
| ERD-PRD-009 | FINDINGS: CLICK composite UK (F07); short_code inline UK (F11); user_id inline UK (F12); destination_url length (F13); reserved prefix list (F16); short_code length (F27) |
| ERD-PRD-010 | FINDINGS: WORKSPACE_MEMBER name (F17); destination_url punycode (F19); WORKSPACE.owner_id documentation (F23) |
| ERD-PRD-011 | FINDING: MIXPANEL_DEAD_LETTER orphaned (F24) |
| ERD-PRD-012 | FINDING: INVITE re-invite semantics (F25) |
| ERD-PRD-013 | CHECKED: No additional nullable FK issues beyond those captured |
| ERD-PRD-014 | DISMISSED: No many-to-many lines; WORKSPACE_MEMBER is explicit junction |
| ERD-PRD-015 | DISMISSED: No multi-currency |
| ERD-PRD-016 | DISMISSED: All PKs are uuid |
| ERD-PRD-017 | FINDINGS: LINK.owner_id mutable — creator lost (F21); WORKSPACE_MEMBER missing invited_by_id (F22) |
| ERD-PRD-018 | DISMISSED: No concurrent editing described in PRD |
| ERD-PRD-019 | FINDINGS: CLICK cascade on LINK hard-delete (F28); ABUSE_REVIEW cascade (F29); INVITE cancellation cascade (F30) |
| ERD-PRD-020 | FINDING: CLICK no partitioning strategy (F20) |
| ERD-PRD-021 | DISMISSED: No 1NF violations (MIXPANEL_DEAD_LETTER.payload intentionally opaque) |
