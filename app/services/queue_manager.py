# app/services/queue_manager.py

import os
import pika
import json
import logging
import threading
import asyncio
from sqlalchemy.orm import Session
from app.models.orm_models import SubmissionModel
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.submission_service import process_submission

logger = logging.getLogger(__name__)

class SubmissionQueueManager:
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent

        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "user")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "password")

        self.queue_name = "submissions_queue"

        self.shutdown_flag = False

        self._consumer_thread = None

    async def start(self):
        logger.info("Initializing RabbitMQ connection...")

        credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
        parameters = pika.ConnectionParameters(
            host=self.rabbitmq_host,
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue=self.queue_name, durable=True)

        self.channel.basic_qos(prefetch_count=self.max_concurrent)

        self._consumer_thread = threading.Thread(target=self._consume)
        self._consumer_thread.start()

        logger.info("Submission Queue Manager started (RabbitMQ).")

    def _consume(self):
        try:
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.on_message
            )
            logger.info("Start consuming from RabbitMQ...")
            self.channel.start_consuming()
        except Exception as e:
            logger.exception("Error in RabbitMQ consumer thread: %s", e)

    async def stop(self):
        logger.info("Stopping Submission Queue Manager (RabbitMQ).")
        self.shutdown_flag = True

        if self.connection and self.connection.is_open:
            self.connection.close()

        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join()

        logger.info("Submission Queue Manager stopped.")

    async def enqueue_submission(self, submission: SubmissionModel, db: Session):
        if not submission.token:
            logger.warning("Submission has no token, skipping publish.")
            return

        try:
            data = {"token": submission.token}
            body = json.dumps(data)

            if not hasattr(self, 'channel') or self.channel is None:
                logger.error("RabbitMQ channel is not initialized.")
                return

            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2
                )
            )
            logger.info(f"Submission {submission.token} published to RabbitMQ queue.")

        except Exception as e:
            logger.exception(f"Failed to publish submission {submission.token} to RabbitMQ: {e}")

    def on_message(self, ch, method, properties, body):
        try:
            data = json.loads(body)
            token = data.get("token")
            logger.info(f"Received message for submission {token}.")

            def run_in_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.process_token(token))
                loop.close()

            run_in_loop()

            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Submission {token} processed and acknowledged.")

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    async def process_token(self, token: str):
        if not token:
            logger.error("Empty token in process_token.")
            return

        db = SessionLocal()
        try:
            submission = db.query(SubmissionModel).filter_by(token=token).first()
            if not submission:
                logger.error(f"No submission found with token {token}")
                return

            submission.status_id = 2  # Processing Submission
            db.commit()

            await process_submission(submission, db)
            db.commit()

        except Exception as e:
            logger.exception(f"Error in process_token for submission {token}: {e}")
        finally:
            db.close()
