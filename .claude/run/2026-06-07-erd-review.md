# ERD Review — 2026-06-07

**PRD:** `docs/prd.md`
**ERD:** `docs/erd.md`
**Reconciled from:** 2 independent reviewer runs
**Verdict:** PASS_WITH_RISK
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 1 finding

## Lookup
| Location | Finding | Rule ID | Gate | Severity |
|----------|---------|---------|------|----------|
| docs/erd.md:220 (§Click table) | CLICK partitioning is documented as "consider" rather than a committed strategy, yet the 13-month rolling-delete-by-partition design depends on it | ERD-PRD-020 | 3 | warning |

## Gate 1 — Critical (ERD not safe to derive ORM models from)

_None._

## Gate 2 — Blockers (material gaps)

_None._

## Gate 3 — Warnings (soft spots)

### [ERD-PRD-020] — CLICK partitioning hedged as "consider", not committed
**Location:** `docs/erd.md:220` (§Click table)
**Finding:** CLICK is an unbounded, high-throughput, append-only event stream (one row per redirect, sized for redirect p95 ×2 per PRD §Click pipeline). The ERD Notes document partitioning as something to *"consider"* at high traffic volumes rather than a declared/committed strategy, yet the 13-month rolling-delete design ("drops whole partitions rather than single rows") depends on partitioning actually being in place. Without a committed decision, the first scale event yields a CLICK table too large to vacuum/reindex/roll-delete within a maintenance window, and the partition-drop retention job has no partitions to drop.
**Fix:** Commit to a partitioning/archival strategy for CLICK in the ERD Notes: declare range partitioning on `clicked_at` (monthly partitions) and partition-drop for the 13-month rolling-delete job, rather than listing it as optional ("consider").
**Effort:** low

## Dismissed rules
| Rule ID | Considered? | Dismissal reason |
|---------|-------------|------------------|
| ERD-PRD-001 | Yes | Every first-class PRD noun maps to an ERD entity (USER, WORKSPACE, WORKSPACE_MEMBER, INVITE, LINK, CLICK, ABUSE_REVIEW, token tables, EMAIL_SUPPRESSION, MIXPANEL_DEAD_LETTER, SESSION, LOGIN_ATTEMPT). Billing/paid is out of v1 scope and correctly absent. |
| ERD-PRD-002 | Yes | Every PRD relationship has a matching ERD link (User↔Workspace, Workspace↔Member, Workspace/User↔Link, Link↔Click, Workspace↔Invite, User↔tokens, Link↔AbuseReview, User↔Session/LoginAttempt). |
| ERD-PRD-003 | Yes | PII (email) structurally bounded: split into `email_ciphertext` (AES-256-GCM/KMS) + `email_search_hash` across USER/INVITE/EMAIL_SUPPRESSION; passwords Argon2id; tokens hashed; raw IP never persisted. |
| ERD-PRD-004 | Yes | Cardinalities match PRD verbs; one-Workspace-per-Member is a documented partial-unique, optional reviewer/inviter FKs match nullable semantics. |
| ERD-PRD-005 | Yes | Audit-column checklist walked; all Postgres entities carry created_at+updated_at; CLICK omits updated_at (documented append-only); SESSION/LOGIN_ATTEMPT are Redis-backed logical entities. |
| ERD-PRD-006 | Yes | All workspace-scoped entities carry `workspace_id` directly (LINK, INVITE, WORKSPACE_MEMBER, CLICK, ABUSE_REVIEW); MIXPANEL_DEAD_LETTER.workspace_id nullable for account-level events. |
| ERD-PRD-007 | Yes | Lifecycle fields present (LINK deleted_at/disabled_at, WORKSPACE_MEMBER removed_at, INVITE/ABUSE_REVIEW status + timestamps, tokens consumed_at). |
| ERD-PRD-008 | Yes | No money/precise-numeric columns in scope; billing explicitly out of scope for v1. |
| ERD-PRD-009 | Yes | Uniqueness expressed: global UKs inline (email_search_hash, token_hash, CLICK.event_id); partial uniques (slug-while-not-deleted, one-workspace-per-member, pending-invite) documented in §Uniqueness constraints. |
| ERD-PRD-010 | Yes | ERD vocabulary tracks PRD vocabulary (Member→WORKSPACE_MEMBER, Short code/Slug→LINK.short_code, Abuse review queue→ABUSE_REVIEW); no divergent renaming. |
| ERD-PRD-011 | Yes | No orphan entities; EMAIL_SUPPRESSION/MIXPANEL_DEAD_LETTER/LOGIN_ATTEMPT/SESSION all trace to PRD §Email/§Mixpanel/§Account. |
| ERD-PRD-012 | Yes | Enumerable status columns documented with closed value sets inline and in §Enums (roles, invite/abuse status, suppression reason, country_code). |
| ERD-PRD-013 | Yes | Required-side FKs non-nullable (LINK.owner_id/created_by_id); intentionally-optional FKs (INVITE.inviter_id, ABUSE_REVIEW.reviewer_id) documented and match cardinality. |
| ERD-PRD-014 | Yes | No raw M:N lines; User↔Workspace resolved through the explicit WORKSPACE_MEMBER junction with role/timestamps. |
| ERD-PRD-015 | Yes | Not applicable — no multi-currency context; billing out of scope. |
| ERD-PRD-016 | Yes | Externally-exposed identifier (`short_code`) is a random nanoid string, not a sequential integer; all PKs are uuid. No enumeration risk. |
| ERD-PRD-017 | Yes | User-attribution FKs present where the PRD surfaces them (LINK.created_by_id, ABUSE_REVIEW.reviewer_id, INVITE.inviter_id); admin-visible audit logs are out of scope. |
| ERD-PRD-018 | Yes | PRD never describes concurrent/collaborative editing of the same record ("Any Member may edit" is shared-mutable but uses no concurrency trigger language); optimistic-lock column not required. |
| ERD-PRD-019 | Yes | Hierarchical-deletion declared: LINK soft-delete→hard-delete cascade and CLICK 13-month retention documented; Workspace deletion is an acknowledged deferred gap, not undeclared. |
| ERD-PRD-021 | Yes | No 1NF violations; collections normalized into relations (CLICK, WORKSPACE_MEMBER, ABUSE_REVIEW); MIXPANEL_DEAD_LETTER.payload is an intentionally-opaque replay blob. |

## Reconciliation (reflexion)
- **Runs usable:** 2 (Run A = 0 findings / PASS; Run B = 1 Gate-3 finding / PASS_WITH_RISK).
- **Consensus (both runs):** 0 findings.
- **Divergent — kept:** 1.
  - [ERD-PRD-020] @ docs/erd.md:220 — kept. The artifact's verbatim wording is "At high traffic volumes, **consider** range-partitioning CLICK on `clicked_at`." "Consider" is hedged/optional language, not a declaration. Run A's dismissal ("explicitly declares a partitioning + archival plan") misreads "consider" as "declare." The rule genuinely applies (CLICK unbounded/append-only; retention is partition-drop-dependent) and the snippet exists verbatim, so the evidence is unambiguous and precision bias does not favor dropping.
- **Divergent — dropped:** 0.
- **Gate/severity corrections:** none — ERD-PRD-020 is canonically Gate 3 / warning; both runs already treated it so.
- **Dismissal reconciliation:** union of both dismissal tables = all 21 rules; ERD-PRD-020 removed (now a finding); remaining 20 retained with the more specific reason where the runs elaborated. Every rule appears exactly once (1 finding + 20 dismissals).
- **Verdict:** PASS_WITH_RISK — recomputed from 0 Gate-1 / 0 Gate-2 / 1 Gate-3 reconciled findings.

## Summary
The ERD is unusually well-aligned with the PRD: every entity, relationship, and constraint the PRD requires is present, and the Notes section pre-empts the structural concerns Mermaid can't express inline (partial uniques, PII encryption split, per-tenant `workspace_id` scoping, append-only CLICK). The single soft spot is the high-volume CLICK table hedging on partitioning ("consider") even though its own 13-month roll-delete design assumes partitioning exists — committing that decision now means the ORM/migration derives a partitioned table from day one. No Gate-1 or Gate-2 defects: the ERD is safe to derive ORM models from.

Report saved to c:\Users\faraz\Desktop\Code\url-shortener\.claude\run\2026-06-07-erd-review.md
