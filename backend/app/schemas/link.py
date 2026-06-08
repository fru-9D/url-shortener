import uuid
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
import re

_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")

RESERVED_SLUGS = frozenset({
    "admin", "api", "app", "auth", "dashboard",
    "help", "login", "logout", "settings", "signup",
    "static", "www",
})


class CreateLinkRequest(BaseModel):
    destination_url: str = Field(max_length=2048)
    custom_slug: str | None = Field(default=None, max_length=32)

    @field_validator("destination_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only http and https links are supported.")
        if not parsed.netloc:
            raise ValueError("That doesn't look like a URL. Make sure it starts with http:// or https://.")
        return v

    @field_validator("custom_slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _SLUG_RE.match(v):
            raise ValueError("Short links must be 3–32 letters, numbers, hyphens, or underscores.")
        if v.lower() in RESERVED_SLUGS:
            raise ValueError("That short link is reserved. Try a different one.")
        return v


class UpdateLinkRequest(BaseModel):
    destination_url: str = Field(max_length=2048)

    @field_validator("destination_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only http and https links are supported.")
        if not parsed.netloc:
            raise ValueError("That doesn't look like a URL. Make sure it starts with http:// or https://.")
        return v


class LinkResponse(BaseModel):
    id: uuid.UUID
    short_code: str
    short_url: str
    destination_url: str
    is_custom_slug: bool
    click_count: int
    creator_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class LinkListResponse(BaseModel):
    items: list[LinkResponse]
    next_cursor: str | None
