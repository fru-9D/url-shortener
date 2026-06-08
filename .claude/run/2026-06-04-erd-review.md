# ERD Review — 2026-06-04

**PRD:** `docs/prd.md`
**ERD:** `docs/erd.md`
**Verdict:** PASS
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 0 findings

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|----------|---------|---------|------|----------|
| (none)   | No findings — all rules dismissed | — | — | — |

## Dismissed rules

| Rule ID      | Considered? | Dismissal reason |
|--------------|-------------|-----------------|
| ERD-PRD-001  | Yes | All 13 PRD first-class entities (USER, SESSION, LOGIN_ATTEMPT, WORKSPACE, WORKSPACE_MEMBER, INVITE, LINK, CLICK, PASSWORD_RESET_TOKEN, EMAIL_VERIFICATION_TOKEN, EMAIL_SUPPRESSION, MIXPANEL_DEAD_LETTER, ABUSE_REVIEW) are present in the ERD. |
| ERD-PRD-002  | Yes | All PRD-described relationships are drawn. EMAIL_SUPPRESSION has no relationship lines but Notes explicitly documents it has no FK to USER by design. |
| ERD-PRD-003  | Yes | ERD Notes §Email encryption at rest fully documents the email_ciphertext (AES-256-GCM + per-row DEK + AWS KMS) + email_search_hash (keyed HMAC-SHA256) pattern on USER, INVITE, and EMAIL_SUPPRESSION. Satisfies the rule's intent. |
| ERD-PRD-004  | Yes | All relationship cardinalities checked against PRD verbs. USER→WORKSPACE_MEMBER is ||--o{ (correct for soft-delete history model). USER→INVITE is o|--o{ — documented in Notes §INVITE.inviter_id as intentional nullable FK for future-proofing. No contradiction found. |
| ERD-PRD-005  | Yes | All Postgres-backed entities have created_at. SESSION and LOGIN_ATTEMPT are Redis-backed (Notes §Session — "no ORM model or migration generated"). CLICK omits updated_at — Notes §Click table documents CLICK as append-only with no post-insert mutations. All exemption criteria satisfied. |
| ERD-PRD-006  | Yes | ERD Notes §Multi-tenant scoping confirms workspace_id is carried directly on LINK, INVITE, WORKSPACE_MEMBER, CLICK, and ABUSE_REVIEW. |
| ERD-PRD-007  | Yes | LINK has deleted_at and disabled_at. INVITE has status covering all PRD lifecycle states. ABUSE_REVIEW has status (pending_review, whitelisted, disabled, hard_deleted). WORKSPACE_MEMBER has removed_at. |
| ERD-PRD-008  | Yes | No monetary amounts in v1 — billing is explicitly out of scope per PRD §Out of scope. Not applicable. |
| ERD-PRD-009  | Yes | USER.email_search_hash is UK. LINK.short_code partial UK (WHERE deleted_at IS NULL), WORKSPACE_MEMBER user_id partial UK (WHERE removed_at IS NULL), INVITE partial UK on (workspace_id, email_search_hash) WHERE status='pending' — all documented in Notes §Uniqueness constraints. Token hash UK markers present on all token tables. |
| ERD-PRD-010  | Yes | All ERD entity names are directly derivable from PRD vocabulary. WORKSPACE_MEMBER correctly captures the PRD's "Member" concept as a junction entity. |
| ERD-PRD-011  | Yes | Every ERD entity maps to an explicit PRD requirement: EMAIL_SUPPRESSION (§Email delivery suppression list), MIXPANEL_DEAD_LETTER (§Mixpanel failure handling), SESSION (§Account sessions), LOGIN_ATTEMPT (§Account failed-login throttling). No orphan entities. |
| ERD-PRD-012  | Yes | ERD Notes §Enums documents all closed value sets (WORKSPACE_MEMBER.role, INVITE.role, INVITE.status, EMAIL_SUPPRESSION.reason, CLICK.country_code, ABUSE_REVIEW.status) with PRD references. Rule intent satisfied. |
| ERD-PRD-013  | Yes | All required-side FKs are non-nullable via ||-- cardinality. INVITE.inviter_id nullable FK is documented as intentional in Notes §INVITE.inviter_id cardinality. No undocumented nullable FK on a PRD-mandatory relationship. |
| ERD-PRD-014  | Yes | No many-to-many relationship lines exist. All relationships are one-to-many or zero/one-to-many. Not applicable. |
| ERD-PRD-015  | Yes | No multi-currency context in v1; billing is out of scope. Not applicable. |
| ERD-PRD-016  | Yes | All database-entity PKs are uuid. SESSION.id is a HMAC-signed opaque string (Redis-backed). LINK.short_code is nanoid/custom slug, not a sequential integer. |
| ERD-PRD-017  | Yes | LINK has created_by_id FK (immutable, for PRD §Link list "creator" display). ABUSE_REVIEW has reviewer_id FK (nullable until reviewer acts). PRD §Out of scope excludes admin audit logs. |
| ERD-PRD-018  | Yes | PRD does not describe concurrent multi-user editing. Link editing is single-field (destination URL) with no concurrent-editing language. Rule trigger conditions not met. |
| ERD-PRD-019  | Yes | PRD does not describe workspace deletion in v1 (noted in ERD §Out of ERD scope). CLICK has its own independent 13-month retention policy; PRD does not prescribe cascade behavior for click orphans on LINK hard-delete. Rule trigger not satisfied. |
| ERD-PRD-020  | Yes | ERD Notes §Click table explicitly documents range-partitioning on clicked_at (monthly partitions) and the 13-month rolling-delete dropping whole partitions. Partitioning signal is present. |
| ERD-PRD-021  | Yes | No column stores multi-valued domain relations as serialized strings. MIXPANEL_DEAD_LETTER.payload is an opaque Mixpanel event blob, not a collection of addressable entities. No 1NF violation. |

## Gate 1 — Critical (ERD not safe to derive ORM models from)

No Gate 1 findings.

## Gate 2 — Blockers (material gaps)

No Gate 2 findings.

## Gate 3 — Warnings (soft spots)

No Gate 3 findings.

## Summary

The ERD passes all 21 rules cleanly against the PRD. The diagram is structurally sound and safe to derive ORM models from immediately. The Notes section is the primary reason for the clean result — it proactively addresses every structural concern before it becomes a rule violation: partial unique constraints, append-only justifications for absent `updated_at` columns, enum closed-sets with PRD references, the email PII encryption strategy (ciphertext + search-hash split), Redis-backed entity exemptions for SESSION and LOGIN_ATTEMPT, partitioning signal on the high-volume CLICK table, and the intentional nullable `inviter_id` FK. The only outstanding risk for downstream work comes from the PRD's seven Gate 2 blockers (reported in the prd-review run), particularly the undefined Cloudflare cache purge contract and the missing Link deletion feature — but those are PRD defects, not ERD defects.
