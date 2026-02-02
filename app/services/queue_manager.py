# app/services/queue_manager.py

import asyncio
import logging
import pickle
import aio_pika
from aio_pika import Message, DeliveryMode
from typing import Optional
from app.db.session import SessionLocal
from app.services.submission_service import process_submission
from app.models.orm_models import SubmissionModel
from app.core.config import settings

logger = logging.getLogger(__name__)

RABBITMQ_URL = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:5672/"

class SubmissionQueueManager:
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self.queue_name = "submissions_queue"
        self.completed_tasks = 0
        self.failed_tasks = 0

    async def start(self):
        self.connection = await aio_pika.connect_robust(
            RABBITMQ_URL,
            # event_loop=asyncio.get_event_loop() #not necessary
        )
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=self.max_concurrent)
        self.queue = await self.channel.declare_queue(
            self.queue_name,
            durable=True
        )
        await self.queue.consume(self.handle_message)

        logger.info("SubmissionQueueManager started with aio-pika.")

    async def stop(self):
        if self.connection:
            await self.connection.close()
            logger.info("SubmissionQueueManager stopped.")

    async def enqueue_submission(self, submission: SubmissionModel, db, reply_queue=None, correlation_id=None):
        try:
            payload = {
                "submission_token": submission.token
            }
            body = pickle.dumps(payload)

            msg = Message(
                body,
                delivery_mode=DeliveryMode.PERSISTENT,
                reply_to=reply_queue.name if reply_queue else None,
                correlation_id=correlation_id,
            )

            await self.channel.default_exchange.publish(msg, routing_key=self.queue_name)
            logger.info(f"Submission {submission.token} enqueued to RabbitMQ.")

        except Exception as e:
            logger.error(f"Failed to publish submission {submission.token}: {e}")
            raise

    async def handle_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            async with self.semaphore:
                try:
                    data = pickle.loads(message.body)
                    submission_token = data["submission_token"]

                    db = SessionLocal()
                    try:
                        submission = db.query(SubmissionModel).filter_by(token=submission_token).first()
                        if not submission:
                            logger.error(f"Submission {submission_token} not found in DB.")
                            return

                        submission.status_id = 2
                        db.commit()

                        await process_submission(submission, db)

                        db.commit()
                        logger.info(f"Submission {submission.token} processing completed.")
                        self.completed_tasks += 1
                        
                        if message.reply_to:
                            result = {
                                "token": submission.token,
                                "status_id": submission.status_id,
                                "stdout": submission.stdout,
                                "stderr": submission.stderr,
                                "compile_output": submission.compile_output,
                            }
                            response_body = pickle.dumps(result)

                            await self.channel.default_exchange.publish(
                                Message(
                                    response_body,
                                    correlation_id=message.correlation_id
                                ),
                                routing_key=message.reply_to
                            )

                    finally:
                        db.close()

                except Exception as e:
                    logger.exception(f"Error handling message: {e}")
                    self.failed_tasks += 1
