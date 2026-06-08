# PRD Review (compressed) — 2026-06-07

**File reviewed:** `docs/prd.md`
**Reconciled from:** 2 independent compressed reviewer runs
**Verdict:** PASS_WITH_RISK
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 3 findings

> **Cross-track note:** The standard PRD pipeline returned `FAIL_BLOCKER` (5 Gate-2 findings); this compressed pipeline returned `PASS_WITH_RISK`. The difference is severity judgment, not missed issues — both tracks flagged `referrer_host` provenance and the client-IP-source ambiguity, but the standard reviewers classified them as Gate-2 PRD-006 (ambiguous behavior that forks the data model) while the compressed reviewers classified them as Gate-3 PRD-011/PRD-012 (boundary/under-specified). See the standard report `2026-06-07-prd-review.md` for the stricter read.

## Lookup
| Location | Finding | Rule ID | Gate | Severity |
|----------|---------|---------|------|----------|
| docs/prd.md:113 | Slug uniqueness is case-sensitive (`Foo`/`foo` coexist) while reserved-word blocking is case-insensitive; interaction boundary + near-duplicate confusability for a non-technical audience unspecified | PRD-011 | 3 | warning |
| docs/prd.md:198 | "Country is derived from the requester IP" never names which IP; redirect runs at the edge behind Cloudflare, so the socket peer is an edge/proxy IP — source fed to MaxMind unstated, affects the whole country breakdown | PRD-012 | 3 | warning |
| docs/prd.md:371 | `referrer_host` required on both the click-pipeline event schema (371) and the `link_clicked` Mixpanel event (287), but no AC/flow defines derivation or the empty/boundary case (direct navigation, no Referer) | PRD-011 | 3 | warning |

## Gate 1 — Critical (must fix before deriving ERD / architecture)

_None._

## Gate 2 — Blockers (must fix before downstream work)

_None._

## Gate 3 — Warnings (lead approval)

### [PRD-011] — Slug case-sensitivity vs reserved-word case-insensitivity boundary
**Location:** `docs/prd.md:113`
**Finding:** Slug uniqueness is case-sensitive (`Foo`/`foo` coexist) while reserved-word blocking is case-insensitive (`Admin`/`admin` both blocked). The interaction boundary is under-specified and creates a confusability hazard for a non-technical audience; neither the create flow nor the link list (line 141) addresses near-duplicate case-variant short codes, and implementers may conflate the two case rules.
**Fix:** State that case-insensitivity applies ONLY to the reserved-word exact-match check and nowhere else in slug handling; either document the case-variant confusability as accepted or add a create-time warn-on-case-variant AC plus list-rendering treatment.
**Effort:** low

### [PRD-012] — Unnamed IP source feeding MaxMind on the edge path
**Location:** `docs/prd.md:198`
**Finding:** "Derived from the requester IP" never names which IP. The redirect service is deployed at the edge behind Cloudflare (lines 357, 416), so the socket peer is an edge/proxy IP, not the visitor's. Whether geo reads the true client IP (e.g. `CF-Connecting-IP` / first XFF hop) is unstated and affects the entire country breakdown.
**Fix:** Specify the exact IP source fed to MaxMind on the edge path (`CF-Connecting-IP` / first XFF hop) and the fallback when it is absent or spoofed.
**Effort:** low

### [PRD-011] — referrer_host derivation undefined
**Location:** `docs/prd.md:371`
**Finding:** `referrer_host` is required on the click-pipeline event schema (371) and the `link_clicked` Mixpanel event (287), but no AC/flow defines its derivation or the empty/boundary case. The redirect AC (196) omits referrer derivation entirely; direct-navigation clicks (no `Referer` header) are the common unhandled boundary.
**Fix:** Add an AC defining `referrer_host` derivation (host of the `Referer` header, lowercased, host only) and its value when the header is absent or unparsable (null or "direct"), consistent across the click pipeline and Mixpanel; note whether it is surfaced to Members.
**Effort:** low

## Dismissed rules
| Rule ID | Considered? | Dismissal reason |
|---------|-------------|------------------|
| PRD-001 | Yes | No defect found in either run (six quantitative metrics with targets). |
| PRD-002 | Yes | No defect (primary + secondary personas defined). |
| PRD-003 | Yes | No defect (five step-by-step flows A–E). |
| PRD-004 | Yes | No defect (no contradictions; SLO/freshness numerically consistent). |
| PRD-005 | Yes | No defect (every feature + safety-net has AC). |
| PRD-006 | Yes | No Gate-2 ambiguity flagged by either compressed run. _(Standard track rated referrer_host/IP-source as PRD-006 Gate 2.)_ |
| PRD-007 | Yes | No defect (every flow has failure paths). |
| PRD-007a | Yes | No defect (failure branches woven into flow narration). |
| PRD-008 | Yes | No defect (explicit 14-item out-of-scope section). |
| PRD-009 | Yes | No defect (all eight external systems fully contracted). |
| PRD-010 | Yes | No defect (NFRs carry target values). |
| PRD-013 | Yes | No defect (Glossary reconciles vocabulary). |

## Reconciliation (reflexion)
- **Runs usable:** 2 (both `PASS_WITH_RISK`, 3 Gate-3 findings each).
- **Consensus (both runs):** 2 kept — PRD-011 @113 (merged Run A's confusability framing with Run B's reserved-word-boundary framing) and PRD-011 @371 (referrer_host derivation gap).
- **Divergent — kept:** 1 — PRD-012 @198 (Run A only). Verified: line 198 text confirmed; §MaxMind + edge-deployment (357/416) confirm the redirect runs behind Cloudflare, so the IP source is genuinely ambiguous and material. Real recall gap Run B missed.
- **Divergent — dropped:** 1 — PRD-011 @233 member-removal concurrency (Run B only). Line 233 already states owner_id reassignment is performed "atomically" and line 234 enforces the last-Admin invariant at the API layer across all surfaces; the proposed fix invents design-layer detail rather than a concrete PRD gap. Ambiguous after checking → precision bias → drop.
- **Gate/severity corrections:** none — all findings are PRD-011/PRD-012, canonical Gate 3.
- **Verdict:** PASS_WITH_RISK — recomputed from 0/0/3 reconciled findings.

## Summary
The compressed pipeline rates this PRD as usable-with-warnings: no Gate-1 or (by the compressed reviewers' judgment) Gate-2 defects, three Gate-3 boundary/derivation gaps clustered around the redirect/analytics path (slug case-variant confusability, the unnamed client-IP source feeding MaxMind, and `referrer_host` derivation). The one substantive disagreement with the standard track is severity: the standard reviewers treat the IP-source and `referrer_host` ambiguities as Gate-2 blockers because they silently fork the data model an ERD inherits, whereas the compressed reviewers treat them as Gate-3 warnings. Either way, resolving these three before the click-analytics/redirect components are built is advisable.

Report saved to c:\Users\faraz\Desktop\Code\url-shortener\.claude\run\2026-06-07-prd-review-compressed.md
