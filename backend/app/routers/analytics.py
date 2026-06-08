"""
Analytics routes:
  GET /v1/links/{short_code}/analytics — click count + 30-day time-series + country breakdown
"""
from datetime import datetime, timezone, timedelta, date

from fastapi import APIRouter
from sqlalchemy import select, func, cast, Date

from app.dependencies import DBDep, MemberDep
from app.exceptions import NotFoundError
from app.models.click import Click
from app.models.link import Link
from app.schemas.analytics import LinkAnalyticsResponse, DailyClickBucket, CountryBucket

router = APIRouter(prefix="/v1/links", tags=["analytics"])


@router.get("/{short_code}/analytics", response_model=LinkAnalyticsResponse)
async def get_link_analytics(
    short_code: str,
    ctx: MemberDep,
    db: DBDep,
) -> LinkAnalyticsResponse:
    # Verify link belongs to this workspace
    link_result = await db.execute(
        select(Link).where(
            Link.short_code == short_code,
            Link.workspace_id == ctx.workspace_id,
            Link.deleted_at.is_(None),
        )
    )
    link = link_result.scalar_one_or_none()
    if not link:
        raise NotFoundError()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)

    # Total click counts (human vs bot)
    counts = await db.execute(
        select(Click.is_bot, func.count().label("cnt"))
        .where(Click.link_id == link.id)
        .group_by(Click.is_bot)
    )
    bot_clicks = 0
    human_clicks = 0
    for is_bot, cnt in counts.all():
        if is_bot:
            bot_clicks = cnt
        else:
            human_clicks = cnt

    # Daily time-series for last 30 days (human only, UTC day buckets)
    daily_result = await db.execute(
        select(
            cast(Click.clicked_at, Date).label("day"),
            func.count().label("cnt"),
        )
        .where(
            Click.link_id == link.id,
            Click.is_bot.is_(False),
            Click.clicked_at >= since,
        )
        .group_by("day")
        .order_by("day")
    )
    daily_map: dict[date, int] = {row.day: row.cnt for row in daily_result.all()}

    # Fill all 30 days (even zeros)
    daily_clicks = []
    for i in range(30):
        day = (now - timedelta(days=29 - i)).date()
        daily_clicks.append(DailyClickBucket(date=day, clicks=daily_map.get(day, 0)))

    # Country breakdown (human only, last 30 days)
    country_result = await db.execute(
        select(Click.country_code, func.count().label("cnt"))
        .where(
            Click.link_id == link.id,
            Click.is_bot.is_(False),
            Click.clicked_at >= since,
        )
        .group_by(Click.country_code)
        .order_by(func.count().desc())
    )
    country_breakdown = [
        CountryBucket(country_code=row.country_code, clicks=row.cnt)
        for row in country_result.all()
    ]

    return LinkAnalyticsResponse(
        total_clicks=human_clicks + bot_clicks,
        bot_clicks=bot_clicks,
        human_clicks=human_clicks,
        daily_clicks=daily_clicks,
        country_breakdown=country_breakdown,
    )
