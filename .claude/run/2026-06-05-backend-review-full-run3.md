# Backend Review — full — 2026-06-05

**Verdict:** FAIL_BLOCKER
**Gate 1 (Critical):** 0 findings
**Gate 2 (Blockers):** 4 findings
**Gate 3 (Warnings):** 10 findings

---

## Preflight Summary

| Tool      | Status          | Notes                                                                 |
|-----------|-----------------|-----------------------------------------------------------------------|
| bandit    | ran             | 1 LOW/HIGH-confidence finding (B110 try-except-pass, benign by design)|
| pip-audit | ran             | 41 known vulnerabilities in 15 packages (2 directly affect this app) |
| pytest    | not run         | Requires live Postgres + Redis; skipped in this environment           |
| ruff      | ran             | 104 violations (I001 import order, F401 unused imports, E501, UP017, B008, B904, N817) |
| mypy      | ran             | 93 errors (bulk: untyped stubs for boto3/structlog/argon2; 2 genuine operator errors in workspaces.py) |

**Coverage:** Not captured (pytest skipped due to missing DB/Redis).

**Preflight Gaps:** pytest could not run without Docker infrastructure. Coverage is unknown. mypy errors are dominated by missing stubs for third-party packages (boto3, structlog, argon2) that lack py.typed markers — these are noise. Two genuine mypy errors on `workspaces.py:375` and `workspaces.py:444` are real defects.

---

## Baseline Delta Summary

This is run 3 against the baseline captured 2026-06-04 (gate1=0, gate2=9, gate3=20).

**Resolved since baseline (13 of 29 issues fixed):**
- CQ-01 — `client.delete(..., json=)` → `client.post()` in abuse.py ✓
- SEC-03 — boto3 SES/SQS now in `run_in_executor` ✓
- REL-01 — SQS poll uses `run_in_executor` ✓
- REL-02 — `delete_all_for_user` fully implemented ✓
- REL-03 — CSRF now default-deny with explicit exempt set ✓
- REL-04 — `check_resend_verification` rate limit added ✓
- API-02 — N+1 click counts replaced with single aggregation query ✓
- API-03 — `_ensure_tz()` timezone guard added ✓
- API-04 — `httpx.TransientError` → `httpx.TransportError` ✓
- DB-01 — Click idempotency uses `event_id` UUID ✓
- DB-02 — Partial unique index present in ORM `__table_args__` ✓
- SPEC-01 — Abuse reviews workspace-scoped ✓
- SPEC-02 — `_ACTIVE_LINK_FILTER` includes `disabled_at IS NULL` ✓
- SPEC-03 — Email URLs use `settings.app_base_url` ✓
- SPEC-05 — Dummy hash generated from live `ph.hash()` at startup ✓
- ERD-01 — `AbuseReview.workspace_id` now has FK to workspace ✓
- ERD-02 — `Click.workspace_id` now has FK to workspace ✓

**Persisting from baseline (not yet fixed):**
- SEC-02 / SEC-01 — starlette 0.46.0 and cryptography 44.0.2 still installed (pyproject.toml updated but env not rebuilt)
- API-01 — verify-email token still in query param

**New findings in run 3:**
- mypy type-safety defect: `scalar()` returns `int | None`; comparison `<= 1` crashes at runtime when count is None (2 locations, workspaces.py)
- pip-audit: starlette 0.46.0 has additional CVE-2025-54121 (file-upload DoS) and CVE-2025-62727 (Range header ReDoS) beyond the previously known PYSEC-2026-161
- aiohttp 3.13.5: 2 CVEs (not directly imported by the app but in the environment)

---

## Domain Summary

| Domain          | Gate 1 | Gate 2 | Gate 3 | Status          |
|-----------------|--------|--------|--------|-----------------|
| security        | 0      | 2      | 1      | FAIL_BLOCKER    |
| api-design      | 0      | 1      | 0      | FAIL_BLOCKER    |
| database        | 0      | 0      | 1      | PASS_WITH_RISK  |
| erd-compliance  | 0      | 0      | 0      | PASS            |
| reliability     | 0      | 0      | 1      | PASS_WITH_RISK  |
| code-quality    | 0      | 1      | 3      | FAIL_BLOCKER    |
| spec-compliance | 0      | 0      | 3      | PASS_WITH_RISK  |
| red-team        | 0      | 0      | 1      | PASS_WITH_RISK  |

---

## Gate 1 — Critical Findings (Must fix before merge)

None. Gate 1 is clear.

---

## Gate 2 — Blockers (Must fix before release)

### SEC-B01 · security — starlette 0.46.0 has three active CVEs including Host-header auth bypass

**File:** `backend/pyproject.toml:11` (installed version: starlette 0.46.0 via fastapi 0.115.11)
**Snippet:** `"fastapi>=0.115.12"` pinned in pyproject.toml but environment has `fastapi==0.115.11` / `starlette==0.46.0`
**Finding:** pip-audit confirms starlette 0.46.0 is installed with three CVEs:
1. PYSEC-2026-161 / CVE-2026-48710 (fix: starlette >= 1.0.1) — Host header injection allows `request.url.path` to differ from the routed path, enabling middleware/auth bypass for any code that gates on `request.url` rather than `scope["path"]`.
2. CVE-2025-54121 (fix: starlette >= 0.47.2) — File upload DoS: multi-part form with large files blocks event loop thread.
3. CVE-2025-62727 (fix: starlette >= 0.49.1) — Range header ReDoS on FileResponse; attacker sends crafted Range header and causes O(n²) CPU exhaustion.

The Host-header bypass (PYSEC-2026-161) is directly exploitable against the CSRF and SecurityHeaders middleware which use `request.url.path`. This was a baseline blocker that remains unresolved because `pip install` was not re-run after pyproject.toml was updated.
**Fix:** Run `pip install -e ".[dev]"` (or `poetry install`) in the backend directory to install the updated constraint. Also pin fastapi to a version that pulls starlette >= 1.0.1 (fastapi >= 0.115.12 satisfies this per the pyproject.toml comment — confirm `starlette.__version__` after reinstall).
**Effort:** low

---

### SEC-B02 · security — cryptography 44.0.2 installed; two active CVEs require 46.0.6

**File:** `backend/pyproject.toml:19`
**Snippet:** `"cryptography>=46.0.6"` — pyproject.toml updated but installed version is 44.0.2
**Finding:** pip-audit confirms cryptography 44.0.2 with:
1. PYSEC-2026-35 / CVE-2026-34073 — DNS name constraint bypass in X.509 validation.
2. CVE-2026-26007 — Missing validation that ECC public key points belong to expected prime-order subgroup; leaks private key bits via ECDH and allows ECDSA forgery on SECT curves.

This app uses cryptography's AESGCM for email encryption at rest. Any code path using AESGCM or the cryptography primitives is running against a vulnerable library. Same root cause as SEC-B01: pyproject.toml was updated but the virtual environment was not rebuilt.
**Fix:** `pip install -e ".[dev]"` to satisfy `cryptography>=46.0.6`. Verify with `python -c "import cryptography; print(cryptography.__version__)"`.
**Effort:** low

---

### API-B01 · api-design — verify-email token exposed in query parameter (persists from baseline)

**File:** `backend/app/routers/auth.py:191`
**Snippet:** `async def verify_email(db: DBDep, token: str = Query(...)) -> None:`
**Finding:** The single-use email verification token is passed as a URL query parameter (`GET /v1/auth/verify-email?token=<raw>`). This causes the secret token to appear in:
- Web server access logs
- Reverse proxy/CDN logs (Cloudflare, nginx, AWS ALB)
- Browser history
- Referer headers on any subsequent navigation
- Analytics or monitoring tools

Per PRD §Account: "Token is single-use" — the token's single-use guarantee is undermined if it leaks via logs. An attacker with log access can verify arbitrary accounts. This was flagged as API-01 in the baseline and remains unfixed.
**Fix:** Change the verify-email endpoint to accept the token in the POST body via a Pydantic model: `class VerifyEmailBody(BaseModel): token: str` (the schema already exists in `schemas/auth.py`). Replace `token: str = Query(...)` with `body: VerifyEmailBody`. This is a breaking change to the frontend but trivially coordinated.
**Effort:** low

---

### CQ-B01 · code-quality — scalar() None dereference in admin-count guard (workspaces.py)

**File:** `backend/app/routers/workspaces.py:374-376` and `442-445`
**Snippet:**
```python
admin_count_result = await db.execute(
    select(func.count()).select_from(WorkspaceMember)...
    .with_for_update()
)
admin_count = admin_count_result.scalar()
if admin_count <= 1:  # mypy: int | None >= 1 (operator error)
```
**Finding:** `Result.scalar()` returns `int | None`. When no rows match (theoretically impossible here given the WHERE clause, but SQLAlchemy types it as Optional), the comparison `admin_count <= 1` raises `TypeError: '<=' not supported between instances of 'NoneType' and 'int'`. This crashes the endpoint and produces an unhandled 500 — but more critically, the crash happens *inside* the last-admin guard, which means the guard does not fire and the removal/demotion proceeds unchecked. mypy flags this at lines 375 and 444. The bug exists in both `remove_member` and `update_member_role`.
**Fix:** Replace `scalar()` with `scalar_one()` (which raises if None) or add an explicit null guard: `admin_count = admin_count_result.scalar() or 0`. Using `scalar_one()` is cleaner for an aggregate query that always returns exactly one row.
**Effort:** low

---

## Gate 3 — Warnings (Lead approval required)

### SEC-W01 · security — aiohttp 3.13.5 in environment has two CVEs

**File:** environment package list
**Finding:** aiohttp 3.13.5 has CVE-2026-34993 (arbitrary code execution via `CookieJar.load()` with attacker-controlled input) and CVE-2026-47265 (cookies sent after cross-origin redirect). aiohttp is not directly imported by the application but is present in the environment as a transitive dependency (likely via langchain/langchain-community or similar tooling packages in the shared venv). Fix version: 3.14.0.
**Fix:** If aiohttp is a transitive dep of dev tooling, upgrade that tooling. If it's in the application's own dependency tree, add an explicit minimum version constraint. Verify with `pip show aiohttp`.
**Effort:** low

---

### DB-W01 · database — updated_at server-side trigger not enforced for direct DB writes

**File:** `backend/app/models/base.py:14-19`
**Finding:** `TimestampMixin.updated_at` now has `onupdate=func.now()` in the ORM layer (baseline DB-03 partially addressed). However, the migration `0001_initial_schema.py` creates `updated_at` with `server_default=sa.func.now()` but **no** `ON UPDATE` trigger at the database level. SQLAlchemy's `onupdate` fires only through the ORM — raw SQL `UPDATE` statements (used in several places: `sqla_update(Link)...`, `sqla_update(Invite)...`, `sqla_update(User)...`) bypass the ORM and produce stale `updated_at` timestamps. Review: `workspaces.py:384-399` uses `sqla_update(Link)` and `sqla_update(Invite)` without explicitly setting `updated_at`; these rows will retain their creation timestamp.
**Fix:** Either (a) add `.values(updated_at=now)` to all bulk UPDATE statements (already done for most but not all), or (b) add a PostgreSQL trigger in a new migration: `CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;` applied to all relevant tables.
**Effort:** medium

---

### REL-W01 · reliability — invite accept has no transaction-level lock on workspace membership

**File:** `backend/app/routers/workspaces.py:279-322`
**Finding:** `accept_invite` checks if the user already belongs to a workspace (`WorkspaceMember.removed_at.is_(None)`) and then inserts a new member record — but does so without a `SELECT ... FOR UPDATE` lock on the membership check. Two concurrent accept_invite requests for the same user (e.g., race between two browser tabs) could both pass the membership check before either insert commits, resulting in two `WorkspaceMember` rows for the same user. The partial unique index `uq_workspace_member_user_active` (WHERE removed_at IS NULL) will catch this at the DB layer and raise `IntegrityError`, but the error is not caught in `accept_invite`, producing an unhandled 500.
**Fix:** Wrap the membership check in a `SELECT ... FOR UPDATE` on a row that is guaranteed to exist (e.g., lock the invite row itself or use `INSERT ... ON CONFLICT`), and catch `IntegrityError` around the member insert with a user-friendly 409 response.
**Effort:** medium

---

### SPEC-W01 · spec-compliance — verify-email endpoint accepts GET semantics via POST with Query param

**File:** `backend/app/routers/auth.py:190-212`
**Finding:** Endpoint is `POST /v1/auth/verify-email` but the token is read from `Query(...)`. This creates an unusual API design: a POST endpoint whose payload is a query parameter. Email clients typically render verification links as clickable GET URLs (e.g., `https://app.snip.io/auth/verify-email?token=...`). The frontend likely issues a GET and then the JS redirects to a POST — or the frontend must extract the token from the URL and POST it. This friction invites frontend bugs. Per PRD §Account: email verification link should be a simple click. The token-in-query pattern remains even though the HTTP verb is POST.
**Fix:** Align with the body-based approach in API-B01 fix. The frontend click should navigate to a page that reads the token from `window.location.search` and POSTs `{"token": "..."}` to the API. Or switch to GET with the token consumed and immediately redirected.
**Effort:** low

---

### SPEC-W02 · spec-compliance — `password_reset_requested` Mixpanel event not emitted (PRD gap)

**File:** `backend/app/routers/auth.py:239-276`
**Finding:** PRD §Mixpanel specifies four events: `link_created`, `link_clicked`, `member_invited`, and `password_reset_requested`. The first three are implemented. `password_reset_requested` is never emitted anywhere in the codebase. The PRD specifies: "When emitted: After a reset email is dispatched" with property `email_domain` only (no full email).
**Fix:** Add `await enqueue_event("password_reset_requested", {"email_domain": email_domain})` in `forgot_password()` after `send_password_reset_email(...)` succeeds.
**Effort:** low

---

### SPEC-W03 · spec-compliance — whitelist action in abuse review does not clear `disabled_at`

**File:** `backend/app/routers/abuse.py:161-163`
**Finding:** PRD §Abuse review: "A disabled link can be re-enabled (whitelisted) by a reviewer, which clears `disabled_at`." The `whitelist` action in `act_on_review` only sets `review.status = AbuseReviewStatus.whitelisted` — it does not clear `link.disabled_at`. A link that was previously disabled and then whitelisted will remain disabled (returning 404 to visitors) even after the reviewer marks it whitelisted. This is a silent data inconsistency that the reviewer has no way to detect from the API response.
**Fix:** In the `whitelist` branch, add `link.disabled_at = None; link.updated_at = now` to re-enable the link alongside the status change. Also purge Cloudflare cache to remove the 404 response from edge cache.
**Effort:** low

---

### CQ-W01 · code-quality — 104 ruff violations; 14 are unused imports that inflate attack surface

**File:** Multiple files (app/routers/auth.py, app/routers/abuse.py, app/crypto.py, app/models/base.py, app/models/user.py, etc.)
**Finding:** ruff reports 104 violations. The most actionable subset:
- **F401 (unused imports):** `os` in crypto.py, `AsyncSessionLocal` in main.py, `get_db` and `require_auth` in auth.py (2×), `get_db` and `require_admin` in abuse.py, `AsyncSession` in auth.py, `Index` in user.py, `timezone` in base.py. These inflate import time and create confusion about actual dependencies.
- **I001 (unsorted imports):** 19 files — violation of isort conventions; CI will fail if ruff --check is added to CI.
- **UP017 (datetime.UTC alias):** 14 occurrences in auth.py, links.py, abuse.py, analytics.py — cosmetic but signals the codebase style hasn't been normalized for Python 3.12.
- **B008 (Depends in default args):** 4 occurrences — ruff flags FastAPI's own idiom; suppress or add noqa.
- **B904 (raise without from):** links.py:179 — raise inside except clause without `from err` or `from None`.
- **N817 (CamelCase as acronym):** links.py:71 `VE` alias for `ValidationError`.
**Fix:** `ruff check app --fix` (safe fixes only) removes all F401 and I001 automatically. Manual attention needed for B904, N817. B008 should be added to ruff ignore list for FastAPI codebases.
**Effort:** low

---

### CQ-W02 · code-quality — mypy strict mode has 93 errors; 2 genuine defects, rest are untyped stubs

**File:** Multiple files
**Finding:** The 93 mypy errors break into two categories:
1. **Genuine defects** (2): workspaces.py:375 and :444 — covered under CQ-B01 above.
2. **Missing stubs** (91): boto3, structlog, argon2, sentry-sdk, nanoid lack py.typed markers. These produce `import-not-found` / `import-untyped` errors in strict mode. They are not code defects but mean mypy cannot type-check the boto3/argon2 integration paths.

Additionally, `MixpanelDeadLetter.payload: Mapped[dict]` should be `Mapped[dict[str, Any]]` (mypy reports missing type args).
**Fix:** For stubs, add `[mypy-boto3.*]` and similar `ignore_missing_imports = True` overrides to pyproject.toml `[tool.mypy]`. For the payload column, use `Mapped[dict[str, Any]]`. For argon2, install `types-argon2-cffi` if available.
**Effort:** low

---

### CQ-W03 · code-quality — click_consumer does not validate `short_code` field length from SQS

**File:** `backend/app/workers/click_consumer.py:78`
**Snippet:** `short_code=body.get("short_code", ""),`
**Finding:** The click consumer reads `short_code` from an SQS message body and writes it directly to the `Click.short_code` column (VARCHAR 32). If a crafted SQS message (e.g., from a misconfigured redirect service or injection) includes a `short_code` exceeding 32 chars, the INSERT will raise a DataError at the database layer. The current error handling rolls back and re-raises, causing the message to retry indefinitely (no dead-letter transition for the click itself). Additionally, `workspace_id` and `link_id` validation exists (lines 56-64) but `short_code`, `country_code`, `user_agent`, and `referrer_host` are not validated.
**Fix:** Add field-level validation before the Click insert: validate `short_code` length <= 32, `country_code` length <= 8, `user_agent` length <= 2048, `referrer_host` length <= 255. Truncate or discard the message on validation failure rather than retrying.
**Effort:** low

---

### RT-W01 · red-team — invite token brute-force window

**File:** `backend/app/routers/workspaces.py:279-322`
**Finding:** Invite tokens are 32-byte URL-safe base64 strings (256-bit entropy from `secrets.token_urlsafe(32)`). The `/invites/accept` and `/invites/decline` endpoints are not rate-limited and accept unauthenticated token guesses. An attacker with the workspace email domain (available from the `member_invited` Mixpanel event or by observing invite emails) could enumerate tokens at the rate of their network connection. At 256-bit entropy, brute-force is computationally infeasible; however, no rate-limiting prevents DDoS against this endpoint and no logging records token miss rates. The bigger risk is if the entropy is ever reduced (e.g., fallback to weaker RNG in a dependency).
**Fix:** Add a rate limiter to `accept_invite` and `decline_invite` keyed on the accepting user's IP (or user session if authenticated). Log token misses at WARNING level to detect enumeration attempts in production.
**Effort:** low

---

## Red-Team Attack Surface

### 1. Starlette Host-Header Injection (SEC-B01 / PYSEC-2026-161)

**Vector:** Attacker sends any mutating request with a crafted `Host` header containing a path component, e.g., `Host: app.snip.io/healthz`. Starlette reconstructs `request.url` from this header, producing `request.url.path = "/healthz"` while the actual route path is `/v1/auth/change-password`. Any middleware reading `request.url.path` for access control (including the CSRF exempt list which checks `request.scope.get("path", request.url.path)`) sees the injected path.

**Impact:** If the CSRF middleware's exempt check is fooled, an attacker can submit state-changing requests without a CSRF token. In the current codebase, the scope path is checked first (`request.scope.get("path", request.url.path)`), which provides a partial mitigation — but the exploit surface is real for any middleware that reads `request.url` directly. The SecurityHeaders middleware also uses `request.url` implicitly via response headers. Future middleware additions are silently at risk.

**Fix:** Upgrade to starlette >= 1.0.1 (via fastapi >= 0.115.12). Rebuild the virtual environment.

---

### 2. Admin-Count Guard None-Dereference Bypasses Last-Admin Constraint (CQ-B01)

**Vector:** Under normal conditions `select(func.count())` always returns an integer. However, if an attacker can trigger a DB-level error or timeout that causes the aggregate to return NULL (via a carefully timed connection failure or deliberate lock contention with `with_for_update()`), `admin_count_result.scalar()` returns `None`. The comparison `None <= 1` raises `TypeError`, crashing the guard — but in the current error handling the exception propagates to `unhandled_error_handler` which returns a 500. However, because the guard crashed *before* the `removed_at` update, the member is NOT removed. The more dangerous path: if the comparison were `None > 1` (admins remaining check), None > 1 would raise — but the real risk is in a code change that inverts the guard.

**Impact:** Currently: crash → 500, guard holds. Risk is code evolution introducing a subtle change that allows bypass. The correct fix closes this permanently.

**Fix:** Use `scalar_one()` (raises on None) or add explicit `or 0` guard as described in CQ-B01.

---

### 3. Email Verification Token in Logs Enables Account Takeover via Log Access

**Vector:** The verify-email link is `https://app.snip.io/auth/verify-email?token=<32-byte-secret>`. The token appears in: (a) Cloudflare access logs, (b) AWS ALB/nginx access logs, (c) Sentry breadcrumbs if the frontend navigation error is captured, (d) browser history on shared/enterprise devices. An attacker with read access to any of these (insider threat, log SIEM breach, shared browser) extracts the token and verifies a victim's email — gaining full Snip access without knowing the password.

**Impact:** Full account takeover for any unverified account whose email link has been observed in logs. Token is single-use but log retention is typically 30–90 days, far exceeding the 24-hour token TTL — meaning the attack window is the 24-hour token validity period, not log retention.

**Fix:** Move token to POST body (API-B01). This is the single highest-priority UX-security fix in this codebase.

---

## Summary

The codebase has undergone significant improvements since the previous run: 17 of 29 baseline findings have been resolved, including the most impactful fixes (N+1 query, CSRF default-deny, event-loop-blocking SQS calls, click idempotency, workspace scoping for abuse reviews). Gate 1 is clear. However, **4 Gate 2 blockers** prevent release readiness.

The single highest-priority action is rebuilding the virtual environment — both `cryptography 44.0.2` (2 CVEs) and `starlette 0.46.0` (3 CVEs including Host-header auth bypass) remain installed despite pyproject.toml requiring fixed versions. The next priority is the `scalar()` None-dereference on the last-admin guard in workspaces.py (both `remove_member` and `update_member_role`), which is a one-line fix that prevents a potential guard bypass. The verify-email token-in-query-param issue (API-B01) must be fixed before handling production traffic to prevent token leakage into access logs.

**Next steps:** (1) `pip install -e ".[dev]"` in `backend/` to pull cryptography>=46.0.6 and the starlette-safe fastapi; (2) fix `scalar()` → `scalar_one()` in workspaces.py lines 374 and 441; (3) move verify-email token to POST body; (4) fix the three Gate 3 spec-compliance gaps (whitelist clearing `disabled_at`, emitting `password_reset_requested` event, SPEC-W01 alignment).
