# PRD Review — 2026-06-07

**File reviewed:** `docs/prd.md`
**Reconciled from:** 2 independent reviewer runs
**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 5 findings
**Gate 3 (Warnings):** 1 finding

## Lookup
| PRD location     | Finding                                                          | Rule ID  | Gate | Severity |
|------------------|-----------------------------------------------------------------|----------|------|----------|
| docs/prd.md:44   | "after activation" is t0 for 3 time-windowed metrics but the activation moment (activated_at) is never defined | PRD-006  | 2    | blocker  |
| docs/prd.md:198  | "the requester IP" ambiguous for a Cloudflare-fronted service (socket peer vs XFF vs CF-Connecting-IP) | PRD-006  | 2    | blocker  |
| docs/prd.md:371  | referrer_host required in click schema + Mixpanel event but its source on the redirect path is unspecified | PRD-006  | 2    | blocker  |
| docs/prd.md:58   | Flow A step 3 is linear happy-path; failure branches (incl. Safe Browsing fail-open) live only in a separate paragraph | PRD-007a | 2    | blocker  |
| docs/prd.md:67   | Flow B step 3 omits infra-failure branches (503 datastore-unreachable, queue-unavailable local buffer) inline | PRD-007a | 2    | blocker  |
| docs/prd.md:333  | 21–30 day staleness window behavior left implicit (alert at 21, hard-degrade at 30) | PRD-011  | 3    | warning  |

## Gate 1 — Critical (must fix before deriving ERD / architecture)

_None._

## Gate 2 — Blockers (must fix before downstream work)

### [PRD-006] — Activation moment (t0) for time-windowed metrics is undefined
**Location:** `docs/prd.md:44`
**Finding:** 'activation' is the t0 for three time-windowed success metrics (lines 44, 47, 48) but its timestamp is never defined. Activated Workspace = email verified AND ≥1 link created (two events, either order); the PRD never says whether `activated_at` stamps at email-verify, at first-link, or at the later of the two. Each interpretation yields a different cohort and a different measurement window.
**Fix:** Add a sentence to the Activated Workspace glossary entry defining `activated_at` (e.g. the later of {email verified, first link created}).
**Effort:** low

### [PRD-006] — "the requester IP" ambiguous on a CDN-fronted redirect path
**Location:** `docs/prd.md:198`
**Finding:** 'the requester IP' is ambiguous for a Cloudflare-fronted edge service (redirect service runs at the edge, lines 416 / 355–364): socket peer IP vs `X-Forwarded-For` vs `CF-Connecting-IP` produce different — and potentially wrong — country attribution with different trust implications. The PRD does not state which IP is authoritative.
**Fix:** State the authoritative client-IP source for the GeoLite2 lookup (e.g. `CF-Connecting-IP`) in §Click analytics or §MaxMind.
**Effort:** low

### [PRD-006] — referrer_host has no stated provenance
**Location:** `docs/prd.md:371`
**Finding:** `referrer_host` is a required field in both the click-event schema (371) and the Mixpanel `link_clicked` event (287), but its provenance is never specified. Unlike `country_code` (sourced from GeoLite2) and `user_agent` (captured raw), `referrer_host` has no stated source — parse the `Referer` header, read a query param, or record null are all valid implementations, yielding divergent data.
**Fix:** Add a sentence to Flow B step 3 or the Click analytics AC stating the source of `referrer_host` (e.g. the `Referer` request header) and its null-handling.
**Effort:** low

### [PRD-007a] — Flow A step 3 is happy-path; failures not woven in
**Location:** `docs/prd.md:58`
**Finding:** Flow A's System-response step (58) collapses five outcomes into one happy-path sentence. A sequence diagram derived from the steps would miss the validation/rate-limit/storage/401 branches and, critically, the Safe Browsing fail-open branch (link created AND enqueued to Abuse review). Flows B–E reference step transitions; Flow A step 3 does not.
**Fix:** Add a conditional branch at Flow A step 3 referencing the failure cases, including the Safe Browsing fail-open path (link created and added to the Abuse review queue).
**Effort:** low

### [PRD-007a] — Flow B step 3 omits infra-failure branches inline
**Location:** `docs/prd.md:67`
**Finding:** Flow B step 3 weaves in the application-level outcomes but omits the infrastructure-failure branches inline: datastore-unreachable returns 503 (not a branded 404) and queue-unavailable falls back to local durable buffering while the 302 still completes. These appear only in the Failure paths paragraph (70), so a sequence diagram built from the steps would miss them.
**Fix:** Reference the datastore-unreachable (503) and queue-unavailable (local buffer, 302 still completes) branches inline at Flow B step 3.
**Effort:** low

## Gate 3 — Warnings (lead approval)

### [PRD-011] — 21–30 day GeoLite2 staleness window behavior implicit
**Location:** `docs/prd.md:333`
**Finding:** Two staleness thresholds are stated (hard-degrade to "Unknown" at >30 days; ops alert at 21 days) but the behavior in the 21–30 day window is left implicit. A DB at 25 days is past the alert yet under the hard-degrade, so it keeps attributing country from stale data with no stated change beyond the alert — the boundary behavior is unspecified.
**Fix:** State explicitly that during the 21–30 day window normal attribution continues (alert only), and that "Unknown" applies strictly past 30 days.
**Effort:** low

## Dismissed rules
| Rule ID | Considered? | Dismissal reason |
|---------|-------------|------------------|
| PRD-001 | Yes | Quantitative success metrics present in Goals table (e.g. p95 redirect <100ms, ≥99.95% availability, <5s paste-to-copy, ≥60% activation). |
| PRD-002 | Yes | Primary persona (marketing manager at 5–50-employee small business) and secondary users (teammates) explicitly defined in §Target users. |
| PRD-003 | Yes | Core use cases stated as step-by-step flows A–E (trigger/action/system-response/end-state). |
| PRD-004 | Yes | No unresolved contradictions; retention (13-month click, 30-day soft-delete) and reuse windows are internally reconciled. |
| PRD-005 | Yes | Every feature section, plus the Abuse review queue safety-net, carries explicit acceptance criteria. |
| PRD-007 | Yes | Each flow has failure paths and feature sections include Error-scenario tables (distinct from the PRD-007a weaving defect). |
| PRD-008 | Yes | Explicit "Out of scope for v1" section with 14 enumerated exclusions present. |
| PRD-009 | Yes | Every named integration (Mixpanel, Pwned Passwords, SES, GeoLite2, Safe Browsing, KMS, Cloudflare, click pipeline) has a contract: transport, auth, timeout/retry, fail-open/closed, PII treatment. |
| PRD-010 | Yes | NFRs carry quantified targets (latency, availability, GeoLite2 21/30-day thresholds, update cadence); the 21–30d behavior gap is captured under PRD-011 @333, not a missing-target defect. |
| PRD-012 | Yes | Country-derivation actor IS named one section over (§MaxMind line 329: "Used by the redirect service to populate country_code"); passive voice at line 198 is resolvable, not actor-obscuring. |
| PRD-013 | Yes | Consistent vocabulary backed by a Glossary (Workspace/Member/Short code/Slug/Click/Activated Workspace etc.); no unreconciled synonym drift. |

## Reconciliation (reflexion)
- **Runs usable:** 2 (both parseable; both independently returned FAIL_BLOCKER, verdict recomputed not copied).
- **Consensus (both runs):** 1 finding kept.
  - [PRD-007a] @58 — both flagged Flow A step 3 as happy-path-only; verified at line 58 (failures, incl. Safe Browsing fail-open, live in the separate paragraph at 61). Kept the richer message/fix.
- **Divergent — kept:** 4.
  - [PRD-006] @44 (Run B only) — glossary defines the Activated Workspace *state* but never the activation *moment*; metrics at 44/47/48 use "after activation" as t0. Genuine ambiguity.
  - [PRD-006] @198 (Run A only) — "the requester IP" genuinely under-determined for an edge/Cloudflare-fronted redirect service. Real divergent-attribution ambiguity.
  - [PRD-006] @371 (Run A only) — referrer_host required at 371 and 287 but has no stated source anywhere, unlike country_code and user_agent. Distinct locus.
  - [PRD-007a] @67 (Run A only) — Flow B step 3 omits the 503 / local-buffer infra branches that exist only in the separate paragraph at 70. Distinct locus from @58.
- **Divergent — dropped:** 2.
  - [PRD-012] @198 (Run B only) — actor IS named one section over (§MaxMind line 329). Passive voice resolvable; PRD-012's "implementer must guess the actor" bar not met. The real defect here is the IP-source ambiguity, kept as PRD-006 @198.
  - [PRD-010] @333 (Run B only) — section states quantified targets (21-day alert, 30-day hard-degrade, twice-weekly cadence at 332), so not a "missing NFR target". Re-describes the same gap as PRD-011 @333 under a different rule ID — dropped as a duplicate.
- **Rule-ID dispute resolutions (same locus, different rule):** @198 → PRD-006 over PRD-012; @333 → PRD-011 over PRD-010.
- **Gate/severity corrections:** none — every kept finding already carried its canonical gate/severity.
- **Verdict:** FAIL_BLOCKER — recomputed from 0 Gate-1 / 5 Gate-2 / 1 Gate-3 reconciled findings.

## Summary
This is a mature PRD that clears every Gate-1 critical rule — it has quantified success metrics, defined personas, step-by-step flows, contracted integrations, and an explicit out-of-scope section. The verdict is `FAIL_BLOCKER` solely on Gate-2 findings, all of them low author-effort. Fix first the three PRD-006 ambiguities (activation `t0`, authoritative client IP, and `referrer_host` provenance) — each is a single sentence but each silently forks the data model an ERD/analytics design would inherit. The two PRD-007a findings are about weaving existing failure handling into the numbered flow steps so downstream sequence diagrams capture it. With those six lines addressed, this PRD is safe to derive an ERD from.

Report saved to c:\Users\faraz\Desktop\Code\url-shortener\.claude\run\2026-06-07-prd-review.md
