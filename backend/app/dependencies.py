"""
FastAPI dependency-injection helpers.

Provides:
  - get_db         — yields an AsyncSession (unit-of-work committed in database.py)
  - get_session    — resolves the current session from cookie
  - require_auth   — asserts the session is valid; returns AuthContext
  - require_member — asserts the user is an active member of their workspace
  - require_admin  — asserts the member has the admin role
"""
import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import UnauthorizedError, PermissionDeniedError
from app.models.workspace import WorkspaceMember, MemberRole
from app.services.session import SessionService


@dataclass
class AuthContext:
    user_id: uuid.UUID
    session_id: str
    workspace_id: uuid.UUID | None
    role: MemberRole | None


async def get_session(
    session_id: Annotated[str | None, Cookie(alias="sid")] = None,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Resolve and validate the session cookie."""
    if not session_id:
        raise UnauthorizedError()

    svc = SessionService()
    session_data = await svc.get(session_id)
    if session_data is None:
        raise UnauthorizedError()

    from app.models.user import User
    result = await db.execute(select(User).where(User.id == uuid.UUID(session_data["user_id"])))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError()

    # Session version check — invalidates all sessions on password change or admin removal
    if int(session_data["session_version"]) != user.session_version:
        raise UnauthorizedError()

    # Refresh idle timer
    await svc.touch(session_id)

    return AuthContext(
        user_id=uuid.UUID(session_data["user_id"]),
        session_id=session_id,
        workspace_id=None,
        role=None,
    )


async def require_auth(
    ctx: Annotated[AuthContext, Depends(get_session)],
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Require auth and attach workspace + role to context."""
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == ctx.user_id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    member = result.scalar_one_or_none()
    if member:
        ctx.workspace_id = member.workspace_id
        ctx.role = member.role
    return ctx


async def require_member(
    ctx: Annotated[AuthContext, Depends(require_auth)],
) -> AuthContext:
    """Require the user to be an active member of a workspace."""
    if ctx.workspace_id is None:
        raise PermissionDeniedError("You must belong to a workspace.")
    return ctx


async def require_admin(
    ctx: Annotated[AuthContext, Depends(require_member)],
) -> AuthContext:
    """Require the member to have the admin role."""
    if ctx.role != MemberRole.admin:
        raise PermissionDeniedError("Admin role required.")
    return ctx


# Shorthand aliases for route handlers
DBDep = Annotated[AsyncSession, Depends(get_db)]
AuthDep = Annotated[AuthContext, Depends(require_auth)]
MemberDep = Annotated[AuthContext, Depends(require_member)]
AdminDep = Annotated[AuthContext, Depends(require_admin)]
