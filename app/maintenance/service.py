from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from time import monotonic
from typing import Callable

from sqlalchemy.orm import Session

from app.maintenance.cleanup import (
    CleanupResult,
    cleanup_api_tokens_batch,
    cleanup_submissions_batch,
)
from app.maintenance.config import MaintenanceSettings

logger = logging.getLogger(__name__)

class MaintenanceService:
    def __init__(
        self,
        settings: MaintenanceSettings,
        session_factory: Callable[[], Session],
    ):
        self.settings = settings
        self.session_factory = session_factory

    async def run(self, stop_event: asyncio.Event):
        next_submissions = 0.0
        next_tokens = 0.0
        logger.info("event=maintenance.started")
        while not stop_event.is_set():
            current = monotonic()
            if current >= next_submissions:
                started = monotonic()
                logger.info("event=maintenance.cycle.started task=submission_retention")
                try:
                    deleted = await asyncio.to_thread(self.cleanup_submissions)
                except Exception:
                    logger.exception(
                        "event=maintenance.cycle.failed task=submission_retention duration_ms=%d",
                        round((monotonic() - started) * 1000),
                    )
                    raise
                logger.info(
                    "event=maintenance.cycle.completed task=submission_retention "
                    "deleted=%s duration_ms=%d",
                    deleted,
                    round((monotonic() - started) * 1000),
                )
                next_submissions = current + self.settings.submissions_interval
            if current >= next_tokens:
                started = monotonic()
                logger.info("event=maintenance.cycle.started task=expired_tokens")
                try:
                    deleted = await asyncio.to_thread(self.cleanup_api_tokens)
                except Exception:
                    logger.exception(
                        "event=maintenance.cycle.failed task=expired_tokens duration_ms=%d",
                        round((monotonic() - started) * 1000),
                    )
                    raise
                logger.info(
                    "event=maintenance.cycle.completed task=expired_tokens "
                    "deleted=%s duration_ms=%d",
                    deleted,
                    round((monotonic() - started) * 1000),
                )
                next_tokens = current + self.settings.api_tokens_interval
            timeout = max(0.01, min(next_submissions, next_tokens) - monotonic())
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass
        logger.info("event=maintenance.stopped")

    def cleanup_submissions(self, *, now: datetime | None = None):
        return self._drain(
            lambda db: cleanup_submissions_batch(
                db,
                self.settings.submission_retention_days,
                self.settings.delete_batch_size,
                now=now,
            )
        )

    def cleanup_api_tokens(self, *, now: datetime | None = None):
        return self._drain(
            lambda db: cleanup_api_tokens_batch(
                db,
                self.settings.delete_batch_size,
                now=now,
            )
        )

    def _drain(self, cleanup: Callable[[Session], CleanupResult]):
        total = 0
        for _ in range(self.settings.max_batches_per_run):
            db = self.session_factory()
            try:
                result = cleanup(db)
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
            if not result.lock_acquired:
                logger.info("event=maintenance.lock_skipped reason=already_running")
                break
            total += result.deleted
            if result.deleted < self.settings.delete_batch_size:
                break
        return total
