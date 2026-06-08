"""
Transactional email via AWS SES.
boto3 calls are wrapped in run_in_executor to avoid blocking the async event loop.
All public `send_*` functions open their own DB session for suppression checks so
they can be safely enqueued as FastAPI BackgroundTasks.
"""
import asyncio
import structlog
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.crypto import email_search_hash

log = structlog.get_logger()

_ses_config = Config(
    connect_timeout=3,
    read_timeout=10,
    retries={"max_attempts": 3, "mode": "standard"},
)


def _ses_client():
    return boto3.client(
        "ses",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        config=_ses_config,
    )


async def _is_suppressed(email: str) -> bool:
    """Check suppression list using its own short-lived session."""
    from app.database import AsyncSessionLocal
    from app.models.email_suppression import EmailSuppression
    from sqlalchemy import select
    search_hash = email_search_hash(email)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(EmailSuppression).where(EmailSuppression.email_search_hash == search_hash)
        )
        return result.scalar_one_or_none() is not None


async def send_verification_email(email: str, token: str) -> bool:
    if await _is_suppressed(email):
        log.info("email_suppressed", reason="suppression_list", template="verification")
        return False
    verify_url = f"{settings.app_base_url}/auth/verify-email"
    subject = "Verify your Snip email"
    body_text = f"Click the link to verify your email:\n{verify_url}?token={token}\n\nExpires in 24 hours."
    body_html = (
        f"<p>Click the link to verify your email:</p>"
        f"<p><a href=\"{verify_url}?token={token}\">{verify_url}</a></p>"
        f"<p>Expires in 24 hours.</p>"
    )
    return await _send(email, subject, body_text, body_html)


async def send_password_reset_email(email: str, token: str) -> bool:
    if await _is_suppressed(email):
        return False
    reset_url = f"{settings.app_base_url}/auth/reset-password"
    subject = "Reset your Snip password"
    body_text = f"Click to reset your password:\n{reset_url}?token={token}\n\nExpires in 60 minutes."
    body_html = (
        f"<p>Click to reset your password:</p>"
        f"<p><a href=\"{reset_url}?token={token}\">{reset_url}</a></p>"
        f"<p>Expires in 60 minutes.</p>"
    )
    return await _send(email, subject, body_text, body_html)


async def send_already_registered_email(email: str) -> bool:
    """Sent when a signup attempt is made for an already-registered address.
    Keeps the HTTP response uniform — no 409 enumeration oracle.
    """
    login_url = f"{settings.app_base_url}/auth/login"
    reset_url = f"{settings.app_base_url}/auth/forgot-password"
    subject = "You already have a Snip account"
    body_text = (
        f"Someone tried to create a Snip account using this email address.\n\n"
        f"If that was you, sign in at {login_url} or reset your password at {reset_url}.\n"
        f"If it wasn't you, you can ignore this email."
    )
    body_html = (
        f"<p>Someone tried to create a Snip account using this email address.</p>"
        f"<p>If that was you, <a href=\"{login_url}\">sign in</a> or "
        f"<a href=\"{reset_url}\">reset your password</a>.</p>"
        f"<p>If it wasn't you, you can ignore this email.</p>"
    )
    return await _send(email, subject, body_text, body_html)


async def send_invite_email(email: str, workspace_name: str, token: str) -> bool:
    if await _is_suppressed(email):
        return False
    invite_url = f"{settings.app_base_url}/invites/accept?token={token}"
    subject = f"You've been invited to join {workspace_name} on Snip"
    body_text = f"You've been invited to join {workspace_name}.\nAccept: {invite_url}\n\nExpires in 7 days."
    body_html = (
        f"<p>You've been invited to join <strong>{workspace_name}</strong> on Snip.</p>"
        f"<p><a href=\"{invite_url}\">Accept invitation</a></p>"
        f"<p>Expires in 7 days.</p>"
    )
    return await _send(email, subject, body_text, body_html)


async def _send(to_email: str, subject: str, body_text: str, body_html: str) -> bool:
    if not settings.aws_access_key_id:
        log.info("email_send_skipped", reason="no_aws_creds", to=to_email)
        return True  # Dev mode

    def _blocking_send() -> bool:
        try:
            client = _ses_client()
            client.send_email(
                Source=settings.ses_from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body_text, "Charset": "UTF-8"},
                        "Html": {"Data": body_html, "Charset": "UTF-8"},
                    },
                },
            )
            return True
        except ClientError as exc:
            log.error("ses_send_failed", error=str(exc), to=to_email)
            return False
        except Exception as exc:
            log.error("ses_send_exception", error=str(exc), to=to_email)
            return False

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _blocking_send)
