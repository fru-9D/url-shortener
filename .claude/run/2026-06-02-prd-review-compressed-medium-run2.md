# PRD Review — Compressed Agent — Medium Effort — Run 2
**Date:** 2026-06-02
**Agent:** prd-review-compressed
**Effort:** medium
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| PRD location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| Goals table, row "Conversion to paid" | Metric "Activated Workspaces who convert to paid by week 8" requires a paid tier that does not exist in v1. Billing, paid plans, and Stripe are all explicitly out of scope. Direct conflict with out-of-scope section. | PRD-004 | G1 | Critical |
| Link creation AC — Abuse review queue | The Abuse review queue is a system component the link-creation path relies on but has no acceptance criteria: no criteria for what 'disable' means to redirects, no idempotency guarantee on reviewer actions, no queue capacity or SLA beyond the 24-hour review window, no AC for the link state machine transitions triggered by reviewer actions. | PRD-005 | G2 | Blocker |
| Link creation AC — slug reuse vs soft-delete | "A previously deleted slug becomes reusable after 30 days" conflicts with "Deleted links: soft-delete for 30 days, then hard-delete." Flow B says soft-deleted links return 404. It is unspecified whether 'reusable' means after soft-delete (day 0) or hard-delete (day 30), and whether reuse begins at exactly day 30 or day 31. | PRD-006 | G2 | Blocker |
| Flow B, step 3; Link creation AC — disabled state | Flow B says "On miss or soft-delete, returns branded 404 page" but has no branch for the 'disabled' link state (introduced by abuse review). A disabled link is neither a miss nor a soft-delete. HTTP response code, page, and SEO implications for a disabled link are unspecified in the flow. | PRD-007 | G2 | Blocker |
| Account AC — Failed-login throttling; error scenarios table | The Account error scenarios table does not include a 'Login attempt while locked out' row. No HTTP status code, user-facing message, indication of remaining lockout duration, or whether further attempts reset the timer are specified. | PRD-007 | G2 | Blocker |
| Teams AC — invite acceptance flow | No flow or error handling covers what happens when a recipient without a Snip account clicks the accept link. Must they sign up first? Is the invite pre-associated with sign-up? What if they sign up with a different email? | PRD-007 | G2 | Blocker |
| Account AC; Email delivery failure handling | No TTL for the original verification link is stated. No rate-limit on re-send requests is defined. No failure path for 'resend itself fails' is specified. | PRD-007 | G2 | Blocker |
| Flow A, steps 1–4 vs Failure path paragraph | Flow A step 3 presents a single linear narrative. The Safe Browsing lookup, rate-limit check, slug collision, and storage write are all inline branch points, but flow steps contain no conditional language. Error handling described only in a detached table. | PRD-007a | G2 | Blocker |
| Link creation AC — Google Safe Browsing | Google Safe Browsing contract is incomplete: missing API key management, PII treatment (destination URL query strings may contain PII), retry policy on non-timeout errors, and fail-closed vs fail-open distinction for 5xx vs timeout. | PRD-009 | G2 | Blocker |
| Link creation AC — Reserved prefixes | "Reserved prefixes" is ambiguous: exact-match only (just `admin`) or prefix-match (any slug starting with `admin`, e.g. `admin-campaign`)? Two valid implementations with different UX and security properties. | PRD-006 | G2 | Blocker |
| Flow B, step 3 vs Click pipeline section | "The redirect service emits a click event synchronously to the click pipeline, then returns a 302 Found" — "synchronously" conflicts with the async queue (SQS) transport described in the click pipeline section. A blocking queue.publish() would threaten the 100ms p95 target; a fire-and-forget is not 'synchronous'. | PRD-006 | G2 | Blocker |
| Non-functional requirements — Performance | "Redirect p95 < 100ms server-side globally" — "globally" and "server-side" are not defined with a measurement point (POP edge, synthetic monitor, RUM). Different measurement points can yield numbers that differ by 30-80ms. | PRD-010 | G3 | Warning |
| Non-functional requirements — Security | "TLS 1.2+ everywhere" is vague about scope: does it apply to SQS, DB connections, internal calls? "Everywhere" without scope clarification is not a verifiable NFR. | PRD-010 | G3 | Warning |
| Click pipeline message schema | No maximum length or sanitization rule for `referrer_host` / `destination_host`. Arbitrarily long or malformed Referer headers are not addressed. | PRD-011 | G3 | Warning |
| Teams AC — member removal | "The system atomically reassigns `owner_id` to the Admin performing the removal." No concurrency boundary described: if two Admins simultaneously remove the same Member, which Admin's ID is used? Is it a DB transaction, optimistic lock, or last-writer-wins? | PRD-011 | G3 | Warning |
| Account AC — Sessions | No AC describes whether all active sessions are invalidated when a password reset completes. This is a common security expectation that is unstated. | PRD-011 | G3 | Warning |
| Link creation AC — no deduplication + no cap | "Submitting the same Destination URL twice by the same Member creates a second short code." Combined with 60/min rate limit, a single Member could accumulate thousands of duplicate links per hour. No total-links-per-Workspace cap defined. | PRD-011 | G3 | Warning |
| Flow B, step 3 — actor ambiguity | "the redirect service emits a click event … to the click pipeline" — it is unclear whether the redirect service writes directly to SQS (SDK call, fire-and-forget) or calls an internal click ingest service HTTP endpoint. Two different components with different cost and latency. | PRD-012 | G3 | Warning |
| Overview vs Glossary; Flow B | Overview: "the redirect service records every click before redirecting." Flow B: "emits a click event … then returns a 302 Found." 'Before' in Overview implies blocking; 'then' in Flow B implies sequencing without blocking. Also, 'team' used casually in Overview alongside Glossary-defined 'Workspace'. | PRD-013 | G3 | Warning |

---

## STEP A-bis — Rules not flagged

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| PRD-001 | Yes | Six quantitative success metrics with numeric targets and time bounds. |
| PRD-002 | Yes | Primary user (marketing manager, 5–50 employee firm, non-technical) and secondary users explicitly defined. |
| PRD-003 | Yes | Three step-by-step flows (A, B, C) with trigger/action/system response/end state. |
| PRD-008 | Yes | "Out of scope for v1" section lists 14 exclusions explicitly. |
| PRD-009 (Mixpanel) | Yes | Transport, auth, failure handling (retry 3× + dead-letter), PII exclusions stated. Contract complete. |
| PRD-009 (Pwned Passwords) | Yes | Transport, timeout (500ms), retry, fail-open, PII (only 5-char SHA1 prefix sent), auth. Contract complete. |
| PRD-009 (AWS SES) | Yes | Transport, sender identity, suppression enforcement, failure handling per mail type, rate limits, SLA. Contract sufficient. |
| PRD-009 (MaxMind GeoLite2) | Yes | Transport (local mmdb), update cadence, fallback, stale alert, license. Contract complete. |
| PRD-009 (Click pipeline) | Yes | Transport, schema, durability, ordering, SLOs, failure/fallback, idempotency key stated. Contract complete. |
| PRD-009 (Google Safe Browsing) | Flagged | Contract incomplete. |

---

## STEP B — JSON findings array

```json
[
  {"domain":"prd-review","rule_id":"PRD-004","gate":1,"severity":"Critical","location":"Goals table — Conversion to paid","quote":"Activated Workspaces who convert to paid by week 8 — ≥ 5%","finding":"Metric references a paid tier that doesn't exist in v1 and is explicitly out of scope."},
  {"domain":"prd-review","rule_id":"PRD-005","gate":2,"severity":"Blocker","location":"Link creation AC — Abuse review queue","finding":"Abuse review queue has no AC for reviewer UI, disable semantics, SLA enforcement, or state machine transitions."},
  {"domain":"prd-review","rule_id":"PRD-006","gate":2,"severity":"Blocker","location":"Link creation AC — slug reuse vs soft-delete","finding":"Slug reuse timing conflicts with soft-delete semantics; 'reusable after 30 days' is ambiguous about day 0 vs day 30."},
  {"domain":"prd-review","rule_id":"PRD-007","gate":2,"severity":"Blocker","location":"Flow B — disabled link state","finding":"Flow B has no branch for the 'disabled' state; disabled is neither miss nor soft-delete."},
  {"domain":"prd-review","rule_id":"PRD-007","gate":2,"severity":"Blocker","location":"Account AC — locked-out login","finding":"No HTTP status, user-facing message, or lockout duration info specified for locked-out login attempt."},
  {"domain":"prd-review","rule_id":"PRD-007","gate":2,"severity":"Blocker","location":"Teams AC — invite acceptance by non-account-holder","finding":"No flow for what happens when recipient without Snip account clicks the accept link."},
  {"domain":"prd-review","rule_id":"PRD-007","gate":2,"severity":"Blocker","location":"Account AC — email verification re-send","finding":"No TTL for verification link, no resend rate limit, no failure path for resend failure."},
  {"domain":"prd-review","rule_id":"PRD-007a","gate":2,"severity":"Blocker","location":"Flow A, steps 1–4","finding":"Flow A steps are entirely happy-path; all failure branches in detached table only."},
  {"domain":"prd-review","rule_id":"PRD-009","gate":2,"severity":"Blocker","location":"Link creation AC — Google Safe Browsing","finding":"Missing: API key management, PII treatment for query strings, retry on non-timeout errors, fail-closed vs fail-open for 5xx."},
  {"domain":"prd-review","rule_id":"PRD-006","gate":2,"severity":"Blocker","location":"Link creation AC — reserved prefixes","finding":"Exact-match vs prefix-match behavior undefined."},
  {"domain":"prd-review","rule_id":"PRD-006","gate":2,"severity":"Blocker","location":"Flow B step 3 vs click pipeline","finding":"'Synchronously' conflicts with async SQS transport; at least two valid implementations with different latency profiles."},
  {"domain":"prd-review","rule_id":"PRD-010","gate":3,"severity":"Warning","location":"NFR — Performance","finding":"Redirect p95 'globally' measurement point undefined."},
  {"domain":"prd-review","rule_id":"PRD-010","gate":3,"severity":"Warning","location":"NFR — Security","finding":"TLS 1.2+ 'everywhere' scope is vague regarding internal communications."},
  {"domain":"prd-review","rule_id":"PRD-011","gate":3,"severity":"Warning","location":"Click pipeline schema","finding":"No max-length or sanitization rule for referrer_host / destination_host."},
  {"domain":"prd-review","rule_id":"PRD-011","gate":3,"severity":"Warning","location":"Teams AC — member removal","finding":"No concurrency boundary on atomic owner_id reassignment."},
  {"domain":"prd-review","rule_id":"PRD-011","gate":3,"severity":"Warning","location":"Account AC — password reset","finding":"Password reset does not specify whether all active sessions are invalidated."},
  {"domain":"prd-review","rule_id":"PRD-011","gate":3,"severity":"Warning","location":"Link creation AC — deduplication","finding":"No total-links-per-Workspace cap; unlimited duplicates possible."},
  {"domain":"prd-review","rule_id":"PRD-012","gate":3,"severity":"Warning","location":"Flow B step 3","finding":"Actor ambiguity: direct SQS SDK call vs internal click ingest service HTTP call."},
  {"domain":"prd-review","rule_id":"PRD-013","gate":3,"severity":"Warning","location":"Overview vs Glossary; Flow B","finding":"'Before redirecting' in Overview conflicts with 'then returns 302' in Flow B; 'team' used casually vs Glossary 'Workspace'."}
]
```

---

## STEP C

```json
{
  "domain": "prd-review",
  "gate1_count": 1,
  "gate2_count": 9,
  "gate3_count": 8,
  "verdict": "FAIL_CRITICAL"
}
```
