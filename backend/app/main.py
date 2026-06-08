from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.exceptions import AppError, app_error_handler, validation_error_handler, unhandled_error_handler
from app.middleware import RequestIDMiddleware, SecurityHeadersMiddleware, CSRFMiddleware, BodySizeLimitMiddleware
from app.redis_client import close_redis
from app.routers import auth, workspaces, links, analytics, abuse, health

# ── Sentry ────────────────────────────────────────────────────────────────────
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.1,
    )

# ── Structured logging ────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)


# ── Lifespan (replaces deprecated on_event) ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: warm up the connection pool so the first request doesn't pay cold-start latency
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    # Shutdown: close the Redis connection pool
    await close_redis()
    await engine.dispose()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Snip API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── Middleware (order matters: outermost = first to run) ──────────────────────
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-Id"],
)
app.add_middleware(RequestIDMiddleware)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(links.router)
app.include_router(analytics.router)
app.include_router(abuse.router)
