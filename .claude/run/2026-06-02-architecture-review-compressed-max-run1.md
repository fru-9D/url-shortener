# Architecture Review — Compressed Agent — Max Effort — Run 1
**Date:** 2026-06-02
**Agent:** architecture-review-compressed
**Effort:** max
**Project:** Snip (url-shortener)

---

## STEP C — Summary Verdict

```json
{
  "domain": "architecture-review",
  "gate1_count": 3,
  "gate2_count": 4,
  "gate3_count": 10,
  "verdict": "FAIL_CRITICAL"
}
```

---

## Gate 1 — Critical (3)

| ID | Rule | Finding |
|---|---|---|
| ARCH-005-a | ARCH-005 | CORS allowlist includes "branded-domain origins registered per Workspace" — Custom branded domains are explicitly out of scope for v1 per PRD. Creates an unbounded CORS expansion with no concrete constraint beyond one known origin. |
| ARCH-005-b | ARCH-005 | CI/CD pipeline omits SAST tooling — PRD NFR Security requires "OWASP Top-10 2021 baseline, verified by SAST tooling on every release"; CI gate enumerates type-check, lint, tests, OpenAPI diff, Alembic check — no SAST tool named. |
| ARCH-004-a | ARCH-004 | TLS 1.2+ enforcement requirement from PRD NFR not addressed in architecture — no TLS version policy declared at ALB, Cloudflare, ElastiCache, RDS, or inter-service communication level. |

---

## Gate 2 — Blockers (4)

| ID | Rule | Finding |
|---|---|---|
| ARCH-008-a | ARCH-008 | Dashboard scaling strategy not declared — PRD requires p95 < 2s mobile NFR; architecture groups dashboard under Link API autoscale without independent CDN strategy, SSR cache headers, or capacity model for the dashboard tier. |
| ARCH-009-a | ARCH-009 | No timeout declared for AWS SES SDK calls — all other external integrations declare explicit timeouts; SES calls on sign-up verification and password-reset paths have no timeout bound, allowing unbounded blocking on slow SES endpoints. |
| ARCH-010-a | ARCH-010 | ABUSE_REVIEW lacks workspace_id; base-repository tenant enforcement claim is unsatisfied — the architecture declares base-repository auto-AND'es workspace_id but ABUSE_REVIEW has no direct workspace_id column; the architecture does not declare this entity as exempt or describe a join-based filter. |
| ARCH-026-a | ARCH-026 | Error envelope declared only for FastAPI; Cloudflare Worker error surface undefined — PRD Flow B explicitly describes Worker-level failure modes (503 on datastore unreachable); Worker is a separate V8 runtime with no declared error shape, exception handler, or response envelope. |

---

## Gate 3 — Warnings (10)

| ID | Rule | Finding |
|---|---|---|
| ARCH-032-a | ARCH-032 | request_id generation point not declared; propagation into outbound HTTP calls (SES, Safe Browsing, Pwned Passwords) absent; dual-identifier relationship (request_id vs X-Amzn-Trace-Id) unreconciled |
| ARCH-013-a | ARCH-013 | Password-reset, signup, and email-verification endpoints have no declared rate-limit strategy — common vectors for SES quota exhaustion and enumeration |
| ARCH-014-a | ARCH-014 | Application caching deferred with no analysis against p95 < 2s dashboard NFR — "Revisit if needed" transfers verification risk entirely to production |
| ARCH-015-a | ARCH-015 | Staging anonymization method and KMS key separation not declared — given email_ciphertext uses KMS-managed per-row DEKs, anonymization approach is non-trivial; prod/staging CMK separation is ambiguous |
| ARCH-016-a | ARCH-016 | CI/CD lacks dependency vulnerability scanning (OWASP A06:2021 — Vulnerable and Outdated Components); distinct from SAST gap at ARCH-005 |
| ARCH-017-a | ARCH-017 | Login lockout fails open when Redis (single-AZ) is unavailable — failure mode and security consequence not addressed; architecture acknowledges single-AZ risk for cold-starts but not for security controls |
| ARCH-028-a | ARCH-028 | Connection pool sizing declared only for Link API; click consumer/Mixpanel forwarder/mail worker pool sizes excluded — click consumer scales to 50 tasks, potentially exhausting db.r6g.large max_connections |
| ARCH-029-a | ARCH-029 | Mixpanel SQS publish idempotency from click consumer undeclared under at-least-once reprocessing — CLICK insert is idempotent; downstream link_clicked Mixpanel publish may duplicate |
| ARCH-030-a | ARCH-030 | Analytics aggregation query range bounds not declared for CLICK table — cursor pagination covers list endpoints; unbounded time-range aggregation queries possible |
| ARCH-031-a | ARCH-031 | CLICK insert → SQS:mixpanel crash-window recovery path not declared — acknowledged crash window for link_create→Mixpanel; parallel gap for click_consumer→Mixpanel publish not addressed |
| ARCH-012-a | ARCH-012 | Next.js and FastAPI tech-stack choices lack stated alternatives considered (borderline Gate 3) |

---

## STEP A-bis — Dismissal Table (abbreviated)

All 34 rules considered. Rules dismissed: ARCH-001 (auth fully declared), ARCH-002 (secrets fully declared), ARCH-003 (backup fully declared), ARCH-006 (observability fully declared), ARCH-007 (all async work behind queues), ARCH-009 (partial — SES timeout gap flagged), ARCH-011 (migrations fully declared), ARCH-018 (frontend/backend contract fully declared), ARCH-019 (CORS declared — branded-domain inconsistency at ARCH-005), ARCH-020 (HTTP headers fully declared), ARCH-021 (cookie flags fully declared), ARCH-022 (versioning fully declared), ARCH-023 (health checks fully declared), ARCH-024 (body limits declared), ARCH-025 (input validation declared), ARCH-033 (graceful shutdown fully declared), ARCH-034 (compression fully declared).
