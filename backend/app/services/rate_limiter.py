"""
Redis-backed rate limiters.

All counters use atomic Redis primitives (Lua scripts or SET NX EX) to prevent
race conditions under concurrent requests.
"""
import time
import structlog
from app.redis_client import get_redis
from app.config import settings
from app.exceptions import RateLimitError, ServiceUnavailableError

log = structlog.get_logger()

# Lua script for atomic login attempt increment + lockout set
# Returns: [attempt_count, locked_until]
_LOGIN_ATTEMPT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_attempts = tonumber(ARGV[3])
local lockout_seconds = tonumber(ARGV[4])

local data = redis.call('HMGET', key, 'attempt_count', 'window_start', 'locked_until')
local count = tonumber(data[1]) or 0
local window_start = tonumber(data[2]) or now
local locked_until = tonumber(data[3]) or 0

-- Reset window if expired
if now - window_start > window then
    count = 0
    window_start = now
end

count = count + 1
if count >= max_attempts then
    locked_until = now + lockout_seconds
end

redis.call('HSET', key,
    'attempt_count', count,
    'window_start', window_start,
    'locked_until', locked_until)
redis.call('EXPIRE', key, window + 60)

return {count, locked_until}
"""


class RateLimiter:
    def __init__(self) -> None:
        self._redis = get_redis()

    # ── Link creation — sliding window ────────────────────────────────────

    async def check_link_create(self, user_id: str) -> None:
        """Raise RateLimitError if user exceeds 60 link-creates per 60 seconds."""
        key = f"rate:link_create:{user_id}"
        now = time.time()
        window = 60.0
        limit = settings.link_create_rate_limit

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(window) + 1)
        results = await pipe.execute()
        if results[2] > limit:
            raise RateLimitError("You're creating links faster than allowed. Try again in a minute.")

    # ── Login attempt lockout ─────────────────────────────────────────────

    async def check_login_attempt(self, email_hash: str) -> None:
        """Raise RateLimitError if locked out. Raise ServiceUnavailableError on Redis failure."""
        key = f"login_attempts:{email_hash}"
        try:
            data = await self._redis.hgetall(key)
        except Exception:
            # Redis unavailable — fail closed to prevent brute-force bypass
            raise ServiceUnavailableError("Authentication service temporarily unavailable.")

        if not data:
            return

        locked_until = float(data.get("locked_until", 0))
        if locked_until and time.time() < locked_until:
            remaining = int((locked_until - time.time()) / 60) + 1
            raise RateLimitError(
                f"Too many failed sign-in attempts. Try again in {remaining} minutes."
            )

    async def record_failed_login(self, email_hash: str) -> None:
        """Atomically increment attempt counter via Lua; set lockout if threshold reached."""
        key = f"login_attempts:{email_hash}"
        now = time.time()
        window = settings.login_lockout_minutes * 60
        try:
            await self._redis.eval(  # type: ignore[no-untyped-call]
                _LOGIN_ATTEMPT_LUA,
                1,
                key,
                str(now),
                str(window),
                str(settings.login_max_attempts),
                str(window),
            )
        except Exception as exc:
            # Best-effort — a dropped increment is preferable to crashing the login path.
            # check_login_attempt() fails closed on Redis error, so no lockout bypass.
            log.warning("login_lockout_increment_failed", exc=str(exc))

    async def clear_login_attempts(self, email_hash: str) -> None:
        await self._redis.delete(f"login_attempts:{email_hash}")

    # ── Signup rate limits — fail-closed ─────────────────────────────────

    async def check_signup(self, ip: str, email_domain: str) -> None:
        """Atomic INCR using SET NX EX to ensure the TTL is always set on first creation."""
        try:
            ip_key = f"rate:signup_ip:{ip}"
            domain_key = f"rate:signup_domain:{email_domain}"
            ip_count = await self._incr_with_ttl(ip_key, 3600)
            domain_count = await self._incr_with_ttl(domain_key, 3600)
        except RateLimitError:
            raise
        except Exception:
            raise ServiceUnavailableError("Sign-up temporarily unavailable. Please try again.")

        if ip_count > settings.signup_rate_limit_ip:
            raise RateLimitError("Too many accounts created from this IP. Try again later.")
        if domain_count > settings.signup_rate_limit_domain:
            raise RateLimitError("Too many accounts created for this email domain. Try again later.")

    async def _incr_with_ttl(self, key: str, ttl: int) -> int:
        """Atomically increment a counter, setting TTL only on first creation (no INCR+EXPIRE race)."""
        # SET key 1 NX EX ttl returns "OK" if key was new, None if key existed
        set_result = await self._redis.set(key, 1, nx=True, ex=ttl)
        if set_result:
            return 1
        return int(await self._redis.incr(key))

    # ── Resend verification ───────────────────────────────────────────────

    async def check_resend_verification(self, user_id: str) -> None:
        """3 resends per hour per user."""
        key = f"rate:resend_verification:{user_id}"
        count = await self._incr_with_ttl(key, 3600)
        if count > 3:
            raise RateLimitError("Too many verification email requests. Try again later.")

    # ── Password reset rate limits ────────────────────────────────────────

    async def check_password_reset(self, email_hash: str, ip: str) -> None:
        email_count = await self._incr_with_ttl(f"rate:pwd_reset_email:{email_hash}", 3600)
        ip_count = await self._incr_with_ttl(f"rate:pwd_reset_ip:{ip}", 3600)
        if email_count > settings.password_reset_rate_limit_email:
            raise RateLimitError("Too many password reset requests. Try again later.")
        if ip_count > settings.password_reset_rate_limit_ip:
            raise RateLimitError("Too many password reset requests from this IP. Try again later.")
