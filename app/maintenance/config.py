from __future__ import annotations

from dataclasses import dataclass

from app.core.config_file import ini_value

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
class MaintenanceSettings:
    submission_retention_days: int
    delete_batch_size: int
    max_batches_per_run: int
    submissions_interval: float
    api_tokens_interval: float
    db_max_retries: int
    db_retry_interval: float

    @classmethod
    def from_ini(cls) -> "MaintenanceSettings":
        return cls(
            submission_retention_days=_positive_int(
                "SUBMISSION_RETENTION_DAYS",
                ini_value("MAINTENANCE SETTINGS", "SUBMISSION_RETENTION_DAYS"),
                36500,
            ),
            delete_batch_size=_positive_int(
                "MAINTENANCE_DELETE_BATCH_SIZE",
                ini_value("MAINTENANCE SETTINGS", "MAINTENANCE_DELETE_BATCH_SIZE"),
                100000,
            ),
            max_batches_per_run=_positive_int(
                "MAINTENANCE_MAX_BATCHES_PER_RUN",
                ini_value("MAINTENANCE SETTINGS", "MAINTENANCE_MAX_BATCHES_PER_RUN"),
                10000,
            ),
            submissions_interval=_positive_float(
                "MAINTENANCE_SUBMISSIONS_INTERVAL",
                ini_value("MAINTENANCE SETTINGS", "MAINTENANCE_SUBMISSIONS_INTERVAL"),
                31536000,
            ),
            api_tokens_interval=_positive_float(
                "MAINTENANCE_API_TOKENS_INTERVAL",
                ini_value("MAINTENANCE SETTINGS", "MAINTENANCE_API_TOKENS_INTERVAL"),
                31536000,
            ),
            db_max_retries=_positive_int(
                "DB_MAX_RETRIES",
                ini_value("DB CONNECTION SETTINGS", "DB_MAX_RETRIES"),
                10000,
            ),
            db_retry_interval=_positive_float(
                "DB_MAX_TIMEOUT",
                ini_value("DB CONNECTION SETTINGS", "DB_MAX_TIMEOUT"),
                3600,
            ),
        )
