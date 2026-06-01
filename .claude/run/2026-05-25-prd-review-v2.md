# PRD Review — 2026-05-25 (v2)

**File reviewed:** `docs/prd.md` (v2, after iterating against v1 findings)
**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 5 findings
**Gate 3 (Warnings):** 5 findings

## Change vs v1

| Counter | v1 | v2 | Delta |
|---|---|---|---|
| Gate 1 | 2 | 0 | -2 |
| Gate 2 | 12 | 5 | -7 |
| Gate 3 | 13 | 5 | -8 |
| **Total** | **27** | **10** | **-17** |
| Verdict | FAIL_CRITICAL | FAIL_BLOCKER | one step better |

## Lookup

| PRD location | Defect | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/prd.md:94 | "Destination on blocklist" referenced without defining the blocklist | PRD-006 | 2 | blocker |
| docs/prd.md:41 | "Activated Workspaces" used as the denominator in 3 success metrics, never defined | PRD-006 | 2 | blocker |
| docs/prd.md:160 | Pwned Passwords API has no contract (fail-open vs fail-closed, timeout, caching) | PRD-009 | 2 | blocker |
| docs/prd.md (no §) | Email delivery (reset/verify/invite) has no provider / transport / SLA / failure semantics | PRD-009 | 2 | blocker |
| docs/prd.md:123 | MaxMind GeoLite2 has no contract (local DB vs hosted, update cadence, fallback) | PRD-009 | 2 | blocker |
| docs/prd.md:200 | NFR section has no scale/capacity targets (peak clicks/sec, links/workspace, total workspaces) | PRD-010 | 3 | warning |
| docs/prd.md:204 | "Email addresses encrypted at rest" — algorithm / key management / scope unspecified | PRD-010 | 3 | warning |
| docs/prd.md (no §) | Workspace deletion entirely unaddressed (not in features, not in out-of-scope) | PRD-011 | 3 | warning |
| docs/prd.md:141 | "Removed Members lose access immediately" — session revocation mechanism unspecified | PRD-011 | 3 | warning |
| docs/prd.md:204 | "Email addresses encrypted at rest" — passive voice, actor of encryption unstated | PRD-012 | 3 | warning |

## Gate 2 — Blockers

### [PRD-006] — "Blocklist" referenced without definition
**Location:** `docs/prd.md:94`
**Finding:** Link Creation error scenarios reference a "Destination on blocklist" failure mode but the blocklist is never defined — static internal list? Google Safe Browsing? Microsoft SmartScreen? Manually-curated abuse list? Hybrid? Each has different latency, cost, and ops implications.
**Fix:** Add an AC under Link Creation naming the blocklist source(s), lookup transport, latency budget, and the override/appeal path the error message ("Contact support") implies must exist.
**Effort:** low

### [PRD-006] — "Activated Workspaces" used as metric denominator, never defined
**Location:** `docs/prd.md:41`
**Finding:** Three success metrics use "activated Workspaces" as the denominator (lines 41, 44, 45). "Activated" is never defined — Workspace was created? Email verified? ≥1 link created? ≥1 click received? The metric is not measurable until "activated" is fixed.
**Fix:** Add "Activated Workspace" to the Glossary with a single concrete predicate.
**Effort:** low

### [PRD-009] — Pwned Passwords API contract missing
**Location:** `docs/prd.md:160`
**Finding:** Pwned Passwords API is a hard gate on every password create / change but no timeout, fail-open vs fail-closed policy, retry policy, or caching is specified. Architecture cannot plan the sign-up critical path without resolution.
**Fix:** Add a Pwned Passwords subsection under External Integrations specifying transport, timeout, retry policy, fail-open vs fail-closed decision.
**Effort:** low

### [PRD-009] — Email delivery contract missing
**Location:** `docs/prd.md` (PRD-wide absence)
**Finding:** Email delivery is a hard dependency of Account (verification + reset) and Teams (invites), but no provider, sender domain, bounce/complaint handling, SLA, or failure semantics are specified anywhere.
**Fix:** Add an "Email delivery" subsection under External Integrations matching the format of the Mixpanel section.
**Effort:** medium

### [PRD-009] — MaxMind GeoLite2 contract missing
**Location:** `docs/prd.md:123`
**Finding:** GeoLite2 is named for country lookup but lookup transport (local mmdb vs hosted GeoIP2 API), update cadence, and behavior when DB is stale or missing are unspecified. Drives different edge deployment requirements.
**Fix:** Add a sub-bullet (or External Integrations subsection) stating transport, update cadence, distribution to edge POPs, and unavailable-DB fallback.
**Effort:** low

## Gate 3 — Warnings

(Five — see lookup table. Highlights: scale/capacity NFRs absent; Workspace deletion entirely unaddressed.)

## Summary

The v2 PRD closed all Gate 1 issues (measurable metrics, named flows, persona). What remains is sharper: two real ambiguities ("blocklist", "activated Workspaces") and three external-system contracts the v1 review didn't surface because v1 didn't have detailed-enough acceptance criteria to mention them yet. The Gate 3 findings now point at genuinely-secondary concerns. One short v3 pass focused on the 5 Gate-2 items would move the verdict to PASS_WITH_RISK.
