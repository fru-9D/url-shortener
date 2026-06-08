# API Skeleton Review — 2026-06-07

**Architecture:** `docs/architecture.md`
**Routes reviewed:** `backend/app/main.py`, `backend/app/routers/{health,auth,workspaces,links,analytics,abuse}.py` (with `dependencies.py`, `middleware.py`, `schemas/` for context)
**PRD:** `docs/prd.md`
**Reconciled from:** 2 independent reviewer runs
**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 1 finding
**Gate 3 (Warnings):** 2 findings

## Lookup
| Location | Finding | Rule ID | Gate | Severity |
|----------|---------|---------|------|----------|
| backend/app/routers/workspaces.py:277 | invite-accept implemented as `POST` while architecture §Idempotency specifies an idempotent `PATCH` on the token hash; method locks into the generated client, POST→PATCH later is breaking | API-SKEL-007 | 2 | blocker |
| backend/app/routers/workspaces.py:277 | `POST /v1/invites/accept` embeds an action verb in the path, off the canonical `/v1/workspaces/{id}/invites` collection; non-RESTful | API-SKEL-011 | 3 | warning |
| backend/app/routers/workspaces.py:324 | `POST /v1/invites/decline` embeds an action verb in the path, same non-RESTful pattern as accept | API-SKEL-011 | 3 | warning |

## Dismissed rules
| Rule ID | Considered? | Dismissal reason |
|---------|-------------|------------------|
| API-SKEL-001 | Yes | Every architecture-declared resource group has a router: Links (`links.py`), Workspaces/Invites/Members (`workspaces.py`), Auth/Account (`auth.py`), Analytics (`analytics.py`), Abuse review queue (`abuse.py`), Health (`health.py`). The redirect `GET /<short-code>` is the edge-tier Cloudflare Worker per architecture §Overview, correctly not in the FastAPI Link API. |
| API-SKEL-002 | Yes | All non-public routes carry an auth dependency (`MemberDep`/`AdminDep`/`AuthDep`); public endpoints (signup, login, forgot/reset/verify-email, invite decline, `/healthz`, `/readyz`) are correctly dependency-free. `delete_workspace` (workspaces.py:45) is the one mutating route with no auth dependency, but it unconditionally raises `NotImplementedError`/501 with zero reachable logic — no auth bypass — and architecture §Open questions defers workspace deletion. (Add `AdminDep` when implemented.) |
| API-SKEL-003 | Yes | Every body-returning handler declares `response_model` (LinkResponse, LinkListResponse, WorkspaceResponse, MemberResponse, MemberListResponse, InviteResponse, UserResponse, LinkAnalyticsResponse, AbuseReview*Response, HealthResponse, ReadyzResponse). 204 handlers return `None` and correctly omit a model; no raw ORM objects returned. |
| API-SKEL-004 | Yes | Every POST/PUT/PATCH with a body binds a Pydantic model (CreateLinkRequest, UpdateLinkRequest, CreateWorkspaceRequest, InviteRequest, UpdateRoleRequest, AcceptInviteRequest, Signup/Login/PasswordReset*/ChangePassword, UpdateAbuseReviewRequest). No `request.json()`/bare `dict`; `verify_email` takes a typed `Query` token (documented choice). |
| API-SKEL-005 | Yes | All collection GETs paginate: `list_links`, `list_members`, `list_abuse_reviews` accept `after` (cursor) + `page_size` (ge=1, le=200), matching architecture §Pagination (max 200). |
| API-SKEL-006 | Yes | Every Link API router carries the `/v1` prefix; `/healthz` and `/readyz` are intentionally unversioned infra-probe paths per architecture §Health check endpoints. |
| API-SKEL-008 | Yes | All six routers (health, auth, workspaces, links, analytics, abuse) are registered via `app.include_router` in `main.py:79-84`. |
| API-SKEL-009 | Yes | Every router declares `tags` (links, workspaces, auth, analytics, ops, health). |
| API-SKEL-010 | Yes | Every resource-creation POST declares `status_code=201` (`POST /v1/links`, `/v1/workspaces`, `/v1/workspaces/{id}/invites`, `/v1/auth/signup`); accept/decline are token actions returning 204. The `delete_workspace` stub omits `status_code` but is a DELETE, not a creation POST — rule does not apply (observation only). |

## Gate 1 — Critical (skeleton not safe to build business logic on top of)

_None._

## Gate 2 — Blockers (will require breaking changes to fix later)

### [API-SKEL-007] — invite-accept method contradicts the architecture (POST vs PATCH)
**Location:** `backend/app/routers/workspaces.py:277`
**Finding:** Architecture §Idempotency specifies invite-accept as a naturally-idempotent `PATCH` on the token hash (no `Idempotency-Key` needed); the handler implements `POST /v1/invites/accept`. Generated clients/types will treat accept as a non-idempotent create, and a retry after a dropped 204 could re-run the accept handler. The HTTP method is locked into the OpenAPI-derived TypeScript client the dashboard consumes — changing POST→PATCH after types ship is a breaking change.
**Fix:** Expose invite-accept as `PATCH` on the invite/token-hash resource per §Idempotency, or amend the architecture to specify POST as the intended contract.
**Effort:** low

## Gate 3 — Warnings

### [API-SKEL-011] — verb-in-path on invite accept
**Location:** `backend/app/routers/workspaces.py:277`
**Finding:** The path embeds an action verb and fragments the invite resource across two path families (`/v1/invites/accept` vs `/v1/workspaces/{id}/invites`); the RESTful shape is a method against the invite/token resource.
**Fix:** Express acceptance as a `PATCH` state transition on the invite resource keyed by token under one canonical path family, e.g. `PATCH /v1/invites/{token_hash}` with the new status in the body.
**Effort:** medium

### [API-SKEL-011] — verb-in-path on invite decline
**Location:** `backend/app/routers/workspaces.py:324`
**Finding:** Same non-RESTful verb-in-path pattern as accept: `/v1/invites/decline` embeds an action verb instead of modeling a state transition on the invite resource.
**Fix:** Model decline as a state transition on the invite resource keyed by token under the canonical path family.
**Effort:** medium

## Reconciliation (reflexion)
- **Runs usable:** 2.
- **Consensus (both runs):** 3 findings kept — API-SKEL-007 @277, API-SKEL-011 @277, API-SKEL-011 @324 — identical rule/locus/gate in both runs. Reconciled prose by merging the clearer message + fix from each; snippets quote the actual route decorators and architecture §Idempotency.
- **Divergent — kept:** 0. The only divergence was framing, not findings.
- **Divergent — dropped:** 0 formal findings. The `delete_workspace` @45 observation was the sole divergent item, and **both** runs already declined to make it a finding (Run A folded it into the API-SKEL-002 dismissal; Run B withdrew its API-SKEL-010 candidate). Adjudicated against the artifact and upheld as a non-finding: the handler unconditionally raises `AppNotImplementedError` (workspaces.py:46-48) with zero reachable logic — no DB access, no mutation, no data exposure — so the missing auth dependency is not an exploitable API-SKEL-002 bypass (an unauthenticated caller gets a 501, deletes nothing). Architecture §Open questions defers "Workspace deletion lifecycle." API-SKEL-010 does not apply (creation POSTs → 201; this is a DELETE 501 stub). Carried-forward recommendation (non-blocking): add `AdminDep` to `delete_workspace` when it is implemented.
- **Gate/severity corrections:** none — both runs used the canonical gates (API-SKEL-007 = Gate 2, API-SKEL-011 = Gate 3).
- **Verdict:** FAIL_BLOCKER — recomputed from 0 Gate-1 / 1 Gate-2 / 2 Gate-3 reconciled findings (highest-severity gate with a finding is Gate 2).

## Summary
The route skeleton is structurally strong — full resource coverage, consistent `/v1/` versioning, complete auth wiring (`MemberDep`/`AdminDep`/`AuthDep`), `response_model` on every body-returning handler, Pydantic bodies on every mutation, cursor pagination on every collection, all routers registered and tagged, 201 on creates. The single blocker is the invite-accept HTTP method (`POST` vs the architecture's stated idempotent `PATCH` on the token hash) — it matters because the OpenAPI document is the declared source of truth for the dashboard's generated types, so fixing the method after types ship is a breaking change. The two Gate-3 warnings are the same design seam (verb-in-path on `/invites/accept` and `/invites/decline`) and would be resolved by the same refactor. Watch item for v2: give `delete_workspace` an `AdminDep` when it gains a real implementation.

Report saved to c:\Users\faraz\Desktop\Code\url-shortener\.claude\run\2026-06-07-api-skeleton-review.md
