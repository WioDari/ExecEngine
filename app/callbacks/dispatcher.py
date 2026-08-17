from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Callable
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.callbacks.config import CallbackSettings
from app.callbacks.delivery import (
    CallbackClaim,
    claim_due_callbacks,
    load_callback_request,
    mark_callback_delivered,
    mark_callback_failed,
)


logger = logging.getLogger(__name__)


class CallbackDispatcher:
    def __init__(
        self,
        settings: CallbackSettings,
        session_factory: Callable[[], Session],
        *,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ):
        self.settings = settings
        self.session_factory = session_factory
        self.client_factory = client_factory

    async def run(self, stop_event: asyncio.Event):
        logger.info(
            "event=callback.worker.started worker_id=%s concurrency=%s batch_size=%s",
            self.settings.worker_id,
            self.settings.concurrency,
            self.settings.batch_size,
        )
        while not stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=self.settings.poll_interval
                )
            except asyncio.TimeoutError:
                pass
        logger.info("event=callback.worker.stopped worker_id=%s", self.settings.worker_id)

    async def run_once(self):
        claims = await asyncio.to_thread(self._claim)
        if not claims:
            return 0
        logger.info(
            "event=callback.batch.claimed worker_id=%s count=%s",
            self.settings.worker_id,
            len(claims),
        )
        semaphore = asyncio.Semaphore(self.settings.concurrency)
        async with self.client_factory(
            timeout=httpx.Timeout(self.settings.http_timeout),
            follow_redirects=False,
        ) as client:
            async def deliver(claim: CallbackClaim):
                async with semaphore:
                    await self._deliver(client, claim)

            await asyncio.gather(*(deliver(claim) for claim in claims))
        return len(claims)

    def _claim(self):
        db = self.session_factory()
        try:
            return claim_due_callbacks(
                db,
                self.settings.worker_id,
                self.settings.batch_size,
                self.settings.lease_duration,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def _deliver(self, client: httpx.AsyncClient, claim: CallbackClaim):
        started = monotonic()
        destination_host = urlsplit(claim.callback_url).hostname or "unknown"
        logger.info(
            "event=callback.delivery.started delivery_id=%s worker_id=%s attempt=%s host=%s",
            claim.delivery_id,
            self.settings.worker_id,
            claim.attempt_count,
            destination_host,
        )
        request = await asyncio.to_thread(self._load_request, claim)
        if request is None:
            await asyncio.to_thread(
                self._mark_failed, claim, "Submission not found", None
            )
            logger.error(
                "event=callback.delivery.failed delivery_id=%s attempt=%s "
                "reason=submission_not_found duration_ms=%d",
                claim.delivery_id,
                claim.attempt_count,
                round((monotonic() - started) * 1000),
            )
            return
        body, headers = request
        try:
            response = await client.post(
                claim.callback_url,
                content=body,
                headers=headers,
            )
        except Exception as exc:
            logger.warning(
                "event=callback.delivery.failed delivery_id=%s attempt=%s host=%s "
                "error_type=%s terminal=%s duration_ms=%d",
                claim.delivery_id,
                claim.attempt_count,
                destination_host,
                type(exc).__name__,
                claim.attempt_count >= self.settings.max_attempts,
                round((monotonic() - started) * 1000),
            )
            await asyncio.to_thread(self._mark_failed, claim, str(exc), None)
            return
        if 200 <= response.status_code < 300:
            owned = await asyncio.to_thread(
                self._mark_delivered, claim, response.status_code
            )
        else:
            owned = await asyncio.to_thread(
                self._mark_failed,
                claim,
                f"HTTP {response.status_code}",
                response.status_code,
            )
        if not owned:
            logger.warning(
                "event=callback.delivery.stale delivery_id=%s attempt=%s",
                claim.delivery_id,
                claim.attempt_count,
            )
        elif 200 <= response.status_code < 300:
            logger.info(
                "event=callback.delivery.completed delivery_id=%s attempt=%s host=%s "
                "status_code=%s duration_ms=%d",
                claim.delivery_id,
                claim.attempt_count,
                destination_host,
                response.status_code,
                round((monotonic() - started) * 1000),
            )
        else:
            logger.warning(
                "event=callback.delivery.failed delivery_id=%s attempt=%s host=%s "
                "status_code=%s terminal=%s duration_ms=%d",
                claim.delivery_id,
                claim.attempt_count,
                destination_host,
                response.status_code,
                claim.attempt_count >= self.settings.max_attempts,
                round((monotonic() - started) * 1000),
            )

    def _load_request(self, claim: CallbackClaim):
        db = self.session_factory()
        try:
            return load_callback_request(db, claim)
        finally:
            db.close()

    def _mark_delivered(self, claim: CallbackClaim, status: int):
        db = self.session_factory()
        try:
            return mark_callback_delivered(db, claim, status)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _mark_failed(
        self, claim: CallbackClaim, error: str, status: int | None
    ):
        db = self.session_factory()
        try:
            return mark_callback_failed(
                db,
                claim,
                error,
                self.settings.max_attempts,
                self.settings.retry_delays,
                http_status=status,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
