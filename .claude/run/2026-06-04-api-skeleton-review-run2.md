# API Skeleton Review — Snip URL Shortener (Run 2)

**Date:** 2026-06-04
**Reviewer:** api-skeleton-review agent
**Architecture:** `docs/architecture.md` (v1 Draft v3)
**PRD:** `docs/prd.md` (v6)
**Route files reviewed:**
- `backend/app/main.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/links.py`
- `backend/app/routers/workspaces.py`
- `backend/app/routers/analytics.py`
- `backend/app/routers/abuse.py`
- `backend/app/routers/health.py`

---

## Architecture extraction summary

| Concern | Architecture declaration |
|---|---|
| API versioning | All Link API routes prefixed `/v1/` (§Frontend/backend contract) |
| Auth strategy | Cookie-based session; auth middleware gate on every non-public endpoint via `require_auth` / `AuthDep` / `MemberDep` / `AdminDep` FastAPI dependencies |
| Public endpoints | Health checks (`/healthz`, `/readyz`), signup, login, forgot-password, reset-password, email verification token consumption, invite decline (token-in-body) |
| Pagination | Cursor-based (`after`, `page_size`); response envelope `{ items, next_cursor }` |
| Response model | Every non-204 handler must declare `response_model`; ORM objects must never be returned directly |
| Resource groups | auth, links, workspaces (incl. members/invites), analytics, ops/abuse-reviews, health |

---

## STEP A — Lookup table

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `backend/app/routers/health.py:16` | `GET /healthz` has no `response_model`; returns raw `dict` without a declared schema | API-SKEL-003 | 2 | blocker |
| `backend/app/routers/health.py:21` | `GET /readyz` has no `response_model`; returns a `JSONResponse` directly without a declared schema | API-SKEL-003 | 2 | blocker |
| `backend/app/routers/workspaces.py:268` (`POST /v1/invites/accept`) and line 315 (`POST /v1/invites/decline`) | Route paths contain verbs (`accept`, `decline`) in the path segment, violating REST convention | API-SKEL-011 | 3 | warning |

---

## STEP A-bis — Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| API-SKEL-001 | Yes | All architecture resource groups have corresponding router files: auth, links, workspaces, analytics, ops/abuse-reviews, health. |
| API-SKEL-002 | Yes | All non-public endpoints carry `AuthDep`, `MemberDep`, or `AdminDep` in their parameter lists. Public endpoints (`/healthz`, `/readyz`, signup, login, forgot-password, reset-password, verify-email, invites/decline) are either explicitly documented as public in the architecture/PRD or are token-in-body flows where anonymity is intentional. `POST /v1/auth/logout` is unauthenticated by design — a session cookie that does not validate is harmless to delete, and the architecture does not require auth on logout. |
| API-SKEL-003 (non-health routes) | Yes | All non-health non-204 route handlers declare an explicit `response_model`. 204-returning handlers correctly omit it. The two health endpoints are flagged separately. |
| API-SKEL-004 | Yes | Every POST/PUT/PATCH handler uses a Pydantic model parameter for the request body. No handler calls `request.json()` directly or uses a plain `dict` type annotation. `POST /v1/auth/logout` carries no body, which is correct for a cookie-clearing operation. |
| API-SKEL-005 | Yes | All three list endpoints (`GET /v1/links`, `GET /v1/workspaces/{id}/members`, `GET /v1/ops/abuse-reviews`) declare `after` and `page_size` cursor-pagination parameters matching the architecture's cursor-based pagination contract. |
| API-SKEL-006 | Yes | All Link API routes are registered under `/v1/` as required. Health endpoints at `/healthz` and `/readyz` are exempt: the architecture §Scaling explicitly documents their bare paths ("each ECS service exposes `GET /healthz`... `GET /readyz`") without a version prefix, and the ALB health check config references these bare paths. |
| API-SKEL-007 | Yes | All HTTP methods match the architecture/PRD descriptions. The Cloudflare cache-purge outbound call in `abuse.py` uses `POST` while the architecture §Cloudflare says "HTTPS DELETE" — but this is an outbound HTTP call to a third-party API, not a declared route on the FastAPI service, and falls outside this reviewer's scope. The code comment on line 68 of `abuse.py` explicitly acknowledges the discrepancy. |
| API-SKEL-008 | Yes | All six routers are imported and registered via `app.include_router()` in `main.py` (lines 59–64). |
| API-SKEL-009 | Yes | Every `APIRouter` instance declares a `tags` parameter: `["health"]`, `["auth"]`, `["links"]`, `["workspaces"]`, `["analytics"]`, `["ops"]`. |
| API-SKEL-010 | Yes | All resource-creation POST handlers explicitly declare `status_code=201`: signup (auth.py:61), create_link (links.py:104), create_workspace (workspaces.py:46), create_invite (workspaces.py:165). `POST /v1/auth/login` returns 200, which is correct — it is a session establishment operation, not a resource creation. |

---

## STEP B — JSON findings array

```json
[
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-003",
    "file": "backend/app/routers/health.py",
    "line": 16,
    "snippet": "@router.get(\"/healthz\")\nasync def healthz() -> dict:\n    return {\"status\": \"ok\"}",
    "message": "GET /healthz has no response_model declared. FastAPI will return the raw dict and the OpenAPI schema will document this endpoint as returning an untyped object. No comment documents the absence of response_model as intentional.",
    "fix": "Declare a small inline schema (e.g. class HealthResponse(BaseModel): status: str) and add response_model=HealthResponse to the decorator. This also applies to GET /readyz.",
    "effort": "low"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "API-SKEL-003",
    "file": "backend/app/routers/health.py",
    "line": 21,
    "snippet": "@router.get(\"/readyz\")\nasync def readyz() -> JSONResponse:",
    "message": "GET /readyz returns a JSONResponse directly with no response_model. FastAPI cannot introspect JSONResponse returns for OpenAPI schema generation; the endpoint will appear schema-less in the generated docs.",
    "fix": "Define a ReadyzResponse schema with status: str and checks: dict[str, str] fields, declare response_model=ReadyzResponse on the decorator, and return the model instance directly (let FastAPI serialise it) rather than constructing a JSONResponse manually. Keep the status_code logic via the response parameter instead.",
    "effort": "low"
  },
  {
    "domain": "api-skeleton-review",
    "gate": 3,
    "severity": "warning",
    "rule": "API-SKEL-011",
    "file": "backend/app/routers/workspaces.py",
    "line": 268,
    "snippet": "@router.post(\"/invites/accept\", status_code=204)\nasync def accept_invite(...)\n\n@router.post(\"/invites/decline\", status_code=204)\nasync def decline_invite(...)",
    "message": "Route paths /v1/invites/accept and /v1/invites/decline embed verbs in the path, violating REST conventions. The canonical REST pattern for a state transition on an invite resource is PATCH /v1/invites/{token} with a body carrying the desired state (accepted | declined).",
    "fix": "Consolidate to PATCH /v1/invites/{token} with an UpdateInviteRequest body containing action: Literal[\"accept\", \"decline\"]. This matches the single-PATCH pattern already used on /v1/ops/abuse-reviews/{id} and /v1/workspaces/{id}/members/{id}. Alternatively, if verb-in-path is preferred for discoverability of the token-flow, add a comment to both handlers explicitly documenting the deviation so it is not treated as an oversight.",
    "effort": "low"
  }
]
```

---

## STEP C — Domain summary

```json
{
  "domain": "api-skeleton-review",
  "gate1_count": 0,
  "gate2_count": 2,
  "gate3_count": 1,
  "verdict": "FAIL_BLOCKER"
}
```

---

## Summary

The skeleton is substantially improved compared to a first pass: all resource groups are present, all auth dependencies are correctly wired, all list endpoints are paginated with cursor parameters, the versioning prefix is uniformly applied, and all creation endpoints declare `status_code=201`. The two Gate 2 findings are confined to the health-check router and have no impact on the business-logic routes — they are a schema documentation gap rather than a runtime correctness problem. The Gate 3 warning on the invite paths is a convention issue that does not affect functionality.

**Recommended actions before proceeding to business logic build-out:**

1. (Low effort) Add a `HealthResponse` schema and wire `response_model` on both `/healthz` and `/readyz`.
2. (Low effort) Either refactor the invite accept/decline paths to `PATCH /v1/invites/{token}` or add explicit comments documenting the verb-in-path as an intentional decision.

Once those two items are resolved, the skeleton is clean to build on.
