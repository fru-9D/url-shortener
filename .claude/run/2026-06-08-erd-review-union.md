# ERD Review — Cross-Track Worklist — 2026-06-08

**Stage:** `erd`
**Artifact(s):** `docs/erd.md` (+ `docs/prd.md` context)
**Tracks unioned:** standard (`2026-06-07-erd-review.md`) + compressed (`2026-06-07-erd-review-compressed.md`)
**Authoritative verdict:** PASS  *(from cross-confirmed findings only — Tier A is empty; zero defects were independently confirmed by both tracks — carries no confirmation weight here)*
**Advisory ceiling:** FAIL_BLOCKER  *(if all single-track + disputed findings hold at their more-severe reading)*
**Recall recovered:** 1 verified finding (ERD-PRD-013) caught by only one track — a standard-only review would have shipped without it
**Tier counts:** A confirmed 0 · B single-track 1 · C disputed 3 · D rejected 0

> **Honest read:** this is the contested case the cross-track step exists to surface. The two tracks shipped **opposite verdicts** (PASS_WITH_RISK vs FAIL_BLOCKER) and **each dismissed exactly what the other flagged.** Nothing is cross-confirmed, so there is no defensible automated gate — a human must adjudicate the three disputes before deriving ORM models. The PASS floor and FAIL_BLOCKER ceiling bracket the real uncertainty.

## Worklist

### Tier A — Confirmed (both tracks, verified) — gate-worthy
_None._ No `(rule, locus)` was independently flagged by both tracks; the tracks caught disjoint defect sets.

### Tier B — Single-track (one track, verified) — advisory, needs human

#### [ERD-PRD-013] — USER↔LOGIN_ATTEMPT relationship drawn without a connecting FK
**Location:** `docs/erd.md:27` · **Found by:** compressed only (standard's ERD-PRD-013 dismissal reasoned about LINK/INVITE/ABUSE_REVIEW FKs and never addressed line 27 — a generic miss, not a contrary judgment → recall gap, not a dispute).
**Verified:** line 27 `USER ||--o{ LOGIN_ATTEMPT` (mandatory USER side); LOGIN_ATTEMPT (lines 50–56) has no `user_id` FK — keyed on `email_search_hash`; PRD §Account confirms lockout is per-email and tracks emails with no USER row, so the mandatory linkage cannot be satisfied.
**Fix:** remove the `USER ||--o{ LOGIN_ATTEMPT` line, or annotate it as a non-FK soft association via `email_search_hash`. **Gate 3 / warning · effort low.**

### Tier C — Disputed (tracks disagree) — human must adjudicate
_(applicability disputes — one track flagged, the other's dismissal specifically addressed the same locus with a contrary judgment; more-severe reading first)_

#### [ERD-PRD-005] — SESSION omits `updated_at` despite recurring mutation
**Location:** `docs/erd.md:41`
- **Flagged (compressed, Gate 2):** SESSION mutates `last_activity_at` on every request but has only `created_at`; Notes describe the refresh but never invoke the audit-column exemption.
- **Dismissed (standard):** SESSION is a Redis-backed logical entity (Notes line 179: "not Postgres tables, no ORM model or migration generated") → audit-column rule N/A.
- **Artifact:** both premises are true — the entity lacks `updated_at` AND is Redis-backed. **The dispute is purely interpretive: does ERD-PRD-005 apply to Redis-backed logical entities?**

#### [ERD-PRD-005] — LOGIN_ATTEMPT has no audit columns
**Location:** `docs/erd.md:50`
- **Flagged (compressed, Gate 2):** mutable (`attempt_count`/`locked_until`) yet has neither `created_at` nor `updated_at`; no Notes exemption.
- **Dismissed (standard):** same Redis-backed-logical-entity basis as the SESSION dispute.
- **Decide jointly with the SESSION dispute** — one ruling on "audit-column rule vs Redis logical entities" resolves both.

#### [ERD-PRD-020] — CLICK partitioning hedged as "consider", not committed
**Location:** `docs/erd.md:220` (§Click table)
- **Flagged (standard, Gate 3):** verbatim "At high traffic volumes, **consider** range-partitioning…" is a hedge, yet the 13-month rolling-delete "drops whole partitions" depends on partitioning existing.
- **Dismissed (compressed):** the §Click table Notes already describe the partition-drop plan and satisfy the signal.
- **Artifact:** the word *is* "consider", but the same paragraph describes the mechanics. **Dispute: does descriptive intent count as a committed strategy?**

### Tier D — Rejected (failed artifact verification) — likely false positive
_None._ All four unioned findings verified against the ERD.

## Lookup
| Location | Finding | Rule ID | Gate | Severity | Tier | Tracks |
|----------|---------|---------|------|----------|------|--------|
| docs/erd.md:27 | USER ‖--o{ LOGIN_ATTEMPT drawn (mandatory) but LOGIN_ATTEMPT has no user_id FK (keyed on email_search_hash) | ERD-PRD-013 | 3 | warning | B | compressed |
| docs/erd.md:41 | SESSION mutates last_activity_at every request but has no updated_at | ERD-PRD-005 | 2 | blocker | C | compressed |
| docs/erd.md:50 | LOGIN_ATTEMPT mutable yet has neither created_at nor updated_at | ERD-PRD-005 | 2 | blocker | C | compressed |
| docs/erd.md:220 | CLICK partitioning documented as "consider" rather than committed; retention-by-partition depends on it | ERD-PRD-020 | 3 | warning | C | standard |

## Cross-track reconciliation (reflexion)
- **Tracks unioned:** standard + compressed (both 2026-06-07, no date skew; ERD on disk current).
- **Cross-confirmed (Tier A):** 0 — the tracks caught disjoint defect sets and each dismissed precisely what the other flagged.
- **Single-track recall recovered (Tier B):** 1 — ERD-PRD-013 @ erd.md:27, compressed-only. Standard's dismissal was generic (never addressed line 27) → Tier B, not Tier C. A standard-only review would have shipped without this finding.
- **Disputes for a human (Tier C):** 3 — ERD-PRD-005 ×2 (Redis audit-column applicability) + ERD-PRD-020 (CLICK "consider" vs committed). Each grounded in the artifact on both sides; neither track can settle them.
- **Rejected (Tier D):** 0 — all four findings verified (cited snippets exist; both absence claims genuinely absent).
- **Authoritative verdict:** PASS from 0/0/0 Tier-A. **Advisory ceiling:** FAIL_BLOCKER (higher readings: ERD-PRD-005 ×2 → Gate 2; ERD-PRD-020 → Gate 3; ERD-PRD-013 → Gate 3; worst = Gate 2). **Ceiling ≥ floor invariant holds** (FAIL_BLOCKER ≥ PASS).
- **Order independence:** confirmed — tiering, counts (A0/B1/C3/D0), and both verdicts are invariant under swapping the inputs; only the descriptive `tracks` label names the originating track.

## How to read this report
- **Tier A** is the gate decision (empty here → no automated gate is defensible).
- **Tier B** is real but caught by only one track — worklist for a human, not an auto-block.
- **Tier C** needs a human to adjudicate — the two tracks disagree on applicability/severity.
- **Tier D** failed artifact verification (excluded).
- A single-track report on its own is advisory; this cross-track worklist is the authoritative output. **The one ruling that resolves two of the three blockers: does ERD-PRD-005 (audit columns) bind Redis-backed logical entities?**

Report saved to c:\Users\faraz\Desktop\Code\url-shortener\.claude\run\2026-06-08-erd-review-union.md
