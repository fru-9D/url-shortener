"""
Mixpanel event publisher — publishes to SQS:mixpanel.
boto3 SQS calls wrapped in run_in_executor to avoid blocking the event loop.
"""
import asyncio
import json
import uuid
import structlog
import boto3
from botocore.exceptions import ClientError

from app.config import settings

log = structlog.get_logger()


def _sqs():
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


async def enqueue_event(event_name: str, properties: dict, insert_id: str | None = None) -> None:
    """Publish to SQS:mixpanel. Non-blocking best-effort — failures are logged, never raised."""
    if not settings.sqs_mixpanel_url:
        log.debug("mixpanel_event_skipped", event=event_name, reason="no_sqs_url")
        return

    payload = {
        "event": event_name,
        "properties": {
            **properties,
            "token": settings.mixpanel_token,
            "$insert_id": insert_id or str(uuid.uuid4()),
        },
    }

    def _blocking_enqueue() -> None:
        client = _sqs()
        client.send_message(
            QueueUrl=settings.sqs_mixpanel_url,
            MessageBody=json.dumps(payload),
        )

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _blocking_enqueue)
    except ClientError as exc:
        log.error("mixpanel_enqueue_failed", event=event_name, error=str(exc))
    except Exception as exc:
        log.error("mixpanel_enqueue_exception", event=event_name, error=str(exc))
