from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

SUBMISSION_JOB_VERSION = 1
MAX_SUBMISSION_JOB_BYTES = 16 * 1024
_JOB_FIELDS = {
    "version",
    "job_id",
    "submission_token",
    "language_slug",
    "pool",
    "enqueued_at",
}
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")

class SubmissionJobValidationError(ValueError):
    pass

def _canonical_uuid(value: Any, field_name: str):
    if not isinstance(value, str):
        raise SubmissionJobValidationError(f"{field_name} must be a UUID string")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise SubmissionJobValidationError(f"{field_name} must be a valid UUID") from exc
    canonical = str(parsed)
    if value.lower() != canonical:
        raise SubmissionJobValidationError(f"{field_name} must use canonical UUID format")
    return canonical

def _identifier(value: Any, field_name: str):
    if not isinstance(value, str) or not _IDENTIFIER_PATTERN.fullmatch(value):
        raise SubmissionJobValidationError(
            f"{field_name} must contain lowercase letters, digits, hyphens or dots"
        )
    return value

def _aware_utc(value: Any):
    if isinstance(value, str):
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            value = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise SubmissionJobValidationError("enqueued_at must be an ISO-8601 timestamp") from exc
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SubmissionJobValidationError("enqueued_at must include a timezone")
    return value.astimezone(timezone.utc)

@dataclass(frozen=True)
class SubmissionJob:
    version: int
    job_id: str
    submission_token: str
    language_slug: str
    pool: str
    enqueued_at: datetime

    def __post_init__(self):
        if type(self.version) is not int or self.version != SUBMISSION_JOB_VERSION:
            raise SubmissionJobValidationError(
                f"Unsupported submission job version: {self.version!r}"
            )
        object.__setattr__(self, "job_id", _canonical_uuid(self.job_id, "job_id"))
        object.__setattr__(
            self,
            "submission_token",
            _canonical_uuid(self.submission_token, "submission_token"),
        )
        object.__setattr__(
            self, "language_slug", _identifier(self.language_slug, "language_slug")
        )
        object.__setattr__(self, "pool", _identifier(self.pool, "pool"))
        object.__setattr__(self, "enqueued_at", _aware_utc(self.enqueued_at))

    @classmethod
    def create(
        cls,
        submission_token: str,
        language_slug: str,
        pool: str,
        *,
        job_id: str | None = None,
        enqueued_at: datetime | None = None,
    ) -> "SubmissionJob":
        return cls(
            version=SUBMISSION_JOB_VERSION,
            job_id=job_id or str(uuid4()),
            submission_token=submission_token,
            language_slug=language_slug,
            pool=pool,
            enqueued_at=enqueued_at or datetime.now(timezone.utc),
        )

    def to_dict(self):
        return {
            "version": self.version,
            "job_id": self.job_id,
            "submission_token": self.submission_token,
            "language_slug": self.language_slug,
            "pool": self.pool,
            "enqueued_at": self.enqueued_at.isoformat().replace("+00:00", "Z"),
        }

    def encode(self):
        body = json.dumps(
            self.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        if len(body) > MAX_SUBMISSION_JOB_BYTES:
            raise SubmissionJobValidationError("Submission job exceeds the size limit")
        return body

    @classmethod
    def decode(cls, body: bytes) -> "SubmissionJob":
        if not isinstance(body, bytes):
            raise SubmissionJobValidationError("Submission job body must be bytes")
        if len(body) > MAX_SUBMISSION_JOB_BYTES:
            raise SubmissionJobValidationError("Submission job exceeds the size limit")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SubmissionJobValidationError("Submission job must be valid UTF-8 JSON") from exc
        if not isinstance(payload, dict):
            raise SubmissionJobValidationError("Submission job must be a JSON object")
        fields = set(payload)
        if fields != _JOB_FIELDS:
            missing = sorted(_JOB_FIELDS - fields)
            extra = sorted(fields - _JOB_FIELDS)
            raise SubmissionJobValidationError(
                f"Submission job fields do not match the contract; missing={missing}, extra={extra}"
            )
        return cls(**payload)
