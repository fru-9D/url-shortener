# PRD Review — Compressed Agent — Max Effort — Run 1
**Date:** 2026-06-02
**Agent:** prd-review-compressed
**Effort:** max
**Project:** Snip (url-shortener)

---

## STEP C — Verdict

```json
{
  "domain": "prd-review",
  "gate1_count": 1,
  "gate2_count": 28,
  "gate3_count": 16,
  "verdict": "FAIL_CRITICAL"
}
```

---

## Summary of Gate 1

- **F-15 (PRD-004):** "Conversion to paid" success metric requires a billing/paid tier explicitly out of scope for v1 — unmeasurable, direct contradiction.

## Summary of Gate 2 (28 blockers)

| ID | Rule | Location | Finding |
|---|---|---|---|
| F-01 | PRD-007a | Flow A step 3 | Happy-path only; failure branch not woven into steps |
| F-02 | PRD-006 | Flow B step 3 vs Click pipeline | "synchronously" conflicts with async SQS transport |
| F-03 | PRD-006 | Link creation AC — reserved prefixes | Exact-match vs prefix-match ambiguity |
| F-04 | PRD-007 | Link creation AC — soft-delete window | No AC for visitor behavior during 0–30-day window; no coverage of cleanup job failure |
| F-05 | PRD-005 | Abuse review queue | Named safety-net component with no acceptance criteria |
| F-06 | PRD-007 | Teams AC — member removal | No failure path for removal API returning 5xx mid-transaction |
| F-07 | PRD-007 | Teams AC — invite acceptance | Accept flow entirely unspecified (existing vs new account, session/email mismatch) |
| F-08 | PRD-007 | Flow C — link detail page | No cross-Workspace access control branch |
| F-09 | PRD-007 | Account AC — failed-login throttling | No lockout-triggering attempt behavior, no early-unlock, no active session behavior during lockout |
| F-10 | PRD-007 | Account AC — email verification | Verification link flow unspecified; no TTL stated for verification token |
| F-11 | PRD-007 | Account AC — sign-up; Teams AC | Post-signup/pre-Workspace state undefined |
| F-12 | PRD-009 | Google Safe Browsing | No dedicated integration section; missing auth, retry, PII treatment |
| F-16 | PRD-005 | Link creation AC — reserved prefixes | No error message specified for "slug matches a reserved prefix" case |
| F-17 | PRD-007 | Flow B; Click analytics AC | Bot detection not placed in redirect flow; no latency budget or unavailability handling |
| F-18 | PRD-005 | Click analytics AC — bot filtering | No AC for where bot detection occurs (redirect vs ingest consumer) |
| F-19 | PRD-009 | Mixpanel integration | No per-request timeout for /track API call |
| F-20 | PRD-007 | Flow C; soft-delete | No AC for link detail page behavior for soft-deleted links |
| F-23 | PRD-006 | Account AC — session idle expiry | "Idle expiry" undefined — any API call vs navigation only? |
| F-25 | PRD-009 | Mixpanel — failure handling | In-process queue has no capacity bound, eviction policy, or crash recovery |
| F-26 | PRD-005 | Teams AC — roles | No AC for role change: Admin→Editor promotion/demotion |
| F-28 | PRD-007 | Account AC — password reset; unverified user | No flow for password reset when user has unverified email |
| F-30 | PRD-005 | Abuse review queue — 24-hour SLA | No AC for what happens if 24-hour SLA is missed |
| F-31 | PRD-009 | AWS KMS (NFR) | External key-management service with no integration contract |
| F-33 | PRD-006 | Click pipeline SLOs vs Flows B/C | Ingest (≤2s) + Visibility (≤60s) = ≤62s but Flows say ≤60s — numeric inconsistency |
| F-35 | PRD-007 | Account AC — account deletion | No flow or AC for account deletion; Workspace membership and data handling undefined |
| F-37 | PRD-006 | Link creation AC — rate limit | "60 links/min/user" — rolling window vs fixed-bucket unspecified |
| F-38 | PRD-009 | Email delivery — SNS | SNS topic for SES bounces referenced with no integration contract |
| F-44 | PRD-007 | Flow A — session expiry mid-flow | No flow step or error scenario for session expiry occurring mid-create |
| F-45 | PRD-006 | Goals and success metrics | Multiple metric denominators undefined in Glossary: "week 1", "open" a page, "paste-to-copy time" instrumentation |
| F-47 | PRD-007 | Teams AC — Editor role permissions | No error scenario for Editor calling Members-management API endpoint |
| F-49 | PRD-006 | Goals — Conversion to paid | "Paid" undefined in Glossary (terminal cross-check finding) |

## Summary of Gate 3 (16 warnings)

| ID | Rule | Finding |
|---|---|---|
| F-13 | PRD-010 | Click pipeline throughput "redirect p95 traffic × 2" — not quantified |
| F-14 | PRD-010 | SAST tool not named; "every release" not defined |
| F-21 | PRD-011 | Date range filter DST transition / "Today" timezone edge cases |
| F-22 | PRD-010 | Session invalidation "at the moment of removal" — no mechanism or latency bound |
| F-24 | PRD-011 | IDN destination URL: UI display (punycode vs Unicode) unspecified |
| F-27 | PRD-013 | "Teams (Workspaces)" heading vs "Workspace" system-of-record name |
| F-29 | PRD-010 | "13 months rolling" — rolling not defined operationally; no compliance basis cited |
| F-34 | PRD-011 | Pagination edge case: page requested beyond total after bulk deletion |
| F-36 | PRD-011 | link_clicked Mixpanel event for hard-deleted link — workspace_id lookup may fail |
| F-39 | PRD-011 | IAB bot list: no version/update cadence; no UA spoofing coverage |
| F-40 | PRD-012 | "Passwords are stored" — passive voice; actor unspecified |
| F-41 | PRD-012 | "Email addresses encrypted at rest" — passive voice; encryption/decryption layer unspecified |
| F-42 | PRD-012 | "active sessions are invalidated" — passive voice; actor unspecified |
| F-43 | PRD-012 | "the system atomically reassigns owner_id" — "the system" ambiguous |
| F-46 | PRD-013 | Target users: "content writers, social-media coordinators" never mapped to "Editor" role |
| F-48 | PRD-011 | Invites accepted before inviter was removed — are resulting Members affected? |

---

## STEP A-bis — Terminal Cross-Checks

1. **Success metric denominators:** "Activated Workspace" defined ✓; "Paid" undefined ✗ (F-15, F-49); "week 1" undefined ✗; "open" undefined ✗.
2. **External system contracts:** Google Safe Browsing no contract (F-12) ✗; Mixpanel no timeout (F-19), no crash recovery (F-25) ✗; KMS no contract (F-31) ✗; SNS no contract (F-38) ✗. All others complete ✓.
3. **Flow actors named:** "the system" in member removal (F-43) ✗; "active sessions are invalidated" (F-42) ✗.
4. **SLO/freshness consistency:** Ingest (≤2s) + Visibility (≤60s) = ≤62s but Flows B/C say ≤60s (F-33) ✗.
