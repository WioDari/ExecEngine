from __future__ import annotations

import re
import socket
from dataclasses import dataclass

from app.core.config_file import ini_value
from app.messaging.rabbit import RabbitMQConnectionSettings

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_POOL_PATTERN = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")

def _required_ini(section: str, name: str):
    value = str(ini_value(section, name)).strip()
    if not value:
        raise RuntimeError(f"Required configuration option is not set: [{section}] {name}")
    return value

def _positive_integer(name: str, value: str | int, maximum: int):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not 1 <= parsed <= maximum:
        raise RuntimeError(f"{name} must be between 1 and {maximum}")
    return parsed

def _positive_float(name: str, value: str | float, maximum: float):
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if not 0 < parsed <= maximum:
        raise RuntimeError(f"{name} must be greater than 0 and at most {maximum}")
    return parsed

@dataclass(frozen=True)
class WorkerSettings:
    worker_id: str
    pool: str
    concurrency: int
    rabbitmq: RabbitMQConnectionSettings
    db_max_retries: int
    db_retry_interval: float
    box_id_offset: int = 0
    heartbeat_interval: float = 10.0
    stale_threshold: float = 45.0
    lease_duration: float = 60.0
    lease_renewal_interval: float = 10.0
    redelivery_backoff: float = 1.0

    @classmethod
    def from_ini(cls) -> "WorkerSettings":
        worker_id = str(ini_value("WORKER SETTINGS", "WORKER_ID")).strip()
        worker_id = worker_id or socket.gethostname()
        if not _IDENTIFIER_PATTERN.fullmatch(worker_id):
            raise RuntimeError(
                "WORKER_ID must start with a letter or digit and contain at most "
                "128 letters, digits, underscores, dots, colons or hyphens"
            )

        pool = str(ini_value("WORKER SETTINGS", "WORKER_POOL")).strip()
        if not _POOL_PATTERN.fullmatch(pool):
            raise RuntimeError("WORKER_POOL must be a lowercase identifier")

        concurrency = _positive_integer(
            "WORKER_CONCURRENCY",
            ini_value("WORKER SETTINGS", "WORKER_CONCURRENCY"),
            maximum=128,
        )
        try:
            box_id_offset = int(
                ini_value("WORKER SETTINGS", "WORKER_BOX_ID_OFFSET")
            )
        except ValueError as exc:
            raise RuntimeError("WORKER_BOX_ID_OFFSET must be an integer") from exc
        if box_id_offset < 0 or box_id_offset + concurrency > 1000:
            raise RuntimeError(
                "WORKER_BOX_ID_OFFSET and WORKER_CONCURRENCY must fit box IDs 0..999"
            )
        rabbitmq_port = _positive_integer(
            "RABBITMQ_PORT",
            ini_value("RABBITMQ SETTINGS", "RABBITMQ_PORT"),
            maximum=65535,
        )
        db_max_retries = _positive_integer(
            "DB_MAX_RETRIES",
            ini_value("DB CONNECTION SETTINGS", "DB_MAX_RETRIES"),
            maximum=10000,
        )
        try:
            db_retry_interval = float(
                ini_value("DB CONNECTION SETTINGS", "DB_MAX_TIMEOUT")
            )
        except ValueError as exc:
            raise RuntimeError("DB_MAX_TIMEOUT must be a number") from exc
        if not 0 <= db_retry_interval <= 3600:
            raise RuntimeError("DB_MAX_TIMEOUT must be between 0 and 3600 seconds")

        heartbeat_interval = _positive_float(
            "WORKER_HEARTBEAT_INTERVAL",
            ini_value("WORKER SETTINGS", "WORKER_HEARTBEAT_INTERVAL"),
            maximum=3600,
        )
        stale_threshold = _positive_float(
            "WORKER_STALE_THRESHOLD",
            ini_value("WORKER SETTINGS", "WORKER_STALE_THRESHOLD"),
            maximum=86400,
        )
        lease_duration = _positive_float(
            "WORKER_LEASE_DURATION",
            ini_value("WORKER SETTINGS", "WORKER_LEASE_DURATION"),
            maximum=86400,
        )
        lease_renewal_interval = _positive_float(
            "WORKER_LEASE_RENEWAL_INTERVAL",
            ini_value("WORKER SETTINGS", "WORKER_LEASE_RENEWAL_INTERVAL"),
            maximum=3600,
        )
        redelivery_backoff = _positive_float(
            "WORKER_REDELIVERY_BACKOFF",
            ini_value("WORKER SETTINGS", "WORKER_REDELIVERY_BACKOFF"),
            maximum=300,
        )
        if heartbeat_interval >= stale_threshold:
            raise RuntimeError(
                "WORKER_HEARTBEAT_INTERVAL must be lower than WORKER_STALE_THRESHOLD"
            )
        if lease_renewal_interval >= lease_duration:
            raise RuntimeError(
                "WORKER_LEASE_RENEWAL_INTERVAL must be lower than WORKER_LEASE_DURATION"
            )

        return cls(
            worker_id=worker_id,
            pool=pool,
            concurrency=concurrency,
            rabbitmq=RabbitMQConnectionSettings(
                host=str(ini_value("RABBITMQ SETTINGS", "RABBITMQ_HOST")).strip(),
                port=rabbitmq_port,
                login=_required_ini("RABBITMQ SETTINGS", "RABBITMQ_USER"),
                password=_required_ini("RABBITMQ SETTINGS", "RABBITMQ_PASSWORD"),
                connection_name=f"execengine-worker-{worker_id}",
            ),
            db_max_retries=db_max_retries,
            db_retry_interval=db_retry_interval,
            box_id_offset=box_id_offset,
            heartbeat_interval=heartbeat_interval,
            stale_threshold=stale_threshold,
            lease_duration=lease_duration,
            lease_renewal_interval=lease_renewal_interval,
            redelivery_backoff=redelivery_backoff,
        )
