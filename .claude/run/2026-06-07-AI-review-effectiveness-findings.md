# AI for Software Review: Effectiveness and Reliability Boundaries
## Report 1 of 2 — Stability, Calibration, and What You Can Trust

*Audience: engineering lead. Scope: a corpus of ~80 staged AI-review runs on one project (the "Snip" url-shortener), spanning a standard reviewer track (2026-06-01), a compressed reviewer track (2026-06-02), single-agent code-stage runs (2026-06-04/05), an 8-domain backend review (2026-06-04/05), and a new 2-reviewer + reflexion-reconciler architecture (2026-06-07). All counts below were recounted against raw files; verifier corrections have been applied and contradictions across analysts reconciled. Three headline claims (the `auth.py:201` shared false-negative, the "Paid undefined" hallucination, the ERD Redis audit-column split) were independently re-verified against the on-disk artifacts.*

---

## 1. Executive Summary — the blunt bottom line

**AI review is reliable for exactly one class of work and unreliable for everything else, and the boundary is sharp.**

- **What is trustworthy:** *pure-absence / structural checks* — "does this document declare CORS? a global exception handler? API versioning? an audit-column on this table?" These fire if-and-only-if the section is absent and converge byte-for-byte even across reviewer prompts. Architecture's structural floor (rules ARCH-019, 020, 022–026) fired in **6 of 6** standard runs and held the verdict stable, and once the architecture doc was actually filled in, both the standard and compressed reconciled tracks flipped cleanly to `0/0/0 PASS` (`2026-06-07-architecture-review.md:50-57`). This layer behaves like a linter.

- **What is not trustworthy without mitigation:** *everything requiring judgment* — crediting a mitigation, applying an exemption clause, recognizing scope, and assigning severity. These are provably unstable. The single sharpest exhibit: the **same `docs/erd.md`, reviewed by the same 2-reviewer + reconciler pipeline, produced `PASS_WITH_RISK` on the standard track and `FAIL_BLOCKER` on the compressed track** — opposite go/no-go decisions, with disjoint findings, each track internally "reconciled" and confident (`2026-06-07-erd-review.md:6` vs `2026-06-07-erd-review-compressed.md:6-8`, verified on disk).

- **The real failure mode is missed findings, not invented ones** — with an honest exception. No run fabricated a non-existent file or column; flagged findings are overwhelmingly real (estimated stage precision ~85–100% on a spot-check). But the corpus's self-asserted "no false positives in 18 runs" is **false** — compression injected at least one hallucinated merge-blocking critical, and severity over-flagging produced additional false-positive-grade findings. The deeper problem is recall: **no single run or track surfaces the full defect set** (single-track recall of the cross-track union is roughly 50% on the ERD case).

- **The reflexion reconciler is a real but partial win.** It removes the run-to-run verdict coin-flip and adds precision, but it does not make the pipeline deterministic and it does not close the recall gap — it merely moves the disagreement from run-vs-run to track-vs-track.

**Recommendation in one line:** Let deterministic linters own the objective floor (single-run, CI-blocking). Treat every AI judgment finding as a *candidate worklist* requiring at least 2 runs + reconciliation, and require a human for any go/no-go where tracks diverge or an exemption/severity call is load-bearing.

**Two honesty caveats that bound every number in this report:** (1) every stability statistic rests on **n=2 runs per cell** (n=3–5 for code stages) with no confidence intervals — these are point estimates, not powered measurements; (2) the `backend/` source tree is git-untracked, so "same code between runs" claims cannot be verified from version control and rest on the reviewers' own self-reported prose.

---

## 2. Per-stage reliability ranking

Ranked most-reliable to least-reliable by run-to-run **verdict stability** (paired runs returning the same verdict) on the frozen-artifact 2026-06-01 study, which is the only era that deliberately held the artifact constant to isolate pure model noise.

| Rank | Stage | Verdict-stable pairs | Key variance number | Why it ranks here |
|---|---|---|---|---|
| **1 (best)** | **Architecture** | **3/3** | 6/6 runs `FAIL_BLOCKER`; max Gate-3 set byte-identical (7/7) | Stable — but **structurally**, not because the reasoning is reliable (see below) |
| **2** | **PRD** | **1/3** | Verdict-stable at medium/max only; **flips at low: PASS (0/0/0) ↔ FAIL_BLOCKER (0/2/5)** | Stable verdict masks unstable finding *identity* |
| **3 (worst doc)** | **ERD** | **0/3** | 3 distinct verdicts across 6 runs; **2 of 3 tiers cross go/no-go** | "Most unstable reviewer; cannot be trusted for go/no-go as a single run" |
| — | **ORM** (code) | 0/5 single-verdict | `FAIL_BLOCKER`×4 → `PASS`; same-day R3↔R4 swap 0/3/1 ↔ 0/4/0 | Converges via code fixes, not reviewer determinism; residual noise visible |
| — | **Migration** (code) | 0/3 single-verdict | 3 verdicts in 3 runs: `FAIL_BLOCKER` → `PASS_WITH_RISK` → `PASS` | Monotonic Gate-2 decay (7→0→0) = real fixes |
| — | **API-skeleton** (code) | 0/4 single-verdict | Touched **every** verdict bucket: `FAIL_BLOCKER` → `FAIL_BLOCKER` → **`FAIL_CRITICAL`** → `PASS` | One run escalated an unchanged 501 stub to a lone critical |
| — | **Backend** (8-domain) | n/a (remediation series) | `BASELINE_ONLY` → `FAIL_BLOCKER`×3 → `PASS_WITH_RISK`×2; G2: 9→17→4→3→0→0 | Downward remediation trend with an up-tick; discovery volatile (±4 blockers/domain) |

**The critical nuance the ranking hides — Architecture's stability is a floor artifact, not reasoning reliability.** Architecture ranks #1 only because 6–7 deterministic *absence* checks (ARCH-019, 020, 022–026) fire in every single run and pin the verdict to `FAIL_BLOCKER` regardless of what the reasoning rules do. Underneath that floor, the *reasoning* rules are as noisy as everywhere else: ARCH-027 (SSRF exemption) and ARCH-012 (stack justification) flip across runs and are explicitly described as having "both readings defensible." So the correct statement is: **Architecture's verdict is the most stable; Architecture's reasoning is not.** This is the single most important caveat in the whole ranking, and it is *why* absence-checks are the only fully reliable layer.

**ERD is the cautionary tale.** Worst same-effort event in the corpus by finding-count magnitude: ERD medium R1 = `0/0/0 PASS` vs R2 = `0/5/5 FAIL_BLOCKER` — identical artifact, identical effort, opposite go/no-go (`2026-06-01-erd-review-medium.md` vs `-medium-run2.md`). Note for fairness: PRD low ties this on *severity* (`PASS 0/0/0` ↔ `FAIL_BLOCKER 0/2/5`); ERD is "worst" only by the +5 vs +2 Gate-2 magnitude. PRD's master-table "Same verdict" green-checks at medium/max are also misleading — those pairs share *zero* (medium) or 2-of-5 (max) Gate-2 finding identities despite matching counts, so a reader trusting a single PRD run is over-trusting it.

---

## 3. Effort-level findings (low / medium / max)

**(a) Effort is non-monotonic — confirmed in direction, over-interpreted in magnitude.** On the single-run effort table (`2026-06-01-effort-comparison.md`), ERD goes PASS(orig) → FAIL_BLOCKER(low) → PASS(med) → PASS(max), with **low as the outlier**. Architecture rises then falls: low `0/7/8` → medium `0/8/9` → max `0/7/7`. So "more effort is not monotonically better" is correct.

**(b) Medium over-flags; max is more discriminating — true qualitatively, but the data cannot prove it is an effort effect.** The "max dropped 3 findings" story (ARCH-027 SSRF, ARCH-012 stack, ARCH-032 correlation-IDs) holds only for max **run 1** (`0/7/7`). Max **run 2** re-flags ARCH-027 and returns `0/8/7` — identical Gate-2 count to medium. **The medium→max gap (−1 Gate-2) is the same size as max's own run-to-run noise (+1 Gate-2).** Of the two headline "max correctly recognized the exemption" wins: ARCH-032 is stably dismissed in both max runs (genuine), but ARCH-027 is re-flagged in max R2 (does not replicate). The honest verdict: *the data cannot separate "max is smarter" from "max R1 happened to land on the lenient side of two coin-flip rules."*

**(c) Effort changes the finding list, never the gate — for Architecture.** Both max runs return `FAIL_BLOCKER`. "Max is more discriminating" must not be read as "max changes the go/no-go." The discrimination is invisible to the gate.

**(d) Low effort skips the Notes section,** which is precisely why ERD-low is the non-monotonic outlier: low-effort reviewers miss mitigation language in document footnotes and either over-block (failing to credit a mitigation) or under-detect.

---

## 4. Precision vs recall — the real picture, with the nuance

**The real weakness is recall, not fabrication.** No run in the corpus invented a non-existent file, column, or section. On a spot-check of ~23 findings from two 2026-06-04 reports, every flagged finding was corroborated against the current artifacts (e.g., ORM-ERD-005 FKs, ORM-ERD-006 partial-unique index, PRD-009 timeout contracts all now present in the exact recommended form). Estimated stage precision: **PRD ~90–100%, ERD ~80%, ORM/API-skeleton ~95–100%.**

**But the corpus's "no false positives in 18 runs" self-assessment is false — three honest counterexamples.** This is the contradiction two analysts collided on, and it must be reconciled in favor of "FPs exist":

1. **A hallucinated, merge-blocking false positive (the worst).** The compressed PRD track flagged the "Activated Workspaces who convert to paid" metric as a Gate-1 *critical contradiction* in all 6 PRD runs, claiming "Paid is undefined in the Glossary." This is **factually wrong against the artifact**: `docs/prd.md:27` defines "Paid" in the Glossary and `prd.md:50` footnotes the metric as tracked manually via an external CRM with billing out of scope by design. The standard track correctly returned Gate-1 = 0. Compression manufactured a CRITICAL that blocks merge. *(Independently re-verified on disk for this report.)*
2. **An over-strict severity false positive.** Compressed ERD flagged audit columns on the Redis-backed SESSION/LOGIN_ATTEMPT entities as two Gate-2 *blockers*; `erd.md:179` documents these as Redis hash structures with TTLs for which "no ORM model or migration is generated." Flagging them as merge-blocking is over-strict (this is contested — see §6).
3. **A second over-strict-severity candidate.** The standard PRD review rated PRD-007a (failure handling in flow steps) as Gate-2 blockers, but the failure branches *do* exist in the PRD (`prd.md:61, 70`) — only their inline weaving into the numbered step is missing. Elevating a documentation-style gap to a blocker is debatable.

**The nuance the accuracy analyst surfaced — high precision is partly engineered, and severity is a third, separate axis.** Two refinements matter for an engineering lead:

- **Precision is inflated by reconciler design.** The reconciler's stated "precision bias → drop on ambiguity" policy (`2026-06-07-prd-review-compressed.md:67`) keeps measured precision high *by trading away recall*. So the high-precision/low-recall profile is a design choice, not purely reviewer accuracy.
- **Severity calibration is unstable independently of detection.** On identical PRD prose, the standard track rated findings Gate-2 (→ `FAIL_BLOCKER`) while the compressed track rated the *same findings* Gate-3 (→ `PASS_WITH_RISK`). The compressed cross-track note itself concedes "the difference is severity judgment, not missed issues." **The gate-assignment layer is its own unstable axis** — a finding can be detected correctly and still swing the verdict purely on how it is graded.

**Net:** false positives are *not* zero, but they are rare and mostly severity-grade rather than fabrication. The dominant, structural weakness is recall — *the true worklist is the union across runs/tracks, and no single pipeline output produces that union.*

---

## 5. Did reflexion (2 runs + reconcile) fix the variance problem?

**Partially. It fixes the verdict coin-flip and adds precision; it does not make the pipeline deterministic and it does not close recall.**

**What it fixed (real gains):**
- **Verdict instability is genuinely removed *within a track*.** The reconciler recomputes the verdict deterministically from the adjudicated finding union via a fixed rule (Gate1>0 → critical/blocker; else Gate2>0 → blocker; else Gate3>0 → PASS_WITH_RISK; else PASS), stated as "recomputed deterministically / order-independent" (`2026-06-07-architecture-review.md:74`, `orm:55`, `migration:53`). The old pipeline let one reviewer's missed finding flip the gate; the new one unions two reviewers, then applies the rule.
- **Recall over a single run improves** via the union step — divergent-but-real findings that only one of the two runs caught are rescued (e.g., standard PRD: 1 consensus + 4 divergent-kept; compressed ERD: 2 consensus + 1 Run-A-only).
- **Precision gains the headline story underweights:** the reconciler caught a severity drift ("low" → canonical "blocker", `erd-review-compressed.md:74`) and dropped genuine false positives the agents raised (the member-removal-concurrency invention; same-locus duplicates). Reflexion adds precision, not only recall.
- **Micro-judgment is sound on the cases present.** The load-bearing keep/drop/correct calls verified correct against `docs/erd.md` on disk — e.g., overturning a reviewer who misread `erd.md:220`'s "**consider** range-partitioning" as a firm declaration.

**What it did NOT fix:**
- **Determinism is downstream of non-determinism.** "Order-independent" is true only *given a fixed finding set*. The finding union is produced by non-deterministic keep/drop/severity judgment. Reflexion kills the verdict coin-flip after adjudication; it does not make end-to-end review deterministic. Tellingly, "order-independent" is asserted only on the **zero-finding** stages where determinism is trivial; the non-trivial reconciliations (PRD, ERD-compressed) carry no order-independence check.
- **Recall gap survives — it just moved.** The pipeline pairs two runs of the **same agent variant** (standard+standard, or compressed+compressed) — never standard-vs-compressed. So the two tracks ship **un-unioned**, and the `PASS_WITH_RISK` vs `FAIL_BLOCKER` ERD divergence on identical input is *structurally outside reflexion's design envelope*. This is an architecture gap, not a reconciler-judgment failure — but the practical consequence is the same: a single shipped track still misses ~half the union.
- **It cannot catch a shared blind spot.** On zero-finding stages the reconciler only does a "skeptic spot-check" of dismissals, not independent re-derivation (`architecture-review.md:73`). A false-negative both reviewers share passes through unflagged. The reconciler guarantees consensus, not correctness. *(Live exhibit: the verify-email token-in-query defect at `auth.py:201` — still on disk — was flagged by backend runs 1–3 and then silently dropped by runs 4–6.)*

**Scope honesty:** only **5 of 9** reconciled stages did real adjudication work (both PRDs, both ERDs, api-skeleton); the other **4** (architecture std, orm, migration, architecture-compressed) were unanimous `0/0/0` where reflexion only confirmed. The reflexion conclusion rests on a handful of decisions (1 overturn, 1 severity fix, ~4 drops/upholds) — all correct, but a small sample. Per-run Run-A/Run-B inputs were not on disk, so we confirm the reconciled output is artifact-consistent but cannot independently confirm faithful unioning of inputs.

---

## 6. Three-tier reliability table — what to trust at each level

| Tier | Check class | Concrete examples | Operating mode | Evidence |
|---|---|---|---|---|
| **RELY ON FULLY** (single AI run, CI-blocking) | **Pure-absence / structural presence checks** + literal interpretation of deterministic preflight output | "Does the doc declare CORS / security headers / API versioning / health checks / body limits / DTO policy / global exception handler?" Section/policy presence. Reading ruff/mypy/bandit/pip-audit output. | Single run is safe; fires iff absent, flips cleanly to PASS once filled | ARCH-019..026 fired in 6/6 std runs; both 06-07 tracks `0/0/0 PASS` once doc filled; absence-detection mechanism is the stable invariant (`architecture-review.md:50-57`) |
| **RELY ON WITH 2+ RUNS + RECONCILE** | **Mitigation-crediting; per-entity clause application; severity/scope assignment; duplicate-resolution** | "Did the Notes already mitigate this?" Applying "audit columns on every entity." Gate-2-vs-Gate-3 grading. De-duping same-locus findings. | Union two runs, then reconcile; treat output as candidate worklist | No single PRD run found all 7+ Gate-2 defects; reconciler rescues divergent-but-real findings and normalizes severity; "complete coverage needs max effort AND aggregated multiple runs" |
| **DO NOT RELY ON WITHOUT A HUMAN** | **Exemption-recognition calls; any go/no-go where tracks diverge; severity that determines the gate** | "Does 'Redis-backed' excuse missing audit columns?" The ERD `PASS_WITH_RISK` vs `FAIL_BLOCKER` split. SSRF "exempt for pure redirects." | Human adjudicates; AI provides both readings as input | Same `erd.md` → opposite verdicts across tracks; ARCH-027 SSRF flips in 3 of 6 runs; compressed report itself: "neither track is strictly superior… treat the union as the worklist" |

**The cross-dimension contradiction reconciled here — is the ERD split a symmetric coin-flip or asymmetric?** Two analysts framed the standard-`PASS_WITH_RISK` vs compressed-`FAIL_BLOCKER` ERD divergence differently. Reconciled position: **it is a genuine, unresolved interpretive split that nonetheless leans toward the FAIL_BLOCKER track being more defensible.** The compressed track's findings are **ground-truth TRUE** on disk — SESSION (`erd.md:41-48`) has `created_at` only despite `last_activity_at` resetting on every request; LOGIN_ATTEMPT has no audit columns; the diagram draws `USER ||--o{ LOGIN_ATTEMPT` with no `user_id` FK (`erd.md:27`). The standard track's dismissal rests on an inference ("Redis-backed ⇒ audit rule N/A") that the artifact never explicitly states. *However*, that inference is not baseless: `erd.md:179` does say these entities generate no ORM model or migration, and `erd.md:226`'s "audit-column contract across all tables" arguably excludes Redis hashes (which are not tables). *(Strengthening the "defensible split" verdict: `erd.md:229` shows the author explicitly added `updated_at` to the mutating MIXPANEL_DEAD_LETTER entity — proving they reasoned about audit columns on mutation, which cuts toward the compressed reading; yet they pointedly did not for the Redis entities, which cuts toward the standard reading. Both are honest reads of an under-specified rule.)* So the correct framing for the lead: **this belongs firmly in the "human required" tier** — the FAIL reading is the safer default, but the question "does the audit-column rule bind non-Postgres logical entities?" is a real spec ambiguity no reviewer can resolve unilaterally, and the reconciler cannot resolve it because the two tracks never meet.

---

## 7. How AI review sits relative to deterministic linters

**The division of labor is sound: deterministic floor + interpretive ceiling. But the floor must be the linters, and the ceiling is exactly the unreliable layer.**

**What the linters own (100% reproducible, never spend AI on it):**
- `ruff` — 120 violations, all stylistic/mechanical (unsorted imports ×36, line length ×35, unused imports ×7), every record carries an auto-fix.
- `mypy` — 92 errors across 26 files (many SQLAlchemy forward-ref / boto3 false positives).
- `bandit` — 0 findings across 3,116 LOC / 44 files (a clean true-negative).
- `pip-audit` — 41 CVE/PYSEC findings across 15 of 182 deps (pyjwt 7, urllib3 6, setuptools 5, pip 4, starlette 4). *Correction applied:* the top-level fix-plan array is empty, but 40 of 41 findings carry populated `fix_versions` — remediation guidance is available per-finding.

These are deterministic, complete within scope, zero-judgment. They are the gold standard, and the backend review correctly honors the design by declining to re-litigate ruff ("all stylistic") and mypy ("false positives"), reserving AI attention for behavior.

**Where AI uniquely adds value no linter can express:**
1. **Semantic security reasoning** — RT-BE-010: the signup uniform-201 fix closed a status-code enumeration oracle but *opened a new timing + Set-Cookie oracle* because the existing-email branch skips argon2/pwned/session-cookie (`2026-06-05-backend-review-full-run6.md:63-66`). Pair this with bandit's `0/3116` true-negative: the deterministic floor found *nothing* in the same code where AI found a real injection-class behavioral defect. That is the hard ceiling of static tooling, in one exhibit.
2. **Interpreting deterministic output** — SEC-BE-016 correctly reads pip-audit's installed-venv vulnerabilities as "venv stale, but pyproject pins already remediate" (a source-vs-artifact distinction a linter cannot make).
3. **Architectural / authz / business-logic findings** — cross-tenant privilege escalation, N+1 and cache reasoning, the Cloudflare-purge "disabled links stay live at edge" consequence chain.

**Two honest corrections to the "AI beats the baseline" narrative:**
- **The backend `baseline.json` is NOT pure linter output** — it is itself a full multi-domain *LLM* review (it contains spec-compliance and erd-compliance semantic findings). So the "LLM layer beats a deterministic preflight" framing is invalid and is dropped: the baseline already *is* an LLM review. The only genuinely net-new LLM finding versus that baseline is the run-4 signup-enumeration vector.
- **The deterministic floor as actually executed has a hole:** `pytest` never ran in any backend run (no live Postgres/Redis), so an entire class of test/coverage blockers is structurally invisible across the whole corpus. The floor covers style/types/AST-security/CVEs — but **not** test coverage, and neither the linters nor the AI filled that gap.

**Bottom line on the relationship:** linters are *more* reliable than AI for what they cover, AND AI is the only thing that catches the authz/tenancy/business-logic/behavioral defects that are the blockers a human reviewer actually cares about — *but those are precisely the categories with ±4-blocker run-to-run discovery variance.* The deterministic floor should be single-run CI-blocking; the interpretive ceiling must be treated as a candidate worklist (union of 2+ runs), never an autonomous verdict.

---

## 8. Reconciled cross-dimension contradictions (audit trail)

For transparency, the contradictions across the source analyses and how this report resolves each:

- **"Zero false positives" vs documented FPs** → Resolved against zero-FP. The claim is an unquantified self-assessment with contradictory denominators (12 vs 18 runs across two docs) and is locally falsified by the compressed PRD-004 hallucination (refuted by `prd.md:27`/`:50` on disk). Precision is high (~85–100%) but not perfect.
- **Verdict-stability as a quality signal** → Resolved as deceptive. Compression is *more* verdict-stable (1/9 flips vs standard's ~3/9) only because a hallucinated/over-determined Gate-1 floor latches `FAIL_CRITICAL` regardless of wildly varying findings. Lower verdict variance here is a symptom of a false-positive floor, not reliability. (Compression is covered in depth in Report 2; flagged here only to correct the stability-as-quality inference.)
- **ERD split: coin-flip vs asymmetric** → Resolved as "interpretive split, FAIL reading more defensible, human-required" (see §6).
- **"Monotonic decay = real fixes" vs the actual ORM series** → Resolved: Migration (7→0→0) and API (6→2→1→0) are monotonic; **ORM is NOT** (14→7→3→**4**→0, rising at the same-day R3→R4 pair — which is itself the noise signal). Backend rises (9→17) before falling. Convergence is mostly real fixes, but the same-day rises are genuine reasoning noise, not fixes.
- **Architecture: "trustworthy reasoning" vs "structural floor artifact"** → Resolved: the *verdict* is stable (structural absence-floor); the *reasoning* (ARCH-027 SSRF) flips in 3 of 6 runs. Both are true; §2 states them separately.
- **Code "more deterministic" vs unverifiable/confounded** → Downgraded to "code *rules* are more mechanical," not "code *reviewers* are less noisy." `backend/` is git-untracked; the on-disk `workspaces.py` stub matches neither run-3 nor run-4's description, proving post-run editing. The frozen-artifact noise baseline (06-01) and the fix-as-you-go code corpus are apples-to-oranges on isolation.

*Limits of this report's evidence: n=2 per cell, single project, no human-expert ground-truth baseline, model identity not held constant across runs, and artifact versions drifted across the three eras (PRD v3→v6, ERD v2→v5, Architecture v1→expanded), confounding some cross-era comparisons. Treat all magnitudes as directional.*
