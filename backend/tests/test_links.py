"""
Link endpoint tests.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceMember, MemberRole
from tests.conftest import create_test_user


async def _setup_member(db: AsyncSession, email: str = "member@example.com"):
    """Create a verified user + workspace + membership."""
    user = await create_test_user(db, email=email, verified=True)
    now = datetime.now(timezone.utc)
    workspace = Workspace(
        id=uuid.uuid4(),
        name="Test WS",
        owner_id=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(workspace)
    await db.flush()
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        role=MemberRole.admin,
        joined_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(member)
    await db.flush()
    return user, workspace


def _auth_cookies(client: AsyncClient, signed_sid: str) -> None:
    client.cookies.set("sid", signed_sid)
    client.cookies.set("csrf_token", "test-csrf")


@pytest.mark.asyncio
class TestCreateLink:
    async def test_create_link_auto_code(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        user, workspace = await _setup_member(db, "link1@example.com")
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        with (
            patch("app.services.rate_limiter.RateLimiter.check_link_create", new_callable=AsyncMock),
            patch("app.services.safe_browsing.check_url", new_callable=AsyncMock, return_value=False),
            patch("app.services.mixpanel.enqueue_event", new_callable=AsyncMock),
        ):
            resp = await client.post(
                "/v1/links",
                json={"destination_url": "https://example.com/path"},
                headers={"X-CSRF-Token": "tok"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["short_code"]
        assert len(data["short_code"]) == 7
        assert data["destination_url"] == "https://example.com/path"
        assert data["is_custom_slug"] is False

    async def test_create_link_custom_slug(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        user, workspace = await _setup_member(db, "link2@example.com")
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        with (
            patch("app.services.rate_limiter.RateLimiter.check_link_create", new_callable=AsyncMock),
            patch("app.services.safe_browsing.check_url", new_callable=AsyncMock, return_value=False),
            patch("app.services.mixpanel.enqueue_event", new_callable=AsyncMock),
        ):
            resp = await client.post(
                "/v1/links",
                json={"destination_url": "https://example.com", "custom_slug": "my-custom"},
                headers={"X-CSRF-Token": "tok"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["short_code"] == "my-custom"
        assert data["is_custom_slug"] is True

    async def test_create_link_reserved_slug_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        user, workspace = await _setup_member(db, "link3@example.com")
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        resp = await client.post(
            "/v1/links",
            json={"destination_url": "https://example.com", "custom_slug": "admin"},
            headers={"X-CSRF-Token": "tok"},
        )
        assert resp.status_code == 422

    async def test_create_link_invalid_scheme_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        user, workspace = await _setup_member(db, "link4@example.com")
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        resp = await client.post(
            "/v1/links",
            json={"destination_url": "ftp://example.com"},
            headers={"X-CSRF-Token": "tok"},
        )
        assert resp.status_code == 422

    async def test_create_link_rate_limited(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        from app.exceptions import RateLimitError
        user, workspace = await _setup_member(db, "link5@example.com")
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        with patch(
            "app.services.rate_limiter.RateLimiter.check_link_create",
            new_callable=AsyncMock,
            side_effect=RateLimitError("Rate limited"),
        ):
            resp = await client.post(
                "/v1/links",
                json={"destination_url": "https://example.com"},
                headers={"X-CSRF-Token": "tok"},
            )
        assert resp.status_code == 429


@pytest.mark.asyncio
class TestDeleteLink:
    async def test_soft_delete(self, client: AsyncClient, db: AsyncSession) -> None:
        from app.services.session import SessionService
        from app.models.link import Link
        user, workspace = await _setup_member(db, "del@example.com")
        svc = SessionService()
        sid = await svc.create(user.id, 1)
        client.cookies.set("sid", sid)
        client.cookies.set("csrf_token", "tok")

        now = datetime.now(timezone.utc)
        link = Link(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            owner_id=user.id,
            created_by_id=user.id,
            short_code="del1234",
            destination_url="https://example.com",
            is_custom_slug=False,
            created_at=now,
            updated_at=now,
        )
        db.add(link)
        await db.flush()

        resp = await client.delete("/v1/links/del1234", headers={"X-CSRF-Token": "tok"})
        assert resp.status_code == 204

        # Link should be gone from list
        with patch("app.services.rate_limiter.RateLimiter.check_link_create", new_callable=AsyncMock):
            list_resp = await client.get("/v1/links")
        assert all(item["short_code"] != "del1234" for item in list_resp.json()["items"])
