---
name: erd-review
description: Stage-2 review — judge the project's Mermaid `erDiagram` against the PRD for coverage, correctness, and operational fitness. No arguments.
---

You are the ERD review orchestrator. You run in the main conversation (you have the `Agent` tool). You invoke the single `erd-review` agent, build a report, and write it to disk.

**This reviewer is distinct from `be-erd-compliance`.** `be-erd-compliance` runs inside `/backend-review` and compares ORM models to the ERD. This command compares the PRD to the ERD — it answers "does the diagram cover what the PRD requires?", not "does the code match the diagram?".

---

## CRITICAL CONSTRAINTS

**This command does NOT modify the ERD or PRD.** Read-only review.

**This command does NOT enforce preflight.** Skip every preflight concern.

**Exactly one agent.** Only `erd-review`. No fan-out.

---

## Phase 1 — Context gathering

1. Detect repo root by locating `package.json`, `pyproject.toml`, or `.git/`.
2. Read `review.config.json` from repo root if present.
3. **Locate the PRD.** Same logic as `/prd-review` Phase 1: `stages.prd.path` first, then `docs/prd.md`, then fallbacks `PRD.md`, `prd.md`, `docs/PRD.md`, `requirements.md`.
4. **Locate the ERD.**
   - First: `stages.erd.path` from `review.config.json`.
   - Otherwise: auto-discover — scan markdown files at repo root, under `docs/`, and at frontend / backend roots if configured, for any `mermaid` fenced code block whose first non-blank line is `erDiagram`. Use the same logic as `be-erd-compliance.md` Step 1.
   - Common candidate paths to check explicitly: `docs/erd.md`, `docs/ERD.md`, `ERD.md`, `docs/database.md`.
5. **Skip conditions** (mirror the agent's skip behavior — print a one-line notice and stop, do not spawn the agent, do not write a report):
   - No PRD AND no ERD found → `ERD review skipped: neither PRD nor ERD found.`
   - PRD found, ERD missing → `ERD review skipped: PRD found but no Mermaid erDiagram detected.`
   - ERD found, PRD missing → `ERD review skipped: ERD found but no PRD found — cannot evaluate ERD coverage without a PRD.`
6. Read both files in full. Record resolved paths for each.

---

## Phase 2 — Dispatch the agent

Spawn one `Agent` call with `subagent_type: "erd-review"`.

The dispatch prompt must include:
- A one-paragraph framing ("Compare the ERD at `<erd-path>` against the PRD at `<prd-path>` using the rules in your agent spec…").
- The full PRD content, fenced as markdown.
- The full ERD content, fenced as markdown (preserve the embedded ```mermaid block).
- The resolved file paths for both.
- A reminder to emit STEP A / STEP B / STEP C per the agent's output contract at `.claude/agents/review/stages/erd.md`.

---

## Phase 3 — Receive findings

Same handling as `/prd-review` Phase 3. If the agent returns a `note` indicating it skipped, forward and stop.

---

## Phase 4 — Build report

```
# ERD Review — <YYYY-MM-DD>

**PRD:** `<resolved PRD path>`
**ERD:** `<resolved ERD path>`
**Verdict:** <PASS | PASS_WITH_RISK | FAIL_BLOCKER | FAIL_CRITICAL>
**Gate 1 (Critical):** <N> findings
**Gate 2 (Blockers):** <N> findings
**Gate 3 (Warnings):** <N> findings

## Lookup
<paste agent's STEP A lookup table>

## Gate 1 — Critical (ERD not safe to derive ORM models from)

**MANDATORY:** Every Gate 1 finding listed individually.

### [<RULE-ID>] — <short description>
**Location:** `<file>:<line>`
**Finding:** <message>
**Fix:** <fix>
**Effort:** <low | medium | high>

## Gate 2 — Blockers (material gaps)

<same shape>

## Gate 3 — Warnings (soft spots)

<same shape>

## Summary

<2-3 sentences: the highest-priority mismatch, the single most expensive defect if it reaches code, and whether the ERD is safe to start building ORM models against.>
```

---

## Phase 5 — Write report

1. Read `output.directory` from `review.config.json` (default `.claude/run`).
2. Build filename: `<YYYY-MM-DD>-erd-review.md`.
3. Use the **Write tool** to save the report at `<directory>/<filename>`. Mandatory.

---

## Phase 6 — Emit to user

Print the full report Markdown, then on a final line: `Report saved to <path>`.
