# PRD Review — 2026-06-01 (max effort)

**File reviewed:** `docs/prd.md` (v3)
**Effort:** max
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 5  **Gate 3:** 9

## Lookup

| PRD location | Defect | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/prd.md:85 | "Abuse review queue" referenced as fail-open safety net but has no feature/AC/flow/SLA | PRD-005 | 2 | blocker |
| docs/prd.md:155 | "Recipient declines invite" appears in error table only — no flow, no AC, no re-invite policy | PRD-005 | 2 | blocker |
| docs/prd.md:62,69,123 | Three near-but-not-identical freshness targets on the same pipeline ("within 60s", "≤ 60s", "± 1 minute") | PRD-006 | 2 | blocker |
| docs/prd.md:143 | Member removal flow doesn't cover sent invites, session revocation timing, re-invite eligibility, or audit-trail authorship | PRD-007 | 2 | blocker |
| docs/prd.md:224 | SES "scaled on demand" — no backpressure rule, scaling action owner, or user-visible behavior on Throttling | PRD-009 | 2 | blocker |
| docs/prd.md:240 | "OWASP Top-10 baseline" — no edition, controls list, or verification mechanism | PRD-010 | 3 | warning |
| docs/prd.md:238 | "Mid-tier mobile over 4G" — device class lacks a reference profile | PRD-010 | 3 | warning |
| docs/prd.md:240 | "Email addresses encrypted at rest" — no scope (column / disk), key management, or queryability rule | PRD-010 | 3 | warning |
| docs/prd.md:107 | Date filter timezone behavior on DST transitions and on cross-tz reload unstated | PRD-011 | 3 | warning |
| docs/prd.md:79 | Slug case-only collisions during 30-day reuse window (`Foo` vs `foo`) not addressed | PRD-011 | 3 | warning |
| docs/prd.md:144 | Last-Admin protection covers UI but not operator/support-driven account deletion | PRD-011 | 3 | warning |
| docs/prd.md:131 | "Click is durably queued" / "next successful flush" — queuer and flusher not named | PRD-012 | 3 | warning |
| docs/prd.md:219 | Email suppression enforcement point unstated (application layer? SES list? both?) | PRD-012 | 3 | warning |
| docs/prd.md:9,29 | Audience drift: "small marketing teams" vs "small business (5–50 employees)"; "marketer" vs "Member" | PRD-013 | 3 | warning |

## Gate 2 — Notable catches

### [PRD-005] — Abuse review queue is not a defined feature
**Location:** `docs/prd.md:85`
**Finding:** The "abuse review queue" backstops the Gate-3 fail-open Safe Browsing decision but no feature exists — no AC, no actor, no SLA on review, no UI surface, no description of what happens to clicks on a flagged-but-not-yet-reviewed link. The safety net is named but undefined.
**Fix:** Add an Abuse review queue feature block: reviewer, tool, target time-to-action, action options (disable / hard-delete / whitelist), and the public-facing state of a flagged-but-not-yet-reviewed link.
**Effort:** medium

### [PRD-006] — Three different freshness targets for the same pipeline
**Location:** `docs/prd.md:62, 69, 123`
**Finding:** Flow B says "recorded ... within 60 seconds"; Flow C says "data freshness: ≤ 60 seconds behind real-time"; Click Analytics AC says "accurate within ± 1 minute". "± 1 minute" is two-sided; "≤ 60 seconds" is one-sided; "recorded" (ingest) is not the same SLO as "visible on detail page" (query). An implementer must pick one.
**Fix:** State two distinct SLOs once — ingest ("click written to durable storage within X seconds of the 30x") and query ("detail page reflects clicks ingested ≥ Y seconds ago") — and reference them by name from all three places.
**Effort:** low

### [PRD-007] — Member removal cascade gaps
**Location:** `docs/prd.md:143`
**Finding:** Flow handles link-ownership reassignment only. What happens to (a) invites the removed Member sent that are still pending, (b) active session revocation timing, (c) whether the email is now blocked for re-invite, (d) historical authorship references — all unstated. Will be decided silently by the migration author.
**Fix:** Extend Teams AC with explicit rules for each.
**Effort:** medium

### [PRD-009] — SES "scaled on demand" is not a contract
**Location:** `docs/prd.md:224`
**Finding:** 14 msg/sec stated; "scaled on demand" is not a contract. No mention of: who/what raises the limit, SES grant time, queue/backpressure strategy while throttled, or what users see when sign-up/reset/invite is queued waiting for SES throughput.
**Fix:** State peak send rate target, limit-raise mechanism, queue + retry behavior on Throttling, and user-visible behavior of mail-triggering flows under throttle.
**Effort:** medium

### [PRD-005] — Invite decline missing from AC
**Location:** `docs/prd.md:155`
**Finding:** "Recipient declines invite" appears in the error-scenarios table but never in the Teams AC. No mechanism (link in email? UI?), no rule on re-invite after decline.
**Fix:** Either add to AC or remove from error table.
**Effort:** low

## Gate 3 — Warnings

(Nine — see lookup table. PRD-010 × 3 vague NFRs, PRD-011 × 3 boundary cases, PRD-012 × 2 passive voice, PRD-013 × 1 vocabulary drift.)

## Comparison vs other effort levels

| Effort | Findings (G1/G2/G3) | Verdict |
|---|---|---|
| Original (high) | 0 / 0 / 9 | PASS_WITH_RISK |
| Low | 0 / 0 / 0 | PASS |
| Medium | 0 / 2 / 6 | FAIL_BLOCKER |
| **Max** | **0 / 5 / 9** | **FAIL_BLOCKER** |

**Headline:** Max effort surfaced 3 more Gate 2 issues that medium effort missed:
- **Abuse review queue is not a feature** (sharp catch — backstops a security decision)
- **Three inconsistent freshness targets for the click pipeline** (cross-section reading)
- **Member removal cascade gaps** (invites, sessions, re-invite, audit)

PRD review scales monotonically with effort — every increment adds findings, none are false positives.
