# PRD Review — Compressed Agent — Max Effort — Run 2
**Date:** 2026-06-02
**Agent:** prd-review-compressed
**Effort:** max
**Project:** Snip (url-shortener)

---

## STEP C — Verdict

```json
{
  "domain": "prd-review",
  "gate1_count": 7,
  "gate2_count": 26,
  "gate3_count": 10,
  "verdict": "FAIL_CRITICAL"
}
```

---

## Gate 1 — Critical (7)

| ID | Rule | Finding |
|---|---|---|
| F-01 | PRD-004 | Conversion-to-paid metric contradicts billing being out of scope |
| F-07 | PRD-004 | Error message for cross-Workspace invite says "sign in" implying Workspace switching — explicitly out of scope |
| F-15 | PRD-004 | Flow B calls click pipeline emit "synchronous"; click pipeline contract defines async SQS — direct contradiction with p95 SLO implications |
| F-25 | PRD-001 | Conversion-to-paid success metric is unmeasurable within v1 (no billing system) |
| F-33 | PRD-003 | No user flow defined for sign-up — onboarding journey from landing page through verification absent |
| F-34 | PRD-003 | No user flow defined for Workspace creation/onboarding — path from new User to first Member unspecified |
| (F-01/F-25 are related) | PRD-001 + PRD-004 | The paid-conversion metric fails both PRD-001 (unmeasurable) and PRD-004 (contradicts billing out of scope) |

---

## Gate 2 — Blockers (26)

| ID | Rule | Finding |
|---|---|---|
| F-02 | PRD-007a | Flow A steps are entirely happy-path; Safe Browsing lookup not woven into steps |
| F-04 | PRD-007 / PRD-007a | Flow C has no failure branch; no role-restricted access path |
| F-05 | PRD-005 | "Editors can create/edit/delete links" — link editing referenced but has no AC, no editable fields, no flow |
| F-06 | PRD-006 | "Atomically reassigns owner_id" — true atomic transaction vs eventual consistency; failure of partial execution unaddressed |
| F-08 | PRD-006 | link_clicked Mixpanel event — emitting actor ambiguous (redirect service directly vs click ingest service post-consume) |
| F-09 | PRD-009 | Google Safe Browsing contract incomplete: missing auth (API key), retry policy, PII treatment for query strings |
| F-10 | PRD-009 | Mixpanel /track API contract missing per-request timeout |
| F-11 | PRD-007 | Failed-login lockout defined but no error scenario for locked-out login attempt |
| F-12 | PRD-007 | Lockout is per-email; no behavior for lockout error message (enumeration risk) |
| F-13 | PRD-005 | Abuse review queue is named safety-net component with no acceptance criteria |
| F-14 | PRD-009 | IAB/ABC Spiders & Bots List is external data dependency with no contract |
| F-16 | PRD-009 | AWS KMS referenced with no failure contract (no fail-open/closed for write operations) |
| F-17 | PRD-007 | Pending invite cancellation on member removal — no error scenario for cancellation failure |
| F-18 | PRD-006 | Multiple password-reset tokens within 60-min TTL — are earlier ones invalidated? Unspecified |
| F-19 | PRD-009 | Google Safe Browsing PII: query strings in destination URLs may carry PII — no redaction stated |
| F-21 | PRD-006 | X-Forwarded-For with multiple IPs — which IP is used for country lookup? Undefined |
| F-24 | PRD-006 | "Convert to paid" numerator concept "paid" undefined in Glossary |
| F-26 | PRD-009 | AWS SNS topic for SES bounces — no contract (failure behavior, PII treatment) |
| F-29 | PRD-006 | "Workspaces creating ≥ 3 links in week 1" metric — "week 1" definition and denominator scoping ambiguous |
| F-30 | PRD-006 | Reserved prefix list: prefix-match vs exact-match unspecified |
| F-31 | PRD-006 | Reserved prefix list is lowercase-only; whether uppercase variants (Admin, API) are reserved unspecified |
| F-32 | PRD-007 | Click pipeline requires workspace_id but Flow B is anonymous — workspace_id lookup contract unspecified |
| F-39 | PRD-007 | No role-based AC for analytics visibility between Admin and Editor |
| F-40 | PRD-006 | "Pending invites sent by the removed Member cancelled" — only Admins can invite per line 146; ambiguous for Editor removal |
| F-41 | PRD-009 | IAB/ABC Spiders & Bots List — licensed external data source with no contract |
| F-43 | PRD-006 | Ingest SLO (≤2s) + Visibility SLO (≤60s) = ≤62s end-to-end; Flows B/C promise ≤60s — 2-second inconsistency |

---

## Gate 3 — Warnings (10)

| ID | Rule | Finding |
|---|---|---|
| F-03 | PRD-012 | Passive voice in Flow A step 3 and Flow C step 3; rendering component actor unnamed |
| F-20 | PRD-011 | Date-range picker bounded to 12 months but boundary enforcement behavior unspecified |
| F-22 | PRD-011 | No AC for Admin self-invite edge case |
| F-23 | PRD-011 | No AC for whether sessions are invalidated on password change/reset |
| F-27 | PRD-010 | "Redirect p95 < 100ms globally" — 'globally' undefined, measurement methodology unstated |
| F-28 | PRD-010 | "Dashboard p95 < 2s" — no definition of which dashboard page |
| F-35 | PRD-010 | SAST tooling not named; "every release" not defined |
| F-36 | PRD-010 | Session invalidation "at moment of removal" — no cross-region/edge invalidation mechanism specified |
| F-37 | PRD-011 | When reviewer disables link via Abuse queue, no AC for cache invalidation propagation delay |
| F-38 | PRD-010 | "Median paste-to-copy time" — measurement methodology not specified |

---

## Terminal Cross-Checks

1. **Denominators:** "Activated Workspace" defined ✓; "paid" undefined ✗ (F-24); "week 1" timing ambiguous ✗ (F-29).
2. **External contracts:** Google Safe Browsing incomplete ✗ (F-09, F-19); Mixpanel no timeout ✗ (F-10); KMS no contract ✗ (F-16); SNS no contract ✗ (F-26); IAB bot list no contract ✗ (F-14, F-41). All others complete ✓.
3. **Flow actors:** Flow A step 3 passive ✗ (F-03); Flow B emitter ambiguity ✗ (F-08).
4. **SLO consistency:** Ingest (≤2s) + Visibility (≤60s) = ≤62s but Flows say ≤60s ✗ (F-43).
