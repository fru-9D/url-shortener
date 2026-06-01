# PRD Review — 2026-05-25

**File reviewed:** `docs/prd.md`
**Verdict:** FAIL_CRITICAL
**Gate 1 (Critical):** 2 findings
**Gate 2 (Blockers):** 12 findings
**Gate 3 (Warnings):** 13 findings

## Lookup

| PRD location | Defect | Rule ID | Gate | Severity |
|--------------|--------|---------|------|----------|
| docs/prd.md:57 | Success criteria is qualitative only — no quantitative target | PRD-001 | 1 | critical |
| docs/prd.md:20 | Core use cases described as feature bullets, not step-by-step flows | PRD-003 | 1 | critical |
| docs/prd.md:22 | Feature "Link creation" lacks acceptance criteria | PRD-005 | 2 | blocker |
| docs/prd.md:29 | Feature "Link list" lacks acceptance criteria | PRD-005 | 2 | blocker |
| docs/prd.md:35 | Feature "Click analytics" lacks acceptance criteria | PRD-005 | 2 | blocker |
| docs/prd.md:41 | Feature "Teams" lacks acceptance criteria | PRD-005 | 2 | blocker |
| docs/prd.md:47 | Feature "Account" lacks acceptance criteria | PRD-005 | 2 | blocker |
| docs/prd.md:25 | "If it isn't taken" — uniqueness scope, reserved words, slug grammar unspecified | PRD-006 | 2 | blocker |
| docs/prd.md:32 | "Filter by date range" — which date, timezone, bound inclusivity unspecified | PRD-006 | 2 | blocker |
| docs/prd.md:20 | Link-creation flow has no failure scenarios | PRD-007 | 2 | blocker |
| docs/prd.md:34 | Redirect / click flow has no failure scenarios | PRD-007 | 2 | blocker |
| docs/prd.md:41 | Teams flow has no failure / edge scenarios | PRD-007 | 2 | blocker |
| docs/prd.md:60 | "Future considerations" exists but no explicit "Out of scope for v1" section | PRD-008 | 2 | blocker |
| docs/prd.md:37 | Mixpanel referenced without integration contract | PRD-009 | 2 | blocker |
| docs/prd.md:68 | Stripe referenced without contract (even though deferred) | PRD-009 | 2 | blocker |
| docs/prd.md:51 | "The system should be fast" — no target latency / throughput | PRD-010 | 3 | warning |
| docs/prd.md:52 | "Short URLs must redirect quickly" — no percentile target | PRD-010 | 3 | warning |
| docs/prd.md:53 | "Data should be secure" — no concrete security requirements | PRD-010 | 3 | warning |
| docs/prd.md:18 | "Links should never go down" — no availability target | PRD-010 | 3 | warning |
| docs/prd.md:25 | Auto-generated short-code collision behavior unstated | PRD-011 | 3 | warning |
| docs/prd.md:22 | URL edge cases unstated (length, schemes, dedup, IDN) | PRD-011 | 3 | warning |
| docs/prd.md:42 | Removed-teammate ownership & last-admin protection unstated | PRD-011 | 3 | warning |
| docs/prd.md:34 | Passive voice: "the click is recorded" — actor unstated | PRD-012 | 3 | warning |
| docs/prd.md:37 | Passive voice: "Analytics data is fed into Mixpanel" — actor unstated | PRD-012 | 3 | warning |
| docs/prd.md:23 | Passive voice: "the system returns" / "is auto-generated" — actor unstated | PRD-012 | 3 | warning |
| docs/prd.md:12 | Vocabulary drift: user / teammate / admin / workspace / team | PRD-013 | 3 | warning |
| docs/prd.md:23 | Vocabulary drift: short URL / short link / short code / slug | PRD-013 | 3 | warning |

## Gate 1 — Critical (must fix before deriving ERD / architecture)

### [PRD-001] — No measurable success metric
**Location:** `docs/prd.md:57`
**Finding:** Success criterion is qualitative only ("marketing teams adopt it and use it regularly"). No quantitative target — activation rate, links-created-per-active-user, week-4 retention, paid-conversion %, redirect p95 latency, monthly active workspaces — is stated, so success cannot be validated and scope drift is unconstrained.
**Fix:** Replace with at least one measurable target per goal — e.g. "X% of signups create ≥3 links in week 1", "p95 redirect latency < 100ms", "Y paid workspaces by month 6".
**Effort:** low

### [PRD-003] — Core use case not stated as a flow
**Location:** `docs/prd.md:20`
**Finding:** The product's core use cases (create link, click-and-redirect, view analytics) are described as bullet-point feature notes, not as end-to-end step-by-step flows naming actor, trigger, system response, and end state. Downstream ERD and architecture cannot be derived from feature lists alone.
**Fix:** Add a "User flows" section with at least three numbered flows: authenticated user creates a short link; anonymous visitor follows a short URL and is redirected; user opens a link's analytics detail page. Each step must name the actor, the action, and the observable system response.
**Effort:** medium

## Gate 2 — Blockers (must fix before downstream work)

### [PRD-005] — "Link creation" lacks acceptance criteria
**Location:** `docs/prd.md:22`
**Finding:** No acceptance criteria. URL validation rules, allowed schemes, max URL length, short-code length/alphabet, uniqueness scope, response payload all undefined.
**Fix:** Add AC, e.g. "Given a logged-in user submits a syntactically valid http(s) URL of ≤2048 chars, when they click Create, then the system returns a 6-char alphanumeric short code unique within snip.io and a copy-to-clipboard control."
**Effort:** low

### [PRD-005] — "Link list" lacks acceptance criteria
**Location:** `docs/prd.md:29`
**Finding:** Pagination, default sort tiebreaker, max list size, empty state, and filter semantics are unspecified.
**Fix:** Add AC covering pagination (page size, max), empty state, sort stability, and exact filter behavior (which date field, inclusive/exclusive bounds).
**Effort:** low

### [PRD-005] — "Click analytics" lacks acceptance criteria
**Location:** `docs/prd.md:35`
**Finding:** What counts as a click (unique vs raw, bot filtering), the time-series granularity, country-detection source, and data freshness window are all unspecified.
**Fix:** Add AC, e.g. "A click is any GET on /{code} returning 30x; bot User-Agents per the IAB list are excluded; counts visible within 60s; country derived from IP via MaxMind GeoLite2; series buckets are UTC days."
**Effort:** low

### [PRD-005] — "Teams" lacks acceptance criteria
**Location:** `docs/prd.md:41`
**Finding:** Roles, permission matrix, invite mechanics (email vs link, expiry, accept flow), seat limits, and ownership transfer are all unspecified.
**Fix:** Add a roles & permissions table and AC for invite/accept/remove flows, including invite expiry and removed-user link disposition.
**Effort:** medium

### [PRD-005] — "Account" lacks acceptance criteria
**Location:** `docs/prd.md:47`
**Finding:** Password policy, email verification requirement, password-reset token lifetime, lockout / rate-limit on failed login, and session/refresh model unspecified.
**Fix:** Add AC for signup (verification required? duplicate-email behavior), password policy, reset token TTL and single-use, and login throttling.
**Effort:** low

### [PRD-006] — Ambiguous: "if it isn't taken"
**Location:** `docs/prd.md:25`
**Finding:** Permits multiple valid implementations — uniqueness scope (global vs per-workspace), reserved words, allowed character set, length, case sensitivity, slug reusability after deletion all unspecified.
**Fix:** State uniqueness scope, define the allowed slug grammar (regex), list reserved prefixes/words, and specify whether deleted slugs are reusable.
**Effort:** low

### [PRD-006] — Ambiguous: "filter by date range"
**Location:** `docs/prd.md:32`
**Finding:** Could mean filter by creation date, by clicks-received date, or both. Timezone basis, bound inclusivity, and UI affordances (presets vs picker) unspecified.
**Fix:** Specify which date field, timezone basis, bound inclusivity, and the allowed range UI.
**Effort:** low

### [PRD-007] — Link-creation flow has no failure scenarios
**Location:** `docs/prd.md:20`
**Finding:** Invalid URL syntax, unsupported scheme, domain-blocklist hit, custom slug collision, rate-limit, and storage-write failure are unaddressed — implementer will invent UX not approved by the product owner.
**Fix:** Add an "Error scenarios" subsection per flow listing each failure mode and the user-visible behavior.
**Effort:** medium

### [PRD-007] — Redirect / click flow has no failure scenarios
**Location:** `docs/prd.md:34`
**Finding:** Unknown short code, deleted/expired link, destination unreachable, redirect loop, abusive traffic, and Mixpanel ingestion failure are unaddressed.
**Fix:** Specify HTTP status and landing page for unknown / deleted codes, link expiry behavior, and whether click recording is best-effort or durable.
**Effort:** medium

### [PRD-007] — Teams flow has no failure scenarios
**Location:** `docs/prd.md:41`
**Finding:** Invite collision with existing user, duplicate pending invites, last-admin removal, link ownership transfer on removal, and invite decline/expiry are unaddressed.
**Fix:** Add explicit rules for each.
**Effort:** medium

### [PRD-008] — No explicit "Out of scope for v1"
**Location:** `docs/prd.md:60`
**Finding:** PRD has "Future considerations" but no explicit out-of-scope section. Adjacent capabilities (SSO, audit logs, link expiry, password-protected links, GDPR self-serve, billing UI) are unaddressed and will surface mid-build as "obvious v1" items.
**Fix:** Add an "Out of scope for v1" section enumerating excluded capabilities.
**Effort:** low

### [PRD-009] — Mixpanel referenced without contract
**Location:** `docs/prd.md:37`
**Finding:** Event schema, identity model, auth, ingestion path (client SDK vs server-side), rate limits, retry/back-pressure semantics, and failure-handling expectations unspecified.
**Fix:** Add a "Mixpanel integration contract" subsection.
**Effort:** medium

### [PRD-009] — Stripe referenced without contract
**Location:** `docs/prd.md:68`
**Finding:** Even though deferred, v1 data-model decisions (user, workspace, plan/seat) will constrain future Stripe integration.
**Fix:** Either remove Stripe entirely from v1 PRD or add a one-paragraph "Future billing constraint" subsection.
**Effort:** low

## Gate 3 — Warnings (lead approval)

(13 warnings — see Lookup table above for full enumeration. Vague NFRs × 4, edge cases × 3, passive voice × 3, vocabulary drift × 2, one "never go down" availability target.)

## Summary

The PRD's most expensive defect is **PRD-001** — no measurable success metric. Without one, downstream design has no rubric to optimize against and the product cannot be evaluated post-launch. Pair-fix it with **PRD-003** by adding a "User flows" section that names actors and observable system responses — that's the minimum needed before deriving an ERD. The 12 Gate 2 blockers are real but will mostly resolve once the user flows section forces the AC and failure scenarios to be specified. Not safe to start the ERD yet.
