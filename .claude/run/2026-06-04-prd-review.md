# PRD Review — 2026-06-04

**File reviewed:** `docs/prd.md`
**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 7 findings
**Gate 3 (Warnings):** 2 findings

## Lookup

| PRD location             | Finding                                                                                               | Rule ID  | Gate | Severity |
|--------------------------|-------------------------------------------------------------------------------------------------------|---------|------|----------|
| docs/prd.md:43           | "Median paste-to-copy time per link" — measurement method (client-side vs server-side) is undefined   | PRD-006 | 2    | blocker  |
| docs/prd.md:214          | Editors can "delete links" stated in Teams AC but no Link deletion feature, flow, or AC exists anywhere in PRD | PRD-006 | 2    | blocker  |
| docs/prd.md:220          | Invite acceptance sub-flow (3-branch happy path) has no failure branch for the Workspace-add step failing after invitee sign-up completes | PRD-007 | 2    | blocker  |
| docs/prd.md:262          | Mixpanel integration section has no per-request timeout stated                                        | PRD-009 | 2    | blocker  |
| docs/prd.md:296          | AWS SES integration section has no per-request timeout for the SES send API call                      | PRD-009 | 2    | blocker  |
| docs/prd.md:206          | Cloudflare cache purge referenced as a hard dependency but has no contract section (no transport, auth, failure semantics, timeout, or PII treatment) | PRD-009 | 2    | blocker  |
| docs/prd.md:328          | AWS KMS is described as a hard dependency for write/read operations but has no timeout or retry policy stated | PRD-009 | 2    | blocker  |
| docs/prd.md:99           | Workspace name (Flow E) has no length, format, or uniqueness constraints defined anywhere in the PRD   | PRD-011 | 3    | warning  |
| docs/prd.md:206          | "handled by the ops action" — actor who calls the Cloudflare purge API is undefined (ops UI? backend worker? manual step?) | PRD-012 | 3    | warning  |

## Dismissed rules

| Rule ID       | Considered? | Dismissal reason |
|---------------|-------------|-----------------|
| PRD-001       | Yes         | Goals table (line 41) contains six quantitative success metrics with numeric targets and a time horizon. |
| PRD-002       | Yes         | Target users section (line 29) defines a primary persona (marketing manager, 5–50 employee business, non-technical) and secondary users. |
| PRD-003       | Yes         | Flows A–E provide step-by-step numbered flows covering all core use cases (creation, redirect, analytics, sign-up, workspace creation). |
| PRD-004       | Yes         | No unresolved contradictions found. Slug case-sensitivity vs. reserved-word case-insensitive check are explicitly reconciled. Two deletion paths (soft-delete vs. ops hard-delete) are described and distinguished. |
| PRD-005       | Yes         | All named feature sections (Link creation, Link list, Link editing, Click analytics, Abuse review queue, Teams/Workspaces, Account) contain acceptance criteria. |
| PRD-007a      | Yes         | Every numbered flow (A–E) has an explicit "Failure paths" paragraph immediately following the happy-path steps. No flow is purely happy-path. |
| PRD-008       | Yes         | Explicit "Out of scope for v1" section (line 354) enumerates 13 excluded items. |
| PRD-010       | Yes         | All NFRs (performance, availability, security, data retention) carry specific, measurable targets or named standards. No vague target found. |
| PRD-013       | Yes         | Glossary defines all key terms (Workspace, Member, User, Slug, Short code, Click, Activated Workspace, Paid). Terms are used consistently across sections. "Teams" in the feature section heading is explicitly cross-referenced to Workspaces. |
| Cross-check 1 | Yes         | "Activated Workspace" denominator is defined in the Glossary (line 25). All other metric denominators are self-evident. |
| Cross-check 4 | Yes         | The 60-second freshness target appears four times (Flows B, C; Click pipeline section; Click analytics AC) and is numerically consistent across all occurrences. |

## Gate 1 — Critical (must fix before deriving ERD / architecture)

No Gate 1 findings.

## Gate 2 — Blockers (must fix before downstream work)

### [PRD-006] — Paste-to-copy metric measurement boundary undefined
**Location:** `docs/prd.md:43`
**Finding:** The measurement method for this success metric is undefined. "Paste-to-copy time" could be measured client-side (JS timer from paste event to clipboard API call) or server-side (API round-trip). The two differ by network latency and render time and produce incomparable values. Without specifying who measures this and at which boundary, implementation teams will instrument it differently and the metric cannot be validated against the < 5 second target.
**Fix:** Specify the measurement boundary: e.g., "client-side elapsed time from the paste event firing on the input field to the user clicking the Copy button, as measured by the frontend performance instrumentation."
**Effort:** low

### [PRD-006] — Link deletion feature undefined despite being referenced
**Location:** `docs/prd.md:214`
**Finding:** Link deletion is granted to Editors in the Teams AC but no Link deletion feature, flow, or acceptance criteria exists anywhere else in the PRD. The following are undefined: which roles may delete a link (the Teams AC says Editors can, but the Link editing AC says "any Member"; the scopes are inconsistent); whether deletion is a soft-delete that starts the 30-day reuse clock; what happens when a Member deletes a link that is currently pending in the Abuse review queue; and what the user-visible behavior is on deletion API failure.
**Fix:** Add a "Link deletion" feature section with AC covering: permitted roles, soft-delete mechanics (does it start the 30-day reuse clock?), behavior when the link is in the Abuse review queue, and error scenarios for API failure.
**Effort:** medium

### [PRD-007] — Invite acceptance sub-flow missing post-signup Workspace-add failure branch
**Location:** `docs/prd.md:220`
**Finding:** The invite acceptance sub-flow describes three happy-path branches (no account, account but not signed in, already signed in) but provides no failure branch for the step where the system adds the new user to the Workspace after sign-up completes. If the Workspace-add operation fails (5xx) after sign-up succeeds, the user has a verified Snip account but belongs to no Workspace and is not in the onboarding flow for creating one — leaving them in a broken state. This failure path is absent from both the Teams error scenarios table and the Account error scenarios table.
**Fix:** Add a failure case to the invite acceptance sub-flow: "If the Workspace-add step fails after sign-up completes, the user is directed to an error page with the message [X] and the invite token remains valid for retry."
**Effort:** low

### [PRD-009] — Mixpanel integration missing per-request timeout
**Location:** `docs/prd.md:262`
**Finding:** The Mixpanel integration section specifies retry counts and backoff (3×, 1s/4s/16s) but states no per-request timeout. Without a timeout, a hung Mixpanel connection blocks the in-process queue thread for an unbounded duration. Architecture cannot set thread/connection pool sizing or determine whether Mixpanel events could back-pressure user-visible requests.
**Fix:** Add a "Timeout" line to the Mixpanel contract section, e.g., "Timeout: 2000ms per request before triggering the retry."
**Effort:** low

### [PRD-009] — AWS SES integration missing per-request timeout
**Location:** `docs/prd.md:296`
**Finding:** The AWS SES integration section covers bounce/complaint handling, rate limits, and suppression enforcement but states no per-request timeout for the SES send API call. SES is a hard dependency for sign-up, password reset, and invite flows. Without a timeout, a hung SES call blocks user-visible requests (sign-up, invite) for an unbounded duration. The failure semantics section does not cover what happens when the SES API call itself hangs before returning a success or error response.
**Fix:** Add a "Timeout" line to the SES contract section, e.g., "SES API call timeout: 3000ms. On timeout, treat as a send failure and follow the per-flow failure path."
**Effort:** low

### [PRD-009] — Cloudflare cache purge has no integration contract
**Location:** `docs/prd.md:206`
**Finding:** Cloudflare is named as a system the product depends on for cache purge operations in the Abuse review queue AC. There is no contract section for Cloudflare anywhere in the PRD. The following are undefined: which Cloudflare API is called (Cache Purge API? Zone-based purge?), how auth is handled (API token? Zone ID stored where?), what the failure semantics are if the purge call fails (does the disabled link remain live at the CDN edge?), timeout, retry policy, and PII treatment. This is a significant omission because a failed purge means a disabled or hard-deleted link continues to redirect visitors from the edge.
**Fix:** Add a "Cloudflare — edge cache purge" integration section with: transport (which API endpoint), auth (API token stored in Secrets Manager), timeout, retry policy, and failure semantics (e.g., "if purge fails, the backend retries up to N times; ops alert fires if still failing").
**Effort:** medium

### [PRD-009] — AWS KMS missing timeout and retry policy
**Location:** `docs/prd.md:328`
**Finding:** AWS KMS is declared a hard dependency for sign-up and invite creation (write) and for login and password-reset lookup (read), but the contract section states no timeout or retry policy. For a hard dependency where KMS unavailability causes a 500 and blocks sign-up and login, architecture needs to know the timeout ceiling to set connection pool and circuit-breaker parameters. Without these, engineers will pick values independently.
**Fix:** Add timeout and retry lines to the AWS KMS section, e.g., "KMS API timeout: 500ms. Retry: 1 immediate retry on network error. After retry exhaustion, return 500 and fire ops alert."
**Effort:** low

## Gate 3 — Warnings (lead approval)

### [PRD-011] — Workspace name has no constraints
**Location:** `docs/prd.md:99`
**Finding:** Workspace name has no constraints defined anywhere in the PRD: no minimum or maximum length, no allowed character set, no uniqueness requirement (can two Workspaces share the same name?), and no reserved-name list. The database schema designer and frontend validator will each invent constraints independently, likely producing inconsistencies.
**Fix:** Add Workspace name constraints to the Teams (Workspaces) AC: minimum and maximum length, allowed characters (e.g., Unicode display characters), and whether names must be globally unique.
**Effort:** low

### [PRD-012] — Cloudflare cache purge actor is unspecified
**Location:** `docs/prd.md:206`
**Finding:** "Handled by the ops action" does not name a system actor. Possible interpretations: (a) the reviewer's UI calls a backend endpoint that calls the Cloudflare purge API synchronously; (b) a background worker polls for disabled/deleted links and purges asynchronously; (c) the ops reviewer manually calls Cloudflare. The cost, latency, reliability, and architectural implications differ substantially across these interpretations.
**Fix:** Replace "handled by the ops action" with an explicit actor, e.g., "The Abuse review queue backend calls the Cloudflare Cache Purge API synchronously as part of the disable/hard-delete transaction."
**Effort:** low

## Summary

The PRD is structurally strong — personas, flows, glossary, success metrics, out-of-scope section, and acceptance criteria are all present and well-formed, and the Pwned Passwords, MaxMind, and Google Safe Browsing contract sections are complete models for what the others should look like. The seven Gate 2 blockers fall into two buckets: four missing integration contracts (Mixpanel and SES lack per-request timeouts; Cloudflare has no contract at all despite being a hard dependency for cache purge; KMS has no timeout/retry policy) and three incomplete feature definitions (link deletion is mentioned but never elaborated as a feature, the paste-to-copy metric lacks a measurement boundary, and the invite acceptance sub-flow has no failure branch for the post-signup Workspace-add step). Fix the Cloudflare contract and link deletion feature section first — both are load-bearing for ERD table design (ABUSE_REVIEW_QUEUE state, LINK soft-delete vs. hard-delete, an external-system config table) — before deriving the ERD or architecture.
