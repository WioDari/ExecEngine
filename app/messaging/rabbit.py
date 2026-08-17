from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

SUBMISSIONS_QUEUE = "submissions.full"
SUBMISSIONS_ROUTING_KEY = SUBMISSIONS_QUEUE
_POOL_PATTERN = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")

def submission_queue_name(pool: str):
    if not isinstance(pool, str) or not _POOL_PATTERN.fullmatch(pool):
        raise ValueError("RabbitMQ pool must be a lowercase identifier")
    return f"submissions.{pool}"

@dataclass(frozen=True)
class RabbitMQConnectionSettings:
    host: str
    port: int
    login: str
    password: str = field(repr=False)
    connection_name: str = "execengine-api-publisher"

    @classmethod
    def from_application_settings(cls) -> "RabbitMQConnectionSettings":
        from app.core.config import settings

        return cls(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_USER,
            password=settings.RABBITMQ_PASSWORD.get_secret_value(),
        )

    def connection_kwargs(self):
        return {
            "host": self.host,
            "port": self.port,
            "login": self.login,
            "password": self.password,
            "client_properties": {"connection_name": self.connection_name},
        }

async def declare_submission_queue(channel, pool: str = "full"):
    return await channel.declare_queue(submission_queue_name(pool), durable=True)
