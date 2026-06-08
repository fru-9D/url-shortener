# API Skeleton Review — 2026-06-05

**Architecture:** `c:\Users\faraz\Desktop\Code\url-shortener\docs\architecture.md`
**Routes reviewed:** `backend\app\main.py`, `backend\app\routers\auth.py`, `backend\app\routers\links.py`, `backend\app\routers\workspaces.py`, `backend\app\routers\analytics.py`, `backend\app\routers\abuse.py`, `backend\app\routers\health.py`
**PRD:** `c:\Users\faraz\Desktop\Code\url-shortener\docs\prd.md`
**Verdict:** FAIL_CRITICAL
**Gate 1 (Critical):** 1 finding
**Gate 2 (Blockers):** 1 finding
**Gate 3 (Warnings):** 0 findings

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `backend/app/routers/workspaces.py:47` | `DELETE /v1/workspaces/{workspace_id}` stub has no auth dependency — unauthenticated callers reach the handler | API-SKEL-002 | 1 | critical |
| `backend/app/routers/workspaces.py:47` | `DELETE /v1/workspaces/{workspace_id}` stub returns raw `dict` with no `response_model` | API-SKEL-003 | 2 | blocker |

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| API-SKEL-001 | Yes | All architecture-declared resource groups have router files: auth, links, workspaces, analytics, ops/abuse, health. |
| API-SKEL-002 | Partially fired | See Gate 1 finding. All other routes examined: public endpoints (signup, login, forgot-password, reset-password, verify-email) are correctly unauthenticated; token-as-auth endpoints (invites/accept, invites/decline) follow the established token-substitutes-for-session pattern consistent with PRD flow; 204 no-auth logout is fail-safe by design. Only the workspace delete stub is flagged. |
| API-SKEL-003 | Partially fired | See Gate 2 finding. All 204-returning routes correctly omit `response_model` (no body on 204). All other routes carry explicit `response_model`. Only the workspace delete stub returns a raw `dict` without declaring a schema. |
| API-SKEL-004 | Yes | Every POST/PUT/PATCH route carries a named Pydantic `BaseModel` parameter. No `request: Request` + `await request.json()` patterns found. No plain `dict` body annotations found. |
| API-SKEL-005 | Yes | All list endpoints use cursor pagination: `GET /v1/links` has `after` + `page_size`; `GET /v1/workspaces/{workspace_id}/members` has `after` + `page_size`; `GET /v1/ops/abuse-reviews` has `after` + `page_size`. Architecture §Pagination specifies cursor-based pagination — all three comply. |
| API-SKEL-006 | Yes | Architecture §Frontend/backend contract: "All Link API routes are prefixed `/v1/`". Every application router uses a `/v1/...` prefix. Health routes (`/healthz`, `/readyz`) have no prefix — these are infrastructure liveness/readiness endpoints explicitly called out in architecture §Scaling as unversioned infrastructure probes, not API resources. |
| API-SKEL-007 | Yes | No method mismatches found. POST for creation, PATCH for partial updates, DELETE for removal, GET for reads — all consistent with architecture and PRD descriptions. The Cloudflare Cache Purge in `abuse.py` uses `client.post(...)` (Cloudflare's API requires POST for cache purge, not DELETE) — this is correct per architecture §Cloudflare and is internal HTTP client code, not a route method. |
| API-SKEL-008 | Yes | `main.py` lines 78–83 call `app.include_router()` for all six routers: `health.router`, `auth.router`, `workspaces.router`, `links.router`, `analytics.router`, `abuse.router`. No orphaned router files found. |
| API-SKEL-009 | Yes | All routers declare `tags`: auth → `["auth"]`, links → `["links"]`, workspaces → `["workspaces"]`, analytics → `["analytics"]`, abuse → `["ops"]`, health → `["health"]`. |
| API-SKEL-010 | Yes | Creation POST endpoints all declare `status_code=201`: `POST /v1/auth/signup` (201), `POST /v1/links` (201), `POST /v1/workspaces` (201), `POST /v1/workspaces/{workspace_id}/invites` (201). Non-creation POSTs (login, logout, verify-email, resend-verification, forgot-password, reset-password, change-password, invites/accept, invites/decline) correctly use 200 or 204. |
| API-SKEL-011 | Yes | No verb-in-path, inconsistent plural/singular, or nesting-beyond-two-levels issues found. `POST /v1/invites/accept` and `POST /v1/invites/decline` use noun-like sub-paths on an invite token resource — this is a standard pattern for token-based state transitions (consistent with email verification links). `GET /v1/workspaces/me` uses the established `/me` convention for current-user resource shortcuts. |

---

## Gate 1 — Critical (skeleton not safe to build business logic on top of)

### [API-SKEL-002] — Auth-required stub endpoint has no auth dependency

**Location:** `backend/app/routers/workspaces.py:47`

**Finding:** `DELETE /v1/workspaces/{workspace_id}` is declared as a 501 "not implemented" stub for workspace deletion (deferred to v2). The handler signature is `async def delete_workspace(workspace_id: uuid.UUID) -> dict:` — it has no auth dependency (`AdminDep`, `MemberDep`, or `AuthDep`) in its parameter list, and the router itself has no router-level auth dependency. Workspace deletion is an admin-scoped operation; an unauthenticated caller can already hit this endpoint and receive the 501 response. When implementation is added in v2, the missing dependency will not be caught by reviewers expecting it to already be in place, and the endpoint will ship publicly accessible.

**Fix:** Add `ctx: AdminDep` (or at minimum `ctx: AuthDep`) to the stub parameter list. The stub body can continue to return 501, but auth must be enforced now so the structural contract is correct before implementation begins.

**Effort:** low

---

## Gate 2 — Blockers (will require breaking changes to fix later)

### [API-SKEL-003] — Workspace delete stub missing `response_model`

**Location:** `backend/app/routers/workspaces.py:47`

**Finding:** The `DELETE /v1/workspaces/{workspace_id}` stub returns `dict` with no `response_model` declared on the decorator: `@router.delete("/workspaces/{workspace_id}", status_code=501)`. The raw `dict` is returned directly: `return {"error": {"code": "not_implemented", "message": "..."}}`. Per architecture §API design, ORM objects and raw dicts are never returned from handlers — every response uses an explicit `response_model` schema. Without a `response_model`, FastAPI will not validate the response shape and the OpenAPI schema for this route will be undeclared (shown as `object` with no schema). When v2 implementation ships and the return type changes, callers will have been relying on undeclared behaviour.

**Fix:** Declare a `response_model` on the decorator — either the canonical error envelope schema (`ErrorResponse`) or a simple `NotImplementedResponse` Pydantic model matching the `{"error": {...}}` shape. This aligns the stub with the architecture's serialization contract.

**Effort:** low

---

## Gate 3 — Warnings

No Gate 3 findings.

---

## Summary

The skeleton is substantially improved from prior runs. All resource groups have router files, all routers are registered, versioning is consistent under `/v1/`, list endpoints use cursor pagination, all mutating routes carry Pydantic body schemas, and `status_code=201` is correctly declared on creation endpoints. The single remaining structural gap is a 501 placeholder stub for workspace deletion (`DELETE /v1/workspaces/{workspace_id}`) that lacks both an auth dependency and a declared `response_model`. This is a Gate 1 finding because the missing auth dependency on the stub will carry forward into the v2 implementation if not corrected now — it is faster and safer to establish the structural contract on the stub than to retrofit auth enforcement after implementation is written on top of it. Fixing both issues on this stub is low-effort (add one dependency parameter, add one `response_model` attribute) and can be done before any business logic is built. The skeleton is safe to build on for all other routes.
