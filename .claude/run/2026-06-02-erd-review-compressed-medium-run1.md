# ERD Review — Compressed Agent — Medium Effort — Run 1
**Date:** 2026-06-02
**Agent:** erd-review-compressed
**Effort:** medium
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| No entity in ERD | PRD §Account: "Failed-login throttling: 5 failed attempts per email per 15 minutes → 15-minute lockout. Per-email." No LOGIN_ATTEMPT entity, no failed_attempt_count, no lockout_until, no throttle_window_start on USER. No ERD annotation acknowledging where this state lives. | ERD-PRD-001 | G1 | Critical |
| USER entity | PRD §Account: "Sessions: 30-day absolute expiry, 7-day idle expiry." Plus §Teams: "active sessions are invalidated at the moment of removal." USER.session_version handles bulk invalidation but cannot enforce per-session 7-day idle expiry — every session would need its own last-activity timestamp. Without a SESSION entity or server-side session store, the 7-day idle TTL cannot be enforced independently of the 30-day absolute TTL. | ERD-PRD-001 | G1 | Critical |
| CLICK entity | PRD §Click pipeline: CLICK is append-only time-series with 13-month rolling retention at redirect-service scale. ERD Notes documents a composite index on (workspace_id, clicked_at) but no partitioning strategy, range-partition hint, or TTL/archival approach. At marketing-campaign scale this table will grow to tens or hundreds of millions of rows within the 13-month retention window. | ERD-PRD-020 | G3 | Warning |

---

## STEP A-bis — Rule Disposition Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ERD-PRD-001 | Yes — 2 findings | G1-1: Login throttle state missing (no entity/columns). G1-2: Per-session idle-expiry state missing (USER.session_version insufficient). |
| ERD-PRD-002 | Yes — no finding | All PRD relationships have ERD lines. WORKSPACE↔LINK, USER↔LINK, LINK↔CLICK, USER↔WORKSPACE_MEMBER, WORKSPACE↔INVITE, USER↔INVITE, USER↔PASSWORD_RESET_TOKEN, USER↔EMAIL_VERIFICATION_TOKEN, LINK↔ABUSE_REVIEW all present. |
| ERD-PRD-003 | Yes — no finding | Email PII split into email_ciphertext + email_search_hash with AES-256-GCM documented in Notes. PRD NFR §Security satisfied. |
| ERD-PRD-004 | Yes — no finding | All cardinalities reviewed and consistent with PRD verbs. USER↔WORKSPACE_MEMBER `||--o{` correct (zero memberships valid for un-onboarded user). Partial UK in Notes restricts only active memberships. |
| ERD-PRD-005 | Yes — no finding | All 11 entities pass. CLICK exempt (append-only, documented in Notes). |
| ERD-PRD-006 | Yes — no finding | Notes §Multi-tenant scoping documents workspace_id on LINK, INVITE, WORKSPACE_MEMBER, CLICK. Other tables are system-level or user-scoped by design. |
| ERD-PRD-007 | Yes — no finding | LINK has deleted_at and disabled_at. INVITE has status. WORKSPACE_MEMBER has removed_at. All lifecycle signals present. |
| ERD-PRD-008 | Yes — no finding | No money/precise numeric fields in v1 schema. Billing/Stripe explicitly out of scope. |
| ERD-PRD-009 | Yes — no finding | USER.email_search_hash UK, LINK.short_code UK (partial, Notes), INVITE partial UK (Notes). All PRD uniqueness requirements covered. |
| ERD-PRD-010 | Yes — no finding | Entity names align with PRD vocabulary. WORKSPACE_MEMBER maps to "Member." No significant divergence. |
| ERD-PRD-011 | Yes — no finding | All ERD entities trace to PRD. EMAIL_SUPPRESSION→SES bounce handling, MIXPANEL_DEAD_LETTER→Mixpanel failure handling, ABUSE_REVIEW→abuse review queue. No orphans. |
| ERD-PRD-012 | Yes — no finding | Notes §Enums documents all closed-value-set columns with PRD references. Skip condition satisfied. |
| ERD-PRD-013 | Yes — no finding | FKs on required relationships: LINK.owner_id, LINK.workspace_id, CLICK.link_id, CLICK.workspace_id all required and present. ABUSE_REVIEW.reviewer_id nullable justified in Notes. |
| ERD-PRD-014 | Yes — no finding | No raw many-to-many lines. WORKSPACE_MEMBER is explicit junction entity. |
| ERD-PRD-015 | Yes — no finding | No multi-currency requirement in PRD v1. |
| ERD-PRD-016 | Yes — no finding | All PKs are uuid type. |
| ERD-PRD-017 | Yes — no finding | LINK.owner_id serves creator attribution for link list "creator" display. Audit logs explicitly out of scope. |
| ERD-PRD-018 | Yes — no finding | PRD does not describe concurrent multi-user editing of shared resources. |
| ERD-PRD-019 | Yes — no finding | No Workspace deletion scenario in v1. Member removal uses soft-removal (removed_at). Link owner reassignment is explicit, not cascade. |
| ERD-PRD-020 | Yes — 1 warning | CLICK is append-only time-series with 13-month rolling retention at redirect-service scale; no partitioning strategy documented. |
| ERD-PRD-021 | Yes — no finding | No multi-valued columns. All collections normalized into dedicated entities. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "erd-review",
    "id": "G1-1",
    "rule": "ERD-PRD-001",
    "gate": 1,
    "severity": "CRITICAL",
    "entity": null,
    "line": 0,
    "prd_section": "§Account — Failed-login throttling",
    "title": "No login-throttle state entity or columns in ERD",
    "detail": "PRD requires per-email failed-login throttling: 5 failed attempts per 15-minute window triggers a 15-minute lockout. This is durable, per-email state. The ERD has no LOGIN_ATTEMPT or FAILED_LOGIN entity, no failed_attempt_count, no lockout_until, no throttle_window_start on USER. Even if Redis is used at runtime, the ERD must document where this state is anchored."
  },
  {
    "domain": "erd-review",
    "id": "G1-2",
    "rule": "ERD-PRD-001",
    "gate": 1,
    "severity": "CRITICAL",
    "entity": "USER",
    "line": 0,
    "prd_section": "§Account — Sessions; §Teams — Member removal",
    "title": "No per-session entity for idle-expiry and immediate-invalidation enforcement",
    "detail": "PRD specifies a 7-day idle expiry in addition to 30-day absolute expiry. It also requires immediate invalidation of all active sessions when a Member is removed. USER.session_version supports global invalidation via version bump, but cannot distinguish idle sessions per-session. Without a SESSION entity or equivalent server-side session store, the 7-day idle TTL cannot be enforced."
  },
  {
    "domain": "erd-review",
    "id": "G3-1",
    "rule": "ERD-PRD-020",
    "gate": 3,
    "severity": "WARNING",
    "entity": "CLICK",
    "line": 0,
    "prd_section": "§Click analytics; §Non-functional requirements — Data retention",
    "title": "CLICK table has no partitioning or archival strategy in ERD Notes",
    "detail": "PRD describes CLICK as an append-only time-series event log with 13-month rolling retention. ERD Notes documents a composite index on (workspace_id, clicked_at) but no partitioning strategy or TTL/archival approach. At marketing-campaign scale this table will grow to tens or hundreds of millions of rows within the 13-month retention window."
  }
]
```

---

## STEP C — Summary Verdict

```json
{
  "domain": "erd-review",
  "gate1_count": 2,
  "gate2_count": 0,
  "gate3_count": 1,
  "verdict": "FAIL_CRITICAL",
  "note": "Two Gate 1 findings: (1) login-throttle state has no ERD representation; (2) per-session idle-expiry tracking is structurally absent. One Gate 3 warning: CLICK table lacks partitioning/archival strategy."
}
```
