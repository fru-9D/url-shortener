"""
Abuse review routes (internal ops):
  GET   /v1/ops/abuse-reviews           — list pending reviews (scoped to caller's workspace)
  PATCH /v1/ops/abuse-reviews/{id}      — act on a review (whitelist | disable | hard_delete)
"""
import base64
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import APIRouter, Query
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.dependencies import require_admin, AdminDep, DBDep
from app.exceptions import NotFoundError
from app.models.abuse_review import AbuseReview, AbuseReviewStatus
from app.models.link import Link
from app.schemas.abuse import (
    AbuseReviewResponse, AbuseReviewListResponse,
    UpdateAbuseReviewRequest, AbuseReviewAction, AbuseReviewActionResponse,
)

log = structlog.get_logger()
router = APIRouter(prefix="/v1/ops/abuse-reviews", tags=["ops"])


# ── Cursor helpers ────────────────────────────────────────────────────────────

def _encode_cursor(flagged_at: datetime, review_id: uuid.UUID) -> str:
    raw = f"{flagged_at.isoformat()}|{review_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.split("|", 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except Exception:
        return None


# ── Cloudflare cache purge ────────────────────────────────────────────────────

async def _purge_cloudflare_cache(short_code: str) -> bool:
    if not settings.cloudflare_zone_id or not settings.cloudflare_api_token:
        log.warning("cf_purge_skipped", reason="not_configured", short_code=short_code)
        return True  # Dev mode — treat as success

    url = f"https://api.cloudflare.com/client/v4/zones/{settings.cloudflare_zone_id}/purge_cache"
    payload = {"files": [f"{settings.snip_base_url}/{short_code}"]}

    for attempt in range(3):
        backoff = [0.0, 0.5, 2.0][attempt]
        if backoff:
            import asyncio
            await asyncio.sleep(backoff)
        try:
            async with httpx.AsyncClient(timeout=settings.cloudflare_purge_timeout) as client:
                # Cloudflare Cache Purge uses POST with a JSON body, not DELETE
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
                    json=payload,
                )
            if resp.is_success:
                return True
            log.error("cf_purge_failed", status=resp.status_code, short_code=short_code)
        except Exception as exc:
            log.error("cf_purge_exception", exc=str(exc), short_code=short_code, attempt=attempt)

    log.error("cf_purge_exhausted", short_code=short_code)
    return False


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=AbuseReviewListResponse)
async def list_abuse_reviews(
    ctx: AdminDep,
    db: DBDep,
    after: str | None = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AbuseReviewListResponse:
    # Scoped to the caller's workspace — admins can only act on their own workspace's reviews
    query = (
        select(AbuseReview)
        .where(
            AbuseReview.workspace_id == ctx.workspace_id,
            AbuseReview.status == AbuseReviewStatus.pending_review,
        )
        .order_by(AbuseReview.flagged_at.asc(), AbuseReview.id.asc())
    )

    if after:
        cursor = _decode_cursor(after)
        if cursor:
            cursor_ts, cursor_id = cursor
            query = query.where(
                (AbuseReview.flagged_at > cursor_ts)
                | ((AbuseReview.flagged_at == cursor_ts) & (AbuseReview.id > cursor_id))
            )

    query = query.limit(page_size + 1)
    result = await db.execute(query)
    reviews = list(result.scalars().all())

    has_more = len(reviews) > page_size
    items = reviews[:page_size]
    next_cursor = _encode_cursor(items[-1].flagged_at, items[-1].id) if has_more and items else None

    return AbuseReviewListResponse(
        items=[
            AbuseReviewResponse(
                id=r.id,
                link_id=r.link_id,
                workspace_id=r.workspace_id,
                status=r.status,
                flagged_at=r.flagged_at,
                reviewed_at=r.reviewed_at,
                reviewer_id=r.reviewer_id,
            )
            for r in items
        ],
        next_cursor=next_cursor,
    )


@router.patch("/{review_id}", response_model=AbuseReviewActionResponse)
async def act_on_review(
    review_id: uuid.UUID,
    body: UpdateAbuseReviewRequest,
    ctx: AdminDep,
    db: DBDep,
) -> AbuseReviewActionResponse:
    """Single PATCH endpoint for all ops state transitions (REST-idiomatic)."""
    result = await db.execute(
        select(AbuseReview, Link)
        .join(Link, Link.id == AbuseReview.link_id)
        .where(
            AbuseReview.id == review_id,
            # Workspace scoping — admins can only act on their own workspace's reviews
            AbuseReview.workspace_id == ctx.workspace_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise NotFoundError()

    review, link = row
    now = datetime.now(timezone.utc)
    review.reviewer_id = ctx.user_id
    review.reviewed_at = now
    review.updated_at = now

    cache_purged: bool | None = None

    if body.action == AbuseReviewAction.whitelist:
        review.status = AbuseReviewStatus.whitelisted

    elif body.action == AbuseReviewAction.disable:
        review.status = AbuseReviewStatus.disabled
        link.disabled_at = now
        link.updated_at = now
        await db.flush()  # Commit DB state before attempting purge
        cache_purged = await _purge_cloudflare_cache(link.short_code)
        if not cache_purged:
            log.error("cf_purge_failed_after_disable", link_id=str(link.id))

    elif body.action == AbuseReviewAction.hard_delete:
        review.status = AbuseReviewStatus.hard_deleted
        short_code = link.short_code
        await db.delete(link)
        await db.flush()
        cache_purged = await _purge_cloudflare_cache(short_code)
        if not cache_purged:
            log.error("cf_purge_failed_after_hard_delete", short_code=short_code)

    return AbuseReviewActionResponse(action=body.action, cache_purged=cache_purged)
