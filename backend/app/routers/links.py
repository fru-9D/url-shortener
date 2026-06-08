"""
Link routes:
  POST   /v1/links
  GET    /v1/links
  GET    /v1/links/{short_code}
  PATCH  /v1/links/{short_code}
  DELETE /v1/links/{short_code}
"""
import base64
import json
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import structlog
from nanoid import generate as nanoid_generate
from fastapi import APIRouter, Query, Header
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import DBDep, MemberDep
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.link import Link
from app.models.abuse_review import AbuseReview, AbuseReviewStatus
from app.models.click import Click
from app.models.user import User
from app.redis_client import get_redis
from app.schemas.link import (
    CreateLinkRequest, UpdateLinkRequest, LinkResponse, LinkListResponse,
)
from app.services.mixpanel import enqueue_event
from app.services.rate_limiter import RateLimiter
from app.services.safe_browsing import check_url

log = structlog.get_logger()
router = APIRouter(prefix="/v1/links", tags=["links"])

_NANOID_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
_NANOID_SIZE = 7


def _generate_short_code() -> str:
    return nanoid_generate(_NANOID_ALPHABET, _NANOID_SIZE)


def _short_url(short_code: str) -> str:
    return f"{settings.snip_base_url}/{short_code}"


def _encode_cursor(created_at: datetime, link_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{link_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.split("|", 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except Exception:
        return None


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """Reject naive datetimes — all timestamps must be UTC-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        from app.exceptions import ValidationError as VE
        raise VE("date_from and date_to must include a timezone offset (e.g. 2024-01-01T00:00:00Z).")
    return dt


async def _batch_click_counts(db: AsyncSession, link_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Single aggregation query for all link_ids in the page — avoids N+1."""
    if not link_ids:
        return {}
    result = await db.execute(
        select(Click.link_id, func.count().label("cnt"))
        .where(Click.link_id.in_(link_ids), Click.is_bot.is_(False))
        .group_by(Click.link_id)
    )
    return {row.link_id: row.cnt for row in result.all()}


def _link_to_response(link: Link, click_count: int) -> LinkResponse:
    return LinkResponse(
        id=link.id,
        short_code=link.short_code,
        short_url=_short_url(link.short_code),
        destination_url=link.destination_url,
        is_custom_slug=link.is_custom_slug,
        click_count=click_count,
        creator_id=link.created_by_id,
        created_at=link.created_at,
        updated_at=link.updated_at,
        deleted_at=link.deleted_at,
    )


# ── Active-link filter: not deleted AND not disabled (disabled is invisible to members) ──
_ACTIVE_LINK_FILTER = (Link.deleted_at.is_(None), Link.disabled_at.is_(None))


@router.post("", status_code=201, response_model=LinkResponse)
async def create_link(
    body: CreateLinkRequest,
    ctx: MemberDep,
    db: DBDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> LinkResponse:
    from app.exceptions import PermissionDeniedError
    user_result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = user_result.scalar_one()
    if user.email_verified_at is None:
        raise PermissionDeniedError("Please verify your email to create links.")

    rl = RateLimiter()
    await rl.check_link_create(str(ctx.user_id))

    # Idempotency check
    if idempotency_key:
        redis = get_redis()
        idem_key = f"idem:link:{ctx.user_id}:{idempotency_key}"
        cached = await redis.get(idem_key)
        if cached:
            return LinkResponse(**json.loads(cached))

    is_custom = False
    if body.custom_slug:
        short_code = body.custom_slug
        is_custom = True
        reuse_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        conflict = await db.execute(
            select(Link).where(
                Link.short_code == short_code,
                Link.deleted_at.is_not(None),
                Link.deleted_at > reuse_cutoff,
            )
        )
        if conflict.scalar_one_or_none():
            raise ConflictError("That short link is already in use. Try a different one.")
        active_conflict = await db.execute(
            select(Link).where(Link.short_code == short_code, Link.deleted_at.is_(None))
        )
        if active_conflict.scalar_one_or_none():
            raise ConflictError("That short link is already in use. Try a different one.")
    else:
        for _ in range(10):
            short_code = _generate_short_code()
            existing = await db.execute(
                select(Link).where(Link.short_code == short_code, Link.deleted_at.is_(None))
            )
            if not existing.scalar_one_or_none():
                break
        else:
            raise ValidationError("Could not generate a unique short code. Please try again.")

    now = datetime.now(timezone.utc)
    link = Link(
        id=uuid.uuid4(),
        workspace_id=ctx.workspace_id,  # type: ignore[arg-type]
        owner_id=ctx.user_id,
        created_by_id=ctx.user_id,
        short_code=short_code,
        destination_url=body.destination_url,
        is_custom_slug=is_custom,
        created_at=now,
        updated_at=now,
    )
    db.add(link)
    try:
        await db.flush()
    except IntegrityError:
        # Concurrent insert beat us to the same short_code — retry with a fresh code
        await db.rollback()
        raise ConflictError("That short link is already in use. Try a different one.")

    # Safe Browsing — fail-open: link created, added to abuse queue if flagged
    flagged = await check_url(body.destination_url)
    if flagged:
        review = AbuseReview(
            id=uuid.uuid4(),
            link_id=link.id,
            workspace_id=ctx.workspace_id,  # type: ignore[arg-type]
            status=AbuseReviewStatus.pending_review,
            flagged_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(review)
        log.info("link_flagged_abuse_queue", link_id=str(link.id))

    host = urlparse(body.destination_url).netloc
    await enqueue_event(
        "link_created",
        {
            "workspace_id": str(ctx.workspace_id),
            "member_id": str(ctx.user_id),
            "short_code": short_code,
            "destination_host": host,
            "is_custom_slug": is_custom,
        },
        insert_id=str(link.id),
    )

    response = _link_to_response(link, 0)

    if idempotency_key:
        redis = get_redis()
        await redis.set(idem_key, json.dumps(response.model_dump(mode="json")), ex=86400)

    return response


@router.get("", response_model=LinkListResponse)
async def list_links(
    ctx: MemberDep,
    db: DBDep,
    after: str | None = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=200),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> LinkListResponse:
    date_from = _ensure_tz(date_from)
    date_to = _ensure_tz(date_to)

    query = (
        select(Link)
        .where(Link.workspace_id == ctx.workspace_id, *_ACTIVE_LINK_FILTER)
        .order_by(Link.created_at.desc(), Link.id.desc())
    )

    if date_from:
        query = query.where(Link.created_at >= date_from)
    if date_to:
        query = query.where(Link.created_at <= date_to)

    if after:
        cursor = _decode_cursor(after)
        if cursor:
            cursor_ts, cursor_id = cursor
            query = query.where(
                (Link.created_at < cursor_ts)
                | ((Link.created_at == cursor_ts) & (Link.id < cursor_id))
            )

    query = query.limit(page_size + 1)
    result = await db.execute(query)
    links = list(result.scalars().all())

    has_more = len(links) > page_size
    items = links[:page_size]
    next_cursor = _encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None

    # Single aggregation query — no N+1
    counts = await _batch_click_counts(db, [lnk.id for lnk in items])
    return LinkListResponse(
        items=[_link_to_response(lnk, counts.get(lnk.id, 0)) for lnk in items],
        next_cursor=next_cursor,
    )


@router.get("/{short_code}", response_model=LinkResponse)
async def get_link(short_code: str, ctx: MemberDep, db: DBDep) -> LinkResponse:
    result = await db.execute(
        select(Link).where(
            Link.short_code == short_code,
            Link.workspace_id == ctx.workspace_id,
            *_ACTIVE_LINK_FILTER,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundError()
    counts = await _batch_click_counts(db, [link.id])
    return _link_to_response(link, counts.get(link.id, 0))


@router.patch("/{short_code}", response_model=LinkResponse)
async def update_link(short_code: str, body: UpdateLinkRequest, ctx: MemberDep, db: DBDep) -> LinkResponse:
    result = await db.execute(
        select(Link).where(
            Link.short_code == short_code,
            Link.workspace_id == ctx.workspace_id,
            *_ACTIVE_LINK_FILTER,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundError()

    now = datetime.now(timezone.utc)

    flagged = await check_url(body.destination_url)
    if flagged:
        review = AbuseReview(
            id=uuid.uuid4(),
            link_id=link.id,
            workspace_id=ctx.workspace_id,  # type: ignore[arg-type]
            status=AbuseReviewStatus.pending_review,
            flagged_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(review)
        log.info("link_edit_flagged", link_id=str(link.id))

    link.destination_url = body.destination_url
    link.updated_at = now

    counts = await _batch_click_counts(db, [link.id])
    return _link_to_response(link, counts.get(link.id, 0))


@router.delete("/{short_code}", status_code=204)
async def delete_link(short_code: str, ctx: MemberDep, db: DBDep) -> None:
    result = await db.execute(
        select(Link).where(
            Link.short_code == short_code,
            Link.workspace_id == ctx.workspace_id,
            Link.deleted_at.is_(None),
            # Allow soft-deleting disabled links
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise NotFoundError()

    now = datetime.now(timezone.utc)
    link.deleted_at = now
    link.updated_at = now

    # Auto-transition any pending abuse review
    pending_reviews = await db.execute(
        select(AbuseReview).where(
            AbuseReview.link_id == link.id,
            AbuseReview.status == AbuseReviewStatus.pending_review,
        )
    )
    for review in pending_reviews.scalars().all():
        review.status = AbuseReviewStatus.hard_deleted
        review.reviewed_at = now
        review.updated_at = now
