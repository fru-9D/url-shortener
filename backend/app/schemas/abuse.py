import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.abuse_review import AbuseReviewStatus
import enum


class AbuseReviewAction(str, enum.Enum):
    whitelist = "whitelist"
    disable = "disable"
    hard_delete = "hard_delete"


class UpdateAbuseReviewRequest(BaseModel):
    action: AbuseReviewAction


class AbuseReviewResponse(BaseModel):
    id: uuid.UUID
    link_id: uuid.UUID
    workspace_id: uuid.UUID
    status: AbuseReviewStatus
    flagged_at: datetime
    reviewed_at: datetime | None = None
    reviewer_id: uuid.UUID | None = None


class AbuseReviewListResponse(BaseModel):
    items: list[AbuseReviewResponse]
    next_cursor: str | None


class AbuseReviewActionResponse(BaseModel):
    action: AbuseReviewAction
    cache_purged: bool | None = None
