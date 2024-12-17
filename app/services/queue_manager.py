# app/services/queue_manager.py

import asyncio
from sqlalchemy.orm import Session
from app.models.orm_models import SubmissionModel
from app.services.submission_service import process_submission
import logging

logger = logging.getLogger(__name__)

class SubmissionQueueManager:
    def __init__(self, max_concurrent: int):
        self.queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.worker_task = None
        self.shutdown = False

    async def start(self):
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self.worker())
            logger.info("Submission Queue Manager started.")

    async def stop(self):
        self.shutdown = True
        if self.worker_task:
            await self.queue.put(None)  # Маркер завершения
            await self.worker_task
            logger.info("Submission Queue Manager stopped.")

    async def enqueue_submission(self, submission: SubmissionModel, db: Session):
        await self.queue.put((submission, db))
        logger.info(f"Submission {submission.token} enqueued.")

    async def worker(self):
        while not self.shutdown:
            item = await self.queue.get()
            if item is None:
                break
            submission, db = item
            await self.semaphore.acquire()
            asyncio.create_task(self.handle_submission(submission, db))

    async def handle_submission(self, submission: SubmissionModel, db: Session):
        try:
            logger.info(f"Processing submission {submission.token}.")
            # Устанавливаем статус в 2 (Processing Submission)
            submission.status = 2
            db.commit()
            await process_submission(submission, db)
        except Exception as e:
            logger.exception(f"Error processing submission {submission.token}: {e}")
        finally:
            self.semaphore.release()
            self.queue.task_done()
            logger.info(f"Submission {submission.token} processing completed.")
