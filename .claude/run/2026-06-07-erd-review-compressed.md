# ERD Review (compressed) — 2026-06-07

**PRD:** `docs/prd.md`
**ERD:** `docs/erd.md`
**Reconciled from:** 2 independent compressed reviewer runs
**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 2 findings
**Gate 3 (Warnings):** 1 finding

> **Cross-track note (significant):** The standard ERD pipeline returned `PASS_WITH_RISK` with one finding (ERD-PRD-020, CLICK partitioning hedged as "consider"). This compressed pipeline returned `FAIL_BLOCKER` and found a *different* set of issues entirely: audit-column gaps on the Redis-backed `SESSION`/`LOGIN_ATTEMPT` entities (ERD-PRD-005) plus a relationship-without-FK (ERD-PRD-013) — and it did **not** flag CLICK partitioning (both compressed runs read the Notes as satisfying the partitioning signal). The two tracks genuinely disagree on (a) whether ERD-PRD-005's audit-column rule applies to Redis-backed logical entities, and (b) whether "consider range-partitioning" satisfies ERD-PRD-020. Treat the union of both reports as the real worklist; neither track is strictly superior here.

## Lookup
| Location | Finding | Rule ID | Gate | Severity |
|----------|---------|---------|------|----------|
| docs/erd.md:41 | `SESSION` mutates `last_activity_at` on every authenticated request but has `created_at` only, no `updated_at`; Notes don't justify the omission | ERD-PRD-005 | 2 | blocker |
| docs/erd.md:50 | `LOGIN_ATTEMPT` is mutable (`attempt_count`/`locked_until`) yet has neither `created_at` nor `updated_at`; Notes describe Redis/TTL mechanics but never invoke the audit-column exemption | ERD-PRD-005 | 2 | blocker |
| docs/erd.md:27 | `USER ||--o{ LOGIN_ATTEMPT` drawn (mandatory USER side) but LOGIN_ATTEMPT has no `user_id` FK — keyed on `email_search_hash`; lockout is per-email and tracks emails with no USER row | ERD-PRD-013 | 3 | warning |

## Gate 1 — Critical (ERD not safe to derive ORM models from)

_None._

## Gate 2 — Blockers (material gaps)

### [ERD-PRD-005] — SESSION omits updated_at despite recurring mutation
**Location:** `docs/erd.md:41`
**Finding:** SESSION mutates `last_activity_at` on every authenticated request (a repeated, non-one-way mutation) but has `created_at` only, no `updated_at`. The ERD-PRD-005 checklist permits omitting `updated_at` only for a single one-way transition captured by a dedicated timestamp **and** stated in Notes; the Notes document the refresh mechanics but never invoke that exemption.
**Fix:** Add `updated_at` to SESSION, or add a Notes line declaring that `last_activity_at` fully captures SESSION mutation and `updated_at` is intentionally omitted.
**Effort:** low

### [ERD-PRD-005] — LOGIN_ATTEMPT has no audit columns
**Location:** `docs/erd.md:50`
**Finding:** LOGIN_ATTEMPT is mutable (`attempt_count` increments, `locked_until` is set when the count reaches the threshold) yet has neither `created_at` nor `updated_at`. The Notes describe Redis/TTL mechanics but never invoke the append-only / audit-column exemption the mandatory ERD-PRD-005 checklist requires.
**Fix:** Add `created_at`/`updated_at`, or add a Notes line stating LOGIN_ATTEMPT is an ephemeral Redis-only counter bounded by `window_start`/`locked_until` that intentionally omits audit columns.
**Effort:** low

## Gate 3 — Warnings (soft spots)

### [ERD-PRD-013] — USER↔LOGIN_ATTEMPT relationship drawn without a connecting FK
**Location:** `docs/erd.md:27`
**Finding:** The diagram draws `USER ||--o{ LOGIN_ATTEMPT` (mandatory USER side) but LOGIN_ATTEMPT has no `user_id` FK — it is keyed on `email_search_hash`. Per the PRD, account lockout is per-email and intentionally tracks attempts even for emails with no USER row (to avoid disclosing whether an email exists), so the drawn USER linkage cannot be satisfied by the entity.
**Fix:** Remove the `USER ||--o{ LOGIN_ATTEMPT` line, or annotate it as a non-FK soft association via `email_search_hash`.
**Effort:** low

## Dismissed rules
| Rule ID | Considered? | Dismissal reason |
|---------|-------------|------------------|
| ERD-PRD-001 | Yes | All PRD nouns have ERD entities. |
| ERD-PRD-002 | Yes | PRD-described relationships have corresponding ERD links. |
| ERD-PRD-003 | Yes | Email PII split into `email_ciphertext` (AES-256-GCM) + `email_search_hash` per Notes. |
| ERD-PRD-004 | Yes | Cardinalities match PRD verbs; reviewer/inviter optional. |
| ERD-PRD-006 | Yes | All workspace-scoped rows carry `workspace_id` directly. |
| ERD-PRD-007 | Yes | Lifecycle fields present (LINK deleted_at/disabled_at, INVITE/ABUSE_REVIEW status, WORKSPACE_MEMBER removed_at). |
| ERD-PRD-008 | Yes | No money/precise-numeric fields in scope. |
| ERD-PRD-009 | Yes | Inline UKs + documented partial uniques. |
| ERD-PRD-010 | Yes | ERD names align with PRD vocabulary. |
| ERD-PRD-011 | Yes | No orphan entities. |
| ERD-PRD-012 | Yes | Enum columns documented with closed value sets in Notes §Enums. |
| ERD-PRD-014 | Yes | No naked M:N; WORKSPACE_MEMBER is an explicit junction. |
| ERD-PRD-015 | Yes | No multi-currency amounts. |
| ERD-PRD-016 | Yes | PKs are uuid; exposed identifier is `short_code`, not a sequential int. |
| ERD-PRD-017 | Yes | LINK carries `created_by_id`; no further attribution required. |
| ERD-PRD-018 | Yes | `session_version` provides versioning; no concurrent-edit resource lacks locking per PRD. |
| ERD-PRD-019 | Yes | Workspace-deletion lifecycle is a documented deferred gap; soft-delete/archival declared. |
| ERD-PRD-020 | Yes | Both compressed runs read Notes §"Click table" (range-partition on clicked_at, 13-month partition-drop) as satisfying the partitioning/archival signal. _(Standard track disagreed and kept this as a finding — see cross-track note.)_ |
| ERD-PRD-021 | Yes | No multi-valued columns; collections normalized. |

## Reconciliation (reflexion)
- **Runs usable:** 2 (both `FAIL_BLOCKER`).
- **Consensus (both runs):** 2 kept — ERD-PRD-005 @50 (LOGIN_ATTEMPT) and ERD-PRD-005 @41 (SESSION); both verified against the ERD (mutable entities, no `updated_at`/audit columns, no Notes exemption).
- **Divergent — kept:** 1 — ERD-PRD-013 @27 (Run A only). Verified: line 27 draws `USER ||--o{ LOGIN_ATTEMPT` and LOGIN_ATTEMPT (lines 50-56) has no `user_id` FK (keyed on `email_search_hash`, Notes line 182). Real recall gap Run B missed.
- **Divergent — dropped:** 0.
- **Gate/severity corrections:** ERD-PRD-005 severity normalized to canonical Gate-2 `blocker` (Run B had labeled it "low"; severity is a property of the rule's gate, not the run).
- **Verdict:** FAIL_BLOCKER — recomputed from 0 Gate-1 / 2 Gate-2 / 1 Gate-3 reconciled findings.

## Summary
The compressed pipeline blocks this ERD on two audit-column gaps on the Redis-backed `SESSION` and `LOGIN_ATTEMPT` entities (mutable but missing `updated_at`/`created_at` with no Notes exemption) plus a relationship line drawn without a connecting FK. All three are one-line fixes (add the column or a justifying Notes sentence; remove or annotate the relationship). The notable result is the cross-track disagreement: the standard pipeline passed-with-risk on a CLICK-partitioning concern the compressed runs dismissed, while the compressed pipeline blocked on audit columns the standard runs dismissed as N/A for Redis entities. The honest reading is to address the union — the audit-column Notes exemptions *and* the CLICK partitioning commitment — before deriving ORM models.

Report saved to c:\Users\faraz\Desktop\Code\url-shortener\.claude\run\2026-06-07-erd-review-compressed.md
