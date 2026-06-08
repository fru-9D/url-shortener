"""
Mixpanel forwarder worker.
SQS calls wrapped in run_in_executor to avoid blocking the async event loop.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

import boto3
import httpx
import structlog

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.mixpanel_dead_letter import MixpanelDeadLetter

log = structlog.get_logger()
_MIXPANEL_TRACK = "https://api.mixpanel.com/track"
_MAX_ATTEMPTS = 3
_BACKOFFS = [1.0, 4.0, 16.0]


def _sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


async def _post_to_mixpanel(payload: dict) -> None:
    for attempt, backoff in enumerate(_BACKOFFS):
        if attempt > 0:
            await asyncio.sleep(backoff)
        try:
            async with httpx.AsyncClient(timeout=settings.mixpanel_timeout) as client:
                resp = await client.post(_MIXPANEL_TRACK, json=[payload])
            resp.raise_for_status()
            return
        except Exception as exc:
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            log.warning("mixpanel_retry", attempt=attempt, exc=str(exc))


async def _write_dead_letter(payload: dict, error: str, workspace_id: str | None) -> None:
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            dl = MixpanelDeadLetter(
                id=uuid.uuid4(),
                workspace_id=uuid.UUID(workspace_id) if workspace_id else None,
                event_name=payload.get("event", "unknown"),
                payload=payload,
                attempts=_MAX_ATTEMPTS,
                last_error=error[:1024],
                created_at=now,
                updated_at=now,
            )
            db.add(dl)
            await db.commit()
        except Exception as exc:
            log.error("dead_letter_write_failed", exc=str(exc))


async def process_message(body: dict) -> None:
    workspace_id = body.get("properties", {}).get("workspace_id")
    try:
        await _post_to_mixpanel(body)
        log.info("mixpanel_event_sent", event=body.get("event"))
    except Exception as exc:
        log.error("mixpanel_exhausted", event=body.get("event"), exc=str(exc))
        await _write_dead_letter(body, str(exc), workspace_id)


async def run() -> None:
    if not settings.sqs_mixpanel_url:
        log.warning("mixpanel_forwarder_disabled", reason="SQS_MIXPANEL_URL not set")
        while True:
            await asyncio.sleep(60)

    client = _sqs_client()
    loop = asyncio.get_running_loop()
    log.info("mixpanel_forwarder_started", queue=settings.sqs_mixpanel_url)

    while True:
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.receive_message(
                    QueueUrl=settings.sqs_mixpanel_url,
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
            log.error("mixpanel_forwarder_poll_error", exc=str(exc))
            await asyncio.sleep(5)


async def _handle_message(client, loop, msg: dict) -> None:
    try:
        body = json.loads(msg["Body"])
        await process_message(body)
        await loop.run_in_executor(
            None,
            lambda: client.delete_message(
                QueueUrl=settings.sqs_mixpanel_url,
                ReceiptHandle=msg["ReceiptHandle"],
            ),
        )
    except Exception as exc:
        log.error("mixpanel_message_failed", exc=str(exc))


if __name__ == "__main__":
    asyncio.run(run())
