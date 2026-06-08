# Backend Review — full — 2026-06-04

**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 17 findings
**Gate 3 (Warnings):** 19 findings

**Delta vs Baseline (2026-06-04):** G1: 0→0 (no change), G2: 9→17 (+8), G3: 20→19 (−1). The increase in G2 reflects deeper domain coverage in this run — reliability, red-team, and database agents each surfaced additional blockers not captured by the prior scan.

---

## Preflight Summary

| Tool      | Status  | Notes                                          |
|-----------|---------|------------------------------------------------|
| bandit    | ran     | 0 findings — clean                             |
| pip-audit | ran     | 40 known vulns in environment (15 packages); cryptography 44.0.2, starlette 0.46.0, h11 0.14.0, idna 3.10 are relevant to this codebase |
| pytest    | not run | Requires live Postgres + Redis — skipped       |
| ruff      | ran     | 63 violations across ~20 files                 |
| mypy      | ran     | 100+ errors — structlog/boto3 missing stubs, datetime forward refs in models |

---

## Domain Summary

| Domain          | Gate 1 | Gate 2 | Gate 3 | Status          |
|-----------------|--------|--------|--------|-----------------|
| security        | 0      | 3      | 2      | FAIL_BLOCKER    |
| api-design      | 0      | 1      | 4      | FAIL_BLOCKER    |
| database        | 0      | 2      | 2      | FAIL_BLOCKER    |
| erd-compliance  | 0      | 0      | 2      | PASS_WITH_RISK  |
| reliability     | 0      | 4      | 2      | FAIL_BLOCKER    |
| code-quality    | 0      | 2      | 3      | FAIL_BLOCKER    |
| spec-compliance | 0      | 1      | 2      | FAIL_BLOCKER    |
| red-team        | 0      | 4      | 2      | FAIL_BLOCKER    |

---

## Gate 1 — Critical Findings (Must fix before merge)

No Gate 1 findings. Gate 1 is clear.

---

## Gate 2 — Blockers (Must fix before release)

### [SEC-01] · security — cryptography 44.0.2 installed despite >=46.0.6 requirement
**File:** `backend/pyproject.toml:20`
**Snippet:** `"cryptography>=46.0.6"`
**Finding:** pyproject.toml requires `cryptography>=46.0.6` but the installed version is 44.0.2. CVE-2026-34073 (DNS name constraint bypass) and CVE-2026-26007 (ECC subgroup attack on SECT curves) are unpatched in the installed version. The package constraint is correct but the lockfile or Docker image has not been updated.
**Fix:** Run `pip install --upgrade cryptography` and rebuild the Docker image / update your lockfile. Verify with `pip show cryptography`.
**Effort:** low

---

### [SEC-02] · security — starlette 0.46.0 has three active CVEs
**File:** `backend/app/main.py:44`
**Snippet:** `starlette==0.46.0` (transitive via fastapi)
**Finding:** starlette 0.46.0 carries PYSEC-2026-161 (Host header injection enabling path-prepend that can bypass authentication dependent on reconstructed URL path), CVE-2025-54121 (event loop block on large multipart uploads), and CVE-2025-62727 (Range header ReDoS on FileResponse). See RT-04 for CSRF bypass exploitation path.
**Fix:** Upgrade FastAPI to a version that bundles starlette>=1.0.1 (per pyproject.toml comment `starlette>=1.0.1 required for Host-header CVE fix`). The constraint is already documented — the environment just needs to be rebuilt.
**Effort:** low

---

### [SEC-03] · security — h11 0.14.0 has request smuggling CVE
**File:** `backend/pyproject.toml`
**Snippet:** `h11==0.14.0` (transitive via uvicorn/httpx)
**Finding:** CVE-2025-43859 — h11 does not validate trailing `\r\n` bytes in chunked encoding bodies. An attacker using a buggy reverse proxy (e.g., nginx with specific chunked-encoding behavior) in front of this service can inject smuggled requests.
**Fix:** Upgrade h11 to >=0.16.0 by upgrading uvicorn or pinning h11>=0.16.0.
**Effort:** low

---

### [API-01] · api-design — verify-email token contract mismatch (test sends query param, endpoint reads body)
**File:** `backend/app/routers/auth.py:191`
**Snippet:** `async def verify_email(body: VerifyEmailBody, db: DBDep)`
**Finding:** POST /v1/auth/verify-email reads token from JSON request body (VerifyEmailBody.token). However `test_auth.py` calls `client.post(f"/v1/auth/verify-email?token={raw_token}")` — passing token as a query parameter. FastAPI will not bind a query parameter to a Pydantic body field; the body token will be None and the request will fail with 422. If the frontend was built to match the test pattern (appending `?token=...` to the verification link), email verification is broken for all users — blocking workspace creation and link creation.
**Fix:** Choose one canonical input location. The simpler fix: change the endpoint to accept `token: str = Query(...)` and remove VerifyEmailBody. Update the test to match. Alternatively, fix the test to send `json={"token": raw_token}` and ensure the frontend sends JSON body.
**Effort:** low

---

### [DB-01] · database — short code generation race → unhandled IntegrityError → HTTP 500
**File:** `backend/app/routers/links.py:152`
**Snippet:** `for _ in range(10): short_code = _generate_short_code(); existing = await db.execute(...); if not existing.scalar_one_or_none(): break`
**Finding:** The check-then-insert pattern for short code generation has no database-level atomicity. Two concurrent POST /v1/links requests can both observe the same short_code as available, both pass the loop, and both attempt INSERT. The second hits the partial unique index on `short_code WHERE deleted_at IS NULL` and raises an unhandled SQLAlchemy IntegrityError that propagates to `unhandled_error_handler` as HTTP 500.
**Fix:** Wrap `db.flush()` in a try/except `sqlalchemy.exc.IntegrityError` block and retry short code generation (up to 3 times) before returning 500. This converts a silent data race into a graceful retry.
**Effort:** low

---

### [DB-02] · database — concurrent workspace creation race → unhandled IntegrityError → HTTP 500
**File:** `backend/app/routers/workspaces.py:47`
**Snippet:** `existing = await db.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == ctx.user_id, WorkspaceMember.removed_at.is_(None)))`
**Finding:** create_workspace checks for existing membership then inserts Workspace+WorkspaceMember. Two concurrent calls by the same user both pass the membership check and both attempt to insert WorkspaceMember rows. The second insert violates the partial unique index on `user_id WHERE removed_at IS NULL` → unhandled IntegrityError → HTTP 500.
**Fix:** Catch IntegrityError around the WorkspaceMember flush/commit and return ConflictError("You're already part of a Workspace."). Alternatively use SELECT FOR UPDATE on the membership check row.
**Effort:** low

---

### [REL-01] · reliability — deprecated on_event lifecycle hook; no startup pool warmup
**File:** `backend/app/main.py:67`
**Snippet:** `@app.on_event("shutdown")`
**Finding:** `app.on_event("shutdown")` is deprecated since FastAPI 0.93 / Starlette 0.20. There is no startup event — the database connection pool is not pre-warmed, meaning the first request after a cold start pays connection establishment overhead. In production with strict latency SLOs this causes p99 spikes on deploy.
**Fix:** Replace with `@asynccontextmanager` lifespan function: `app = FastAPI(lifespan=lifespan)`. Add pool warmup in startup: `async with engine.connect(): pass`.
**Effort:** low

---

### [REL-02] · reliability — login rate limiter counter is not atomic (concurrent under-count)
**File:** `backend/app/services/rate_limiter.py:56`
**Snippet:** `data = await self._redis.hgetall(key); count = int(data.get("attempt_count", 0)); count += 1; await self._redis.hset(key, mapping={...})`
**Finding:** The login lockout uses hgetall (read) then hset (write) in two separate operations. Under concurrent failed login bursts, multiple requests can read the same counter value, each increment independently, and each write back — resulting in attempt_count undercounting. The lockout threshold may never be reached under a coordinated burst attack against a single account.
**Fix:** Use a Lua script for atomic read-increment-write, or replace with a Redis INCR key pattern with a separate `locked_until` key set via SET NX EX.
**Effort:** medium

---

### [REL-03] · reliability — signup rate limiter INCR+EXPIRE not atomic (persistent counter on crash)
**File:** `backend/app/services/rate_limiter.py:91`
**Snippet:** `pipe.incr(ip_key); pipe.expire(ip_key, 3600); pipe.incr(domain_key); pipe.expire(domain_key, 3600)`
**Finding:** Redis pipeline sends INCR and EXPIRE together in one roundtrip, but Redis executes them as two separate commands. If the process crashes after INCR is applied but before EXPIRE is applied, the counter key has no TTL and persists indefinitely, permanently blocking that IP/domain from signing up.
**Fix:** Use `SET key 1 EX 3600 NX` for first-time key creation (returns nil if key exists), then `INCR` for subsequent increments. Or use a Lua script to guarantee atomic INCR+EXPIRE.
**Effort:** low

---

### [REL-04] · reliability — asyncio.get_event_loop() deprecated in Python 3.10+, broken in 3.12+
**File:** `backend/app/services/email_service.py:116`
**Snippet:** `loop = asyncio.get_event_loop(); return await loop.run_in_executor(None, _blocking_send)`
**Finding:** `asyncio.get_event_loop()` is deprecated in Python 3.10+ and raises DeprecationWarning. In Python 3.12+ it raises RuntimeError when called from a coroutine running on a non-main thread (which is common under uvicorn workers). This pattern exists in 5 locations: `services/email_service.py`, `services/mixpanel.py`, `workers/click_consumer.py`, `workers/mail_worker.py`, `workers/mixpanel_forwarder.py`.
**Fix:** Replace all 5 instances of `asyncio.get_event_loop()` with `asyncio.get_running_loop()`.
**Effort:** low

---

### [CQ-01] · code-quality — datetime forward references in 7 model files without datetime import
**File:** `backend/app/models/tokens.py:17`
**Snippet:** `expires_at: Mapped["datetime"] = mapped_column(DateTime(timezone=True), nullable=False)`
**Finding:** 7 model files (tokens.py, link.py, workspace.py, click.py, abuse_review.py, invite.py, email_suppression.py) use `Mapped["datetime"]` and `Mapped["datetime | None"]` as forward-reference strings without importing datetime at the top of the file. Mypy reports `name-defined` errors for all of these. Under PEP 563 or 649 (postponed evaluation of annotations), these will raise NameError at import time in future Python versions.
**Fix:** Add `from datetime import datetime` to the top of each of these 7 model files.
**Effort:** low

---

### [CQ-02] · code-quality — worker factory functions missing type annotations (mypy blind spot)
**File:** `backend/app/workers/click_consumer.py:33`
**Snippet:** `def _sqs_client():\n    return boto3.client(...)`
**Finding:** `_sqs_client()` and `_ses_client()` in 4 files are missing return type annotations. Mypy's strict mode flags all callers with `no-untyped-call`, disabling type checking for the entire SQS/SES call chain. This means type errors in message body parsing or response handling are invisible to the type checker.
**Fix:** Add `boto3-stubs[sqs,ses]` to dev dependencies and annotate: `def _sqs_client() -> SQSClient:`. Add `types-boto3-sqs` stub package.
**Effort:** low

---

### [SPEC-01] · spec-compliance — 30-day hard-delete scheduled job not implemented
**File:** `backend/app/routers/links.py:136`
**Snippet:** `reuse_cutoff = datetime.now(timezone.utc) - timedelta(days=30)`
**Finding:** PRD §Data retention specifies a 30-day soft-delete window before slug reuse, plus a hard-delete scheduled job. The app-layer reuse_cutoff check exists and is correct, but the scheduled job that hard-deletes rows with `deleted_at < NOW() - INTERVAL '30 days'` is absent. Soft-deleted link rows and their associated click rows accumulate indefinitely. At scale this becomes a significant storage and query performance issue, and the reuse_cutoff logic silently allows slug reuse once a slug is >30 days deleted even though the data was never purged.
**Fix:** Implement a scheduled job (e.g., a Celery beat task, a cron-invoked script, or an AWS EventBridge + Lambda) that hard-deletes `link` rows `WHERE deleted_at < NOW() - INTERVAL '30 days'`. Cascade DELETE will handle associated clicks via FK.
**Effort:** medium

---

### [RT-01] · red-team — login brute force bypass when Redis is unavailable (fail-open)
**File:** `backend/app/services/rate_limiter.py:42`
**Snippet:** `data = await self._redis.hgetall(key); if not data: return`
**Finding:** `check_login_attempt` returns silently (no exception raised) when Redis is unavailable or when the key does not exist. An attacker who can cause Redis unavailability (memory pressure, network partition, targeted port block) bypasses all brute-force protection for every login attempt during the outage window. The signup rate limiter correctly raises 503 on Redis failure — the login limiter does not.
**Fix:** Add `try/except` around the hgetall call and raise `ServiceUnavailableError` on Redis exception. The empty-dict case (new key) is intentional and should remain as `return` — only the exception case needs fixing.
**Effort:** low

---

### [RT-02] · red-team — email verification broken by token location mismatch (same as API-01)
**File:** `backend/app/routers/auth.py:191`
**Snippet:** `async def verify_email(body: VerifyEmailBody, db: DBDep)`
**Finding:** (See API-01 above.) From an attack surface perspective: if email verification silently fails for all users (because the frontend sends token as query param), `email_verified_at` is never set, all users are permanently locked out of link creation and workspace creation, and the platform is non-functional. This is a high-severity availability issue even though there is no direct security bypass.
**Fix:** Same as API-01.
**Effort:** low

---

### [RT-03] · red-team — concurrent link creation → unhandled IntegrityError → HTTP 500 (same as DB-01)
**File:** `backend/app/routers/links.py:152`
**Finding:** (See DB-01 above.) From a red-team perspective: a client with automatic retry-on-500 and concurrent requests (e.g., a frontend that opens multiple tabs) can trigger this repeatedly, appearing as a platform instability. An attacker could also deliberately time concurrent requests to maximize collision probability for targeted short codes.
**Fix:** Same as DB-01.
**Effort:** low

---

### [RT-04] · red-team — starlette Host header injection → potential CSRF bypass
**File:** `backend/app/main.py:44`
**Snippet:** `starlette==0.46.0`
**Finding:** PYSEC-2026-161: Starlette reconstructs `request.url` from the Host header without validation. The CSRFMiddleware in this app checks `request.url.path not in _CSRF_EXEMPT`. An attacker who crafts `Host: attacker.com/readyz` on a POST request to `/v1/auth/login` causes Starlette to reconstruct `request.url.path` as `/readyz`, which is in `_CSRF_EXEMPT`, bypassing CSRF validation on the login endpoint.
**Fix:** Upgrade starlette to >=1.0.1 (via fastapi upgrade). As a temporary mitigation: in CSRFMiddleware, use `request.scope["path"]` (raw ASGI path, not reconstructed from Host) instead of `request.url.path` for the exempt check.
**Effort:** low

---

## Gate 3 — Warnings (Lead approval required)

### [SEC-04] · security — local DEK derived from single SHA-256 pass over SECRET_KEY
**File:** `backend/app/crypto.py:34`
**Finding:** In dev mode (no KMS), the local DEK is `hashlib.sha256(settings.secret_key.encode()).digest()`. If SECRET_KEY leaks, all email ciphertexts at rest are decryptable. HKDF with a distinct context string would provide better domain separation.
**Fix:** Replace with `HKDF(algorithm=SHA256, length=32, salt=None, info=b'email-dek-v1')` from `cryptography.hazmat.primitives.kdf.hkdf`.
**Effort:** medium

---

### [SEC-05] · security — login rate limiter fail-open on Redis empty key (warning complement to RT-01)
**File:** `backend/app/services/rate_limiter.py:42`
**Finding:** Noted under RT-01. The empty-data case (new key) is intentional but the Redis-exception case is not. Classified as Gate 3 here for the empty-key behavior; the exception-case is Gate 2 under RT-01.
**Fix:** See RT-01.
**Effort:** low

---

### [API-02] · api-design — invite lifecycle routes outside workspace resource hierarchy
**File:** `backend/app/routers/workspaces.py:43`
**Finding:** POST /v1/invites/accept and /v1/invites/decline sit at the top level rather than under /v1/workspaces/. This makes the invite lifecycle API inconsistent with the workspace resource structure.
**Fix:** Consider /v1/workspaces/invites/accept (scoped to workspace) or document the flat structure as intentional.
**Effort:** low

---

### [API-03] · api-design — UserResponse.id typed as str instead of uuid.UUID
**File:** `backend/app/schemas/auth.py:14`
**Finding:** All other response models (LinkResponse, WorkspaceResponse, MemberResponse) use `uuid.UUID` for ID fields. UserResponse uses `str`, causing inconsistency in client SDK generation and JSON output format.
**Fix:** Change `id: str` to `id: uuid.UUID` in UserResponse.
**Effort:** low

---

### [API-04] · api-design — PATCH /v1/ops/abuse-reviews returns 204 without confirming cache purge
**File:** `backend/app/routers/abuse.py:132`
**Finding:** PATCH returns 204 No Content even when action=disable triggers a Cloudflare cache purge. A failed purge is logged but not surfaced to the caller. Ops cannot know if the cache was cleared from the API response alone.
**Fix:** Return 200 with a body `{"action": "disable", "cache_purged": true/false}` for the disable action.
**Effort:** low

---

### [API-05] · api-design — idempotency_key field in CreateLinkRequest schema is dead code
**File:** `backend/app/routers/links.py:110`
**Finding:** `idempotency_key: str | None = Field(default=None, exclude=True)` in CreateLinkRequest is never used — the actual Idempotency-Key comes from the HTTP header. The schema field causes confusion.
**Fix:** Remove `idempotency_key` from CreateLinkRequest.
**Effort:** low

---

### [DB-03] · database — connection pool sizing not documented; no pool_timeout configured
**File:** `backend/app/database.py:7`
**Finding:** pool_size=10 + max_overflow=5 = 15 connections per worker process. At 4 uvicorn workers this is 60 connections — approaching Postgres default max_connections=100. No pool_timeout is set (default 30s), which can mask exhaustion silently.
**Fix:** Set `pool_timeout=10`. Document expected workers × pool_size in deployment runbook. Consider pgBouncer for production connection pooling.
**Effort:** medium

---

### [DB-04] · database — duplicate unique constraint on User.email_search_hash
**File:** `backend/app/models/user.py:15`
**Finding:** `email_search_hash` has both `unique=True` on the column AND a named `UniqueConstraint` in `__table_args__`. PostgreSQL creates two separate unique indexes, wasting storage and adding write overhead on every user insert/update.
**Fix:** Remove `unique=True` from `mapped_column` and keep only the named `UniqueConstraint("email_search_hash", name="uq_user_email_search_hash")`.
**Effort:** low

---

### [ERD-01] · erd-compliance — ERD constraint table inconsistency on CLICK idempotency
**File:** `backend/app/models/click.py:36`
**Finding:** The ERD constraint table notes "Composite unique index on (link_id, clicked_at)" for CLICK idempotency. The ORM and migration implement `UniqueConstraint("event_id")` only. The ERD body text clarifies that event_id is the canonical idempotency key — making the constraint table note a documentation inconsistency rather than a missing constraint.
**Fix:** Update the ERD constraint table to remove the (link_id, clicked_at) composite unique notation and document event_id as the sole idempotency mechanism.
**Effort:** low

---

### [ERD-02] · erd-compliance — duplicate unique on email_search_hash (same root as DB-04)
**File:** `backend/app/models/user.py:15`
**Finding:** See DB-04. The ERD specifies one UK on email_search_hash; the ORM declares it twice.
**Fix:** See DB-04.
**Effort:** low

---

### [REL-05] · reliability — click consumer has no dead-letter queue protection
**File:** `backend/app/workers/click_consumer.py:123`
**Finding:** A persistently malformed SQS message (e.g., missing `link_id` field) raises a KeyError in `process_message`, is not deleted, and re-appears after VisibilityTimeout=90s indefinitely. Without a DLQ configured, one bad message can consume up to 30%+ of worker capacity in a busy queue.
**Fix:** Configure an SQS DLQ for the clicks queue with `maxReceiveCount=3`. Document the DLQ requirement in the infrastructure runbook.
**Effort:** medium

---

### [REL-06] · reliability — Safe Browsing check silently skipped on timeout (no retry, fail-open)
**File:** `backend/app/services/safe_browsing.py:53`
**Finding:** Timeout immediately returns False (safe/fail-open) with no retry. During API latency spikes, every link creation call will skip abuse flagging.
**Fix:** Add one brief retry with a shorter timeout (300ms) before failing open. Document the fail-open behavior in the ops runbook.
**Effort:** low

---

### [CQ-03] · code-quality — deferred imports in hot-path create_link handler
**File:** `backend/app/routers/links.py:111`
**Finding:** `create_link` defers `from sqlalchemy import select as sq`, `from app.models.user import User`, `from app.redis_client import get_redis`, and `import json as _json` inside the function body. This adds import overhead on every call and indicates circular import issues at module level.
**Fix:** Resolve the circular import at module level using `TYPE_CHECKING` guards or by restructuring model imports. Move all imports to module top-level.
**Effort:** medium

---

### [CQ-04] · code-quality — raise without from inside except (B904) in auth.py
**File:** `backend/app/routers/auth.py:125`
**Finding:** Two B904 violations at lines 125 and 320: `raise UnauthorizedError(...)` inside `except` block without `from None` or `from exc`. Exception context is lost in tracebacks, making debugging harder.
**Fix:** Use `raise UnauthorizedError("Invalid email or password.") from None` to suppress context.
**Effort:** low

---

### [CQ-05] · code-quality — 63 auto-fixable ruff violations across ~20 files
**File:** `backend/app`
**Finding:** 63 ruff violations: ~20 I001 (unsorted imports), ~10 F401 (unused imports), ~20 E501 (lines >100 chars), 8 UP017 (use `datetime.UTC` alias), 5 UP042 (inherit from `StrEnum`). All safe to auto-fix. Volume indicates ruff is not enforced in CI.
**Fix:** Run `ruff check app --fix` for safe auto-fixes. Add ruff to the pre-commit hook and CI pipeline. Add `ruff check app` as a required CI check.
**Effort:** low

---

### [SPEC-02] · spec-compliance — bot detection uses 10-entry regex vs IAB/ABC Spiders & Bots List
**File:** `backend/app/workers/click_consumer.py:21`
**Finding:** PRD references the IAB/ABC Spiders & Bots List. The implementation uses a 10-entry regex covering major crawlers only. Many bot frameworks, headless browsers, and scraping tools will not be classified as bots, overstating human click counts in analytics.
**Fix:** Integrate the IAB/ABC Spiders & Bots List (CSV available for download). Load at worker startup and check UA string against it.
**Effort:** high

---

### [SPEC-03] · spec-compliance — no workspace deletion capability (known gap)
**File:** `backend/app`
**Finding:** No workspace delete endpoint exists in v1. This is documented as a known PRD gap. Workspace owners have no self-service path to delete their workspace — requires ops intervention.
**Fix:** Add `DELETE /v1/workspaces/{workspace_id}` returning 501 Not Implemented to reserve the route for v2.
**Effort:** low

---

### [RT-05] · red-team — last-admin removal race (two concurrent removals can leave zero admins)
**File:** `backend/app/routers/workspaces.py:349`
**Finding:** Two concurrent admin-removal requests targeting different admin members can both read admin_count=2, both pass the guard, both succeed, leaving zero admins in the workspace. The partial unique index does not protect against this since the two targets have different user_ids.
**Fix:** Use `SELECT ... FOR UPDATE` on the WorkspaceMember admin count check, or use a CTE with an atomic count-then-update.
**Effort:** medium

---

### [RT-06] · red-team — click consumer trusts SQS message workspace_id without DB validation
**File:** `backend/app/workers/click_consumer.py:46`
**Finding:** The click consumer accepts `workspace_id` from the SQS message body and persists it alongside `link_id` without confirming the link actually belongs to that workspace. A compromised SQS producer could inject clicks with arbitrary workspace_ids, polluting analytics for targeted workspaces.
**Fix:** After parsing `link_id`, query `SELECT workspace_id FROM link WHERE id = link_id` and assert it matches the message's `workspace_id`. Reject (log and delete) mismatched messages.
**Effort:** low

---

## Red-Team Attack Surface

### 1. Login Brute Force via Redis Failure (RT-01)
**Vector:** An attacker causes Redis unavailability (OOM, network partition, or targeted connection exhaustion on port 6379) while simultaneously flooding POST /v1/auth/login against a known email address. `check_login_attempt` returns silently on hgetall failure, bypassing the 5-attempt/15-min lockout. No lockout is applied even after hundreds of failed attempts.
**Impact:** Full brute-force capability against any known email address. Argon2id slows each attempt to ~100ms, but with unlimited concurrent attempts from multiple IPs, a 12-character password is crackable given sufficient time. Account takeover for any targeted user.
**Fix:** Raise ServiceUnavailableError (503) on Redis exception inside check_login_attempt. This is a one-line fix that mirrors check_signup's existing behavior.

### 2. Email Verification Permanently Broken — Platform-Wide Availability (RT-02 / API-01)
**Vector:** POST /v1/auth/verify-email reads token from JSON body. The test sends token as a query parameter (`?token=...`). If the email verification link generated by `send_verification_email` appends `?token=...` to the URL and the frontend follows that link with a GET that is redirected to a POST with the query param preserved, the token is never in the body and every verification attempt returns 422. All new users are permanently locked out of link creation and workspace creation.
**Impact:** Total denial of core product functionality for all new users. No links can be created, no workspaces can be created. The platform is non-functional for new signups.
**Fix:** Accept token as `Query(...)` parameter in the verify-email endpoint, or ensure the test and frontend send `json={"token": raw_token}` in the POST body.

### 3. Starlette Host Header Injection → CSRF Bypass on Login (RT-04 / SEC-02)
**Vector:** An attacker crafts an HTTP request with `Host: attacker.com/readyz` and sends POST /v1/auth/login. Starlette (0.46.0) reconstructs `request.url.path` from the Host header, yielding `/readyz`. The CSRFMiddleware compares `request.url.path` against `_CSRF_EXEMPT = {"/healthz", "/readyz"}` and finds a match, bypassing CSRF validation. The attacker can now submit the login form without a valid CSRF token, enabling cross-site request forgery attacks on authentication.
**Impact:** CSRF protection on the login endpoint is bypassable. An attacker can craft a page that automatically submits login credentials from a victim's browser to the target API without the victim's knowledge. Combined with credential stuffing, this bypasses a significant defense layer.
**Fix:** Upgrade starlette to >=1.0.1 immediately. Temporary mitigation: replace `request.url.path` with `request.scope["path"]` (the raw ASGI path, unmodified by Host header) in the CSRFMiddleware exempt check.

---

## Summary

The codebase has a well-structured security foundation — Argon2id hashing, HMAC-signed sessions, double-submit CSRF, email encryption at rest, and comprehensive rate limiting. Gate 1 is clear. The verdict of FAIL_BLOCKER is driven by 17 Gate 2 findings across 7 of 8 domains.

The single highest-priority finding is RT-02/API-01: the token-location contract mismatch in POST /v1/auth/verify-email. If the frontend sends token as a query parameter (consistent with the test's behavior), email verification is broken for all users, making link creation and workspace creation inaccessible to every new account — a complete platform availability failure. This is a one-line fix.

The next highest-priority cluster is the installed dependency gap (SEC-01/SEC-02/SEC-03): pyproject.toml already declares the correct version constraints (`cryptography>=46.0.6`, `fastapi>=0.115.12`) but the installed environment has not been updated. Running `pip install --upgrade` and rebuilding the Docker image resolves all three CVE blockers simultaneously.

**Recommended next steps in priority order:**
1. Fix verify-email token location (RT-02/API-01) — blocks all new users
2. Rebuild environment with correct dependency versions (SEC-01, SEC-02, SEC-03)
3. Add IntegrityError handling to create_link and create_workspace (DB-01, DB-02)
4. Fix login rate limiter fail-open on Redis exception (RT-01, SEC-05)
5. Replace asyncio.get_event_loop() with asyncio.get_running_loop() in 5 files (REL-04)
6. Add CSRFMiddleware to use request.scope["path"] instead of request.url.path (RT-04)
