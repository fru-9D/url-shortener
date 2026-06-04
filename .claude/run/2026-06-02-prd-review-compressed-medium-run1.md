# PRD Review — Compressed Agent — Medium Effort — Run 1
**Date:** 2026-06-02
**Agent:** prd-review-compressed
**Effort:** medium
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| PRD location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| Goals table, row "Conversion to paid" | "Activated Workspaces who convert to paid by week 8 — ≥ 5%" references "paid" but Billing UI, paid plans, and Stripe are explicitly out of scope for v1. No paid tier exists to convert to, making this metric unmeasurable in v1. | PRD-004 | G1 | Critical |
| Link creation AC, last bullet | "While a link is pending in the queue it redirects normally." vs. reviewer action "disable (link returns 404 to visitors until reviewed)." These two statements are contradictory: pending links redirect normally, but "disable" is a reviewer action available while the link is still in a pending state. | PRD-004 | G1 | Critical |
| Teams (Workspaces) — no flow | The Teams/Workspaces feature (invite → accept → join) is described only as ACs and error scenarios. There is no user flow (step-by-step) for the invite-and-accept path or for member removal. | PRD-003 | G1 | Critical |
| Account — no sign-up/login flow | The Account feature describes ACs for sign-up, verification, login lockout, password reset, and sessions, but no step-by-step user flow exists for any of these paths. Flows A, B, C are the only flows defined. | PRD-003 | G1 | Critical |
| Flow A, steps 1–4 | Flow A step 3 is entirely happy-path. The Google Safe Browsing blocklist rejection and the fail-open queuing branch are not woven into the numbered flow steps. | PRD-007a | G2 | Blocker |
| Flow C, steps 1–3 | Flow C has no failure branch at all in its numbered steps. The error table is in the Click analytics feature section, not referenced from within the flow. | PRD-007a | G2 | Blocker |
| Link creation AC — Abuse review queue | The Abuse review queue is a named system component the platform relies on for safety enforcement. It has no acceptance criteria: no AC for the reviewer UI, no enforcement mechanism for the '24-hour' SLA, no definition of what happens when the queue is not drained within 24 hours. | PRD-005 | G2 | Blocker |
| Link creation AC — Google Safe Browsing | Google Safe Browsing v4 Lookup API is used as a hard dependency but has no contract section in External integrations. Missing: auth (API key sourcing and rotation), retry policy beyond the 800ms timeout, PII treatment (query string not addressed), formal fail-open statement in contract form. | PRD-009 | G2 | Blocker |
| External integrations — Mixpanel section | The Mixpanel contract specifies retry backoff and auth but omits a timeout for the outbound /track HTTP call. Without a timeout, a slow Mixpanel response blocks an in-process worker thread indefinitely. | PRD-009 | G2 | Blocker |
| Link creation AC — reserved prefixes | The term "prefixes" implies any slug beginning with reserved strings is blocked (e.g., `admin-promo`), but the AC describes them as a list of forbidden slugs without specifying exact-match vs. prefix-match. Two valid implementations diverge. | PRD-006 | G2 | Blocker |
| Account AC — email verification gate | No boundary condition stated for email address changes. If a user changes their email (not listed as in- or out-of-scope), it is unspecified whether verification resets. | PRD-011 | G3 | Warning |
| Non-functional requirements — Security | SAST tooling is named without specifying which tool or what constitutes a passing gate (zero critical? zero high+critical?). | PRD-010 | G3 | Warning |
| Non-functional requirements — Performance | "Dashboard initial-render p95 < 2s" — no measurement methodology specified (CI, staging RUM, or production RUM). | PRD-010 | G3 | Warning |
| Link creation AC — deleted slug reuse | No statement about whether auto-generated short codes (not user slugs) are also withheld from regeneration for 30 days after deletion. | PRD-011 | G3 | Warning |
| Click pipeline — ingest bus | "The ingest consumer is idempotent on `(link_id, clicked_at)`." Two distinct visitors clicking the same link within the same UTC second produce identical tuples; the second click is silently deduped and lost. | PRD-011 | G3 | Warning |
| Teams AC — member removal | "The system atomically reassigns `owner_id` to the Admin performing the removal." With multiple concurrent Admins, the actor for the reassignment is ambiguous. | PRD-012 | G3 | Warning |
| External integrations — Mixpanel, link_clicked event | `referrer_host` is sent to Mixpanel. PII exclusions list does not address referrer URLs which can encode search queries or PII in the hostname or before host extraction. | PRD-010 | G3 | Warning |
| Feature section header — Teams (Workspaces) | Glossary designates "Workspace" as system-of-record name; section header uses "Teams (Workspaces)" and AC bullets alternate between "Workspace" and "team." | PRD-013 | G3 | Warning |

---

## STEP A-bis — Rules not flagged

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| PRD-001 | Yes | Six quantitative success metrics with numeric targets present. |
| PRD-002 | Yes | Primary user (marketing manager, 5–50 employee SMB) and secondary users explicitly defined. |
| PRD-003 | Partial | Flows A, B, C cover link creation, redirect, and analytics. Teams and Account lack step-by-step flows — flagged G1. |
| PRD-004 | Flagged (2 findings) | Conversion-to-paid metric vs. billing out-of-scope; pending-queue redirect-normally vs. disable action. |
| PRD-005 | Flagged (Abuse review queue) | All named feature sections have AC. Abuse review queue is the only named component without AC. |
| PRD-006 | Flagged (reserved prefix ambiguity) | Only the reserved-prefix scope is genuinely ambiguous. |
| PRD-007 | Partial — flagged as PRD-007a | Flows A and C have errors in prose/tables but not woven into flow steps. |
| PRD-008 | Yes | Explicit "Out of scope for v1" section exists and is detailed. |
| PRD-009 | Flagged (Google Safe Browsing, Mixpanel timeout) | All other integrations have complete contracts. |
| PRD-010 | Flagged (3 warnings) | Performance targets exist but SAST gate vague, dashboard measurement unspecified, referrer_host PII concern. |
| PRD-011 | Flagged (3 warnings) | Email change re-verification, auto-code reuse window, click idempotency collision. |
| PRD-012 | Flagged (1 warning) | Concurrent multi-Admin member removal actor ambiguity. |
| PRD-013 | Flagged (1 warning) | "Teams" vs "Workspaces" drift. |

**Terminal Cross-Check Results:**
1. "Activated Workspace" defined in Glossary. "Paid" (conversion metric) is not defined anywhere — reinforces PRD-004.
2. Google Safe Browsing referenced in Link creation AC but has no contract section — flagged PRD-009.
3. Flow actors consistently named except Teams removal "the system" — flagged PRD-012.
4. "≤ 60 seconds" freshness: Flow B, Flow C, Click analytics AC, Click pipeline — all consistent.

---

## STEP B — JSON findings array

```json
[
  {"domain":"prd-review","rule_id":"PRD-004","gate":1,"severity":"Critical","location":"Goals table — Conversion to paid","quote":"Activated Workspaces who convert to paid by week 8 — ≥ 5%","finding":"Conversion-to-paid metric requires a paid tier that does not exist in v1 and is explicitly out of scope."},
  {"domain":"prd-review","rule_id":"PRD-004","gate":1,"severity":"Critical","location":"Link creation AC, last bullet","quote":"While a link is pending in the queue it redirects normally. ... Reviewer actions: ... disable (link returns 404 to visitors until reviewed)","finding":"Contradiction: pending links redirect normally, but disable is a reviewer action available during pending state."},
  {"domain":"prd-review","rule_id":"PRD-003","gate":1,"severity":"Critical","location":"Teams (Workspaces) feature section — no flow","finding":"No step-by-step user flow for invite-and-accept or member removal. Multi-step async flows involving email and role state transitions have no flow definition."},
  {"domain":"prd-review","rule_id":"PRD-003","gate":1,"severity":"Critical","location":"Account feature section — no flow","finding":"Sign-up, email verification, login, and password reset are described only as AC bullets. No step-by-step user flow exists for any of these paths."},
  {"domain":"prd-review","rule_id":"PRD-007a","gate":2,"severity":"Blocker","location":"Flow A, steps 1–4","finding":"Flow A steps are entirely happy-path. Safe Browsing blocklist rejection and fail-open branch not woven into numbered steps."},
  {"domain":"prd-review","rule_id":"PRD-007a","gate":2,"severity":"Blocker","location":"Flow C, steps 1–3","finding":"Flow C has no failure branch in its numbered steps. Error table is in Click analytics feature section, not woven into flow."},
  {"domain":"prd-review","rule_id":"PRD-005","gate":2,"severity":"Blocker","location":"Link creation AC — Abuse review queue","finding":"Abuse review queue has no AC for reviewer UI, 24-hour SLA enforcement, or what happens when queue is not drained in time."},
  {"domain":"prd-review","rule_id":"PRD-009","gate":2,"severity":"Blocker","location":"Link creation AC — Google Safe Browsing","finding":"Google Safe Browsing is a hard dependency with no contract section. Missing: auth, retry policy, PII treatment (query string), formal fail-open statement."},
  {"domain":"prd-review","rule_id":"PRD-009","gate":2,"severity":"Blocker","location":"External integrations — Mixpanel","finding":"Mixpanel contract missing timeout for outbound /track HTTP call."},
  {"domain":"prd-review","rule_id":"PRD-006","gate":2,"severity":"Blocker","location":"Link creation AC — reserved prefixes","finding":"Exact-match vs. prefix-match behavior undefined for reserved slugs."},
  {"domain":"prd-review","rule_id":"PRD-011","gate":3,"severity":"Warning","location":"Account AC — email verification gate","finding":"No boundary condition for email address changes and re-verification."},
  {"domain":"prd-review","rule_id":"PRD-010","gate":3,"severity":"Warning","location":"NFR — Security","finding":"SAST tooling named without tool name or passing threshold."},
  {"domain":"prd-review","rule_id":"PRD-010","gate":3,"severity":"Warning","location":"NFR — Performance","finding":"Dashboard p95 measurement environment unspecified."},
  {"domain":"prd-review","rule_id":"PRD-011","gate":3,"severity":"Warning","location":"Link creation AC — deleted slug reuse","finding":"Auto-generated short code reuse policy during 30-day hold window unspecified."},
  {"domain":"prd-review","rule_id":"PRD-011","gate":3,"severity":"Warning","location":"Click pipeline — ingest bus","finding":"(link_id, clicked_at) idempotency key collides for same-second clicks from different visitors."},
  {"domain":"prd-review","rule_id":"PRD-012","gate":3,"severity":"Warning","location":"Teams AC — member removal","finding":"Concurrent multi-Admin removal actor ambiguity."},
  {"domain":"prd-review","rule_id":"PRD-010","gate":3,"severity":"Warning","location":"Mixpanel link_clicked — referrer_host","finding":"referrer_host PII exclusion not addressed in Mixpanel contract."},
  {"domain":"prd-review","rule_id":"PRD-013","gate":3,"severity":"Warning","location":"Feature section header","finding":"'Teams (Workspaces)' header vs. 'Workspace' system-of-record name drift."}
]
```

---

## STEP C

```json
{"domain":"prd-review","gate1_count":4,"gate2_count":6,"gate3_count":8,"verdict":"FAIL_CRITICAL"}
```
