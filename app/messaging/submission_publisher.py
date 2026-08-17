from __future__ import annotations

import logging
from datetime import datetime
from typing import Awaitable, Callable

import aio_pika

from app.messaging.contracts import SubmissionJob
from app.messaging.rabbit import (
    SUBMISSIONS_QUEUE,
    SUBMISSIONS_ROUTING_KEY,
    RabbitMQConnectionSettings,
    declare_submission_queue,
)

logger = logging.getLogger(__name__)

class SubmissionPublishError(RuntimeError):
    pass

class SubmissionPublisher:
    def __init__(
        self,
        connection_settings: RabbitMQConnectionSettings | None = None,
        connection_factory: Callable[..., Awaitable] = aio_pika.connect_robust,
    ) -> None:
        self.connection_settings = connection_settings
        self.connection_factory = connection_factory
        self.connection = None
        self.channel = None
        self.queue = None

    @property
    def is_connected(self) -> bool:
        return bool(
            self.connection
            and not self.connection.is_closed
            and self.channel
            and not self.channel.is_closed
        )

    async def start(self):
        if self.is_connected:
            return
        connection_settings = (
            self.connection_settings or RabbitMQConnectionSettings.from_application_settings()
        )
        try:
            self.connection = await self.connection_factory(
                **connection_settings.connection_kwargs()
            )
            self.channel = await self.connection.channel(
                publisher_confirms=True,
                on_return_raises=True,
            )
            self.queue = await declare_submission_queue(self.channel)
        except Exception as exc:
            connection = self.connection
            self.queue = None
            self.channel = None
            self.connection = None
            if connection is not None and not connection.is_closed:
                await connection.close()
            raise SubmissionPublishError("Failed to start submission publisher") from exc
        logger.info(
            "event=publisher.connected queue=%s",
            SUBMISSIONS_QUEUE,
        )

    async def stop(self):
        connection = self.connection
        self.queue = None
        self.channel = None
        self.connection = None
        if connection is not None and not connection.is_closed:
            await connection.close()
            logger.info("event=publisher.disconnected queue=%s", SUBMISSIONS_QUEUE)

    async def publish_submission(
        self,
        submission_token: str,
        language_slug: str,
        pool: str,
        *,
        enqueued_at: datetime | None = None,
    ):
        if not self.is_connected:
            raise SubmissionPublishError("Submission publisher is not connected")

        job = SubmissionJob.create(
            submission_token=submission_token,
            language_slug=language_slug,
            pool=pool,
            enqueued_at=enqueued_at,
        )
        message = aio_pika.Message(
            body=job.encode(),
            content_type="application/json",
            content_encoding="utf-8",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=job.job_id,
            correlation_id=job.submission_token,
            timestamp=job.enqueued_at,
            type="submission.execute.v1",
            headers={"x-job-version": job.version},
        )

        try:
            await self.channel.default_exchange.publish(
                message,
                routing_key=SUBMISSIONS_ROUTING_KEY,
                mandatory=True,
            )
        except Exception as exc:
            logger.exception(
                "event=job.publish_failed token=%s job_id=%s language=%s pool=%s queue=%s",
                job.submission_token,
                job.job_id,
                job.language_slug,
                job.pool,
                SUBMISSIONS_ROUTING_KEY,
            )
            raise SubmissionPublishError(
                f"Failed to publish submission {job.submission_token}"
            ) from exc
        logger.info(
            "event=job.published token=%s job_id=%s language=%s pool=%s queue=%s",
            job.submission_token,
            job.job_id,
            job.language_slug,
            job.pool,
            SUBMISSIONS_ROUTING_KEY,
        )
        return job

    async def get_queue_snapshot(self):
        if not self.is_connected:
            return {
                "broker_connected": False,
                "queue_name": SUBMISSIONS_QUEUE,
            }
        queue = await self.channel.declare_queue(SUBMISSIONS_QUEUE, passive=True)
        result = queue.declaration_result
        return {
            "broker_connected": True,
            "queue_name": SUBMISSIONS_QUEUE,
            "ready_messages": result.message_count,
            "consumers": result.consumer_count,
        }
