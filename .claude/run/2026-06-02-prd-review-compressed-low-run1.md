# PRD Review — Compressed Agent — Low Effort — Run 1
**Date:** 2026-06-02
**Agent:** prd-review-compressed
**Effort:** low
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| PRD location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| Goals table, row "Conversion to paid" | "Activated Workspaces who convert to paid by week 8 ≥ 5%" — no billing, paid plans, or conversion mechanism exists in v1 (explicitly out of scope). The metric is unmeasurable against the v1 system; its denominator concept "paid" is undefined in the Glossary and contradicts the out-of-scope section. | PRD-004 | G1 | Critical |
| Flow B, step 3 vs. Click pipeline section | Flow B step 3 says the click event is emitted "synchronously" before the 302. The Click pipeline section says the event is published "immediately after emitting the 302 response." These directly contradict each other on whether the queue write blocks the redirect. | PRD-004 | G1 | Critical |
| Flow A, step 3 | Flow A is entirely happy-path. The Safe Browsing call, fail-open queuing to the Abuse review queue, and the blocked-URL branch are documented only in AC prose — none are woven into the flow steps. | PRD-007a | G2 | Blocker |
| Teams (Workspaces) AC — member removal / owner_id reassignment | "Atomically reassigns owner_id" permits two valid implementations: synchronous DB transaction before HTTP 200, or background/async job. Ordering and failure handling on reassignment failure are both unspecified. | PRD-006 | G2 | Blocker |
| Teams (Workspaces) AC — Editor role restrictions | No flow step or error scenario covers the permission-denied branch when an Editor attempts a Member-management action (invite, remove, demote). | PRD-007 | G2 | Blocker |
| Account AC — failed-login lockout release mechanism | The lockout-release mechanism is unspecified: does the lockout auto-expire after 15 minutes, require a CAPTCHA, or require a reset email? At least two valid implementations exist. | PRD-006 | G2 | Blocker |
| Link creation AC — Abuse review queue | The Abuse review queue is named as a system safety-net component but has no acceptance criteria covering reviewer UI context, the disable-action's effect on the live redirect, queue-write failure handling, or SLAs beyond a 24-hour review window. | PRD-005 | G2 | Blocker |
| Link creation AC — Google Safe Browsing v4 | Google Safe Browsing is an external system with no contract section. Missing: transport endpoint, auth/API-key management, retry policy on non-timeout errors, PII treatment of destination URLs sent to Google. | PRD-009 | G2 | Blocker |
| Mixpanel integration — link_clicked event / PII exclusions | `referrer_host` is transmitted to Mixpanel. The PII exclusions section does not address whether referrer_host can contain PII (intranet hostnames, user IDs in referrer strings). PII contract for this field is incomplete. | PRD-009 | G2 | Blocker |
| Non-functional requirements — Security | "OWASP Top-10 2021 baseline, verified by SAST tooling on every release" names no SAST tool, states no pass/fail threshold, and leaves "baseline" undefined. | PRD-010 | G3 | Warning |
| Link creation AC — auto-generated short code collision with soft-deleted slug | No AC addresses whether auto-generation avoids the soft-deleted short-code namespace during the 30-day hold window. A nanoid collision with a held slug has an unspecified resolution. | PRD-011 | G3 | Warning |
| Teams AC — "active sessions are invalidated at the moment of removal" | Passive voice obscures which component performs session invalidation. On an edge-deployed service with cached session state, "at the moment" carries different latency implications. | PRD-012 | G3 | Warning |
| Overview, Target users, Teams section heading | "team" / "teammates" used in narrative sections alongside "Workspace" and "Member". The Teams feature section heading "Teams (Workspaces)" reinforces the drift rather than resolving it. | PRD-013 | G3 | Warning |

---

## STEP A-bis — Rules not flagged

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| PRD-001 | Yes | Six quantitative metrics with explicit targets are present. |
| PRD-002 | Yes | Primary persona (marketing manager, 5–50 employee company) and secondary persona (teammates) clearly defined. |
| PRD-003 | Yes | Three explicit step-by-step flows (A, B, C) cover the core use cases. |
| PRD-008 | Yes | Explicit "Out of scope for v1" section with 13 named exclusions. |
| PRD-010 (Performance/Availability) | Yes | p95 redirect < 100ms, dashboard render p95 < 2s, availability targets quantified. Flagged only the SAST/security sub-item. |

---

## STEP B — JSON findings array

```json
{
  "domain": "prd-review",
  "findings": [
    {
      "id": "F-001",
      "rule": "PRD-004",
      "gate": 1,
      "severity": "Critical",
      "location": "Goals table — 'Conversion to paid' row",
      "summary": "Success metric references a paid-conversion mechanism that is explicitly out of scope for v1. 'Paid' is undefined in the Glossary. The metric contradicts the out-of-scope section and is unmeasurable against the v1 system."
    },
    {
      "id": "F-002",
      "rule": "PRD-004",
      "gate": 1,
      "severity": "Critical",
      "location": "Flow B step 3 vs. Click pipeline section",
      "summary": "Flow B says the click event is emitted 'synchronously' before the 302. The Click pipeline section says the event is published 'immediately after emitting the 302 response.' These directly contradict each other on whether the queue write blocks the redirect."
    },
    {
      "id": "F-003",
      "rule": "PRD-007a",
      "gate": 2,
      "severity": "Blocker",
      "location": "Flow A steps 1–4",
      "summary": "Flow A is entirely happy-path. The Safe Browsing call, fail-open queuing to the Abuse review queue, and the blocked-URL branch are documented only in AC prose — none are woven into the flow steps."
    },
    {
      "id": "F-004",
      "rule": "PRD-006",
      "gate": 2,
      "severity": "Blocker",
      "location": "Teams (Workspaces) AC — member removal / owner_id reassignment",
      "summary": "'Atomically reassigns owner_id' permits two valid implementations: synchronous DB transaction before HTTP 200, or background/async job. Ordering and failure handling on reassignment failure are both unspecified."
    },
    {
      "id": "F-005",
      "rule": "PRD-007",
      "gate": 2,
      "severity": "Blocker",
      "location": "Teams (Workspaces) AC — Editor role restrictions",
      "summary": "No flow step or error scenario covers the permission-denied branch when an Editor attempts a Member-management action (invite, remove, demote)."
    },
    {
      "id": "F-006",
      "rule": "PRD-006",
      "gate": 2,
      "severity": "Blocker",
      "location": "Account AC — failed-login lockout release mechanism",
      "summary": "The lockout-release mechanism is unspecified: does the lockout auto-expire after 15 minutes, require a CAPTCHA, or require a reset email? At least two valid implementations exist."
    },
    {
      "id": "F-007",
      "rule": "PRD-005",
      "gate": 2,
      "severity": "Blocker",
      "location": "Link creation AC — Abuse review queue",
      "summary": "The Abuse review queue is named as a system safety-net component but has no acceptance criteria covering reviewer UI context, the disable-action's effect on the live redirect, queue-write failure handling, or SLAs beyond a 24-hour review window."
    },
    {
      "id": "F-008",
      "rule": "PRD-009",
      "gate": 2,
      "severity": "Blocker",
      "location": "Link creation AC — Google Safe Browsing v4",
      "summary": "Google Safe Browsing is an external system with no contract section. Missing: transport endpoint, auth/API-key management, retry policy on non-timeout errors, PII treatment of destination URLs sent to Google."
    },
    {
      "id": "F-009",
      "rule": "PRD-009",
      "gate": 2,
      "severity": "Blocker",
      "location": "Mixpanel integration — link_clicked event / PII exclusions",
      "summary": "referrer_host is transmitted to Mixpanel. The PII exclusions section does not address whether referrer_host can contain PII (intranet hostnames, user IDs in referrer strings). PII contract for this field is incomplete."
    },
    {
      "id": "F-010",
      "rule": "PRD-010",
      "gate": 3,
      "severity": "Warning",
      "location": "Non-functional requirements — Security",
      "summary": "'OWASP Top-10 2021 baseline, verified by SAST tooling on every release' names no SAST tool, states no pass/fail threshold, and leaves 'baseline' undefined."
    },
    {
      "id": "F-011",
      "rule": "PRD-011",
      "gate": 3,
      "severity": "Warning",
      "location": "Link creation AC — auto-generated short code collision with soft-deleted slug",
      "summary": "No AC addresses whether auto-generation avoids the soft-deleted short-code namespace during the 30-day hold window."
    },
    {
      "id": "F-012",
      "rule": "PRD-012",
      "gate": 3,
      "severity": "Warning",
      "location": "Teams AC — 'active sessions are invalidated at the moment of removal'",
      "summary": "Passive voice obscures which component performs session invalidation."
    },
    {
      "id": "F-013",
      "rule": "PRD-013",
      "gate": 3,
      "severity": "Warning",
      "location": "Overview, Target users, Teams section heading",
      "summary": "'team' / 'teammates' used alongside 'Workspace' and 'Member'. The Teams feature section heading 'Teams (Workspaces)' reinforces the drift."
    }
  ]
}
```

---

## STEP C

```json
{"domain":"prd-review","gate1_count":2,"gate2_count":7,"gate3_count":4,"verdict":"FAIL_CRITICAL"}
```
