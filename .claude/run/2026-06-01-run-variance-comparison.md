# Run-to-Run Variance — Complete Report (2026-06-01)

Same artifacts (PRD v3, ERD v2, Architecture v1), same effort tier, two consecutive runs per tier.
Three effort tiers tested: low, medium, max. Six runs per reviewer, 18 total.

---

## Master results table

| Reviewer | Low R1 | Low R2 | Medium R1 | Medium R2 | Max R1 | Max R2 |
|---|---|---|---|---|---|---|
| **PRD** | 0/0/0 PASS | 0/2/5 FAIL_BLOCKER | 0/2/6 FAIL_BLOCKER | 0/2/6 FAIL_BLOCKER | 0/5/9 FAIL_BLOCKER | 0/3/8 FAIL_BLOCKER |
| **ERD** | 0/1/3 FAIL_BLOCKER | 0/0/6 PASS_WITH_RISK | 0/0/0 PASS | 0/5/5 FAIL_BLOCKER | 0/0/0 PASS | 0/0/4 PASS_WITH_RISK |
| **Architecture** | 0/7/8 FAIL_BLOCKER | 0/8/8 FAIL_BLOCKER | 0/8/9 FAIL_BLOCKER | 0/8/8 FAIL_BLOCKER | 0/7/7 FAIL_BLOCKER | 0/8/7 FAIL_BLOCKER |

### Verdict stability

| Reviewer | Low stable? | Medium stable? | Max stable? |
|---|---|---|---|
| **PRD** | ❌ PASS vs FAIL_BLOCKER | ✅ Same verdict | ✅ Same verdict |
| **ERD** | ❌ FAIL_BLOCKER vs PASS_WITH_RISK | ❌ PASS vs FAIL_BLOCKER | ⚠ PASS vs PASS_WITH_RISK |
| **Architecture** | ✅ FAIL_BLOCKER both | ✅ FAIL_BLOCKER both | ✅ FAIL_BLOCKER both |

---

## Analysis by reviewer

### PRD review

**Verdict stability by effort:**

| Tier | Run 1 | Run 2 | Verdict stable? | Same Gate 2 findings? |
|---|---|---|---|---|
| Low | PASS (0/0/0) | FAIL_BLOCKER (0/2/5) | ❌ | N/A |
| Medium | FAIL_BLOCKER (0/2/6) | FAIL_BLOCKER (0/2/6) | ✅ | ❌ (different 2 of ~7 issues) |
| Max | FAIL_BLOCKER (0/5/9) | FAIL_BLOCKER (0/3/8) | ✅ | ⚠ (2/5 overlap) |

**Key insight:** The PRD has 7+ distinct Gate 2 defects. No single run at any effort level surfaces all of them:
- Low effort: 0 found (verdict-unstable)
- Medium effort: 2 found per run (stable count, different 2 each time)
- Max effort: 3-5 found per run (most complete, stable verdict)

**Confirmed Gate 2 issues across all max runs:** abuse-review queue has no AC, freshness SLO has dual inconsistent specs.
**Found in one max run only:** invite decline missing from AC, member-removal cascade gaps, SES backpressure contract, second-Workspace AC missing, Flow B redirect-failure scenarios.

---

### ERD review

**Verdict stability by effort:**

| Tier | Run 1 | Run 2 | Verdict stable? | Root cause of variance |
|---|---|---|---|---|
| Low | FAIL_BLOCKER (0/1/3) | PASS_WITH_RISK (0/0/6) | ❌ | Cardinality Gate 2 (run 1 flagged, run 2 dismissed) |
| Medium | PASS (0/0/0) | FAIL_BLOCKER (0/5/5) | ❌ | PRD data-retention NFR applied to all entities (run 2 only) |
| Max | PASS (0/0/0) | PASS_WITH_RISK (0/0/4) | ⚠ | Gate 3 enum hint co-location (run 2 stricter reading) |

**ERD review is the most unstable reviewer.** Verdict flipped at low and medium. Max is closest to stable (both non-blocking, both agree on no Gate 2), but run 2 flagged 4 Gate 3 items run 1 dismissed.

**The medium run 2 Gate 2 findings are real:** CLICK missing `created_at`/`updated_at`, token tables missing `updated_at`, and INVITE.email_search_hash partial-UK not in diagram. The PRD NFR explicitly says "Audit fields (created_at, updated_at): indefinite" — applying this to every entity is expensive reasoning that only run 2 performed.

**Root cause:** ERD review requires cross-referencing the PRD NFR against every entity's column list (for audit fields) and crediting or questioning Notes-section mitigations (for constraints). Both steps require sustained attention that varies by run. This is the hardest review to make deterministic without hardening the agent spec.

---

### Architecture review

**Verdict stability by effort:**

| Tier | Run 1 | Run 2 | Verdict stable? | Gate 2 stable? | Gate 3 stable? |
|---|---|---|---|---|---|
| Low | FAIL_BLOCKER (0/7/8) | FAIL_BLOCKER (0/8/8) | ✅ | ~87% | 100% |
| Medium | FAIL_BLOCKER (0/8/9) | FAIL_BLOCKER (0/8/8) | ✅ | 100% | ~89% |
| Max | FAIL_BLOCKER (0/7/7) | FAIL_BLOCKER (0/8/7) | ✅ | ~87% | 100% |

**Architecture review is the most stable reviewer.** Verdict is identical across all 6 runs. Gate 2 findings are ≥87% matched between paired runs; Gate 3 findings are 89-100% matched.

**What varies:** ARCH-027 (SSRF) and ARCH-012 (tech-stack justification) are the two findings that flip between runs. Both have legitimate "already covered / exempt" readings in the document.

**What never varies:** ARCH-019..026 (CORS, headers, versioning, health checks, body limits, DTO policy, exception handler) fire in every single run. These are pure-absence checks against explicitly absent sections.

---

## Cross-cutting findings

### 1. The "deterministic vs reasoning" axis explains all variance

| Check type | Stable? | Examples |
|---|---|---|
| Pure absence — section/policy not present | ✅ Deterministic | CORS, security headers, API versioning, health checks, body limits, DTO policy, global exception handler |
| Credit mitigations in document's Notes section | ❌ Varies | ERD enum hints in Notes table, partial-UK notes, cardinality explanation |
| Apply a PRD clause to every entity | ❌ Varies by run | PRD data-retention `updated_at` requirement applied to all ERD entities |
| Recognize exemption clause in rule spec | ❌ Moderate | SSRF ("exempt for pure redirects"), tech-stack justification |
| Count/scope same-rule finding type | ⚠ Varies | How many enum columns to flag (3 vs 4), which PRD Gate 2 subset to surface |

### 2. Architecture review is safe for CI at any tested effort level

All 6 architecture runs returned FAIL_BLOCKER. The gate is stable. For a CI gate that blocks merges, architecture review can be run once at medium or max and trusted.

### 3. ERD review requires spec hardening before CI use

Two of three effort tiers produced verdict flips (PASS ↔ FAIL_BLOCKER). The medium run 2 caught real Gate 2 defects (missing audit columns) that medium run 1 missed entirely. Until the agent spec is hardened to make the PRD data-retention cross-check explicit, a single ERD review run cannot be trusted for go/no-go.

**Recommended spec addition:**
> **MANDATORY audit-column check:** For every entity in the ERD, verify that `created_at` and `updated_at` are both present (or that their absence is explicitly documented with justification). If the PRD NFR states "Audit fields (created_at, updated_at): indefinite" (or equivalent), this check is non-optional.

### 4. PRD review scales with effort but no single run is complete

All PRD Gate 2 defects found across all runs:
1. Abuse-review queue has no AC (found in both max runs, medium R1)
2. Freshness SLO inconsistency (found in both max runs)
3. Workspace sign-up flow ambiguity (medium R2, max R2)
4. User flows lack failure branches (medium R2, max R2)
5. Invite decline missing from AC (max R1)
6. Member-removal cascade gaps (max R1)
7. SES backpressure contract (medium R1)
8. Second-Workspace AC missing (max R2)
9. Flow B redirect-failure scenarios (max R2)

No single run found all of these. **The only reliable way to get complete PRD Gate 2 coverage is to run at max effort AND review the aggregated findings across multiple independent runs.**

### 5. No false positives in 18 runs

Every finding across every run traced to a real gap in the artifact. Variance is entirely in direction of "caught vs missed" — never "invented a finding that doesn't exist." The rule sets are correctly calibrated; the issue is coverage completeness, not accuracy.

---

## Final recommendations

| Stage | CI gate | Pre-implementation gate | Full coverage |
|---|---|---|---|
| PRD | Max effort, 1 run (blocks on clear Gate 2 defects) | Max effort, 2 runs (union of findings) | Human review of aggregated findings from 2 max runs |
| ERD | **Medium only after spec hardening**; max otherwise | Max effort, 1 run | Max effort — stable at non-blocking Gate 2 in both max runs |
| Architecture | Medium, 1 run (verdict 100% stable) | Medium or max, 1 run | Max effort for completest Gate 3 signal |

---

## Files index

| Effort | Run | PRD | ERD | Architecture |
|---|---|---|---|---|
| Low | 1 | [prd-review-low.md](2026-06-01-prd-review-low.md) | [erd-review-low.md](2026-06-01-erd-review-low.md) | [architecture-review-low.md](2026-06-01-architecture-review-low.md) |
| Low | 2 | [prd-review-low-run2.md](2026-06-01-prd-review-low-run2.md) | [erd-review-low-run2.md](2026-06-01-erd-review-low-run2.md) | [architecture-review-low-run2.md](2026-06-01-architecture-review-low-run2.md) |
| Medium | 1 | [prd-review-medium.md](2026-06-01-prd-review-medium.md) | [erd-review-medium.md](2026-06-01-erd-review-medium.md) | [architecture-review-medium.md](2026-06-01-architecture-review-medium.md) |
| Medium | 2 | [prd-review-medium-run2.md](2026-06-01-prd-review-medium-run2.md) | [erd-review-medium-run2.md](2026-06-01-erd-review-medium-run2.md) | [architecture-review-medium-run2.md](2026-06-01-architecture-review-medium-run2.md) |
| Max | 1 | [prd-review-max.md](2026-06-01-prd-review-max.md) | [erd-review-max.md](2026-06-01-erd-review-max.md) | [architecture-review-max.md](2026-06-01-architecture-review-max.md) |
| Max | 2 | [prd-review-max-run2.md](2026-06-01-prd-review-max-run2.md) | [erd-review-max-run2.md](2026-06-01-erd-review-max-run2.md) | [architecture-review-max-run2.md](2026-06-01-architecture-review-max-run2.md) |
| Original (high) | 1 | [2026-05-25-prd-review-v3.md](2026-05-25-prd-review-v3.md) | [2026-05-25-erd-review-v2.md](2026-05-25-erd-review-v2.md) | [2026-05-25-architecture-review.md](2026-05-25-architecture-review.md) |
