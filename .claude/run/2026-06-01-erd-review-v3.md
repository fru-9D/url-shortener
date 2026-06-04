# ERD Review — 2026-06-01 (v3)

**PRD:** `docs/prd.md`
**ERD:** `docs/erd.md`
**Verdict:** FAIL_CRITICAL
**Gate 1:** 1  **Gate 2:** 2  **Gate 3:** 0

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `docs/prd.md` §Link creation | PRD describes an "Abuse review queue" as a first-class ops concept — links are flagged, queued, and reviewed with actions (whitelist/disable/hard-delete). No ERD entity exists for this queue, and LINK carries no column tracking abuse-queue membership or review state. | ERD-PRD-001 | 1 | critical |
| `docs/erd.md` CLICK entity | CLICK entity has no `created_at` or `updated_at` columns. PRD NFR §Data retention states audit fields are retained indefinitely. ERD Notes do not document CLICK as append-only/immutable to justify the omission; they only note `clicked_at` is the event timestamp and that retention is via scheduled job. | ERD-PRD-005 | 2 | blocker |
| `docs/prd.md` §Link creation | PRD describes a "disable" reviewer action that makes a link return 404 until reviewed — semantically distinct from user-initiated soft-delete (`deleted_at`). LINK has no column for ops-disable state (`disabled_at`, `is_disabled`, `abuse_status`). Conflating disable with `deleted_at` would corrupt the 30-day slug-reuse window and make "whitelist" (undo disable) ambiguous. | ERD-PRD-007 | 2 | blocker |

---

## Findings

### ERD-PRD-001 · Gate 1 · critical · effort: medium

**Message:** PRD §Link creation describes an "Abuse review queue" as a first-class operational concept: links that fail the Google Safe Browsing check are flagged and added to the queue, trust-and-safety reviewers act on them within 24 hours, and reviewer actions are whitelist, disable, or hard-delete. The `LINK` entity has no column tracking abuse-queue membership or review state, and there is no `ABUSE_REVIEW` / `FLAGGED_LINK` entity in the ERD. Without this, the system cannot store which links are under review, what state the review is in, who performed the review action, or when.

**Fix:** Add an `ABUSE_REVIEW` entity (or at minimum an `abuse_status` column on `LINK`) to represent the queue. At minimum the entity needs: a FK to `LINK`, a status column (`pending_review | whitelisted | disabled | hard_deleted`), timestamps for when the flag was created and when the review action was taken, and a reviewer FK to `USER`. `LINK` may also need a derived `disabled_at` or `is_disabled` column so the redirect service can check disable state independently of the soft-delete `deleted_at`.

---

### ERD-PRD-005 · Gate 2 · blocker · effort: low

**Message:** The `CLICK` entity has neither `created_at` nor `updated_at`. PRD NFR §Data retention states "Audit fields (created_at, updated_at): indefinite." Although `CLICK` has `clicked_at` as the event timestamp, `created_at` is a distinct audit field recording when the row was inserted (which may lag `clicked_at` by up to 60 seconds given the pipeline buffering described in PRD §Click pipeline). The ERD Notes document the 13-month rolling-delete strategy and denormalization rationale but do not explicitly declare `CLICK` as append-only/immutable to satisfy the mandatory checklist's exemption criteria.

**Fix:** Add `created_at datetime` to the `CLICK` entity. Because `CLICK` rows are never mutated after insert (the pipeline is append-only), `updated_at` may be omitted — but this must be explicitly documented in the ERD Notes §Click table as: "CLICK is append-only; no field mutates after insert; `updated_at` is intentionally omitted."

---

### ERD-PRD-007 · Gate 2 · blocker · effort: low

**Message:** PRD §Link creation describes a "disable" reviewer action that makes a link return 404 to visitors until reviewed, and a "whitelist" action that undoes the disable with no change to the live link. `LINK` has `deleted_at` for user-initiated soft-delete and the 30-day reuse window, but no column for ops-initiated disable. These are semantically distinct states: disable is reversible (whitelist restores normal redirect), whereas soft-delete is a user or admin action subject to the 30-day reuse clock. Conflating them via `deleted_at` would make "whitelist" indistinguishable from "undelete", corrupt the slug-reuse window, and prevent the redirect service from differentiating a soft-deleted link from a temporarily disabled one.

**Fix:** Add a lifecycle column to `LINK` for the ops-disable state — for example `disabled_at datetime` (nullable, set by reviewer, cleared on whitelist) or an `abuse_status` enum column. Document in ERD Notes §Soft delete how the redirect service distinguishes `deleted_at IS NOT NULL` (soft-deleted, 404 + reuse clock ticking) from `disabled_at IS NOT NULL` (ops-disabled, 404 until whitelisted, reuse clock not affected).

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ERD-PRD-002 | Yes | All PRD-described relationships between existing entities have corresponding ERD lines. EMAIL_SUPPRESSION and MIXPANEL_DEAD_LETTER are system-level tables with no FK-style relationships expected. |
| ERD-PRD-003 | Yes | ERD Notes §Email encryption at rest explicitly documents AES-256-GCM at application layer with KMS, email_ciphertext / email_search_hash pattern for USER, INVITE, and EMAIL_SUPPRESSION. Notes §Token tables documents hash-only storage. PII handling is fully acknowledged. |
| ERD-PRD-004 | Yes | All ERD cardinalities are consistent with PRD verbs. The WORKSPACE_MEMBER partial-UK enforces the v1 single-Workspace constraint at app layer; the ERD's 1:N line is structurally correct for the schema. |
| ERD-PRD-006 | Yes | All workspace-scoped entities (LINK, INVITE, WORKSPACE_MEMBER, CLICK) carry `workspace_id FK`. System-wide entities (PASSWORD_RESET_TOKEN, EMAIL_VERIFICATION_TOKEN, EMAIL_SUPPRESSION, MIXPANEL_DEAD_LETTER) are correctly not workspace-scoped. |
| ERD-PRD-008 | Yes | No monetary columns exist in v1. PRD explicitly excludes billing, Stripe, and paid plans from v1 scope. |
| ERD-PRD-009 | Yes | All PRD-implied uniqueness constraints are expressed: LINK.short_code (partial UK documented in Notes), USER.email_search_hash (UK), token hashes (UK), WORKSPACE_MEMBER one-active-membership (partial UK documented in Notes), INVITE pending-uniqueness (partial UK documented in Notes), EMAIL_SUPPRESSION.email_search_hash (UK). |
| ERD-PRD-010 | Yes | Entity names are consistent with PRD vocabulary. WORKSPACE_MEMBER is a clear junction-table name for the PRD's "Member" concept; no material drift detected. |
| ERD-PRD-011 | Yes | EMAIL_SUPPRESSION is justified by PRD §Email delivery (internal suppression list). MIXPANEL_DEAD_LETTER is justified by PRD §Mixpanel (dead-letter table for failed events). Neither entity has FK relationships by design (system-level tables, not workspace-scoped). |
| ERD-PRD-012 | Yes | All closed value sets are documented in ERD Notes §Enums with column annotations and PRD references. The Notes satisfy the rule's safe-harbor: the closed sets are explicitly documented in the ERD artifact. |
| ERD-PRD-013 | Yes | All required-side FKs match PRD cardinality. The ERD's `\|\|--o{` for USER → WORKSPACE is correct (a new user has zero workspaces initially). No nullable FK contradicts a PRD "required" relationship. |
| ERD-PRD-014 | Yes | No bare many-to-many lines in the ERD. The User ↔ Workspace many-to-many is properly resolved via the WORKSPACE_MEMBER junction entity. |
| ERD-PRD-015 | Yes | No monetary amounts in v1. PRD explicitly excludes billing and Stripe. |
| ERD-PRD-016 | Yes | All PKs are `uuid`. No sequential integer PKs. Short codes are string columns, not PKs. |
| ERD-PRD-017 | Yes | LINK.owner_id serves the PRD link-list "creator" attribution requirement. No other entity has a PRD-described user-visible attribution requirement. |
| ERD-PRD-018 | Yes | PRD describes no concurrent editing scenarios. Operations (invite, remove, create link) are sequential single-user actions. |
| ERD-PRD-019 | Yes | PRD does not describe Workspace deletion or user deletion in v1 (GDPR delete is manual via support). No cascade delete requirement exists in the PRD. ERD Notes acknowledge this gap. |
| ERD-PRD-020 | Yes | CLICK is the high-volume entity (every redirect = one row, "time-series" per PRD). ERD Notes §Out of ERD scope documents the 13-month rolling-delete archival strategy via scheduled job, satisfying the "archival signal" requirement. |
| ERD-PRD-021 | Yes | MIXPANEL_DEAD_LETTER.payload is `json` for opaque Mixpanel event replay — PRD describes it as an opaque dead-letter blob, not a queryable collection. No other multi-valued columns detected. |

---

## JSON findings

```json
[
  {
    "domain": "erd-review",
    "gate": 1,
    "severity": "critical",
    "rule": "ERD-PRD-001",
    "file": "docs/prd.md",
    "line": 0,
    "snippet": "",
    "message": "PRD §Link creation describes an 'Abuse review queue' as a first-class operational concept: links that fail the Google Safe Browsing check are flagged and added to the queue, trust-and-safety reviewers act on them within 24 hours, and reviewer actions are whitelist, disable, or hard-delete. The LINK entity has no column tracking abuse-queue membership or review state, and there is no ABUSE_REVIEW / FLAGGED_LINK entity in the ERD.",
    "fix": "Add an ABUSE_REVIEW entity with a FK to LINK, a status enum (pending_review | whitelisted | disabled | hard_deleted), timestamps, and a reviewer FK to USER. LINK also needs a disabled_at column so the redirect service can distinguish ops-disable from soft-delete.",
    "effort": "medium"
  },
  {
    "domain": "erd-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ERD-PRD-005",
    "file": "docs/erd.md",
    "line": 0,
    "snippet": "",
    "message": "The CLICK entity has neither created_at nor updated_at. PRD NFR §Data retention states audit fields are retained indefinitely. clicked_at is the event time, not the row-insert time — the pipeline's buffering means these can diverge by up to 60 seconds. The ERD Notes do not declare CLICK as append-only to justify the omission.",
    "fix": "Add created_at datetime to CLICK. Since rows are never mutated post-insert, updated_at can be omitted — but the ERD Notes §Click table must explicitly state: 'CLICK is append-only; updated_at intentionally omitted.'",
    "effort": "low"
  },
  {
    "domain": "erd-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ERD-PRD-007",
    "file": "docs/prd.md",
    "line": 0,
    "snippet": "",
    "message": "PRD §Link creation describes a 'disable' reviewer action that makes a link return 404 until reviewed, and a 'whitelist' action that undoes the disable. LINK has deleted_at for user-initiated soft-delete but no column for ops-initiated disable. Conflating them via deleted_at corrupts the 30-day slug-reuse window and makes the two states indistinguishable in the redirect service.",
    "fix": "Add disabled_at datetime (nullable, set on disable, cleared on whitelist) to LINK. Document in ERD Notes §Soft delete how the redirect service distinguishes deleted_at IS NOT NULL from disabled_at IS NOT NULL.",
    "effort": "low"
  }
]
```

## Domain summary

```json
{
  "domain": "erd-review",
  "gate1_count": 1,
  "gate2_count": 2,
  "gate3_count": 0,
  "verdict": "FAIL_CRITICAL"
}
```
