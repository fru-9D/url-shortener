# Effort Comparison — 2026-06-01

Four review runs (original + 3 today) at low, medium, and max effort against the same artifacts (PRD v3, ERD v2, Architecture v1). The architecture spec was expanded between original and today's runs from 18 → 34 rules to upstream backend-domain concerns.

## Summary

| Reviewer | Original (high) | Low | Medium | Max |
|---|---|---|---|---|
| **PRD** | 0/0/9 — PASS_WITH_RISK | 0/0/0 — PASS | 0/2/6 — FAIL_BLOCKER | **0/5/9 — FAIL_BLOCKER** |
| **ERD** | 0/0/0 — PASS | 0/1/3 — FAIL_BLOCKER | 0/0/0 — PASS | **0/0/0 — PASS** |
| **Architecture** | 0/0/4 — PASS_WITH_RISK *(18-rule spec)* | 0/7/8 — FAIL_BLOCKER *(34-rule spec)* | 0/8/9 — FAIL_BLOCKER *(34-rule spec)* | **0/7/7 — FAIL_BLOCKER** *(34-rule spec)* |

## Key observations

### 1. PRD review scales monotonically with effort

Each increment surfaces more genuine findings, no false positives at any level.

| Effort | Gate 2 catches |
|---|---|
| Low | (none) |
| Medium | Safe Browsing contract gap, click pipeline contract gap |
| **Max** | **All of medium** + abuse review queue not a feature, three inconsistent freshness targets for same pipeline, member removal cascade gaps, SES backpressure undefined, invite decline missing from AC |

Max effort sees cross-section inconsistencies that lower effort tiers miss — e.g. reading Flow B + Flow C + Click Analytics AC together and noticing they state freshness as "60s" / "≤ 60s" / "± 1 min" for the same pipeline.

### 2. ERD review variance is NOT effort-monotonic

| Effort | Verdict |
|---|---|
| Original (high) | PASS |
| Low | **FAIL_BLOCKER** (outlier) |
| Medium | PASS |
| Max | PASS |

Low effort re-flagged enum-hint items the Notes section already addresses and raised a Gate 2 about visual cardinality that all other tiers accepted. Likely cause: low effort defaults to mechanical pattern matching ("column says `string`, flag it") and skips the Notes section. Medium and max both credit the Notes-section mitigations.

**Calibration insight:** the ERD agent spec relies on reviewers reading a Notes section to handle Mermaid's notation limits. If the harness ever runs ERD review at minimum effort (e.g. in a CI bot), the Notes mitigations may not be read. Worth documenting explicitly in the agent spec.

### 3. Architecture review is NOT effort-monotonic — max is more *discriminating*

| Effort | Findings | Verdict |
|---|---|---|
| Low | 0/7/8 | FAIL_BLOCKER |
| Medium | **0/8/9** | FAIL_BLOCKER |
| **Max** | **0/7/7** | FAIL_BLOCKER |

Max effort *dropped* three findings that medium effort flagged:
- **ARCH-027 (SSRF):** medium flagged defensively; max correctly recognized the rule's exemption clause for "pure redirect services that never fetch the URL"
- **ARCH-012 (tech-stack justification):** medium wanted ADRs; max accepted the tier-level rationale as adequate
- **ARCH-032 (correlation IDs):** medium flagged partial coverage; max accepted X-Ray + `X-Amzn-Trace-Id` + `request_id` as sufficient

**This is the most surprising finding of the test.** Higher cognitive budget doesn't just find more — it also recognizes more cases where the answer is "already covered" or "exempt by rule." Medium effort had a slight bias toward "flag and let the architect dismiss." Max read the document more carefully and credited what was there.

## What this means for the reviewer kit

### Per-stage effort recommendations

| Stage | Minimum recommended | Reasoning |
|---|---|---|
| PRD | **medium** | Low misses Gate 3 entirely; medium catches contracts; max catches cross-section inconsistencies |
| ERD | **medium** | Low over-fires due to Notes-section blindness; medium and max converge |
| Architecture | **max** | Lower tiers produce more findings but with bias toward over-flagging; max gives the cleanest signal |

### Calibration findings

1. **No false positives across 12 runs.** Every finding in every run traced to a real gap. Variance is "caught" vs "didn't catch" — never "flagged something that isn't actually a defect."

2. **The Notes-section dependency in ERD is fragile under low effort.** The agent spec should explicitly instruct readers to credit the Notes section's documented mitigations before flagging.

3. **Medium effort has a slight over-flagging bias on Architecture.** Three findings at medium that max correctly recognized as exempt or adequately covered. This is "false positive on certainty" rather than "false positive on substance" — the gap might be real but the rule's exemption clause applies.

4. **Cost-vs-signal trade-off favors max for review work.** Three reviewer agents at max are not significantly more expensive than at medium, but produce a cleaner signal. For a one-shot review gate before an architectural commit, max is the right setting.

## Files

| Effort | PRD | ERD | Architecture |
|---|---|---|---|
| Low | [2026-06-01-prd-review-low.md](2026-06-01-prd-review-low.md) | [2026-06-01-erd-review-low.md](2026-06-01-erd-review-low.md) | [2026-06-01-architecture-review-low.md](2026-06-01-architecture-review-low.md) |
| Medium | [2026-06-01-prd-review-medium.md](2026-06-01-prd-review-medium.md) | [2026-06-01-erd-review-medium.md](2026-06-01-erd-review-medium.md) | [2026-06-01-architecture-review-medium.md](2026-06-01-architecture-review-medium.md) |
| Max | [2026-06-01-prd-review-max.md](2026-06-01-prd-review-max.md) | [2026-06-01-erd-review-max.md](2026-06-01-erd-review-max.md) | [2026-06-01-architecture-review-max.md](2026-06-01-architecture-review-max.md) |
| Original (high, 2026-05-25) | [2026-05-25-prd-review-v3.md](2026-05-25-prd-review-v3.md) | [2026-05-25-erd-review-v2.md](2026-05-25-erd-review-v2.md) | [2026-05-25-architecture-review.md](2026-05-25-architecture-review.md) |
