from __future__ import annotations

import asyncio
import logging
import signal

from app.worker.config import WorkerSettings
from app.worker.consumer import SubmissionWorker

logger = logging.getLogger(__name__)

def _install_signal_handlers(stop_event: asyncio.Event):
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        logger.info("Worker shutdown requested")
        stop_event.set()

    for signal_number in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_number, request_stop)
        except NotImplementedError:
            signal.signal(
                signal_number,
                lambda _signum, _frame: loop.call_soon_threadsafe(request_stop),
            )

async def async_main():
    from app.core.config_distribution import validate_role_configuration
    from app.core.config_file import load_ini

    validate_role_configuration(load_ini(), "worker")
    settings = WorkerSettings.from_ini()

    from app.db.session import SessionLocal, wait_for_db
    from app.worker.registry import WorkerHeartbeat

    await asyncio.to_thread(
        wait_for_db,
        max_retries=settings.db_max_retries,
        retry_interval=settings.db_retry_interval,
    )
    stop_event = asyncio.Event()
    _install_signal_handlers(stop_event)
    worker = SubmissionWorker(
        settings,
        registry=WorkerHeartbeat(settings, SessionLocal),
    )
    await worker.run(stop_event)

def main():
    from app.core.logger import setup_logging

    setup_logging("worker")
    asyncio.run(async_main())

if __name__ == "__main__":
    main()