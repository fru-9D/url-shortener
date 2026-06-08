import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from app.models.workspace import MemberRole
from app.models.invite import InviteRole, InviteStatus


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=64)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    role: MemberRole
    joined_at: datetime | None


class InviteRequest(BaseModel):
    email: EmailStr
    role: InviteRole


class InviteResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: InviteRole
    status: InviteStatus
    expires_at: datetime
    created_at: datetime


class UpdateRoleRequest(BaseModel):
    role: MemberRole


class AcceptInviteRequest(BaseModel):
    token: str = Field(max_length=128)


class MemberListResponse(BaseModel):
    items: list[MemberResponse]
    next_cursor: str | None
