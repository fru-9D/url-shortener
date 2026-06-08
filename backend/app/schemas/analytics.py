from pydantic import BaseModel
from datetime import date


class DailyClickBucket(BaseModel):
    date: date
    clicks: int


class CountryBucket(BaseModel):
    country_code: str
    clicks: int


class LinkAnalyticsResponse(BaseModel):
    total_clicks: int
    bot_clicks: int
    human_clicks: int
    daily_clicks: list[DailyClickBucket]
    country_breakdown: list[CountryBucket]
