"""
Custom middleware stack:
  RequestIDMiddleware   — attaches/propagates X-Request-Id (validates as UUID in production)
  SecurityHeadersMiddleware — injects HSTS, CSP, etc.
  CSRFMiddleware        — double-submit cookie; protects ALL mutating requests by default,
                          with an explicit exempt set for paths that don't need it.
  BodySizeLimitMiddleware — rejects requests whose Content-Length exceeds the cap (413).
"""
import secrets
import uuid
from collections.abc import Callable, Awaitable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

# Maximum allowed request body: 64 KB (covers any legitimate JSON payload; files not accepted)
_MAX_BODY_BYTES = 64 * 1024
# Idempotency-Key header must fit in a single UUID or short opaque string
_MAX_IDEMPOTENCY_KEY_LEN = 128

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_CSRF_HEADER = "X-CSRF-Token"
_CSRF_COOKIE = "csrf_token"

# Paths explicitly exempt from CSRF (must be kept minimal)
_CSRF_EXEMPT = frozenset({
    "/healthz",
    "/readyz",
})


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject any request whose Content-Length exceeds the cap before reading the body.
    Also rejects oversized Idempotency-Key headers.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return Response(
                content='{"error":{"code":"payload_too_large","message":"Request body exceeds the 64 KB limit.","request_id":""}}',
                status_code=413,
                media_type="application/json",
            )

        idem_key = request.headers.get("Idempotency-Key", "")
        if len(idem_key) > _MAX_IDEMPOTENCY_KEY_LEN:
            return Response(
                content='{"error":{"code":"validation_error","message":"Idempotency-Key header too long.","request_id":""}}',
                status_code=422,
                media_type="application/json",
            )

        return await call_next(request)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        incoming = request.headers.get("X-Request-Id", "")
        if incoming and (not settings.is_production or _is_valid_uuid(incoming)):
            request_id = incoming
        else:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection.

    Default: ALL mutating requests are protected.
    Exempt paths must be listed in _CSRF_EXEMPT above.
    This is safer than opt-in (where a new endpoint outside /v1/ would silently bypass CSRF).
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if (
            request.method not in _SAFE_METHODS
            and request.scope.get("path", request.url.path) not in _CSRF_EXEMPT
        ):
            cookie_token = request.cookies.get(_CSRF_COOKIE)
            header_token = request.headers.get(_CSRF_HEADER)
            if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                return Response(
                    content='{"error":{"code":"csrf_invalid","message":"CSRF token invalid or missing.","request_id":""}}',
                    status_code=403,
                    media_type="application/json",
                )

        response = await call_next(request)

        if _CSRF_COOKIE not in request.cookies:
            token = secrets.token_hex(32)
            response.set_cookie(
                _CSRF_COOKIE,
                token,
                httponly=False,   # JS-readable — required for double-submit pattern
                secure=True,
                samesite="lax",
                max_age=86400 * 30,
            )
        return response
