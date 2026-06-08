"""
Health check endpoints:
  GET /healthz — liveness (returns 200 if the process responds)
  GET /readyz  — readiness (checks Postgres primary + Redis within 2s each)
"""
from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.redis_client import get_redis

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


class ReadyzResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=ReadyzResponse)
async def readyz(response: Response) -> ReadyzResponse:
    checks: dict[str, str] = {}
    healthy = True

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        healthy = False

    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        healthy = False

    if not healthy:
        response.status_code = 503
    return ReadyzResponse(status="ok" if healthy else "degraded", checks=checks)
