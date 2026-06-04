# PRD Review — Compressed Agent — Low Effort — Run 2
**Date:** 2026-06-02
**Agent:** prd-review-compressed
**Effort:** low
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| PRD location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| Goals table, row "Conversion to paid" | "Activated Workspaces who convert to paid by week 8 ≥ 5%" — no paid plan, no billing flow, and no conversion mechanism exists in v1. The metric is unachievable against defined scope and cannot be measured. Directly contradicts the Out-of-Scope section which excludes billing UI, paid plans, and plan selection. | PRD-004 | G1 | Critical |
| Flow A, step 3 | "The link-creation API validates the URL, generates or accepts the short code, persists the link, and returns the Short URL." — The Safe Browsing lookup is part of link creation per the Link creation AC, but Flow A step 3 does not mention it. Flow steps are entirely happy-path with no mention of what happens during the Safe Browsing check window (800ms lookup). | PRD-007a | G2 | Blocker |
| Teams (Workspaces) AC — Editor role restrictions | No acceptance criterion covers what happens when an Editor attempts a Member-management action (invite, remove, demote). The role restriction is stated but the failure path is absent from both flow steps and the error-scenarios table. | PRD-007 | G2 | Blocker |
| Account AC — email verification gate | Ambiguous scope: does the email-verification gate apply only to link creation or to all authenticated surfaces (link list, analytics, Members page)? Two valid implementations exist: (a) entire dashboard gated until verified; (b) only the create-link action blocked. | PRD-006 | G2 | Blocker |
| Link creation AC — reserved prefixes | The word "prefix" implies slugs beginning with a reserved string (e.g., 'admin123') are blocked, but the AC regex does not encode this. Two valid implementations: block only exact matches, or block any slug starting with a reserved string. | PRD-006 | G2 | Blocker |
| Account AC — failed-login lockout response | No specification of what the lockout response looks like to the user: does it reveal the lockout and remaining duration, or return the same generic auth-failure message? Two valid implementations with different security postures. | PRD-006 | G2 | Blocker |
| Link creation AC — soft-deleted slug reuse window | Behavior during the 30-day hold is partially specified in Flow B ('soft-delete → branded 404') but it is unspecified whether the slug is globally reserved or only within the originating Workspace during that window. | PRD-006 | G2 | Blocker |
| Link creation AC — Abuse review queue | The Abuse review queue is named as a relied-upon safety component but has no acceptance criteria beyond '24 hours' review SLA. No AC for queue failure, backlog growth, or default state when no reviewer acts. | PRD-005 | G2 | Blocker |
| External integrations section — Google Safe Browsing absent | Google Safe Browsing v4 is a hard dependency of link creation but has no integration contract section. Missing: auth (API key management), retry policy, PII treatment (are full destination URLs transmitted?), and canonical fail-open/fail-closed decision. | PRD-009 | G2 | Blocker |
| Non-functional requirements — SAST | SAST requirement lacks a tool name and a pass/fail threshold. 'OWASP Top-10 2021 baseline' is a category reference, not a measurable target. | PRD-010 | G3 | Warning |
| Click analytics AC — IAB bot list | No stated behavior when the IAB/ABC bot list is unavailable or stale at an edge node. Fail-open vs fail-closed for bot filtering is undefined. | PRD-011 | G3 | Warning |
| Teams AC — atomic owner reassignment on Member removal | No failure scenario for a partial-failure state: Member session invalidated but owner_id reassignment transaction fails. | PRD-011 | G3 | Warning |
| Overview and Target users sections | "team" used informally while "Workspace" is the system-of-record term. The Glossary acknowledges this but does not eliminate the drift across prose sections. | PRD-013 | G3 | Warning |

---

## STEP A-bis — Rules not flagged

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| PRD-001 | Yes | Six quantitative success metrics with specific targets and time bounds. |
| PRD-002 | Yes | Primary persona (marketing manager, 5–50 employee teams, non-technical) and secondary users named. |
| PRD-003 | Yes | Three step-by-step flows (A, B, C) cover create, redirect, and analytics. |
| PRD-004 | Yes — partial | "Conversion to paid" metric conflicts with billing being out of scope. Flagged. No other direct contradictions found. |
| PRD-005 | Yes | Link creation, Link list, Click analytics, Teams, Account all have AC sections. Abuse review queue flagged. |
| PRD-007 | Yes | Flow A, B, C each have failure paths. Editor permission denial absence flagged. |
| PRD-007a | Yes | Flow A happy-path steps do not weave in Safe Browsing check. Flagged. |
| PRD-008 | Yes | Explicit "Out of scope for v1" section present and detailed. |
| PRD-009 | Yes | Mixpanel, Pwned Passwords, AWS SES, MaxMind GeoLite2, Click pipeline all have complete contracts. Google Safe Browsing flagged. |
| PRD-010 | Yes | Performance and availability targets are numeric and specific. OWASP/SAST vagueness flagged. |
| PRD-011 | Yes | IAB bot list staleness and atomic reassignment failure flagged. |
| PRD-012 | Yes | Flow steps generally name the actor. No standalone ambiguity sufficient to flag at low-effort level. |
| PRD-013 | Yes | "Team"/"Workspace" drift acknowledged in Glossary itself. Flagged as G3 warning. |

**Terminal Cross-Checks:**
1. "Activated Workspace" defined in Glossary. "Conversion to paid" denominator resolves but metric is unfulfillable — already flagged PRD-004.
2. Google Safe Browsing v4 appears in Link creation AC but has no canonical contract section. Flagged PRD-009.
3. Redirect service, click ingest service, link-creation API are consistently named. No multi-actor ambiguity.
4. "≤ 60 seconds" freshness appears in Flow B end state, Flow C end state, Click analytics AC, and Click pipeline visibility SLO — all consistent.

---

## STEP B — JSON findings array

```json
[
  {
    "domain": "prd-review",
    "rule_id": "PRD-004",
    "gate": 1,
    "severity": "CRITICAL",
    "location": "Goals table — 'Conversion to paid' row",
    "summary": "Success metric requires paid plans, but billing UI, paid plans, and plan selection are all explicitly out of scope for v1. The metric cannot be measured or achieved within the defined scope.",
    "quote": "Activated Workspaces who convert to paid by week 8 | ≥ 5%"
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-007a",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "Flow A, step 3",
    "summary": "Flow A steps are entirely happy-path. The Safe Browsing lookup (800ms synchronous call) is not woven into the flow steps.",
    "quote": "On submit, the link-creation API validates the URL, generates or accepts the short code, persists the link, and returns the Short URL."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-007",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "Teams (Workspaces) feature section",
    "summary": "Role restriction for Editors is defined, but no failure/error scenario exists for an Editor attempting a member-management action."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-006",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "Account AC — email verification gate",
    "summary": "Two valid implementations: (a) entire dashboard gated; (b) only link creation blocked. The phrase 'can sign in but only sees a Please verify your email gate' does not resolve which other pages are accessible.",
    "quote": "until verified, the user can sign in but only sees a 'Please verify your email' gate"
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-006",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "Link creation AC — reserved prefixes",
    "summary": "Two valid implementations: block only exact matches, or block any slug starting with a reserved string.",
    "quote": "Reserved prefixes (cannot be used as slugs): `admin`, `api`, `app`, `auth`, `dashboard`, `help`, `login`, `logout`, `settings`, `signup`, `static`, `www`."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-006",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "Account AC — failed-login lockout",
    "summary": "No specification of what the lockout response looks like to the user.",
    "quote": "5 failed attempts per email per 15 minutes triggers a 15-minute lockout."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-006",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "Link creation AC — soft-deleted slug reuse window",
    "summary": "Behavior during the 30-day hold is partially specified but it is unspecified whether the slug is globally reserved or only within the originating Workspace.",
    "quote": "A previously deleted slug becomes reusable after 30 days."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-005",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "Link creation AC — Abuse review queue",
    "summary": "The Abuse review queue is named as a relied-upon safety component but has no acceptance criteria beyond '24 hours' review SLA.",
    "quote": "silently added to the Abuse review queue — an internal ops tool where trust-and-safety reviewers inspect flagged links within 24 hours."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-009",
    "gate": 2,
    "severity": "BLOCKER",
    "location": "External integrations section — Google Safe Browsing absent",
    "summary": "Google Safe Browsing v4 is a hard dependency but has no integration contract section. Missing: auth, retry policy, PII treatment.",
    "quote": "Destination URLs are checked against the Google Safe Browsing v4 Lookup API (host+path) at create time."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-010",
    "gate": 3,
    "severity": "WARNING",
    "location": "Non-functional requirements — SAST",
    "summary": "SAST requirement lacks a tool name and a pass/fail threshold.",
    "quote": "OWASP Top-10 2021 baseline, verified by SAST tooling on every release."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-011",
    "gate": 3,
    "severity": "WARNING",
    "location": "Click analytics AC — IAB bot list",
    "summary": "No stated behavior when the IAB/ABC bot list is unavailable or stale."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-011",
    "gate": 3,
    "severity": "WARNING",
    "location": "Teams AC — atomic owner reassignment",
    "summary": "No failure scenario for partial-failure state: Member session invalidated but owner_id reassignment transaction fails."
  },
  {
    "domain": "prd-review",
    "rule_id": "PRD-013",
    "gate": 3,
    "severity": "WARNING",
    "location": "Overview and Target users sections",
    "summary": "The term 'team' is used informally while 'Workspace' is the system-of-record term."
  }
]
```

---

## STEP C

```json
{"domain":"prd-review","gate1_count":1,"gate2_count":8,"gate3_count":4,"verdict":"FAIL_CRITICAL"}
```
