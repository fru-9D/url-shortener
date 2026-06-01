# Architecture Review — 2026-06-01 (max effort, 34-rule spec)

**Architecture:** `docs/architecture.md` (v1)
**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** max
**Spec version:** 34 rules (ARCH-001..034)
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 7  **Gate 3:** 7

## Lookup

| Location | Coverage gap | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/architecture.md | CORS allowlist policy not declared | ARCH-019 | 2 | blocker |
| docs/architecture.md | HTTP security headers strategy not declared | ARCH-020 | 2 | blocker |
| docs/architecture.md | API versioning scheme not declared | ARCH-022 | 2 | blocker |
| docs/architecture.md | Health check endpoint strategy not declared | ARCH-023 | 2 | blocker |
| docs/architecture.md | Request body / payload size limits not declared | ARCH-024 | 2 | blocker |
| docs/architecture.md | Input validation / DTO boundary policy not declared | ARCH-025 | 2 | blocker |
| docs/architecture.md | Global exception handler details thin (envelope shape declared but no middleware, no stack-trace policy, no exception→status mapping) | ARCH-026 | 2 | blocker |
| docs/architecture.md | Failure-mode runbook scaffolding thin | ARCH-017 | 3 | warning |
| docs/architecture.md | DB connection pool sizing strategy not declared | ARCH-028 | 3 | warning |
| docs/architecture.md | Idempotency policy for mutating endpoints not declared | ARCH-029 | 3 | warning |
| docs/architecture.md | Pagination scheme details (cursor vs offset, max page) not declared | ARCH-030 | 3 | warning |
| docs/architecture.md | Transaction boundary / unit-of-work pattern not declared | ARCH-031 | 3 | warning |
| docs/architecture.md | Graceful shutdown / draining strategy not declared | ARCH-033 | 3 | warning |
| docs/architecture.md | Payload compression strategy not declared | ARCH-034 | 3 | warning |

## Rules considered and dismissed at max effort

The max-effort agent explicitly worked through borderline rules and dismissed them on merit:

- **ARCH-027 (SSRF):** Considered as a potential blocker because the system accepts user URLs. Concluded the system does NOT fetch user-supplied destination URLs server-side (Safe Browsing is a host+path lookup against Google's API; the redirect path returns a 302 and lets the browser follow). Per the rule's stated exemption ("pure redirect services that never fetch the URL are exempt"), dismissed.
- **ARCH-012 (tech-stack justification):** Considered. Concluded that the tier split (edge / regional / async) is justified by the PRD's latency and SLO targets, and the per-tier choices (Cloudflare Workers, FastAPI, Postgres, Redis, SQS) are standard and adequately justified at the tier-decision level. No flagrant unjustified choice.
- **ARCH-032 (correlation IDs):** Considered. Concluded that X-Ray + `X-Amzn-Trace-Id` SQS attribute propagation + `request_id` in logs is adequately specified. Not flagged.

## Comparison vs other effort levels

| Effort | Spec | Findings (G1/G2/G3) | Verdict |
|---|---|---|---|
| Original | 18 rules | 0 / 0 / 4 | PASS_WITH_RISK |
| Low | 34 rules | 0 / 7 / 8 | FAIL_BLOCKER |
| Medium | 34 rules | 0 / 8 / 9 | FAIL_BLOCKER |
| **Max** | **34 rules** | **0 / 7 / 7** | **FAIL_BLOCKER** |

**Delta medium → max:**
- **−1 Gate 2** — ARCH-027 (SSRF) dismissed as exempt. Max correctly recognized the rule's "pure redirect services that never fetch the URL are exempt" clause.
- **−2 Gate 3** — ARCH-012 (tech justification) and ARCH-032 (correlation IDs) dismissed as adequately covered. Max read the architecture more carefully and credited what was there.

**Headline:** Max effort is *more discriminating*, not just more thorough. It correctly identified three borderline rules as adequately covered or exempt where medium effort flagged them defensively. Total findings dropped 17 → 14 with no loss of genuine signal.

This is an important calibration finding — higher effort doesn't monotonically produce more findings. For mature rules where exemption clauses or partial coverage exist in the document, max-effort cognition can distinguish "genuinely missing" from "present but elsewhere" more reliably than medium.
