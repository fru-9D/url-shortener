# ERD Review — 2026-05-25 (v2)

**PRD:** `docs/prd.md` (v3, PASS_WITH_RISK)
**ERD:** `docs/erd.md` (v2, iterated after v1's FAIL_CRITICAL review)
**Verdict:** PASS
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 0 findings

## Trajectory

| Counter | v1 | v2 |
|---|---|---|
| Gate 1 | 4 | 0 |
| Gate 2 | 3 | 0 |
| Gate 3 | 3 | 0 |
| **Total** | **10** | **0** |
| Verdict | FAIL_CRITICAL | PASS |

## v1 → v2 verification

All seven Gate 1 + Gate 2 items addressed:

| v1 Finding | v2 status |
|---|---|
| PASSWORD_RESET_TOKEN entity missing | Fixed — entity added with `user_id FK`, `token_hash UK`, `expires_at`, `consumed_at` |
| EMAIL_VERIFICATION_TOKEN entity missing | Fixed — entity added with same shape |
| Email encryption-at-rest boundary not signaled | Fixed — split into `email_ciphertext` + `email_search_hash` across USER / INVITE / EMAIL_SUPPRESSION; Notes document AES-256-GCM + HMAC-SHA256 pattern |
| USER → WORKSPACE relationship line missing | Fixed — `USER ||--o{ WORKSPACE : "created by"` drawn |
| CLICK missing workspace_id | Fixed — `workspace_id FK` added + `WORKSPACE ||--o{ CLICK` relationship line |
| WORKSPACE_MEMBER (workspace_id, user_id) uniqueness | Fixed — `user_id FK,UK` marker + Notes documents partial UK on `WHERE removed_at IS NULL` with PRD line ref |
| INVITE (workspace_id, email) pending uniqueness | Fixed — Notes documents partial UK on `WHERE status='pending'` with PRD line ref |

## v1 → v2 enum hints (Gate 3)

The three v1 Gate 3 findings on plain-string enums (INVITE.status, WORKSPACE_MEMBER.role, INVITE.role) are now addressed via a dedicated "Enums" table in the ERD's Notes section, which enumerates closed value sets for each column with PRD line references. The Mermaid column type stays `string` (a notation limitation), but the closed set is unambiguously signaled.

## Considered but not flagged

The reviewer explicitly walked through potential additional findings and rejected each on merit:

- **Failed-login lockout state** (PRD line 165): persisted counters per email + lockout end-time. PRD doesn't describe these as listed / queried / audited — typically Redis-backed, not relational DB. Not first-class data.
- **Link-creation rate limit** (PRD line 97, 60 links/min/user): infrastructure concern, not domain data.
- **Abuse review queue** (PRD line 85, fail-open Safe Browsing): described mechanistically but no operator UI / listing specified in PRD.
- **Workspace deletion lifecycle**: ERD's own Notes acknowledge this as a known PRD Gate 3 gap, not an ERD defect.

## Summary

ERD v2 is safe to derive ORM models from. All v1 review findings substantively addressed — fixes verified against rule intent, not just keyword presence. The Workspace deletion gap remains an upstream PRD concern (Gate 3 in the PRD review); the ERD is faithful to current PRD state and explicitly calls out the inheritance.
