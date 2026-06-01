# PRD Review — 2026-05-25 (v3)

**File reviewed:** `docs/prd.md` (v3, after targeted fixes for v2's Gate 2 items)
**Verdict:** PASS_WITH_RISK
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 0 findings
**Gate 3 (Warnings):** 9 findings

## Trajectory

| Counter | v1 | v2 | v3 |
|---|---|---|---|
| Gate 1 | 2 | 0 | 0 |
| Gate 2 | 12 | 5 | 0 |
| Gate 3 | 13 | 5 | 9 |
| **Total** | **27** | **10** | **9** |
| Verdict | FAIL_CRITICAL | FAIL_BLOCKER | PASS_WITH_RISK |

Note: Gate 3 ticked up from 5 → 9 between v2 and v3 because **fixing Gate 2 surfaces finer-grained edge cases** that were previously hidden behind larger issues. This is normal review behavior — not a regression.

## v2 → v3 verification

All five Gate 2 items addressed:

| v2 Finding | v3 status |
|---|---|
| "Blocklist" undefined | Fixed — Google Safe Browsing v4, fail-open, override path |
| "Activated Workspace" undefined | Fixed — added to Glossary |
| Pwned Passwords contract missing | Fixed — full subsection, fail-open policy stated |
| Email delivery contract missing | Fixed — AWS SES, sender identity, per-context failure UX |
| MaxMind GeoLite2 contract missing | Fixed — local mmdb, biweekly update, fallback |

## Gate 3 — Warnings

| Location | Defect | Rule |
|---|---|---|
| `docs/prd.md:236` | NFR scale targets absent (RPS, link inventory, click throughput) | PRD-010 |
| `docs/prd.md:240` | "Encrypted at rest" — no key-management mechanism | PRD-010 |
| `docs/prd.md:240` | "OWASP Top-10 baseline" — no concrete controls or verification path | PRD-010 |
| `docs/prd.md` (no §) | Workspace deletion / termination unaddressed | PRD-011 |
| `docs/prd.md:143` | "Lose access immediately" — session revocation mechanism unstated | PRD-011 |
| `docs/prd.md:79` | Concurrent custom-slug submission race unaddressed | PRD-011 |
| `docs/prd.md:59` | Redirect endpoint abuse-protection / rate-limit unaddressed | PRD-011 |
| `docs/prd.md:240` | "Email addresses encrypted at rest" — passive voice, no actor | PRD-012 |
| `docs/prd.md:62` | "the click is recorded" in Flow B — passive, no actor | PRD-012 |

## Summary

PRD is ready to derive an ERD and architecture from. The five Gate 2 fixes were genuine — each rule's intent is now met, not just keyword-matched. Nine Gate 3 warnings remain (five carried forward from v2, four newly visible now that bigger issues are out of the way). None block downstream work; they should be cleaned up in a final polish pass after the ERD and architecture stages, but they do not prevent starting.
