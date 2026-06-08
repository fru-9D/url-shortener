"""
k-anonymity Pwned Passwords check.
Sends only the first 5 characters of the SHA-1 hash; never the full hash or password.
"""
import hashlib
import structlog
import httpx

from app.config import settings

log = structlog.get_logger()
_BASE_URL = "https://api.pwnedpasswords.com/range"


async def is_password_pwned(password: str) -> bool:
    """
    Returns True if the password appears in the breach database.
    Fails open (returns False) on timeout or network error.
    """
    sha1 = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=settings.pwned_passwords_timeout) as client:
                resp = await client.get(f"{_BASE_URL}/{prefix}")
            resp.raise_for_status()
            for line in resp.text.splitlines():
                hash_suffix, count = line.split(":")
                if hash_suffix == suffix:
                    return True
            return False
        except httpx.TimeoutException:
            if attempt == 0:
                continue
            log.warning("pwned_check_skipped", reason="timeout", pwned_check_skipped=True)
            return False
        except Exception as exc:
            log.warning("pwned_check_skipped", reason=str(exc), pwned_check_skipped=True)
            return False

    return False
