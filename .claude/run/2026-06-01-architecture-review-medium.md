# Architecture Review — 2026-06-01 (medium effort, 34-rule spec)

**Architecture:** `docs/architecture.md` (v1)
**PRD:** `docs/prd.md` (v3)
**ERD:** `docs/erd.md` (v2)
**Effort:** medium
**Spec version:** 34 rules (ARCH-001..034)
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 8  **Gate 3:** 9

## Lookup

| Location | Coverage gap | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/architecture.md | CORS allowlist policy not declared | ARCH-019 | 2 | blocker |
| docs/architecture.md | HTTP security headers strategy not declared | ARCH-020 | 2 | blocker |
| docs/architecture.md | API versioning scheme not declared | ARCH-022 | 2 | blocker |
| docs/architecture.md | Health check / readiness / liveness endpoints not declared | ARCH-023 | 2 | blocker |
| docs/architecture.md | Request body / payload size limits not declared | ARCH-024 | 2 | blocker |
| docs/architecture.md | Input validation / DTO boundary policy not declared | ARCH-025 | 2 | blocker |
| docs/architecture.md:156 | Global exception handler / envelope details thin (no `request_id`, no stack-trace policy, no exception→status mapping) | ARCH-026 | 2 | blocker |
| docs/architecture.md:107 | SSRF posture not explicitly declared — system doesn't fetch user URLs server-side today, but the architecture should say so | ARCH-027 | 2 | blocker |
| docs/architecture.md | Tech-stack justifications (Cloudflare Workers, FastAPI, SQS, Postgres-for-clicks) not recorded | ARCH-012 | 3 | warning |
| docs/architecture.md | Failure-mode scaffolding / runbooks not enumerated | ARCH-017 | 3 | warning |
| docs/architecture.md | DB connection pool size / `max_connections` math not declared | ARCH-028 | 3 | warning |
| docs/architecture.md | Idempotency policy for mutations and at-least-once SQS consumers not declared | ARCH-029 | 3 | warning |
| docs/architecture.md | Pagination scheme (cursor vs offset, defaults) not declared | ARCH-030 | 3 | warning |
| docs/architecture.md | Transaction boundary / unit-of-work pattern and transactional outbox not declared | ARCH-031 | 3 | warning |
| docs/architecture.md:112 | Correlation ID propagation end-to-end not fully declared (header name, SQS attributes, outbound forwarding) | ARCH-032 | 3 | warning |
| docs/architecture.md | Graceful shutdown / draining strategy (SIGTERM, stopTimeout, queue drain) not declared | ARCH-033 | 3 | warning |
| docs/architecture.md | Payload compression strategy (gzip/brotli, where, threshold) not declared | ARCH-034 | 3 | warning |

## Rules that PASSED

ARCH-001 (auth), ARCH-002 (secrets), ARCH-003 (backup/recovery), ARCH-004 (compliance), ARCH-005 (no PRD contradiction), ARCH-006 (observability), ARCH-007 (async), ARCH-008 (scaling), ARCH-009 (external API resilience), ARCH-010 (multi-tenant isolation), ARCH-011 (migrations), ARCH-013 (rate limiting), ARCH-014 (caching), ARCH-015 (environments), ARCH-016 (CI/CD), ARCH-018 (FE/BE contract), ARCH-021 (cookie flags).

## Comparison vs other effort levels

| Effort | Spec | Findings (G1/G2/G3) | Verdict |
|---|---|---|---|
| Original | 18 rules | 0 / 0 / 4 | PASS_WITH_RISK |
| Low (today) | 34 rules | 0 / 7 / 8 | FAIL_BLOCKER |
| **Medium (today)** | **34 rules** | **0 / 8 / 9** | **FAIL_BLOCKER** |

**Delta low → medium:**
- **+1 Gate 2** — ARCH-027 (SSRF). The medium-effort agent took the position that the architecture should explicitly state the no-server-side-fetch posture (even though the redirect path doesn't fetch URLs, the absence of a stated SSRF defense at architecture stage tends to result in "let's add OG-image preview" creep at code stage without an egress allowlist).
- **+1 Gate 3** — ARCH-012 (tech-stack justification × 4 choices bundled). Low effort accepted the per-tier rationale as adequate justification; medium effort wants explicit ADR-style records for Cloudflare Workers vs alternatives, FastAPI vs alternatives, SQS vs alternatives, and Postgres-for-clicks vs ClickHouse/Timestream.

**Headline:** medium effort identified one more architectural posture gap (SSRF) and re-raised the stack-justification concern from the original 18-rule run. The verdict stays at FAIL_BLOCKER but the picture is now more complete: 17 findings, all genuine, all addressable by an architectural-update pass.
