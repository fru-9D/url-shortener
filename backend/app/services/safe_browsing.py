"""
Google Safe Browsing v4 Lookup API.
Only host+path is sent — query strings stripped to avoid PII leakage.
Fail-open: returns False (safe) on timeout or API error.
"""
from urllib.parse import urlparse, urlunparse
import structlog
import httpx

from app.config import settings

log = structlog.get_logger()
_API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


def _strip_query(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


async def check_url(url: str) -> bool:
    """
    Returns True if the URL is flagged as unsafe.
    Fails open (returns False) on any error.
    """
    if not settings.google_safe_browsing_api_key:
        return False

    stripped = _strip_query(url)
    payload = {
        "client": {"clientId": "snip", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE", "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": stripped}],
        },
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=settings.google_safe_browsing_timeout) as client:
                resp = await client.post(
                    _API_URL,
                    params={"key": settings.google_safe_browsing_api_key},
                    json=payload,
                )
            resp.raise_for_status()
            return bool(resp.json().get("matches"))
        except httpx.TimeoutException:
            log.warning("safe_browsing_timeout", url=stripped)
            return False  # No retry on timeout — latency budget forbids it
        except httpx.TransportError:  # was incorrectly httpx.TransientError
            if attempt == 0:
                continue
            log.warning("safe_browsing_transport_error", url=stripped)
            return False
        except Exception as exc:
            log.warning("safe_browsing_error", exc=str(exc), url=stripped)
            return False

    return False
