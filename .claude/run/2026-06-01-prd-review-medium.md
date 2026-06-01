# PRD Review — 2026-06-01 (medium effort)

**File reviewed:** `docs/prd.md` (v3)
**Effort:** medium
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 2  **Gate 3:** 6

## Lookup

| PRD location | Defect | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/prd.md:85 | Google Safe Browsing v4 contract incomplete (auth model, quotas, abuse-queue contract missing) | PRD-009 | 2 | blocker |
| docs/prd.md:62 | "Click pipeline" referenced but never contracted (transport, schema, durability/ordering, ownership boundary) | PRD-009 | 2 | blocker |
| docs/prd.md:240 | "OWASP Top-10 baseline" — no edition, no verification mechanism | PRD-010 | 3 | warning |
| docs/prd.md:224 | "scaled on demand" SES rate has no ceiling, scaling trigger, or fallback | PRD-010 | 3 | warning |
| docs/prd.md:107 | Date filter Custom bounded to 12 months — behavior beyond 12 months unstated (collides with 13-month click retention) | PRD-011 | 3 | warning |
| docs/prd.md:143 | "owner_id reassigned" — cascade behavior on later removal of the new owner, and re-invite-restoration policy, unstated | PRD-011 | 3 | warning |
| docs/prd.md:62 | "the click is recorded" — passive voice, writer component unnamed | PRD-012 | 3 | warning |
| docs/prd.md:143 | "owner_id reassigned to the removing Admin" — passive voice, actor (atomic system action vs follow-up admin) unstated | PRD-012 | 3 | warning |

## Gate 2 — Blockers

### [PRD-009] — Google Safe Browsing contract incomplete
**Location:** `docs/prd.md:85`
**Finding:** Safe Browsing v4 is named with timeout (800ms) and fail-open semantics, but auth model (API key storage/rotation), per-day quota, request shape (threatTypes/platformTypes), and the contract for the abuse review queue that catches fail-open cases are all unspecified.
**Fix:** Add an External Integrations subsection matching the depth of the Mixpanel / Pwned Passwords / SES entries.
**Effort:** low

### [PRD-009] — "Click pipeline" never contracted
**Location:** `docs/prd.md:62`
**Finding:** The "click pipeline" is referenced in Flow B and error scenarios but has no contract — transport (HTTP / Kinesis / Kafka / SQS), payload schema, durability guarantee, ordering guarantee, and the ownership boundary between the edge redirect service and the regional analytics store are all unspecified. Architecture cannot decide queue technology or write-amplification budget without this.
**Fix:** Add a "Click pipeline" subsection (in External integrations or a dedicated internal-services section) with transport, message schema, durability mode, expected throughput, and how the ≤60s freshness budget maps to component SLOs.
**Effort:** low

## Gate 3 — Warnings

(Six — see lookup table. PRD-010 × 2 vague NFRs, PRD-011 × 2 boundary cases, PRD-012 × 2 passive voice.)

## Comparison vs other effort levels

| Effort | Findings (G1/G2/G3) | Verdict | What changed |
|---|---|---|---|
| Original (v3 PRD review, higher effort) | 0 / 0 / 9 | PASS_WITH_RISK | Caught long-tail Gate 3 items, missed Gate 2 |
| Low (today) | 0 / 0 / 0 | PASS | Skipped Gate 3 entirely; no Gate 2 surfaced |
| **Medium (today)** | **0 / 2 / 6** | **FAIL_BLOCKER** | Caught 2 new Gate 2 issues no prior run caught: Safe Browsing contract gap, click pipeline contract gap |

**Headline:** medium effort found the strongest signal of all three runs. The Gate 2 catches are real — both rules expected first-party-class contracts for first-party-class dependencies, and the original higher-effort run somehow accepted the loose treatment. The PRD genuinely has these gaps; they should be addressed before architecture proceeds.
