# Architecture Review — 2026-05-25 (v1)

**Architecture:** `docs/architecture.md` (v1)
**PRD:** `docs/prd.md` (v3, PASS_WITH_RISK)
**ERD:** `docs/erd.md` (v2, PASS)
**Verdict:** PASS_WITH_RISK
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 4 findings

## Lookup

| Location | Coverage gap | Rule ID | Gate | Severity |
|---|---|---|---|---|
| docs/architecture.md:69 | Postgres-for-everything chosen with no stated alternatives or trade-off (CLICK co-located with OLTP in same cluster) | ARCH-012 | 3 | warning |
| docs/architecture.md:12 | FastAPI / Next.js / ECS Fargate runtime decisions unjustified | ARCH-012 | 3 | warning |
| docs/architecture.md:12 | Single-region (us-east-1) choice without rationale or acknowledgment of ex-US dashboard latency trade-off | ARCH-012 | 3 | warning |
| docs/architecture.md (no §) | No system-level failure-mode / runbook scaffolding (DB outage, Redis outage, SQS outage, viral-link hot-key, KMS unavailable) | ARCH-017 | 3 | warning |

## Gate 3 — Warnings

### [ARCH-012] — Postgres-for-everything unjustified
**Location:** `docs/architecture.md:69`
**Finding:** Postgres is selected as primary OLTP store, click event store, and analytics replica target without any statement of why. CLICK is the highest-volume table (13-month rolling retention, every redirect writes one row) and shares a cluster with OLTP workloads — non-trivial trade-offs that future maintainers cannot rederive.
**Fix:** Add a short justification paragraph naming alternatives considered (DynamoDB for clicks, separate analytics store) and why Postgres-for-everything was preferred for v1.
**Effort:** low

### [ARCH-012] — Stack choices unjustified
**Location:** `docs/architecture.md:12`
**Finding:** FastAPI/Python, Next.js, and ECS Fargate appear as decisions without rationale. PRD has no constraint forcing Python or Next.js; future maintainers cannot rederive why these over alternatives.
**Fix:** Add a "Stack decisions" subsection (or ADR links) summarizing the rationale for each.
**Effort:** low

### [ARCH-012] — Single-region choice unjustified
**Location:** `docs/architecture.md:12`
**Finding:** us-east-1 is selected with no rationale. PRD targets dashboard p95 < 2s globally on mid-tier mobile 4G — a US-only origin is a non-trivial latency commitment for non-US users that should be acknowledged.
**Fix:** Add a paragraph stating the choice's rationale and the dashboard-latency trade-off for ex-US users, plus the future multi-region path.
**Effort:** low

### [ARCH-017] — No system-level failure-mode scaffolding
**Location:** `docs/architecture.md` (architecture-wide)
**Finding:** Per-integration resilience and alerting thresholds are documented, but system-level degraded-mode behaviors are not enumerated — Postgres primary unavailable, Redis/ElastiCache unavailable, SQS unavailable, connection-pool exhaustion, cache stampede on a viral short_code, KMS unavailable. ElastiCache single-AZ is acknowledged as an open question without documenting the cold-start degradation. Without this scaffolding, on-call will improvise during the first real incident.
**Fix:** Add a "Failure modes and degraded operation" section enumerating each failure, the documented degraded behavior, and the user-visible impact. Pairs with the existing PagerDuty alert list.
**Effort:** medium

## What the reviewer chose not to flag

The agent explicitly considered and rejected several borderline findings on merit:

- **ARCH-005 (PRD contradiction).** Single-primary Postgres in us-east-1 + cold-cache redirect Worker fetching from there could be read as contradicting the global p95 < 100ms target. Not flagged because the edge cache absorbs the vast majority of reads and the architecture explicitly relies on that mechanism.
- **ARCH-012 bundling.** FastAPI + Next.js + ECS Fargate are three nominally separate choices but conceptually one stack decision; the agent bundled them into a single finding rather than firing three.

## Summary

The architecture is safe to implement against. Auth, secrets, backups, compliance posture, observability, async boundaries, scaling, external-API resilience, multi-tenant enforcement, and migrations are all explicitly addressed. The four Gate 3 warnings concern long-term maintainability (decision documentation) and operational readiness (runbook scaffolding) — they should be addressed before production launch but do not block starting implementation.
