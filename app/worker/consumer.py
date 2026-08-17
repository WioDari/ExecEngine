from __future__ import annotations

import asyncio
import logging
from enum import Enum
from time import monotonic
from typing import Awaitable, Callable

import aio_pika
from sqlalchemy.orm import Session

from app.core.execution_config import execution_settings
from app.execution.box_pool import BoxPool
from app.execution.errors import ExecutionConfigurationError
from app.execution.executor import (
    ExecutionResult,
    execution_result_values,
    execute_submission,
)
from app.execution.isolate import IsolateRunner
from app.messaging.contracts import SubmissionJob, SubmissionJobValidationError
from app.messaging.rabbit import declare_submission_queue, submission_queue_name
from app.models.orm_models import LanguageModel
from app.services.callback_service import create_callback_delivery
from app.worker.config import WorkerSettings
from app.worker.registry import WorkerHeartbeat
from app.worker.state import (
    ClaimDecision,
    ClaimResult,
    SubmissionLease,
    TERMINAL_STATUS_IDS,
    claim_submission,
    complete_submission,
    release_submission_claim,
)

logger = logging.getLogger(__name__)

class DeliveryOutcome(str, Enum):
    ACKED = "acked"
    REQUEUED = "requeued"
    REJECTED = "rejected"

class SubmissionWorker:
    def __init__(
        self,
        settings: WorkerSettings,
        *,
        connection_factory: Callable[..., Awaitable] = aio_pika.connect_robust,
        session_factory: Callable[[], Session] | None = None,
        executor: Callable[..., Awaitable] | None = None,
        callback_factory: Callable[..., object] = create_callback_delivery,
        box_pool: BoxPool | None = None,
        isolate_runner: IsolateRunner | None = None,
        registry: WorkerHeartbeat | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.settings = settings
        self.connection_factory = connection_factory
        if session_factory is None:
            from app.db.session import SessionLocal

            session_factory = SessionLocal
        self.session_factory = session_factory
        self.executor = executor
        self.callback_factory = callback_factory
        self.box_pool = box_pool or BoxPool(
            settings.concurrency,
            offset=settings.box_id_offset,
        )
        self.isolate_runner = isolate_runner or IsolateRunner(
            cleanup_timeout=execution_settings.isolate_cleanup_timeout,
            max_host_output_bytes=execution_settings.max_captured_output_bytes,
        )
        self.registry = registry
        self.sleep = sleep
        self.connection = None
        self.channel = None
        self.queue = None
        self.consumer_tag: str | None = None
        self._active_handlers: set[asyncio.Task] = set()

    @property
    def queue_name(self):
        return submission_queue_name(self.settings.pool)

    @property
    def is_connected(self):
        return bool(
            self.connection
            and not self.connection.is_closed
            and self.channel
            and not self.channel.is_closed
        )

    async def start(self):
        if self.consumer_tag is not None:
            return
        try:
            self.connection = await self.connection_factory(
                **self.settings.rabbitmq.connection_kwargs()
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.settings.concurrency)
            self.queue = await declare_submission_queue(self.channel, self.settings.pool)
            self.consumer_tag = await self.queue.consume(self._consume_message, no_ack=False)
            if self.registry is not None:
                await self.registry.start()
        except Exception:
            self.consumer_tag = None
            await self._close_connection()
            raise
        logger.info(
            "event=worker.started worker_id=%s pool=%s concurrency=%s queue=%s",
            self.settings.worker_id,
            self.settings.pool,
            self.settings.concurrency,
            self.queue_name,
        )

    async def run(self, stop_event: asyncio.Event):
        await self.start()
        try:
            await stop_event.wait()
        finally:
            await self.stop()

    async def stop(self):
        queue = self.queue
        consumer_tag = self.consumer_tag
        self.consumer_tag = None
        if queue is not None and consumer_tag is not None:
            try:
                await queue.cancel(consumer_tag)
            except Exception:
                logger.exception("Failed to cancel worker consumer worker_id=%s", self.settings.worker_id)

        active = tuple(self._active_handlers)
        if active:
            logger.info(
                "Waiting for %s active submission(s) before worker shutdown worker_id=%s",
                len(active),
                self.settings.worker_id,
            )
            await asyncio.gather(*active, return_exceptions=True)
        if self.registry is not None:
            await self.registry.stop()
        await self._close_connection()
        logger.info(
            "event=worker.stopped worker_id=%s pool=%s",
            self.settings.worker_id,
            self.settings.pool,
        )

    async def _close_connection(self):
        connection = self.connection
        self.queue = None
        self.channel = None
        self.connection = None
        if connection is not None and not connection.is_closed:
            await connection.close()

    async def _consume_message(self, message: aio_pika.IncomingMessage):
        current = asyncio.current_task()
        if current is not None:
            self._active_handlers.add(current)
        try:
            await self.handle_message(message)
        finally:
            if current is not None:
                self._active_handlers.discard(current)

    async def handle_message(self, message: aio_pika.IncomingMessage):
        try:
            job = SubmissionJob.decode(message.body)
        except SubmissionJobValidationError as exc:
            logger.warning(
                "event=worker.job.rejected reason=invalid_message error_type=%s",
                type(exc).__name__,
            )
            await message.reject(requeue=False)
            return DeliveryOutcome.REJECTED

        logger.info(
            "event=worker.job.received token=%s job_id=%s language=%s pool=%s redelivered=%s",
            job.submission_token,
            job.job_id,
            job.language_slug,
            job.pool,
            bool(getattr(message, "redelivered", False)),
        )

        db = None
        try:
            db = self.session_factory()
            claim = claim_submission(
                db,
                job.submission_token,
                self.settings.worker_id,
                self.settings.lease_duration,
            )
        except Exception:
            logger.exception(
                "event=worker.job.claim_failed token=%s job_id=%s worker_id=%s reason=database_error",
                job.submission_token,
                job.job_id,
                self.settings.worker_id,
            )
            if db is not None:
                db.rollback()
                db.close()
            return await self._requeue(
                message,
                token=job.submission_token,
                job_id=job.job_id,
                reason="database_claim_error",
            )

        if claim.decision != ClaimDecision.CLAIMED or claim.submission is None:
            db.close()
            if claim.decision == ClaimDecision.NOT_FOUND:
                logger.error(
                    "event=worker.job.rejected token=%s job_id=%s reason=submission_not_found",
                    job.submission_token,
                    job.job_id,
                )
                await message.reject(requeue=False)
                return DeliveryOutcome.REJECTED
            if claim.decision == ClaimDecision.ALREADY_FINISHED:
                logger.info(
                    "event=worker.job.acked token=%s job_id=%s reason=already_finished",
                    job.submission_token,
                    job.job_id,
                )
                await message.ack()
                return DeliveryOutcome.ACKED
            if claim.decision == ClaimDecision.ACTIVE_LEASE:
                logger.warning(
                    "event=worker.job.requeue_requested token=%s job_id=%s reason=active_lease",
                    job.submission_token,
                    job.job_id,
                )
                return await self._requeue(
                    message,
                    token=job.submission_token,
                    job_id=job.job_id,
                    reason="active_lease",
                )
            logger.error(
                "event=worker.job.rejected token=%s job_id=%s reason=invalid_state",
                job.submission_token,
                job.job_id,
            )
            await message.reject(requeue=False)
            return DeliveryOutcome.REJECTED

        submission = claim.submission
        lease = claim.lease
        if lease is None:
            db.close()
            logger.error(
                "event=worker.job.claim_failed token=%s job_id=%s worker_id=%s reason=missing_lease",
                job.submission_token,
                job.job_id,
                self.settings.worker_id,
            )
            return await self._requeue(
                message,
                token=job.submission_token,
                job_id=job.job_id,
                reason="missing_lease",
            )
        logger.info(
            "event=worker.job.claimed token=%s job_id=%s worker_id=%s attempt=%s",
            job.submission_token,
            job.job_id,
            self.settings.worker_id,
            lease.attempt_count,
        )
        if self.registry is not None:
            await self.registry.job_started(job.submission_token, lease)
        execution_started = monotonic()
        try:
            language = (
                db.query(LanguageModel)
                .filter(LanguageModel.id == submission.language_id)
                .first()
            )
            if language is not None and language.slug != job.language_slug:
                logger.warning(
                    "event=worker.job.metadata_mismatch token=%s job_slug=%s db_slug=%s",
                    job.submission_token,
                    job.language_slug,
                    language.slug,
                )

            try:
                if self.executor is None:
                    result = await execute_submission(
                        submission,
                        language,
                        box_pool=self.box_pool,
                        runner=self.isolate_runner,
                    )
                else:
                    result = await self.executor(submission, language)
            except ExecutionConfigurationError as exc:
                logger.error(
                    "event=execution.configuration_failed token=%s worker_id=%s error=%s",
                    job.submission_token,
                    self.settings.worker_id,
                    exc,
                )
                result = ExecutionResult.internal_error(
                    f"Execution configuration error: {exc}"
                )

            logger.info(
                "event=execution.completed token=%s job_id=%s worker_id=%s attempt=%s "
                "status_id=%s duration_ms=%d cpu_time=%s wall_time=%s memory_kb=%s "
                "exit_code=%s exit_signal=%s",
                job.submission_token,
                job.job_id,
                self.settings.worker_id,
                lease.attempt_count,
                result.status_id,
                round((monotonic() - execution_started) * 1000),
                result.time,
                result.wall_time,
                result.memory,
                result.exit_code,
                result.exit_signal,
            )

            completed = complete_submission(
                db,
                job.submission_token,
                lease,
                execution_result_values(result),
                self.callback_factory,
            )
            if not completed:
                logger.warning(
                    "event=worker.job.acked token=%s job_id=%s worker_id=%s attempt=%s reason=stale_result",
                    job.submission_token,
                    job.job_id,
                    lease.worker_id,
                    lease.attempt_count,
                )
                await message.ack()
                return DeliveryOutcome.ACKED
        except Exception:
            logger.exception(
                "event=execution.failed token=%s job_id=%s worker_id=%s attempt=%s duration_ms=%d",
                job.submission_token,
                job.job_id,
                self.settings.worker_id,
                lease.attempt_count,
                round((monotonic() - execution_started) * 1000),
            )
            db.rollback()
            released = False
            try:
                released = release_submission_claim(db, job.submission_token, lease)
            except Exception:
                logger.exception(
                    "event=worker.job.release_failed token=%s job_id=%s worker_id=%s",
                    job.submission_token,
                    job.job_id,
                    self.settings.worker_id,
                )
                db.rollback()
                return await self._requeue(
                    message,
                    token=job.submission_token,
                    job_id=job.job_id,
                    reason="claim_release_error",
                )
            if released:
                return await self._requeue(
                    message,
                    token=job.submission_token,
                    job_id=job.job_id,
                    reason="temporary_execution_failure",
                )
            logger.warning(
                "event=worker.job.acked token=%s job_id=%s worker_id=%s attempt=%s reason=stale_failed_attempt",
                job.submission_token,
                job.job_id,
                lease.worker_id,
                lease.attempt_count,
            )
            await message.ack()
            return DeliveryOutcome.ACKED
        finally:
            db.close()
            if self.registry is not None:
                await self.registry.job_finished(job.submission_token, lease)

        await message.ack()
        logger.info(
            "event=worker.job.acked token=%s job_id=%s worker_id=%s reason=completed",
            job.submission_token,
            job.job_id,
            self.settings.worker_id,
        )
        return DeliveryOutcome.ACKED

    async def _requeue(
        self,
        message: aio_pika.IncomingMessage,
        *,
        token: str,
        job_id: str,
        reason: str,
    ):
        if self.settings.redelivery_backoff > 0:
            await self.sleep(self.settings.redelivery_backoff)
        await message.nack(requeue=True)
        logger.warning(
            "event=worker.job.nacked token=%s job_id=%s worker_id=%s requeue=true reason=%s",
            token,
            job_id,
            self.settings.worker_id,
            reason,
        )
        return DeliveryOutcome.REQUEUED
