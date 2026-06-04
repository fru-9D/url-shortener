# ERD Review — Compressed Agent — Medium Effort — Run 2
**Date:** 2026-06-02
**Agent:** erd-review-compressed
**Effort:** medium
**Project:** Snip (url-shortener)

---

## STEP A — Findings Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| USER entity (PRD §Account — "5 failed attempts per email per 15 minutes triggers a 15-minute lockout") | Failed-login throttling requires per-email state (attempt count, window start, lockout expiry) that has no structural home. USER has `last_login_at` only. No `failed_login_count`, `locked_until`, no LOGIN_ATTEMPT entity, and no Notes acknowledgment of where this state lives (e.g., Redis). | ERD-PRD-001 | G1 | Critical |
| USER entity (PRD §Account — "7-day idle expiry"; §Teams — "active sessions invalidated immediately") | Session idle-expiry is a per-session property. USER.last_login_at is updated on every login across all sessions, making it impossible to enforce 7-day idle expiry independently per concurrent session. No SESSION entity, no per-token `last_used_at`, and no Notes acknowledgment of an external TTL mechanism. `session_version` only handles mass-invalidation, not per-session idle tracking. | ERD-PRD-001 | G1 | Critical |
| CLICK entity (PRD §Click pipeline — "idempotent on (link_id, clicked_at)") | PRD guarantees idempotency on `(link_id, clicked_at)`. No unique or partial-unique constraint on this column pair is declared in the ERD or Notes. Without a DB-level constraint, duplicate click rows can be inserted by concurrent consumers, violating the at-most-once semantic. | ERD-PRD-009 | G2 | Blocker |
| `USER ||--o{ ABUSE_REVIEW` relationship line | ERD draws `||` (mandatory) on the USER side, implying reviewer_id is non-nullable. ERD Notes explicitly state "reviewer_id is nullable until a reviewer acts." The cardinality notation directly contradicts the entity's own Notes and will mislead implementors into applying a NOT NULL constraint that blocks inserting an unreviewed abuse flag. | ERD-PRD-013 | G3 | Warning |
| `USER ||--o{ WORKSPACE` relationship line | ERD draws `||--o{` (zero-or-many workspaces per user). PRD §Teams states "A signed-in Member who already belongs to a Workspace cannot create an additional Workspace" — v1 cardinality should be `||--o|` (zero-or-one). Overstates permitted multiplicity; could cause migration authors to omit a uniqueness constraint on WORKSPACE.owner_id. | ERD-PRD-004 | G3 | Warning |
| WORKSPACE_MEMBER entity naming | PRD Glossary defines "Member" as the system-of-record term. ERD entity is named `WORKSPACE_MEMBER`. Minor naming divergence from canonical PRD vocabulary. | ERD-PRD-010 | G3 | Warning |
| CLICK entity (PRD §Data retention — 13-month rolling; §Click pipeline — throughput sizing) | CLICK is an append-only, high-throughput event table with 13-month rolling retention. ERD Notes acknowledge retention via scheduled job but document no partitioning strategy or archival approach for what is potentially the largest table in the system. | ERD-PRD-020 | G3 | Warning |

---

## STEP A-bis — Rule Disposition Table

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ERD-PRD-001 | Yes — 2 findings | G1-1: Login throttle state missing. G1-2: Per-session idle-expiry state missing. |
| ERD-PRD-002 | Yes — no finding | All PRD-described relationships have ERD lines. |
| ERD-PRD-003 | Yes — no finding | ERD Notes §Email encryption documents AES-256-GCM/KMS handling for all PII columns. |
| ERD-PRD-004 | Yes — 1 G3 warning | USER ||--o{ WORKSPACE overstates v1 cardinality. |
| ERD-PRD-005 | Yes — no finding | All entities have created_at + updated_at except CLICK (append-only, documented in Notes). |
| ERD-PRD-006 | Yes — no finding | LINK, INVITE, WORKSPACE_MEMBER, CLICK all carry workspace_id FK. Other entities are system-level by design. |
| ERD-PRD-007 | Yes — no finding | LINK has deleted_at and disabled_at. INVITE has status. WORKSPACE_MEMBER has removed_at. All lifecycle signals present. |
| ERD-PRD-008 | Yes — no finding | No monetary amounts in v1. |
| ERD-PRD-009 | Yes — 1 G2 finding | CLICK idempotency key (link_id, clicked_at) has no unique constraint. All other uniqueness requirements covered or Notes-documented. |
| ERD-PRD-010 | Yes — 1 G3 warning | WORKSPACE_MEMBER diverges from PRD canonical term "Member." |
| ERD-PRD-011 | Yes — no finding | All ERD entities trace to PRD. No orphans. |
| ERD-PRD-012 | Yes — no finding | Notes §Enums documents all closed value sets. Skip condition satisfied. |
| ERD-PRD-013 | Yes — 1 G3 warning | ABUSE_REVIEW cardinality contradicts Notes on nullable reviewer_id. |
| ERD-PRD-014 | Yes — no finding | No many-to-many lines. WORKSPACE_MEMBER is explicit junction entity. |
| ERD-PRD-015 | Yes — no finding | No multi-currency in v1. |
| ERD-PRD-016 | Yes — no finding | All PKs are uuid type. |
| ERD-PRD-017 | Yes — no finding | LINK.owner_id covers creator attribution. Audit logs out of scope. |
| ERD-PRD-018 | Yes — no finding | PRD does not describe concurrent editing of shared resources. |
| ERD-PRD-019 | Yes — no finding | No Workspace deletion scenario in v1. Member removal uses soft-removal. |
| ERD-PRD-020 | Yes — 1 G3 warning | CLICK is high-throughput append-only; no partitioning strategy documented. |
| ERD-PRD-021 | Yes — no finding | No multi-valued columns. All collections normalized. |

---

## STEP B — JSON Findings Array

```json
[
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-001",
    "gate": 1,
    "severity": "CRITICAL",
    "entity": null,
    "line": 0,
    "prd_section": "§Account — Failed-login throttling",
    "finding": "Failed-login throttling (5 attempts per email per 15 minutes → 15-minute lockout) is a first-class operational requirement with no structural home. No failed_login_count, locked_until, no LOGIN_ATTEMPT entity, no Notes acknowledgment of external state."
  },
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-001",
    "gate": 1,
    "severity": "CRITICAL",
    "entity": "USER",
    "line": 0,
    "prd_section": "§Account — Sessions 7-day idle; §Teams — immediate invalidation",
    "finding": "Session idle-expiry (7-day) is per-session but USER.last_login_at is a single scalar updated on every login. Per-session idle tracking requires a SESSION entity or per-token last_used_at. No Notes acknowledgment of external TTL mechanism."
  },
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-009",
    "gate": 2,
    "severity": "BLOCKER",
    "entity": "CLICK",
    "line": 0,
    "prd_section": "§Click pipeline — 'idempotent on (link_id, clicked_at)'",
    "finding": "No unique constraint on (link_id, clicked_at) in ERD or Notes. At-least-once SQS delivery means duplicates are expected; without a DB-level constraint the idempotency guarantee is application-only and breakable under concurrent consumers."
  },
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-013",
    "gate": 3,
    "severity": "WARNING",
    "entity": "ABUSE_REVIEW",
    "line": 24,
    "prd_section": "ERD Notes §Abuse review — 'reviewer_id nullable until a reviewer acts'",
    "finding": "ERD relationship 'USER ||--o{ ABUSE_REVIEW' implies reviewer_id is non-nullable. Notes explicitly state reviewer_id is nullable. Direct contradiction; implementors applying the diagram will add a NOT NULL constraint that breaks inserting an unreviewed abuse flag."
  },
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-004",
    "gate": 3,
    "severity": "WARNING",
    "entity": "WORKSPACE",
    "line": 12,
    "prd_section": "§Teams — 'exactly one Workspace in v1'",
    "finding": "USER ||--o{ WORKSPACE (zero-or-many) overstates v1 cardinality. PRD says at most one workspace per user in v1. Should be ||--o| without a Notes callout justifying the forward-compatibility choice."
  },
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-010",
    "gate": 3,
    "severity": "WARNING",
    "entity": "WORKSPACE_MEMBER",
    "line": 0,
    "prd_section": "§Glossary — 'Member'",
    "finding": "PRD canonical term is 'Member'; ERD uses WORKSPACE_MEMBER. Minor but requires mapping in developer onboarding."
  },
  {
    "domain": "erd-review",
    "rule_id": "ERD-PRD-020",
    "gate": 3,
    "severity": "WARNING",
    "entity": "CLICK",
    "line": 0,
    "prd_section": "§Data retention — 13 months rolling; §Click pipeline — throughput sizing",
    "finding": "CLICK is append-only, high-throughput with 13-month rolling retention. ERD Notes acknowledge retention via scheduled job but document no partitioning or archival strategy for potentially the largest table in the system."
  }
]
```

---

## STEP C — Summary Verdict

```json
{
  "domain": "erd-review",
  "gate1_count": 2,
  "gate2_count": 1,
  "gate3_count": 4,
  "verdict": "FAIL_CRITICAL"
}
```
