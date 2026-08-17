from __future__ import annotations

import asyncio
import json
import logging
import platform
import shutil
import socket
from datetime import datetime
from typing import Awaitable, Callable

from sqlalchemy.orm import Session

from app.core.config_file import ini_value
from app.models.orm_models import LanguageModel, WorkerModel
from app.worker.config import WorkerSettings
from app.worker.state import SubmissionLease, renew_submission_leases

logger = logging.getLogger(__name__)

async def detect_isolate_version():
    executable = shutil.which("isolate")
    if executable is None:
        return None
    process = await asyncio.create_subprocess_exec(
        executable,
        "--version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        logger.warning("Timed out while detecting isolate version")
        return None
    if process.returncode != 0:
        logger.warning("Could not detect isolate version: %s", stderr.decode(errors="replace"))
        return None
    version = (stdout or stderr).decode(errors="replace").strip().splitlines()
    return version[0][:64] if version else None


class WorkerHeartbeat:
    def __init__(
        self,
        settings: WorkerSettings,
        session_factory: Callable[[], Session],
        *,
        isolate_version_provider: Callable[[], Awaitable[str | None]] = detect_isolate_version,
        hostname: str | None = None,
        version: str | None = None,
    ):
        self.settings = settings
        self.session_factory = session_factory
        self.isolate_version_provider = isolate_version_provider
        self.hostname = hostname or socket.gethostname()
        self.version = version or str(ini_value("PROJECT BASIC SETTINGS", "PROJECT_VERSION"))
        self._active: dict[str, int] = {}
        self._active_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._isolate_version: str | None = None

    async def start(self):
        if self._task is not None:
            return
        self._stop_event.clear()
        self._isolate_version = await self.isolate_version_provider()
        await asyncio.to_thread(self._register)
        logger.info(
            "event=worker.registered worker_id=%s pool=%s concurrency=%s isolate_version=%s",
            self.settings.worker_id,
            self.settings.pool,
            self.settings.concurrency,
            self._isolate_version,
        )
        self._task = asyncio.create_task(
            self._run(), name=f"worker-heartbeat-{self.settings.worker_id}"
        )

    async def stop(self):
        task = self._task
        self._task = None
        if task is None:
            return
        self._stop_event.set()
        await task
        async with self._active_lock:
            self._active.clear()
        try:
            await asyncio.to_thread(self._write_cycle, {}, True)
        except Exception:
            logger.exception(
                "event=worker.heartbeat.failed worker_id=%s final=true",
                self.settings.worker_id,
            )
        else:
            logger.info("event=worker.unregistered worker_id=%s", self.settings.worker_id)

    async def job_started(self, token: str, lease: SubmissionLease):
        async with self._active_lock:
            self._active[token] = lease.attempt_count

    async def job_finished(self, token: str, lease: SubmissionLease):
        async with self._active_lock:
            if self._active.get(token) == lease.attempt_count:
                self._active.pop(token, None)

    async def _run(self):
        interval = min(
            self.settings.heartbeat_interval,
            self.settings.lease_renewal_interval,
        )
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass
            async with self._active_lock:
                attempts = dict(self._active)
            try:
                renewed = await asyncio.to_thread(self._write_cycle, attempts, False)
                lost = set(attempts) - renewed
                if lost:
                    logger.warning(
                        "event=worker.lease_lost worker_id=%s tokens=%s",
                        self.settings.worker_id,
                        sorted(lost),
                    )
            except Exception:
                logger.exception(
                    "event=worker.heartbeat.failed worker_id=%s final=false",
                    self.settings.worker_id,
                )

    def _capabilities(self, db: Session):
        query = db.query(LanguageModel).filter(LanguageModel.enabled.is_(True))
        if self.settings.pool != "full":
            query = query.filter(LanguageModel.pool == self.settings.pool)
        languages = query.order_by(LanguageModel.id).all()
        return {
            "languages": [
                {"slug": item.slug, "version": item.version, "pool": item.pool}
                for item in languages
            ],
            "box_ids": {
                "first": self.settings.box_id_offset,
                "last": self.settings.box_id_offset + self.settings.concurrency - 1,
            },
            "host": {"system": platform.system(), "machine": platform.machine()},
        }

    def _register(self):
        db = self.session_factory()
        try:
            now = datetime.utcnow()
            worker = db.get(WorkerModel, self.settings.worker_id)
            capabilities_json = json.dumps(
                self._capabilities(db), ensure_ascii=False, sort_keys=True
            )
            if worker is None:
                worker = WorkerModel(id=self.settings.worker_id)
                db.add(worker)
            worker.hostname = self.hostname
            worker.pool = self.settings.pool
            worker.version = self.version
            worker.concurrency = self.settings.concurrency
            worker.active_jobs = 0
            worker.started_at = now
            worker.last_seen_at = now
            worker.completed_jobs = 0
            worker.failed_jobs = 0
            worker.isolate_version = self._isolate_version
            worker.capabilities_json = capabilities_json
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _write_cycle(self, attempts: dict[str, int], final: bool):
        db = self.session_factory()
        try:
            renewed = (
                set()
                if final or not attempts
                else renew_submission_leases(
                    db,
                    self.settings.worker_id,
                    attempts,
                    self.settings.lease_duration,
                )
            )
            updated = db.query(WorkerModel).filter(
                WorkerModel.id == self.settings.worker_id
            ).update(
                {
                    WorkerModel.last_seen_at: datetime.utcnow(),
                    WorkerModel.active_jobs: 0 if final else len(attempts),
                },
                synchronize_session=False,
            )
            if updated != 1:
                db.rollback()
                raise RuntimeError("Worker registry row disappeared")
            db.commit()
            return renewed
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
