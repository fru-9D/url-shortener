"""
Redis-backed session service.

Session record (Redis hash, key: session:<id>):
  user_id, session_version, expires_at (epoch), last_activity_at (epoch)

User session index (Redis set, key: user_sessions:<user_id>):
  set of signed_sid values — used to enumerate and revoke all sessions for a user.

The session id stored in the cookie is HMAC-signed to detect tampering.
"""
import hashlib
import hmac
import secrets
import time
import uuid

from app.config import settings
from app.redis_client import get_redis

_ABSOLUTE_TTL = settings.session_absolute_days * 86400
_IDLE_TTL = settings.session_idle_days * 86400


def _sign(session_id: str) -> str:
    sig = hmac.new(settings.secret_key.encode(), session_id.encode(), hashlib.sha256).hexdigest()
    return f"{session_id}.{sig}"


def _verify_and_extract(cookie_value: str) -> str | None:
    parts = cookie_value.rsplit(".", 1)
    if len(parts) != 2:
        return None
    session_id, sig = parts
    expected = hmac.new(settings.secret_key.encode(), session_id.encode(), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(sig, expected):
        return None
    return session_id


class SessionService:
    def __init__(self) -> None:
        self._redis = get_redis()

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _user_sessions_key(self, user_id: uuid.UUID) -> str:
        return f"user_sessions:{user_id}"

    async def create(self, user_id: uuid.UUID, session_version: int) -> str:
        session_id = secrets.token_urlsafe(32)
        now = int(time.time())
        expires_at = now + _ABSOLUTE_TTL
        signed = _sign(session_id)

        pipe = self._redis.pipeline()
        pipe.hset(
            self._key(session_id),
            mapping={
                "user_id": str(user_id),
                "session_version": str(session_version),
                "expires_at": str(expires_at),
                "last_activity_at": str(now),
            },
        )
        pipe.expireat(self._key(session_id), expires_at)
        # Track this session under the user's session index for bulk revocation
        pipe.sadd(self._user_sessions_key(user_id), signed)
        pipe.expire(self._user_sessions_key(user_id), _ABSOLUTE_TTL + 86400)
        await pipe.execute()
        return signed

    async def get(self, cookie_value: str) -> dict[str, str] | None:
        session_id = _verify_and_extract(cookie_value)
        if session_id is None:
            return None

        data = await self._redis.hgetall(self._key(session_id))
        if not data:
            return None

        now = int(time.time())
        if now > int(data.get("expires_at", 0)):
            await self._redis.delete(self._key(session_id))
            return None
        if now - int(data.get("last_activity_at", 0)) > _IDLE_TTL:
            await self._redis.delete(self._key(session_id))
            return None

        return data

    async def touch(self, cookie_value: str) -> None:
        session_id = _verify_and_extract(cookie_value)
        if session_id is None:
            return
        await self._redis.hset(self._key(session_id), "last_activity_at", str(int(time.time())))

    async def delete(self, cookie_value: str) -> None:
        session_id = _verify_and_extract(cookie_value)
        if not session_id:
            return
        data = await self._redis.hgetall(self._key(session_id))
        pipe = self._redis.pipeline()
        pipe.delete(self._key(session_id))
        if data and "user_id" in data:
            pipe.srem(self._user_sessions_key(uuid.UUID(data["user_id"])), cookie_value)
        await pipe.execute()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all active sessions for a user (security incident response, forced logout)."""
        index_key = self._user_sessions_key(user_id)
        signed_sids = await self._redis.smembers(index_key)

        pipe = self._redis.pipeline()
        for signed in signed_sids:
            session_id = _verify_and_extract(signed)
            if session_id:
                pipe.delete(self._key(session_id))
        pipe.delete(index_key)
        await pipe.execute()
