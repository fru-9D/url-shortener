"""
Click consumer worker.
SQS receive_message runs in an executor thread so it doesn't block the event loop.
"""
import asyncio
import json
import re
import uuid
from datetime import datetime, timezone

import boto3
import structlog

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.click import Click
from app.services.mixpanel import enqueue_event

log = structlog.get_logger()

_BOT_PATTERNS = re.compile(
    r"bot|crawl|spider|slurp|Googlebot|bingbot|Yahoo|DuckDuck|Baidu|Yandex|Sogou",
    re.IGNORECASE,
)


def _is_bot(user_agent: str | None) -> bool:
    if not user_agent:
        return False
    return bool(_BOT_PATTERNS.search(user_agent))


def _sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


async def process_message(body: dict) -> None:
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            from app.models.link import Link

            link_id = uuid.UUID(body["link_id"])
            workspace_id = uuid.UUID(body["workspace_id"])
            event_id = uuid.UUID(body.get("event_id") or str(uuid.uuid4()))
            clicked_at = datetime.fromisoformat(body["clicked_at"])

            # Validate workspace_id against the DB — reject crafted SQS messages (RT-06)
            link_row = await db.execute(
                select(Link.workspace_id).where(Link.id == link_id)
            )
            db_workspace_id = link_row.scalar_one_or_none()
            if db_workspace_id is None or db_workspace_id != workspace_id:
                log.error(
                    "click_workspace_mismatch",
                    link_id=str(link_id),
                    msg_workspace=str(workspace_id),
                    db_workspace=str(db_workspace_id),
                )
                return  # Discard silently — do not retry
            if clicked_at.tzinfo is None:
                clicked_at = clicked_at.replace(tzinfo=timezone.utc)

            user_agent = body.get("user_agent")
            is_bot = _is_bot(user_agent)

            now = datetime.now(timezone.utc)
            click = Click(
                id=uuid.uuid4(),
                link_id=link_id,
                workspace_id=workspace_id,
                event_id=event_id,
                short_code=body.get("short_code", ""),
                country_code=body.get("country_code", "Unknown"),
                user_agent=user_agent,
                is_bot=is_bot,
                referrer_host=body.get("referrer_host"),
                clicked_at=clicked_at,
                created_at=now,
            )
            db.add(click)
            await db.commit()

            await enqueue_event(
                "link_clicked",
                {
                    "workspace_id": str(workspace_id),
                    "short_code": body.get("short_code", ""),
                    "country_code": body.get("country_code", "Unknown"),
                    "is_bot": is_bot,
                    "referrer_host": body.get("referrer_host", ""),
                },
                insert_id=str(click.id),
            )
            log.info("click_persisted", click_id=str(click.id), is_bot=is_bot)
        except Exception as exc:
            await db.rollback()
            log.error("click_process_error", exc=str(exc), body=body)
            raise


async def run() -> None:
    if not settings.sqs_clicks_url:
        log.warning("click_consumer_disabled", reason="SQS_CLICKS_URL not set")
        while True:
            await asyncio.sleep(60)

    client = _sqs_client()
    loop = asyncio.get_running_loop()
    log.info("click_consumer_started", queue=settings.sqs_clicks_url)

    while True:
        try:
            # Run blocking SQS long-poll in a thread pool so the event loop stays free
            response = await loop.run_in_executor(
                None,
                lambda: client.receive_message(
                    QueueUrl=settings.sqs_clicks_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,
                    VisibilityTimeout=90,
                ),
            )
            messages = response.get("Messages", [])
            # Process messages concurrently within the batch
            await asyncio.gather(
                *[_handle_message(client, msg) for msg in messages],
                return_exceptions=True,
            )
        except Exception as exc:
            log.error("click_consumer_poll_error", exc=str(exc))
            await asyncio.sleep(5)


async def _handle_message(client, msg: dict) -> None:
    try:
        body = json.loads(msg["Body"])
        await process_message(body)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: client.delete_message(
                QueueUrl=settings.sqs_clicks_url,
                ReceiptHandle=msg["ReceiptHandle"],
            ),
        )
    except Exception as exc:
        log.error("click_message_failed", exc=str(exc))


if __name__ == "__main__":
    asyncio.run(run())
