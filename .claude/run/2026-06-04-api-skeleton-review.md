# API Skeleton Review — Snip URL Shortener

**Date:** 2026-06-04
**Reviewer:** api-skeleton-review agent
**Architecture:** `docs/architecture.md` (Draft v3, derived from PRD v5, ERD v5)
**PRD:** `docs/prd.md` (Draft v6)
**Route files reviewed:**
- `backend/app/main.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/links.py`
- `backend/app/routers/workspaces.py`
- `backend/app/routers/analytics.py`
- `backend/app/routers/abuse.py`
- `backend/app/routers/health.py`

---

## STEP A — Lookup Table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `backend/app/routers/auth.py:63` | `POST /v1/auth/signup` decorator has no `response_model` | API-SKEL-003 | 2 | blocker |
| `backend/app/routers/auth.py:119` | `POST /v1/auth/login` decorator has no `response_model` | API-SKEL-003 | 2 | blocker |
| `backend/app/routers/auth.py:176` | `GET /v1/auth/me` decorator has no `response_model` | API-SKEL-003 | 2 | blocker |
| `backend/app/routers/abuse.py:61` | `GET /v1/ops/abuse-reviews` uses `response_model=list[dict]` — not an explicit Pydantic schema | API-SKEL-003 | 2 | blocker |
| `backend/app/routers/workspaces.py:95` | `GET /v1/workspaces/{workspace_id}/members` has no pagination parameters | API-SKEL-005 | 2 | blocker |
| `backend/app/routers/abuse.py:61` | `GET /v1/ops/abuse-reviews` has no pagination parameters | API-SKEL-005 | 2 | blocker |
| `backend/app/routers/abuse.py:82` | Path `/v1/ops/abuse-reviews/{id}/whitelist` contains verb in path segment | API-SKEL-011 | 3 | warning |
| `backend/app/routers/abuse.py:96` | Path `/v1/ops/abuse-reviews/{id}/disable` contains verb in path segment | API-SKEL-011 | 3 | warning |
| `backend/app/routers/abuse.py:126` | Path `/v1/ops/abuse-reviews/{id}/hard-delete` contains verb in path segment | API-SKEL-011 | 3 | warning |

---

## STEP A-bis — Dismissed Rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| API-SKEL-001 | Yes | All architecture-declared resource groups (Auth, Links, Workspaces/Teams, Analytics, Abuse review queue, Health) have corresponding router files. |
| API-SKEL-002 | Yes | All auth-required endpoints carry `AuthDep`, `MemberDep`, or `AdminDep`. Public endpoints (`/signup`, `/login`, `/verify-email`, `/forgot-password`, `/reset-password`, `/invites/decline`, health checks) are correctly unauthenticated by design. `POST /logout` intentionally has no auth requirement (safe to call unauthenticated; the handler defensively checks for a cookie). |
| API-SKEL-004 | Yes | Every `POST`, `PUT`, and `PATCH` handler that accepts a payload uses a typed Pydantic model parameter (`CreateLinkRequest`, `UpdateLinkRequest`, `CreateWorkspaceRequest`, `InviteRequest`, `AcceptInviteRequest`, `UpdateRoleRequest`, `SignupRequest`, `LoginRequest`, `PasswordResetRequestBody`, `PasswordResetConfirmBody`, `ChangePasswordBody`). No raw `Request` or `dict` body parameters found. |
| API-SKEL-006 | Yes | All business route prefixes carry `/v1/`. Health endpoints (`/healthz`, `/readyz`) are intentionally unversioned — the architecture explicitly documents them without a version prefix ("Each ECS service exposes: `GET /healthz`... `GET /readyz`...") and the ALB health-check path is configured as `/readyz`. |
| API-SKEL-007 | Yes | No HTTP method contradicts the architecture or PRD descriptions. The three action-style sub-paths on abuse-reviews (`/whitelist`, `/disable`, `/hard-delete`) all use `POST`, which is correct for non-idempotent state transitions. The method is not in conflict with the PRD; the path shape is flagged separately under API-SKEL-011. |
| API-SKEL-008 | Yes | All six routers are imported and registered in `main.py` via `app.include_router()`. |
| API-SKEL-009 | Yes | All routers declare `tags`: `["auth"]`, `["links"]`, `["workspaces"]`, `["analytics"]`, `["ops"]`, `["health"]`. |
| API-SKEL-010 | Yes | `POST /signup` (`status_code=201`), `POST /workspaces` (`status_code=201`), `POST /workspaces/{id}/invites` (`status_code=201`), and `POST /links` (`status_code=201`) all declare the correct status code. `POST /login` returns 200, which is conventional for session creation (not resource creation) and is not flagged. Action-style POSTs on abuse-reviews return 204. |

---

## STEP B — JSON Findings

```json
[
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-003",
    "file": "backend/app/routers/auth.py",
    "line": 63,
    "snippet": "@router.post(\"/signup\", status_code=201)\nasync def signup(body: SignupRequest, request: Request, response: Response, db: DBDep) -> UserResponse:",
    "message": "The POST /v1/auth/signup decorator has no response_model parameter. The handler's return type annotation (-> UserResponse) is not equivalent — FastAPI uses response_model for serialization and OpenAPI schema generation. Without it, the ORM-backed UserResponse is returned unfiltered and the OpenAPI spec is undeclared for this endpoint. The same issue affects POST /v1/auth/login (line 119) and GET /v1/auth/me (line 176) — all three auth endpoints that return a UserResponse body are missing response_model.",
    "fix": "Add response_model=UserResponse to the decorators on /signup (line 63), /login (line 119), and /me (line 176). Architecture §API design: 'every response uses an explicit response_model schema to prevent accidental field leakage'.",
    "effort": "low"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-003",
    "file": "backend/app/routers/auth.py",
    "line": 119,
    "snippet": "@router.post(\"/login\")\nasync def login(body: LoginRequest, response: Response, db: DBDep) -> UserResponse:",
    "message": "POST /v1/auth/login decorator has no response_model. See the finding at line 63 for full context. Login also omits status_code entirely (defaults to 200), which is acceptable for a session-creation endpoint but should be made explicit for clarity.",
    "fix": "Add response_model=UserResponse to the @router.post(\"/login\") decorator.",
    "effort": "low"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-003",
    "file": "backend/app/routers/auth.py",
    "line": 176,
    "snippet": "@router.get(\"/me\")\nasync def me(ctx: AuthDep, db: DBDep) -> UserResponse:",
    "message": "GET /v1/auth/me decorator has no response_model. See the finding at line 63 for full context.",
    "fix": "Add response_model=UserResponse to the @router.get(\"/me\") decorator.",
    "effort": "low"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-003",
    "file": "backend/app/routers/abuse.py",
    "line": 61,
    "snippet": "@router.get(\"\", response_model=list[dict])\nasync def list_abuse_reviews(ctx: AdminDep, db: DBDep) -> list[dict]:",
    "message": "GET /v1/ops/abuse-reviews uses response_model=list[dict]. A plain dict is not an explicit Pydantic schema — FastAPI cannot validate the output shape, filter unexpected fields, or generate a typed OpenAPI schema. Architecture §API design: 'every response uses an explicit response_model schema.' Any AbuseReview fields added to the ORM model will silently leak into the response.",
    "fix": "Define a dedicated AbuseReviewResponse Pydantic schema (id, link_id, workspace_id, status, flagged_at, reviewed_at) and set response_model=list[AbuseReviewResponse] on the decorator.",
    "effort": "low"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-005",
    "file": "backend/app/routers/workspaces.py",
    "line": 95,
    "snippet": "@router.get(\"/workspaces/{workspace_id}/members\", response_model=list[MemberResponse])\nasync def list_members(workspace_id: uuid.UUID, ctx: MemberDep, db: DBDep) -> list[MemberResponse]:",
    "message": "GET /v1/workspaces/{workspace_id}/members returns an unbounded list with no pagination parameters. Architecture §Pagination: 'All list endpoints use cursor-based pagination. Default page size: 50. Maximum page size: 200.' Although the PRD caps team size at 50 in the target segment, the architecture does not explicitly carve out a bounded exception for this endpoint. Without pagination, a workspace that grows beyond the v1 target range — or a pathological data state — causes a full table scan and an oversized response payload.",
    "fix": "Add cursor-based pagination parameters (after: str | None = Query(default=None), page_size: int = Query(default=50, ge=1, le=200)) consistent with the pattern in list_links, and return a MemberListResponse envelope with items and next_cursor.",
    "effort": "medium"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-005",
    "file": "backend/app/routers/abuse.py",
    "line": 61,
    "snippet": "@router.get(\"\", response_model=list[dict])\nasync def list_abuse_reviews(ctx: AdminDep, db: DBDep) -> list[dict]:",
    "message": "GET /v1/ops/abuse-reviews applies a hard-coded .limit(100) inside the query body but exposes no pagination parameters on the API contract. Architecture §Pagination: 'All list endpoints use cursor-based pagination.' The 100-row internal cap is invisible to callers, produces no next_cursor signal, and means items beyond position 100 are silently unreachable. As the abuse queue grows under a Safe Browsing outage scenario, genuine reviews will be inaccessible to ops reviewers.",
    "fix": "Add after and page_size query parameters and return a paginated envelope (items, next_cursor). Remove the hard-coded .limit(100) and replace it with the page_size + 1 probe pattern used in list_links.",
    "effort": "medium"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 3,
    "severity": "warning",
    "rule": "API-SKEL-011",
    "file": "backend/app/routers/abuse.py",
    "line": 82,
    "snippet": "@router.post(\"/{review_id}/whitelist\", status_code=204)\n@router.post(\"/{review_id}/disable\", status_code=204)\n@router.post(\"/{review_id}/hard-delete\", status_code=204)",
    "message": "All three abuse-review action endpoints embed verbs directly in the path segment: /whitelist, /disable, /hard-delete. REST convention models state transitions as mutations of the resource itself (e.g., PATCH /v1/ops/abuse-reviews/{id} with a body field { \"action\": \"whitelist\" | \"disable\" | \"hard_delete\" }), not as verb sub-paths. The current design also silently contradicts the OpenAPI operation naming convention (FastAPI generates operation IDs from the path, producing whitelist_review__review_id__whitelist_post rather than a resource-oriented name). All three paths should be grouped in the same finding as they share the same pattern.",
    "fix": "Consolidate to a single PATCH /v1/ops/abuse-reviews/{review_id} endpoint that accepts an UpdateAbuseReviewRequest body with an action enum (whitelist | disable | hard_delete). This reduces three routes to one, produces a clean REST resource-update shape, and simplifies the OpenAPI schema. Alternatively, if separate endpoints are preferred for operational clarity, rename to noun-oriented sub-resources (e.g., POST /{id}/status with a body specifying the new status).",
    "effort": "medium"
  }
]
```

---

## STEP C — Domain Summary

```json
{
  "domain": "api-skeleton-review",
  "gate1_count": 0,
  "gate2_count": 6,
  "gate3_count": 3,
  "verdict": "FAIL_BLOCKER"
}
```

---

## Summary

**Verdict: FAIL_BLOCKER** — No Gate 1 (critical) findings. Six Gate 2 (blocker) findings; three Gate 3 (warning) findings.

The route skeleton is structurally present and correctly wired for all declared resource groups. Auth dependency coverage is correct across the board, all routers are registered in `main.py`, and versioning is applied consistently. The blocking issues are:

**Missing `response_model` on three auth endpoints** (signup, login, me) and **`list[dict]` as the response model on the abuse review list** — these four findings share the same root cause: the auth routes were written with only a return type annotation, and the abuse router used a raw dict to avoid defining a schema. The architecture is explicit that every route must declare `response_model` to prevent field leakage and produce a typed OpenAPI spec. Fixing these is low-effort (add the decorator parameter and, for abuse reviews, define a small Pydantic schema).

**Missing pagination on two list endpoints** (`GET /workspaces/{id}/members` and `GET /ops/abuse-reviews`) — the architecture's "all list endpoints use cursor-based pagination" rule applies to both. The members endpoint returns a fully unbounded query; the abuse review endpoint has a silent hard-coded `LIMIT 100` that produces invisible truncation. Both need `after`/`page_size` parameters and a paginated response envelope, which requires a small refactor to each handler.

The three Gate 3 warnings are all in `abuse.py`: the three action sub-paths (`/whitelist`, `/disable`, `/hard-delete`) embed verbs in the path in violation of REST conventions. These are addressable by consolidating to a single `PATCH` endpoint with an action enum, but they do not block business logic work.
