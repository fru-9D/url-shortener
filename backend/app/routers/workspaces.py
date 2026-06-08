"""
Workspace routes:
  POST   /v1/workspaces                          — create workspace (verified users only)
  GET    /v1/workspaces/me                        — get current user's workspace
  GET    /v1/workspaces/{workspace_id}/members    — list members
  POST   /v1/workspaces/{workspace_id}/invites    — invite by email
  DELETE /v1/workspaces/{workspace_id}/invites/{invite_id}  — cancel invite
  POST   /v1/invites/accept                       — accept invite (token in body)
  POST   /v1/invites/decline                      — decline invite (token in body)
  DELETE /v1/workspaces/{workspace_id}/members/{member_id}  — remove member (admin)
  PATCH  /v1/workspaces/{workspace_id}/members/{member_id}  — update role (admin)
"""
import base64
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.crypto import encrypt_email, email_search_hash, generate_token, hash_token, decrypt_email
from app.dependencies import DBDep, AuthDep, MemberDep, AdminDep
from app.exceptions import (
    ConflictError, NotFoundError, PermissionDeniedError, ValidationError,
    NotImplementedError as AppNotImplementedError,
)
from app.models.invite import Invite, InviteStatus
from app.models.link import Link
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, MemberRole
from app.schemas.workspace import (
    CreateWorkspaceRequest, WorkspaceResponse,
    MemberResponse, MemberListResponse, InviteRequest, InviteResponse,
    UpdateRoleRequest, AcceptInviteRequest,
)
from app.services.email_service import send_invite_email
from app.services.mixpanel import enqueue_event

log = structlog.get_logger()
router = APIRouter(prefix="/v1", tags=["workspaces"])


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: uuid.UUID) -> None:
    """Workspace deletion is not available in v1. Reserved for v2."""
    raise AppNotImplementedError("Workspace deletion is not available in v1.")


@router.post("/workspaces", status_code=201, response_model=WorkspaceResponse)
async def create_workspace(body: CreateWorkspaceRequest, ctx: AuthDep, db: DBDep) -> WorkspaceResponse:
    # User must be email-verified
    user_result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = user_result.scalar_one()
    if user.email_verified_at is None:
        raise PermissionDeniedError("Please verify your email before creating a workspace.")

    # User must not already belong to a workspace
    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == ctx.user_id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("You're already part of a Workspace. Multiple Workspaces are not supported yet.")

    now = datetime.now(timezone.utc)
    workspace = Workspace(
        id=uuid.uuid4(),
        name=body.name,
        owner_id=ctx.user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(workspace)
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=ctx.user_id,
        role=MemberRole.admin,
        joined_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(member)
    try:
        await db.flush()
    except IntegrityError:
        # Concurrent request by same user won the race — the partial unique on user_id fired
        await db.rollback()
        raise ConflictError("You're already part of a Workspace. Multiple Workspaces are not supported yet.")

    return WorkspaceResponse(id=workspace.id, name=workspace.name, created_at=workspace.created_at)


@router.get("/workspaces/me", response_model=WorkspaceResponse)
async def get_my_workspace(ctx: MemberDep, db: DBDep) -> WorkspaceResponse:
    result = await db.execute(select(Workspace).where(Workspace.id == ctx.workspace_id))
    workspace = result.scalar_one()
    return WorkspaceResponse(id=workspace.id, name=workspace.name, created_at=workspace.created_at)


def _encode_member_cursor(joined_at: datetime | None, member_id: uuid.UUID) -> str:
    ts = joined_at.isoformat() if joined_at else "null"
    raw = f"{ts}|{member_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_member_cursor(cursor: str) -> tuple[datetime | None, uuid.UUID] | None:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.split("|", 1)
        ts = datetime.fromisoformat(ts_str) if ts_str != "null" else None
        return ts, uuid.UUID(id_str)
    except Exception:
        return None


@router.get("/workspaces/{workspace_id}/members", response_model=MemberListResponse)
async def list_members(
    workspace_id: uuid.UUID,
    ctx: MemberDep,
    db: DBDep,
    after: str | None = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=200),
) -> MemberListResponse:
    if workspace_id != ctx.workspace_id:
        raise PermissionDeniedError()

    query = (
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.removed_at.is_(None))
        .order_by(WorkspaceMember.joined_at.asc(), WorkspaceMember.id.asc())
    )

    if after:
        cursor = _decode_member_cursor(after)
        if cursor:
            cursor_ts, cursor_id = cursor
            if cursor_ts:
                query = query.where(
                    (WorkspaceMember.joined_at > cursor_ts)
                    | ((WorkspaceMember.joined_at == cursor_ts) & (WorkspaceMember.id > cursor_id))
                )

    query = query.limit(page_size + 1)
    result = await db.execute(query)
    rows = result.all()

    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = (
        _encode_member_cursor(rows[-1][0].joined_at, rows[-1][0].id) if has_more and rows else None
    )

    return MemberListResponse(
        items=[
            MemberResponse(
                id=m.id,
                user_id=m.user_id,
                email=decrypt_email(u.email_ciphertext),
                role=m.role,
                joined_at=m.joined_at,
            )
            for m, u in rows
        ],
        next_cursor=next_cursor,
    )


@router.post("/workspaces/{workspace_id}/invites", status_code=201, response_model=InviteResponse)
async def create_invite(
    workspace_id: uuid.UUID, body: InviteRequest, ctx: AdminDep, db: DBDep,
    background_tasks: BackgroundTasks,
) -> InviteResponse:
    if workspace_id != ctx.workspace_id:
        raise PermissionDeniedError()

    # Get workspace for email
    ws_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = ws_result.scalar_one()

    search_hash = email_search_hash(body.email)

    # Check if email is already an active member anywhere
    existing_member = await db.execute(
        select(WorkspaceMember).join(User, User.id == WorkspaceMember.user_id).where(
            User.email_search_hash == search_hash,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    if existing_member.scalar_one_or_none():
        raise ConflictError(
            "That email already belongs to another Snip workspace. "
            "They would need to leave that workspace first, or use a different email address."
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.invite_expiry_days)

    # Re-invite: replace existing pending invite for this email in this workspace
    pending = await db.execute(
        select(Invite).where(
            Invite.workspace_id == workspace_id,
            Invite.email_search_hash == search_hash,
            Invite.status == InviteStatus.pending,
        )
    )
    existing_invite = pending.scalar_one_or_none()
    if existing_invite:
        existing_invite.status = InviteStatus.cancelled
        existing_invite.updated_at = now

    raw_token, token_hash = generate_token()
    invite = Invite(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        email_ciphertext=encrypt_email(body.email),
        email_search_hash=search_hash,
        role=body.role,
        inviter_id=ctx.user_id,
        status=InviteStatus.pending,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
    )
    db.add(invite)
    await db.flush()

    # Enqueue as BackgroundTask — handler returns immediately regardless of SES latency.
    # If the task fails, the invite remains in 'pending' status; admin can resend from the members page.
    background_tasks.add_task(send_invite_email, body.email, workspace.name, raw_token)

    await enqueue_event(
        "member_invited",
        {
            "workspace_id": str(workspace_id),
            "inviter_id": str(ctx.user_id),
            "invite_role": body.role.value,
        },
        insert_id=str(invite.id),
    )

    return InviteResponse(
        id=invite.id,
        email=body.email,
        role=invite.role,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.delete("/workspaces/{workspace_id}/invites/{invite_id}", status_code=204)
async def cancel_invite(
    workspace_id: uuid.UUID, invite_id: uuid.UUID, ctx: AdminDep, db: DBDep
) -> None:
    if workspace_id != ctx.workspace_id:
        raise PermissionDeniedError()

    result = await db.execute(
        select(Invite).where(Invite.id == invite_id, Invite.workspace_id == workspace_id)
    )
    invite = result.scalar_one_or_none()
    if not invite or invite.status != InviteStatus.pending:
        raise NotFoundError("Invite not found or already resolved.")

    now = datetime.now(timezone.utc)
    invite.status = InviteStatus.cancelled
    invite.updated_at = now


@router.post("/invites/accept", status_code=204)
async def accept_invite(body: AcceptInviteRequest, ctx: AuthDep, db: DBDep) -> None:
    token_hash = hash_token(body.token)
    result = await db.execute(select(Invite).where(Invite.token_hash == token_hash))
    invite = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not invite or invite.status != InviteStatus.pending:
        raise ValidationError("This invite has expired. Ask the Workspace Admin to resend it.")
    if now > invite.expires_at.replace(tzinfo=timezone.utc):
        invite.status = InviteStatus.expired
        invite.updated_at = now
        raise ValidationError("This invite has expired. Ask the Workspace Admin to resend it.")

    # Verify the accepting user's email matches the invite
    user_result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = user_result.scalar_one()
    if user.email_search_hash != invite.email_search_hash:
        raise PermissionDeniedError("This invite was sent to a different email address.")

    # User must not already be in a workspace
    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == ctx.user_id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("You're already part of a Workspace. Multiple Workspaces are not supported yet.")

    # Accept — add member
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=invite.workspace_id,
        user_id=ctx.user_id,
        role=MemberRole(invite.role.value),
        joined_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(member)

    invite.status = InviteStatus.accepted
    invite.accepted_at = now
    invite.updated_at = now


@router.post("/invites/decline", status_code=204)
async def decline_invite(body: AcceptInviteRequest, db: DBDep) -> None:
    token_hash = hash_token(body.token)
    result = await db.execute(select(Invite).where(Invite.token_hash == token_hash))
    invite = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not invite or invite.status != InviteStatus.pending:
        raise ValidationError("This invite has expired or is no longer valid.")

    invite.status = InviteStatus.declined
    invite.declined_at = now
    invite.updated_at = now


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID, member_id: uuid.UUID, ctx: AdminDep, db: DBDep
) -> None:
    if workspace_id != ctx.workspace_id:
        raise PermissionDeniedError()

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("Member not found.")

    if target.user_id == ctx.user_id:
        raise ValidationError("You're the only Admin. Promote another Member to Admin first.")

    # Enforce last-admin constraint with FOR UPDATE to prevent concurrent removal race (RT-05)
    if target.role == MemberRole.admin:
        admin_count_result = await db.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == MemberRole.admin,
                WorkspaceMember.removed_at.is_(None),
            )
            .with_for_update()
        )
        admin_count = admin_count_result.scalar()
        if admin_count <= 1:
            raise ValidationError("You're the only Admin. Promote another Member to Admin first.")

    now = datetime.now(timezone.utc)
    target.removed_at = now
    target.updated_at = now

    # Reassign their links to the removing admin
    from sqlalchemy import update as sqla_update
    await db.execute(
        sqla_update(Link)
        .where(Link.workspace_id == workspace_id, Link.owner_id == target.user_id)
        .values(owner_id=ctx.user_id, updated_at=now)
    )

    # Cancel any pending invites sent by removed member
    await db.execute(
        sqla_update(Invite)
        .where(
            Invite.workspace_id == workspace_id,
            Invite.inviter_id == target.user_id,
            Invite.status == InviteStatus.pending,
        )
        .values(status=InviteStatus.cancelled, updated_at=now)
    )

    # Bump session_version to immediately invalidate their sessions
    from sqlalchemy import update as sqla_update2
    await db.execute(
        sqla_update2(User)
        .where(User.id == target.user_id)
        .values(session_version=User.session_version + 1, updated_at=now)
    )


@router.patch("/workspaces/{workspace_id}/members/{member_id}", response_model=MemberResponse)
async def update_member_role(
    workspace_id: uuid.UUID, member_id: uuid.UUID, body: UpdateRoleRequest, ctx: AdminDep, db: DBDep
) -> MemberResponse:
    if workspace_id != ctx.workspace_id:
        raise PermissionDeniedError()

    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    row = result.one_or_none()
    if not row:
        raise NotFoundError("Member not found.")

    target, user = row

    # Prevent self-demotion if last admin
    if target.user_id == ctx.user_id and body.role == MemberRole.editor:
        admin_count_result = await db.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == MemberRole.admin,
                WorkspaceMember.removed_at.is_(None),
            )
            .with_for_update()
        )
        if admin_count_result.scalar() <= 1:
            raise ValidationError("You're the only Admin. Promote another Member to Admin first.")

    now = datetime.now(timezone.utc)
    target.role = body.role
    target.updated_at = now

    return MemberResponse(
        id=target.id,
        user_id=target.user_id,
        email=decrypt_email(user.email_ciphertext),
        role=target.role,
        joined_at=target.joined_at,
    )
