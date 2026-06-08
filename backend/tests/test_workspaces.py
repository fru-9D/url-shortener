"""
Workspace endpoint tests.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceMember, MemberRole
from tests.conftest import create_test_user


async def _make_workspace(db: AsyncSession, user_id: uuid.UUID) -> Workspace:
    now = datetime.now(timezone.utc)
    ws = Workspace(id=uuid.uuid4(), name="Test WS", owner_id=user_id, created_at=now, updated_at=now)
    db.add(ws)
    await db.flush()
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=user_id,
        role=MemberRole.admin,
        joined_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(member)
    await db.flush()
    return ws


@pytest.mark.asyncio
class TestCreateWorkspace:
    async def test_create_workspace_success(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        user = await create_test_user(db, email="ws1@example.com", verified=True)
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        resp = await client.post(
            "/v1/workspaces",
            json={"name": "My Team"},
            headers={"X-CSRF-Token": "tok"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Team"

    async def test_create_second_workspace_fails(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        user = await create_test_user(db, email="ws2@example.com", verified=True)
        await _make_workspace(db, user.id)
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        resp = await client.post(
            "/v1/workspaces",
            json={"name": "Second WS"},
            headers={"X-CSRF-Token": "tok"},
        )
        assert resp.status_code == 409

    async def test_unverified_user_cannot_create_workspace(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        user = await create_test_user(db, email="unverified@example.com", verified=False)
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        resp = await client.post(
            "/v1/workspaces",
            json={"name": "Some WS"},
            headers={"X-CSRF-Token": "tok"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestMemberManagement:
    async def test_remove_member_reassigns_links(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        from app.models.link import Link

        admin = await create_test_user(db, email="admin@example.com", verified=True)
        ws = await _make_workspace(db, admin.id)
        editor = await create_test_user(db, email="editor@example.com", verified=True)

        now = datetime.now(timezone.utc)
        editor_member = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            user_id=editor.id,
            role=MemberRole.editor,
            joined_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(editor_member)

        link = Link(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            owner_id=editor.id,
            created_by_id=editor.id,
            short_code="edlink1",
            destination_url="https://example.com",
            is_custom_slug=False,
            created_at=now,
            updated_at=now,
        )
        db.add(link)
        await db.flush()

        svc = SessionService()
        sid = await svc.create(admin.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        resp = await client.delete(
            f"/v1/workspaces/{ws.id}/members/{editor_member.id}",
            headers={"X-CSRF-Token": "tok"},
        )
        assert resp.status_code == 204

        # Verify link was reassigned to admin
        await db.refresh(link)
        assert link.owner_id == admin.id

    async def test_last_admin_cannot_be_removed(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        admin = await create_test_user(db, email="lastadmin@example.com", verified=True)
        ws = await _make_workspace(db, admin.id)

        from sqlalchemy import select
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.user_id == admin.id,
            )
        )
        admin_member = result.scalar_one()

        svc = SessionService()
        sid = await svc.create(admin.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        resp = await client.delete(
            f"/v1/workspaces/{ws.id}/members/{admin_member.id}",
            headers={"X-CSRF-Token": "tok"},
        )
        assert resp.status_code == 422
