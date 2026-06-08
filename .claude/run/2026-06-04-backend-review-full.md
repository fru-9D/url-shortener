# Backend Review — full — 2026-06-04

**Verdict:** BASELINE_ONLY
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 9 findings
**Gate 3 (Warnings):** 20 findings

> This is the first scan of this repository. No prior baseline exists. The verdict is BASELINE_ONLY regardless of findings. Do not block the current state; use this report as the baseline for future delta reviews.

---

## Preflight Summary

| Tool      | Status          | Notes                                                                                      |
|-----------|-----------------|--------------------------------------------------------------------------------------------|
| bandit    | ran             | 0 findings across 2,772 LOC — clean                                                       |
| pip-audit | ran             | Vulnerabilities in `cryptography==43.0.3` (2 CVEs), `starlette==0.46.0` (3 CVEs), `python-jose==3.3.0` (2 CVEs, unused dep) |
| pytest    | not run         | Integration tests require live Postgres + Redis; infrastructure not available in CI scan   |
| ruff      | ran             | 168 violations: 40× F401 (unused imports), 33× I001 (import sort), 31× E501 (line length), 30× UP017, 22× F821, 5× UP042, 4× B008, 3× B904 |
| mypy      | ran             | 42 errors in 16 files; critical: real-bug in `abuse.py:46` (wrong kwarg to httpx), null-deref risk on `user` in `auth.py:142-162`, `safe_browsing.py:55` wrong attribute name |

---

## Domain Summary

| Domain          | Gate 1 | Gate 2 | Gate 3 | Status          |
|-----------------|--------|--------|--------|-----------------|
| security        | 0      | 2      | 4      | FAIL_BLOCKER    |
| api-design      | 0      | 1      | 3      | FAIL_BLOCKER    |
| database        | 0      | 1      | 2      | FAIL_BLOCKER    |
| erd-compliance  | 0      | 0      | 2      | PASS_WITH_RISK  |
| reliability     | 0      | 1      | 3      | FAIL_BLOCKER    |
| code-quality    | 0      | 2      | 3      | FAIL_BLOCKER    |
| spec-compliance | 0      | 2      | 3      | FAIL_BLOCKER    |
| red-team        | 0      | 0      | 0      | PASS            |

---

## Gate 1 — Critical Findings (Must fix before merge)

None. No Gate 1 findings.

---

## Gate 2 — Blockers (Must fix before release)

### [SEC-01] · security — `cryptography` dependency has active CVEs; pinned to vulnerable version

**File:** `backend/pyproject.toml:17`
**Snippet:** `"cryptography==43.0.3"`
**Finding:** `cryptography==43.0.3` has two published CVEs confirmed by pip-audit: CVE-2026-34073 (DNS name constraints bypass — TLS peer validation can be circumvented in certain wildcard + constraint configurations) and CVE-2026-26007 (ECC public key validation missing — small-order-subgroup attack on ECDH/ECDSA). Fix is available at version 46.0.6. This library is used for AES-256-GCM email encryption (`AESGCM` in `crypto.py`) — the CVEs do not directly affect symmetric AES-GCM operations, but this is a security-critical dependency that should always track the patched release.
**Fix:** Upgrade to `cryptography>=46.0.6` in `pyproject.toml` and re-pin after testing.
**Effort:** low

---

### [SEC-02] · security — `starlette==0.46.0` has CVE for Host header injection enabling authentication bypass

**File:** `backend/pyproject.toml:11`
**Snippet:** `"fastapi==0.115.5"` (pulls `starlette==0.46.0`)
**Finding:** pip-audit reports PYSEC-2026-161 against `starlette==0.46.0`: Starlette reconstructs the requested URL from the HTTP Host header without validating it, allowing attackers to inject paths into the host part and prepend them to the actual path. This can lead to authentication bypass if any auth logic depends on the reconstructed URL (e.g., CSRF validation on `request.url.path`). The CSRFMiddleware in `middleware.py:55` checks `request.url.path.startswith("/v1/")` — a Host-header-injected path could bypass this check. Fix versions: starlette >= 1.0.1. Additionally CVE-2025-54121 (event loop blocking on multipart upload > spool size) affects starlette 0.46.0.
**Fix:** Upgrade FastAPI to a version that bundles starlette >= 1.0.1 (or explicitly constrain `starlette>=1.0.1`). Test CSRF behavior after upgrade.
**Effort:** low

---

### [CQ-01] · code-quality — Real bug: `httpx.AsyncClient.delete()` called with `json=` kwarg (not supported)

**File:** `backend/app/routers/abuse.py:46`
**Snippet:** `resp = await client.delete(url, headers={"Authorization": ...}, json=payload)`
**Finding:** mypy reports `error: Unexpected keyword argument "json" for "delete" of "AsyncClient"`. The httpx `AsyncClient.delete()` method does not accept a `json` body parameter — the Cloudflare cache-purge call in `_purge_cloudflare_cache` is using `client.delete(..., json=payload)` which will raise a `TypeError` at runtime when Cloudflare credentials are configured. This means every call to `disable_link` and `hard_delete_link` that reaches the Cloudflare purge step will crash with an unhandled exception. The link is already disabled in the DB at that point (flush was called before the purge), but the purge silently fails without the correct API call being made — disabled links remain in the Cloudflare edge cache.
**Fix:** Replace `client.delete(url, ..., json=payload)` with `client.post(url, ..., json=payload)`. The Cloudflare cache purge API endpoint uses `POST`, not `DELETE`. Reference: https://developers.cloudflare.com/api/operations/zone-purge
**Effort:** low

---

### [SEC-03] · security — SES client is synchronous inside async route handlers

**File:** `backend/app/services/email_service.py:93`
**Snippet:** `client.send_email(...)`
**Finding:** `boto3` SES and SQS clients are invoked synchronously (blocking I/O) inside async FastAPI route handlers and async workers. `boto3` is not async-aware: each call blocks the event loop thread for the full network round-trip (typically 100–500ms). Under load this stalls all concurrent requests on the same worker, defeating the async model. The same pattern exists in `mixpanel.py`, `click_consumer.py`, `mail_worker.py`, and `mixpanel_forwarder.py`.
**Fix:** Wrap all boto3 calls in `await asyncio.get_event_loop().run_in_executor(None, lambda: client.send_email(...))`. Or replace with `aioboto3` for fully async AWS clients.
**Effort:** medium

---

### [API-01] · api-design — `verify-email` token passed as query parameter — appears in server logs

**File:** `backend/app/routers/auth.py:201`
**Snippet:** `async def verify_email(token: str, db: DBDep) -> None:`
**Finding:** FastAPI infers `token` as a query string parameter when it is not in a Pydantic body model. This causes the raw single-use token to appear in server access logs, proxy logs, browser history, and HTTP `Referer` headers. Any log aggregation system (Sentry, CloudWatch, etc.) will capture this token and retain it after the token is consumed — it becomes a persistent credential exposure.
**Fix:** Accept `token` in the request body via a Pydantic model: `class VerifyEmailBody(BaseModel): token: str`. This keeps the token out of the request URI and therefore out of logs.
**Effort:** low

---

### [DB-01] · database — Click idempotency constraint is too narrow; will cause DLQ failures at scale

**File:** `backend/app/models/click.py:33`, `backend/alembic/versions/0001_initial_schema.py:162`
**Snippet:** `UniqueConstraint("link_id", "clicked_at", name="uq_click_link_clicked_at")`
**Finding:** The composite unique index on `(link_id, clicked_at)` uses full microsecond precision. Two distinct clicks on the same link within the same microsecond (plausible under high traffic) will violate the constraint. The second INSERT will throw an unhandled `IntegrityError` in the click consumer, causing the message to be retried and eventually dead-lettered. Conversely, two SQS replays of the same real click event with slightly different `clicked_at` timestamps (e.g., due to clock skew or message transformation) will both insert, double-counting clicks.
**Fix:** Add a stable `event_id` UUID (emitted by the redirect service per click, included in the SQS message) as the idempotency key — create a unique index on `event_id` alone. This decouples deduplication from timestamp precision.
**Effort:** medium

---

### [REL-01] · reliability — Workers call `client.receive_message()` synchronously inside `async def` — blocks event loop

**File:** `backend/app/workers/click_consumer.py:105`, `backend/app/workers/mail_worker.py:104`, `backend/app/workers/mixpanel_forwarder.py:91`
**Snippet:** `response = client.receive_message(... WaitTimeSeconds=20 ...)` inside `async def run()`
**Finding:** All three workers call the synchronous boto3 `receive_message()` with `WaitTimeSeconds=20` directly from an async coroutine running in `asyncio.run()`. This blocks the event loop for up to 20 seconds per poll iteration. During this time no other coroutine — including `process_message` — can run. Concurrency within the worker process is completely eliminated. The 20s blocking poll also prevents graceful shutdown via SIGTERM during the polling window.
**Fix:** Wrap the SQS poll in `await asyncio.get_event_loop().run_in_executor(None, lambda: client.receive_message(...))`. Or switch to `aioboto3`. Also consider processing messages concurrently with `asyncio.gather`.
**Effort:** medium

---

### [SPEC-01] · spec-compliance — No redirect endpoint; ops endpoints accessible to any workspace admin

**File:** `backend/app/routers/abuse.py:62-79` (list_abuse_reviews uses AdminDep)
**Finding:** The abuse review ops endpoints (`GET /v1/ops/abuse-reviews`, `POST /v1/ops/abuse-reviews/{id}/disable`, `POST /v1/ops/abuse-reviews/{id}/hard-delete`) are protected only by `AdminDep` — any workspace admin (e.g., a customer's marketing manager) can view all abuse reviews across all workspaces, disable any link globally, and hard-delete any link from any workspace. The code comments acknowledge this: "In v1, 'ops admin' = any workspace Admin." This is an authorization design gap: ops operations should be scoped to an internal staff role, not any workspace admin.
**Fix:** Introduce an `is_ops_staff` flag on User and enforce it at the ops route level. Minimal v1 fix: add workspace scoping to the abuse review queries so admins can only act on reviews for links in their own workspace.
**Effort:** medium

---

### [SPEC-02] · spec-compliance — `Link.disabled_at` not filtered in workspace-member-facing link queries

**File:** `backend/app/routers/links.py:266-278`, `backend/app/routers/links.py:281-314`
**Snippet:** `.where(Link.short_code == short_code, Link.workspace_id == ctx.workspace_id, Link.deleted_at.is_(None))`
**Finding:** The `GET /v1/links/{short_code}` and `PATCH /v1/links/{short_code}` endpoints filter only on `deleted_at IS NULL`. According to the ERD notes, `disabled_at` should be "invisible to the link owner." Workspace members can currently view and edit disabled links through the API, and `list_links` also returns disabled links. This violates the PRD and ERD contract.
**Fix:** Add `Link.disabled_at.is_(None)` to all workspace-member-facing queries in the links router. Admin ops routes may omit this filter by design.
**Effort:** low

---

## Gate 3 — Warnings (Lead approval required)

### [SEC-04] · security — `python-jose` has CVEs and is an unused dependency

**File:** `backend/pyproject.toml:23`
**Snippet:** `"python-jose[cryptography]==3.3.0"`
**Finding:** `python-jose` 3.3.0 has published CVEs (including algorithm confusion attacks). More critically, the library is imported nowhere in the current codebase — sessions are managed via Redis-backed cookies, not JWTs. This is a dead dependency carrying known vulnerabilities, audited as vulnerable by pip-audit.
**Fix:** Remove `python-jose` from `pyproject.toml`. If JWT is needed in future, add `authlib` or `pyjwt` at that time with the patched version.
**Effort:** low

---

### [SEC-05] · security — CORS allows all headers (`allow_headers=["*"]`) with credentials

**File:** `backend/app/main.py:49`
**Snippet:** `allow_headers=["*"]`
**Finding:** `allow_headers=["*"]` combined with `allow_credentials=True` instructs browsers to reflect any header in preflight responses, weakening CORS hardening. The CSRF middleware requires `X-CSRF-Token` specifically; a locked-down allowlist enforces known headers.
**Fix:** Replace `["*"]` with `["Content-Type", "X-CSRF-Token", "X-Request-Id"]`.
**Effort:** low

---

### [SEC-06] · security — `X-Request-Id` header trusted from all callers — log injection risk

**File:** `backend/app/middleware.py:25`
**Snippet:** `request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())`
**Finding:** Any external client can supply a crafted `X-Request-Id` value that gets echoed into structured logs and error responses. This enables log injection attacks that can pollute log aggregation and confuse incident response. The comment in the code acknowledges a missing IP-based guard.
**Fix:** In production, validate that inbound `X-Request-Id` is a valid UUID before trusting it; otherwise generate a fresh one.
**Effort:** low

---

### [SEC-07] · security — mypy: `user` attribute access on possibly-None in login handler

**File:** `backend/app/routers/auth.py:142-162`
**Snippet:** `ph.verify(user.password_hash if user else dummy_hash, body.password)` then `user.id` accessed unconditionally
**Finding:** mypy reports multiple `Item "None" of "User | None" has no attribute ...` errors on lines 142, 146, 152, 157, 160, 162. The login handler calls `scalar_one_or_none()` and stores the result as `user`. After the argon2 verify (which handles the `None` case), `user.id` and `user.email_ciphertext` are accessed without a null guard — mypy correctly flags these as potential `AttributeError`. At runtime, the verify block raises `UnauthorizedError` when the password is wrong, so a `None` user never reaches the attribute access — but this depends on the exception propagation being correct. If a future refactor changes the control flow, this becomes a silent `AttributeError` crash.
**Fix:** Add `if user is None: raise UnauthorizedError(...)` after the verify block instead of relying on the exception from `ph.verify(dummy_hash, ...)` to handle it implicitly. This makes the null guard explicit and satisfies mypy.
**Effort:** low

---

### [API-02] · api-design — `list_links` N+1 click-count queries

**File:** `backend/app/routers/links.py:262`
**Snippet:** `responses = [await _link_to_response(link, db) for link in items]`
**Finding:** `_link_to_response` issues a `SELECT count(*)` against the click table for each link individually. With page_size=50 (default), listing links fires 51 queries. At high click volumes, the count queries can be slow against a large click table.
**Fix:** Replace per-link count with a single aggregation query over all link_ids in the page, then join the results.
**Effort:** medium

---

### [API-03] · api-design — Date filter query params accept timezone-naive datetimes

**File:** `backend/app/routers/links.py:239-242`
**Snippet:** `if date_from: query = query.where(Link.created_at >= date_from)`
**Finding:** `date_from` and `date_to` are typed as `datetime | None` but FastAPI does not enforce timezone offset. A naive datetime compared against a timezone-aware column produces undefined behavior in SQLAlchemy (wrong results or runtime error depending on the backend).
**Fix:** Validate `date_from.tzinfo is not None` and raise 422 if absent, or default to UTC via `date_from = date_from.replace(tzinfo=timezone.utc)`.
**Effort:** low

---

### [API-04] · api-design — `safe_browsing.py` references non-existent `httpx.TransientError`

**File:** `backend/app/services/safe_browsing.py:55`
**Snippet:** `except httpx.TransientError:`
**Finding:** mypy reports `Module has no attribute "TransientError"; maybe "TransportError"?`. `httpx.TransientError` does not exist in the httpx API — the correct class is `httpx.TransportError`. This means transient network errors in the Safe Browsing check are not caught by this `except` clause and will propagate as unhandled exceptions, potentially surfacing as 500 errors on link creation/edit.
**Fix:** Change `except httpx.TransientError:` to `except httpx.TransportError:` in `safe_browsing.py:55`.
**Effort:** low

---

### [DB-02] · database — `workspace_member` partial unique index not represented in ORM

**File:** `backend/app/models/workspace.py` (no `__table_args__` for active-member unique)
**Finding:** The migration creates `uq_workspace_member_active_user` (partial unique on `user_id WHERE removed_at IS NULL`) but this constraint is absent from the `WorkspaceMember.__table_args__`. Future `alembic --autogenerate` runs will not detect and will silently drop it.
**Fix:** Add `Index("uq_workspace_member_active_user", "user_id", unique=True, postgresql_where=text("removed_at IS NULL"))` to `WorkspaceMember.__table_args__`.
**Effort:** low

---

### [DB-03] · database — No server-side `updated_at` enforcement

**File:** All model files
**Finding:** All `updated_at` columns are set exclusively by application code. There is no `server_default` or DB trigger. Direct DB writes (ops scripts, migrations, admin tooling) will produce stale timestamps.
**Fix:** Add `server_default=func.now()` to `created_at` and `onupdate=func.now()` to `updated_at` at the migration layer, or add a PostgreSQL trigger.
**Effort:** medium

---

### [ERD-01] · erd-compliance — `AbuseReview.workspace_id` has no FK constraint

**File:** `backend/app/models/abuse_review.py:24`, `backend/alembic/versions/0001_initial_schema.py:219`
**Snippet:** `workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)`
**Finding:** The ERD shows `ABUSE_REVIEW.workspace_id` as a FK to WORKSPACE. Both the ORM and migration define it as a plain UUID column with no `ForeignKey` constraint. Orphaned records pointing to non-existent workspaces can silently accumulate.
**Fix:** Add `ForeignKey("workspace.id", ondelete="RESTRICT")` to `AbuseReview.workspace_id` in both ORM and migration.
**Effort:** low

---

### [ERD-02] · erd-compliance — `Click.workspace_id` has no FK constraint

**File:** `backend/app/models/click.py:16`
**Snippet:** `workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)`
**Finding:** Same issue as ERD-01 — `Click.workspace_id` is a bare UUID with no FK to `workspace`. The click consumer writes this from the inbound SQS message with no DB-level guard.
**Fix:** Add `ForeignKey("workspace.id", ondelete="RESTRICT")` to `Click.workspace_id`.
**Effort:** low

---

### [REL-02] · reliability — `delete_all_for_user` on SessionService is a documented no-op

**File:** `backend/app/services/session.py:103-110`
**Snippet:** `async def delete_all_for_user(self, user_id: uuid.UUID) -> None: pass`
**Finding:** The method is a no-op. For security incident response (force-logout of a specific user), this method is silently ineffective. Redis keys accumulate for up to 30 days after an account compromise event even after session_version is bumped.
**Fix:** Implement active Redis key revocation via a per-user session ID set (`user_sessions:<user_id>`) or `SCAN`-based enumeration. At minimum, add a prominent warning docstring.
**Effort:** medium

---

### [REL-03] · reliability — CSRF middleware only covers `/v1/` prefix — fragile by default

**File:** `backend/app/middleware.py:53`
**Snippet:** `request.url.path.startswith("/v1/")`
**Finding:** Any future endpoint outside `/v1/` (e.g., `/webhooks/ses`, `/admin/`) silently bypasses CSRF protection. The current Starlette Host-header CVE (SEC-02) also makes the `request.url.path` check less reliable.
**Fix:** Flip the default — apply CSRF to all mutating requests and use an explicit `_CSRF_EXEMPT` set for genuinely exempt paths.
**Effort:** low

---

### [REL-04] · reliability — No rate limit on `resend-verification` endpoint

**File:** `backend/app/routers/auth.py:224-244`
**Finding:** `POST /v1/auth/resend-verification` has no rate limit. An authenticated user can trigger unlimited SES sends, exhausting email quota or harassing recipients.
**Fix:** Add `RateLimiter.check_resend_verification(str(ctx.user_id))` enforcing e.g. 3 resends per hour per user.
**Effort:** low

---

### [CQ-02] · code-quality — 22 `F821` (undefined names) in ORM models — CI-breaking

**File:** Multiple model files
**Finding:** Ruff reports 22 `F821` violations for forward-reference strings in SQLAlchemy `relationship()` calls. These are runtime-correct but ruff's static analysis cannot resolve them. With the current `pyproject.toml` ruff config selecting `F`, these fail CI.
**Fix:** Add `# noqa: F821` to affected relationship lines, or use `from __future__ import annotations` + `TYPE_CHECKING` guards, or configure per-file ignores in `pyproject.toml`.
**Effort:** low

---

### [CQ-03] · code-quality — 40 unused imports across production code

**File:** Multiple files
**Finding:** Ruff identified 40 unused imports in production code including security-sensitive modules imported but unused (`NotFoundError`, `RateLimitError` in auth.py; `AnyUrl` in config.py; `INTERVAL`, `get_db`, `require_member` in analytics.py; `update`, `get_db`, `require_admin` in abuse.py).
**Fix:** Run `ruff check --fix app/` to auto-remove safe unused imports.
**Effort:** low

---

### [SPEC-03] · spec-compliance — Email URLs use hardcoded domain instead of `settings.snip_base_url`

**File:** `backend/app/services/email_service.py:48`, `:62`, `:77`
**Snippet:** `verify_url = f"https://app.snip.io/auth/verify-email?token={token}"`
**Finding:** Verification, password reset, and invite email URLs hardcode `https://app.snip.io` instead of using a configurable `app_base_url` setting. This makes staging/dev testing impossible (emails will always point to production), and will break if the domain changes.
**Fix:** Add `app_base_url: str = "https://app.snip.io"` to `Settings` and use `f"{settings.app_base_url}/auth/verify-email?token={token}"` in all email templates.
**Effort:** low

---

## Red-Team Attack Surface

### 1. Ops Endpoints Accessible to Any Workspace Admin — Cross-Tenant Privilege Escalation

**Vector:** `GET /v1/ops/abuse-reviews`, `POST /v1/ops/abuse-reviews/{id}/disable`, `POST /v1/ops/abuse-reviews/{id}/hard-delete`
**Impact:** Any workspace admin (a customer's marketing manager) can enumerate all pending abuse reviews across every customer workspace, permanently disable links belonging to other workspaces, and hard-delete records for any workspace's links. A malicious workspace admin could use this to enumerate competitor links, sabotage competitors by disabling their links, or destroy evidence by hard-deleting abuse reviews for their own malicious links. This is the single most exploitable vulnerability in the current codebase because: (a) it requires only a valid admin-role session, which any team admin has; (b) the impact is cross-tenant data access and destruction; (c) it is directly accessible via the documented API.
**Fix:** Add workspace scoping to all ops queries (`AbuseReview.workspace_id == ctx.workspace_id`). Long-term, introduce an `is_ops_staff` flag on User.

---

### 2. Cloudflare Cache Purge Always Fails — Disabled Links Remain Live at Edge

**Vector:** `POST /v1/ops/abuse-reviews/{id}/disable` → `_purge_cloudflare_cache()`
**Impact:** The Cloudflare cache purge call uses `client.delete(..., json=payload)` — httpx's `delete()` method does not accept a `json` keyword argument. This raises a `TypeError` at runtime (confirmed by mypy CQ-01). Every time an ops admin disables a link via the abuse review UI, the DB is updated (link.disabled_at is set) but the Cloudflare edge cache entry is NOT purged. The disabled link continues to serve from Cloudflare cache (TTL permitting) to anonymous visitors for the cache lifetime. A malware or phishing link that was flagged and "disabled" in the admin UI continues redirecting visitors until the Cloudflare cache entry naturally expires.
**Fix:** Change `client.delete(url, ..., json=payload)` to `client.post(url, ..., json=payload)` — the Cloudflare cache purge endpoint uses POST with a JSON body, not DELETE.

---

### 3. Login Timing Side-Channel for Email Enumeration

**Vector:** `POST /v1/auth/login` — comparing argon2 against dummy hash vs real hash
**Impact:** The login handler uses a `dummy_hash` to prevent timing-based email enumeration. However, the dummy hash uses hardcoded parameters (`$argon2id$v=19$m=65536,t=3,p=4$`) which must exactly match the live `PasswordHasher` default parameters. If argon2-cffi ever changes its default parameters (as it did from v21 to v23), the dummy hash timing will diverge from real hash timing by a statistically measurable amount. Over 100–500 requests, an attacker can distinguish "email not found" (dummy hash timing) from "email found, wrong password" (real hash timing), enabling email enumeration. The login rate limiter (5 attempts / 15 min per email) provides some mitigation but the attacker can operate across multiple email guesses below the per-email threshold.
**Fix:** Generate the dummy hash at module startup: `_DUMMY_HASH = ph.hash("dummy-password-do-not-use")`. This ensures the dummy hash always matches the live PasswordHasher configuration.

---

## Summary

This is the first scan of the Snip backend; the verdict is `BASELINE_ONLY` and no merge gate is triggered. The codebase is architecturally well-structured: Argon2id password hashing, AES-256-GCM email encryption with KMS-sealed DEKs, HMAC-signed session cookies with session-version invalidation, double-submit CSRF, and thorough rate limiting on sensitive endpoints. Two findings stand out for immediate action before the service handles real customers: (1) the Cloudflare cache-purge runtime bug (`httpx.delete()` with invalid `json=` kwarg, confirmed by mypy) means disabled malicious links are never actually purged from the edge cache — this is a safety-critical defect in the trust-and-safety pipeline; and (2) the ops admin authorization gap allows any workspace admin to cross-tenant access and destroy abuse review data, which constitutes a privilege escalation vulnerability. Both are Gate 2 blockers with low-to-medium remediation effort.
