from __future__ import annotations

import re
import socket
from dataclasses import dataclass

from app.core.config_file import ini_value


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _positive_int(name: str, value, maximum: int):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not 1 <= parsed <= maximum:
        raise RuntimeError(f"{name} must be between 1 and {maximum}")
    return parsed


def _positive_float(name: str, value, maximum: float):
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if not 0 < parsed <= maximum:
        raise RuntimeError(f"{name} must be greater than 0 and at most {maximum}")
    return parsed


@dataclass(frozen=True)
class CallbackSettings:
    worker_id: str
    poll_interval: float
    batch_size: int
    concurrency: int
    http_timeout: float
    max_attempts: int
    lease_duration: float
    retry_delays: tuple[float, ...]
    db_max_retries: int
    db_retry_interval: float

    @classmethod
    def from_ini(cls) -> "CallbackSettings":
        worker_id = str(ini_value("CALLBACK SETTINGS", "CALLBACK_WORKER_ID")).strip()
        worker_id = worker_id or socket.gethostname()
        if not _IDENTIFIER_PATTERN.fullmatch(worker_id):
            raise RuntimeError("CALLBACK_WORKER_ID is not a valid worker identifier")

        poll_interval = _positive_float(
            "CALLBACK_POLL_INTERVAL",
            ini_value("CALLBACK SETTINGS", "CALLBACK_POLL_INTERVAL"),
            3600,
        )
        batch_size = _positive_int(
            "CALLBACK_BATCH_SIZE",
            ini_value("CALLBACK SETTINGS", "CALLBACK_BATCH_SIZE"),
            1000,
        )
        concurrency = _positive_int(
            "CALLBACK_CONCURRENCY",
            ini_value("CALLBACK SETTINGS", "CALLBACK_CONCURRENCY"),
            256,
        )
        http_timeout = _positive_float(
            "CALLBACK_HTTP_TIMEOUT",
            ini_value("CALLBACK SETTINGS", "CALLBACK_HTTP_TIMEOUT"),
            300,
        )
        max_attempts = _positive_int(
            "CALLBACK_MAX_ATTEMPTS",
            ini_value("CALLBACK SETTINGS", "CALLBACK_MAX_ATTEMPTS"),
            100,
        )
        lease_duration = _positive_float(
            "CALLBACK_LEASE_DURATION",
            ini_value("CALLBACK SETTINGS", "CALLBACK_LEASE_DURATION"),
            3600,
        )
        if lease_duration <= http_timeout:
            raise RuntimeError("CALLBACK_LEASE_DURATION must exceed CALLBACK_HTTP_TIMEOUT")

        retry_value = str(ini_value("CALLBACK SETTINGS", "CALLBACK_RETRY_DELAYS"))
        try:
            retry_delays = tuple(float(item.strip()) for item in retry_value.split(","))
        except ValueError as exc:
            raise RuntimeError("CALLBACK_RETRY_DELAYS must be comma-separated numbers") from exc
        if not retry_delays or any(delay <= 0 or delay > 86400 for delay in retry_delays):
            raise RuntimeError("CALLBACK_RETRY_DELAYS values must be greater than 0 and at most 86400")

        db_max_retries = _positive_int(
            "DB_MAX_RETRIES",
            ini_value("DB CONNECTION SETTINGS", "DB_MAX_RETRIES"),
            10000,
        )
        db_retry_interval = _positive_float(
            "DB_MAX_TIMEOUT",
            ini_value("DB CONNECTION SETTINGS", "DB_MAX_TIMEOUT"),
            3600,
        )
        return cls(
            worker_id=worker_id,
            poll_interval=poll_interval,
            batch_size=batch_size,
            concurrency=concurrency,
            http_timeout=http_timeout,
            max_attempts=max_attempts,
            lease_duration=lease_duration,
            retry_delays=retry_delays,
            db_max_retries=db_max_retries,
            db_retry_interval=db_retry_interval,
        )
