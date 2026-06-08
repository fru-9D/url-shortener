"""
Mail events worker.
SQS calls wrapped in run_in_executor to avoid blocking the async event loop.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

import boto3
import structlog

from sqlalchemy import select

from app.config import settings
from app.crypto import encrypt_email, email_search_hash
from app.database import AsyncSessionLocal
from app.models.email_suppression import EmailSuppression, SuppressionReason

log = structlog.get_logger()


def _sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


async def process_message(body: dict) -> None:
    message_str = body.get("Message") or json.dumps(body)
    try:
        ses_event = json.loads(message_str)
    except json.JSONDecodeError:
        ses_event = body

    notification_type = ses_event.get("notificationType", ses_event.get("eventType", ""))
    reason: SuppressionReason | None = None
    recipients: list[str] = []

    if notification_type in ("Bounce", "bounce"):
        reason = SuppressionReason.bounce
        bounce = ses_event.get("bounce", {})
        recipients = [r.get("emailAddress", "") for r in bounce.get("bouncedRecipients", [])]
    elif notification_type in ("Complaint", "complaint"):
        reason = SuppressionReason.complaint
        complaint = ses_event.get("complaint", {})
        recipients = [r.get("emailAddress", "") for r in complaint.get("complainedRecipients", [])]

    if not reason or not recipients:
        log.warning("mail_event_unrecognised", notification_type=notification_type)
        return

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            valid_recipients = [(email, email_search_hash(email)) for email in recipients if email]

            if not valid_recipients:
                return

            # Batch lookup — single IN query instead of one per recipient
            hashes = [h for _, h in valid_recipients]
            existing_rows = await db.execute(
                select(EmailSuppression).where(EmailSuppression.email_search_hash.in_(hashes))
            )
            existing_map = {row.email_search_hash: row for row in existing_rows.scalars().all()}

            for email, search_hash in valid_recipients:
                supp = existing_map.get(search_hash)
                if supp:
                    supp.reason = reason
                    supp.suppressed_at = now
                    supp.updated_at = now
                else:
                    db.add(EmailSuppression(
                        id=uuid.uuid4(),
                        email_ciphertext=encrypt_email(email),
                        email_search_hash=search_hash,
                        reason=reason,
                        suppressed_at=now,
                        created_at=now,
                        updated_at=now,
                    ))
            await db.commit()
            log.info("email_suppression_recorded", count=len(valid_recipients), reason=reason)
        except Exception as exc:
            await db.rollback()
            log.error("email_suppression_failed", exc=str(exc))
            raise


async def run() -> None:
    if not settings.sqs_mail_events_url:
        log.warning("mail_worker_disabled", reason="SQS_MAIL_EVENTS_URL not set")
        while True:
            await asyncio.sleep(60)

    client = _sqs_client()
    loop = asyncio.get_running_loop()
    log.info("mail_worker_started", queue=settings.sqs_mail_events_url)

    while True:
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.receive_message(
                    QueueUrl=settings.sqs_mail_events_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,
                    VisibilityTimeout=90,
                ),
            )
            messages = response.get("Messages", [])
            await asyncio.gather(
                *[_handle_message(client, loop, msg) for msg in messages],
                return_exceptions=True,
            )
        except Exception as exc:
            log.error("mail_worker_poll_error", exc=str(exc))
            await asyncio.sleep(5)


async def _handle_message(client, loop, msg: dict) -> None:
    try:
        body = json.loads(msg["Body"])
        await process_message(body)
        await loop.run_in_executor(
            None,
            lambda: client.delete_message(
                QueueUrl=settings.sqs_mail_events_url,
                ReceiptHandle=msg["ReceiptHandle"],
            ),
        )
    except Exception as exc:
        log.error("mail_message_failed", exc=str(exc))


if __name__ == "__main__":
    asyncio.run(run())
