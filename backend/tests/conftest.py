"""
Test fixtures.

Uses a real Postgres DB (via TEST_DATABASE_URL env var) and a real Redis.
Run with: docker-compose up db redis, then pytest.

To run without Docker, set:
  TEST_DATABASE_URL=postgresql+asyncpg://snip:snip_dev@localhost:5432/snip_test
  TEST_REDIS_URL=redis://localhost:6379/1
"""
import os
import uuid
import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.crypto import encrypt_email, email_search_hash
from app.models.user import User

TEST_DB_URL = os.getenv("TEST_DATABASE_URL", settings.database_url.replace("/snip", "/snip_test"))

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def create_test_user(
    db: AsyncSession,
    email: str = "test@example.com",
    password_hash: str = "$argon2id$v=19$m=65536,t=3,p=4$test$test",
    verified: bool = True,
) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email_ciphertext=encrypt_email(email),
        email_search_hash=email_search_hash(email),
        password_hash=password_hash,
        email_verified_at=now if verified else None,
        session_version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()
    return user
