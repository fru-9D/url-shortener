"""
Auth endpoint tests.

These are integration tests that hit real Postgres + Redis.
External services (SES, Pwned Passwords) are patched.
"""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import email_search_hash, hash_token, generate_token
from app.models.tokens import EmailVerificationToken, PasswordResetToken
from tests.conftest import create_test_user


@pytest.mark.asyncio
class TestSignup:
    async def test_signup_creates_user(self, client: AsyncClient, db: AsyncSession) -> None:
        with (
            patch("app.routers.auth.is_password_pwned", new_callable=AsyncMock, return_value=False),
            patch("app.routers.auth.send_verification_email", new_callable=AsyncMock, return_value=True),
            patch("app.services.rate_limiter.RateLimiter.check_signup", new_callable=AsyncMock),
        ):
            resp = await client.post(
                "/v1/auth/signup",
                json={"email": "new@example.com", "password": "securepassword123"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["email_verified"] is False
        assert "sid" in resp.cookies

    async def test_signup_duplicate_email(self, client: AsyncClient, db: AsyncSession) -> None:
        await create_test_user(db, email="dup@example.com")
        with (
            patch("app.services.rate_limiter.RateLimiter.check_signup", new_callable=AsyncMock),
        ):
            resp = await client.post(
                "/v1/auth/signup",
                json={"email": "dup@example.com", "password": "securepassword123"},
            )
        assert resp.status_code == 409

    async def test_signup_pwned_password_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        with (
            patch("app.routers.auth.is_password_pwned", new_callable=AsyncMock, return_value=True),
            patch("app.services.rate_limiter.RateLimiter.check_signup", new_callable=AsyncMock),
        ):
            resp = await client.post(
                "/v1/auth/signup",
                json={"email": "pwned@example.com", "password": "password12345678"},
            )
        assert resp.status_code == 422

    async def test_signup_short_password_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        with patch("app.services.rate_limiter.RateLimiter.check_signup", new_callable=AsyncMock):
            resp = await client.post(
                "/v1/auth/signup",
                json={"email": "short@example.com", "password": "short"},
            )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_wrong_password(self, client: AsyncClient, db: AsyncSession) -> None:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        user = await create_test_user(db, email="login@example.com", password_hash=ph.hash("correct_password_123"))
        with patch("app.services.rate_limiter.RateLimiter.check_login_attempt", new_callable=AsyncMock):
            resp = await client.post(
                "/v1/auth/login",
                json={"email": "login@example.com", "password": "wrong_password_123"},
            )
        assert resp.status_code == 401

    async def test_login_success(self, client: AsyncClient, db: AsyncSession) -> None:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        user = await create_test_user(
            db, email="login2@example.com", password_hash=ph.hash("correct_password_123")
        )
        with (
            patch("app.services.rate_limiter.RateLimiter.check_login_attempt", new_callable=AsyncMock),
            patch("app.services.rate_limiter.RateLimiter.clear_login_attempts", new_callable=AsyncMock),
        ):
            resp = await client.post(
                "/v1/auth/login",
                json={"email": "login2@example.com", "password": "correct_password_123"},
            )
        assert resp.status_code == 200
        assert "sid" in resp.cookies


@pytest.mark.asyncio
class TestEmailVerification:
    async def test_verify_valid_token(self, client: AsyncClient, db: AsyncSession) -> None:
        user = await create_test_user(db, email="verify@example.com", verified=False)
        raw_token, token_hash = generate_token()
        now = datetime.now(timezone.utc)
        evt = EmailVerificationToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=24),
            created_at=now,
            updated_at=now,
        )
        db.add(evt)
        await db.flush()

        resp = await client.post(f"/v1/auth/verify-email?token={raw_token}")
        assert resp.status_code == 204

    async def test_verify_expired_token(self, client: AsyncClient, db: AsyncSession) -> None:
        user = await create_test_user(db, email="expired@example.com", verified=False)
        raw_token, token_hash = generate_token()
        now = datetime.now(timezone.utc)
        evt = EmailVerificationToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now - timedelta(hours=1),  # already expired
            created_at=now,
            updated_at=now,
        )
        db.add(evt)
        await db.flush()

        resp = await client.post(f"/v1/auth/verify-email?token={raw_token}")
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestPasswordReset:
    async def test_forgot_password_unknown_email_returns_204(self, client: AsyncClient, db: AsyncSession) -> None:
        with (
            patch("app.services.rate_limiter.RateLimiter.check_password_reset", new_callable=AsyncMock),
        ):
            resp = await client.post(
                "/v1/auth/forgot-password",
                json={"email": "nobody@example.com"},
            )
        # Must not reveal whether email exists
        assert resp.status_code == 204

    async def test_reset_invalid_token(self, client: AsyncClient, db: AsyncSession) -> None:
        resp = await client.post(
            "/v1/auth/reset-password",
            json={"token": "invalid-token", "new_password": "new_secure_pass_123"},
        )
        assert resp.status_code == 422
