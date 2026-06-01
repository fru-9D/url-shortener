---
name: architecture-review
description: Stage-3 review — judge the architecture document against the PRD and ERD for coverage of NFRs, cross-cutting concerns, and compliance constraints before implementation begins. No arguments.
---

You are the architecture review orchestrator. You run in the main conversation (you have the `Agent` tool). You invoke the single `architecture-review` agent, build a report, and write it to disk.

---

## CRITICAL CONSTRAINTS

**This command does NOT modify the architecture doc, PRD, or ERD.** Read-only review.

**This command does NOT enforce preflight.** Skip every preflight concern.

**Exactly one agent.** Only `architecture-review`. No fan-out.

**Judgment vs preference:** The agent flags absences and contradictions, not stylistic differences. If the user pushes back on a finding as a matter of taste rather than correctness, take that pushback at face value — re-read the rule and decide whether it actually applies.

---

## Phase 1 — Context gathering

1. Detect repo root by locating `package.json`, `pyproject.toml`, or `.git/`.
2. Read `review.config.json` from repo root if present.
3. **Locate the architecture doc.**
   - First: `stages.architecture.path` from the config.
   - Otherwise: `docs/architecture.md` (default).
   - Fallbacks in order: `ARCHITECTURE.md`, `architecture.md`, `docs/ARCHITECTURE.md`, `docs/design.md`.
4. **Locate the PRD** — same logic as `/prd-review` Phase 1.
5. **Locate the ERD** — same logic as `/erd-review` Phase 1 (config first, then auto-discover Mermaid `erDiagram` block).
6. **Skip conditions:**
   - No architecture doc found → `Architecture review skipped: no architecture document found.` (stop; no agent; no report.)
   - Architecture doc found but no PRD → continue. Pass an empty PRD section to the agent and instruct it to mark findings that depend on PRD context as "skipped (no PRD)" rather than emitting them as findings.
   - Architecture doc found but no ERD → continue. Same handling.
7. Read all available files in full. Record resolved paths.

---

## Phase 2 — Dispatch the agent

Spawn one `Agent` call with `subagent_type: "architecture-review"`.

The dispatch prompt must include:
- A one-paragraph framing ("Review the architecture document at `<arch-path>` against the PRD at `<prd-path>` and the ERD at `<erd-path>` using the rules in your agent spec…").
- The full architecture document content, fenced.
- The full PRD content (or a placeholder noting it is absent).
- The full ERD content (or a placeholder noting it is absent).
- The resolved file paths.
- A reminder to emit STEP A / STEP B / STEP C per the agent's output contract at `.claude/agents/review/stages/architecture.md`.

---

## Phase 3 — Receive findings

Same handling as the previous stage reviewers. If the agent returns a `note` indicating it skipped, forward and stop.

---

## Phase 4 — Build report

```
# Architecture Review — <YYYY-MM-DD>

**Architecture:** `<resolved arch path>`
**PRD:** `<resolved PRD path or "not found">`
**ERD:** `<resolved ERD path or "not found">`
**Verdict:** <PASS | PASS_WITH_RISK | FAIL_BLOCKER | FAIL_CRITICAL>
**Gate 1 (Critical):** <N> findings
**Gate 2 (Blockers):** <N> findings
**Gate 3 (Warnings):** <N> findings

## Lookup
<paste agent's STEP A lookup table>

## Gate 1 — Critical (architecture not safe to implement against)

**MANDATORY:** Every Gate 1 finding listed individually.

### [<RULE-ID>] — <short description>
**Location:** `<file>:<line>` (or "architecture-wide" if line is 0)
**Finding:** <message>
**Fix:** <fix>
**Effort:** <low | medium | high>

## Gate 2 — Blockers (will surface as production incidents)

<same shape>

## Gate 3 — Warnings (soft spots)

<same shape>

## Summary

<2-3 sentences: the highest-priority coverage gap, the single concern most likely to become a production incident, and whether the architecture is safe to start building against.>
```

---

## Phase 5 — Write report

1. Read `output.directory` from `review.config.json` (default `.claude/run`).
2. Build filename: `<YYYY-MM-DD>-architecture-review.md`.
3. Use the **Write tool** to save the report at `<directory>/<filename>`. Mandatory.

---

## Phase 6 — Emit to user

Print the full report Markdown, then on a final line: `Report saved to <path>`.
