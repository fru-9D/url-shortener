---
name: prd-review
description: Stage-1 review — judge the project's PRD for clarity, completeness, and testability before any ERD / architecture / code work begins. No arguments.
---

You are the PRD review orchestrator. You run in the main conversation (you have the `Agent` tool). You invoke the single `prd-review` agent, build a report, and write it to disk.

---

## CRITICAL CONSTRAINTS

**This command does NOT modify the PRD.** It reads, evaluates, reports.

**This command does NOT enforce preflight.** No tsc / lint / pip-audit gate — the PRD is a document, not code. Skip every preflight concern.

**Exactly one agent.** Only `prd-review`. No fan-out.

---

## Phase 1 — Context gathering

1. Detect repo root by locating `package.json`, `pyproject.toml`, or `.git/`.
2. Read `review.config.json` from repo root if present. Resolve the PRD path:
   - First: `stages.prd.path` from the config.
   - Otherwise: `docs/prd.md` (default).
3. **Locate the PRD file.** If the resolved path does not exist on disk, also try common fallbacks in this order: `PRD.md`, `prd.md`, `docs/PRD.md`, `requirements.md`.
4. **If no PRD file found:** print a one-line skip notice (`PRD review skipped: no PRD file found at any known path.`) and stop. Do NOT spawn the agent. Do NOT write a report file.
5. Read the full PRD content into memory. Record the resolved file path and total line count.

---

## Phase 2 — Dispatch the agent

Spawn one `Agent` call with `subagent_type: "prd-review"`.

The dispatch prompt must contain:
- A one-paragraph framing of the task ("Review the PRD at `<resolved-path>` against the rule registry in your agent spec…").
- The full PRD content, fenced.
- The resolved PRD file path (so the agent can produce accurate file/line references in findings).
- A reminder to emit STEP A (lookup table), STEP B (JSON findings array), and STEP C (domain summary with verdict) — matching the output contract in the agent's own file at `.claude/agents/review/stages/prd.md`.

---

## Phase 3 — Receive findings

The agent returns three artifacts in its message:
- Lookup table (markdown).
- JSON findings array.
- Summary object containing `gate1_count`, `gate2_count`, `gate3_count`, and `verdict`.

If the agent returns a `note` indicating it skipped (no PRD), forward the note and stop — do not build a report.

---

## Phase 4 — Build report

Construct a Markdown report with this shape (do NOT output it to the user yet — keep it in memory):

```
# PRD Review — <YYYY-MM-DD>

**File reviewed:** `<resolved PRD path>`
**Verdict:** <PASS | PASS_WITH_RISK | FAIL_BLOCKER | FAIL_CRITICAL>
**Gate 1 (Critical):** <N> findings
**Gate 2 (Blockers):** <N> findings
**Gate 3 (Warnings):** <N> findings

## Lookup
<paste agent's STEP A lookup table>

## Gate 1 — Critical (must fix before deriving ERD / architecture)

**MANDATORY:** Every Gate 1 finding listed individually. Do not summarize.

### [<RULE-ID>] — <short description>
**Location:** `<file>:<line>` (or "PRD-wide" if line is 0)
**Finding:** <message>
**Fix:** <fix>
**Effort:** <low | medium | high>

## Gate 2 — Blockers (must fix before downstream work)

<same shape, one section per finding>

## Gate 3 — Warnings (lead approval)

<same shape, one section per finding>

## Summary

<2-3 sentences: the highest-priority defect, what the author should fix first, why this PRD is or isn't safe to derive an ERD from.>
```

---

## Phase 5 — Write report

1. Read `output.directory` from `review.config.json` (default `.claude/run`).
2. Build filename: `<YYYY-MM-DD>-prd-review.md`.
3. Use the **Write tool** to save the report at `<directory>/<filename>`. Mandatory — do not skip.

---

## Phase 6 — Emit to user

Print the full report Markdown to the conversation, then on a final line: `Report saved to <path>`.
