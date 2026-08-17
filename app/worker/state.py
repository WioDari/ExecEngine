from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Mapping

from sqlalchemy import and_, case, or_
from sqlalchemy.orm import Session

from app.models.orm_models import SubmissionModel, WorkerModel

IN_QUEUE_STATUS_ID = 1
PROCESSING_STATUS_ID = 2
TERMINAL_STATUS_IDS = frozenset(range(3, 10))

class ClaimDecision(str, Enum):
    CLAIMED = "claimed"
    ACTIVE_LEASE = "active_lease"
    ALREADY_FINISHED = "already_finished"
    NOT_FOUND = "not_found"
    INVALID_STATE = "invalid_state"

@dataclass(frozen=True)
class SubmissionLease:
    worker_id: str
    attempt_count: int
    expires_at: datetime

@dataclass(frozen=True)
class ClaimResult:
    decision: ClaimDecision
    submission: SubmissionModel | None = None
    lease: SubmissionLease | None = None

def _now(value: datetime | None):
    return value or datetime.utcnow()

def _decrement_active_jobs():
    return case(
        (WorkerModel.active_jobs > 0, WorkerModel.active_jobs - 1),
        else_=0,
    )

def claim_submission(
    db: Session,
    submission_token: str,
    worker_id: str,
    lease_duration: float,
    *,
    now: datetime | None = None,
):
    if lease_duration <= 0:
        raise ValueError("lease_duration must be positive")
    claimed_at = _now(now)
    expires_at = claimed_at + timedelta(seconds=lease_duration)
    claimable = or_(
        SubmissionModel.status_id == IN_QUEUE_STATUS_ID,
        and_(
            SubmissionModel.status_id == PROCESSING_STATUS_ID,
            or_(
                SubmissionModel.lease_expires_at.is_(None),
                SubmissionModel.lease_expires_at <= claimed_at,
            ),
        ),
    )
    updated = (
        db.query(SubmissionModel)
        .filter(SubmissionModel.token == submission_token, claimable)
        .update(
            {
                SubmissionModel.status_id: PROCESSING_STATUS_ID,
                SubmissionModel.worker_id: worker_id,
                SubmissionModel.attempt_count: SubmissionModel.attempt_count + 1,
                SubmissionModel.processing_started_at: claimed_at,
                SubmissionModel.lease_expires_at: expires_at,
            },
            synchronize_session=False,
        )
    )
    if updated == 1:
        db.query(WorkerModel).filter(WorkerModel.id == worker_id).update(
            {
                WorkerModel.active_jobs: WorkerModel.active_jobs + 1,
                WorkerModel.last_seen_at: claimed_at,
            },
            synchronize_session=False,
        )
    db.commit()
    submission = (
        db.query(SubmissionModel)
        .filter(SubmissionModel.token == submission_token)
        .populate_existing()
        .first()
    )
    if updated == 1 and submission is not None:
        return ClaimResult(
            ClaimDecision.CLAIMED,
            submission,
            SubmissionLease(worker_id, submission.attempt_count, expires_at),
        )
    if submission is None:
        return ClaimResult(ClaimDecision.NOT_FOUND)
    if submission.status_id == PROCESSING_STATUS_ID:
        return ClaimResult(ClaimDecision.ACTIVE_LEASE, submission)
    if submission.status_id in TERMINAL_STATUS_IDS:
        return ClaimResult(ClaimDecision.ALREADY_FINISHED, submission)
    return ClaimResult(ClaimDecision.INVALID_STATE, submission)

def renew_submission_leases(
    db: Session,
    worker_id: str,
    attempts: Mapping[str, int],
    lease_duration: float,
    *,
    now: datetime | None = None,
):
    """Renew only leases still owned by the exact worker attempt."""
    if lease_duration <= 0:
        raise ValueError("lease_duration must be positive")
    renewed_at = _now(now)
    expires_at = renewed_at + timedelta(seconds=lease_duration)
    renewed: set[str] = set()
    for token, attempt_count in attempts.items():
        updated = (
            db.query(SubmissionModel)
            .filter(
                SubmissionModel.token == token,
                SubmissionModel.status_id == PROCESSING_STATUS_ID,
                SubmissionModel.worker_id == worker_id,
                SubmissionModel.attempt_count == attempt_count,
            )
            .update(
                {SubmissionModel.lease_expires_at: expires_at},
                synchronize_session=False,
            )
        )
        if updated == 1:
            renewed.add(token)
    db.commit()
    return renewed

def complete_submission(
    db: Session,
    submission_token: str,
    lease: SubmissionLease,
    result_values: Mapping[str, object],
    callback_factory: Callable[..., object],
    *,
    now: datetime | None = None,
):
    """Commit result, callback outbox and counters iff this attempt still owns the lease."""
    status_id = result_values.get("status_id")
    if status_id not in TERMINAL_STATUS_IDS:
        raise ValueError(f"Execution did not produce a terminal status: {status_id}")
    completed_at = _now(now)
    values = {
        getattr(SubmissionModel, field_name): value
        for field_name, value in result_values.items()
    }
    values[SubmissionModel.lease_expires_at] = None
    updated = (
        db.query(SubmissionModel)
        .filter(
            SubmissionModel.token == submission_token,
            SubmissionModel.status_id == PROCESSING_STATUS_ID,
            SubmissionModel.worker_id == lease.worker_id,
            SubmissionModel.attempt_count == lease.attempt_count,
        )
        .update(values, synchronize_session=False)
    )
    if updated != 1:
        db.rollback()
        return False

    db.query(WorkerModel).filter(WorkerModel.id == lease.worker_id).update(
        {
            WorkerModel.active_jobs: _decrement_active_jobs(),
            WorkerModel.completed_jobs: WorkerModel.completed_jobs + 1,
            WorkerModel.last_seen_at: completed_at,
        },
        synchronize_session=False,
    )
    db.expire_all()
    submission = (
        db.query(SubmissionModel)
        .filter(SubmissionModel.token == submission_token)
        .populate_existing()
        .one()
    )
    callback_factory(db, submission, commit=False)
    db.commit()
    return True

def release_submission_claim(
    db: Session,
    submission_token: str,
    lease: SubmissionLease,
    *,
    now: datetime | None = None,
):
    released_at = _now(now)
    updated = (
        db.query(SubmissionModel)
        .filter(
            SubmissionModel.token == submission_token,
            SubmissionModel.status_id == PROCESSING_STATUS_ID,
            SubmissionModel.worker_id == lease.worker_id,
            SubmissionModel.attempt_count == lease.attempt_count,
        )
        .update(
            {
                SubmissionModel.status_id: IN_QUEUE_STATUS_ID,
                SubmissionModel.worker_id: None,
                SubmissionModel.processing_started_at: None,
                SubmissionModel.lease_expires_at: None,
            },
            synchronize_session=False,
        )
    )
    if updated == 1:
        db.query(WorkerModel).filter(WorkerModel.id == lease.worker_id).update(
            {
                WorkerModel.active_jobs: _decrement_active_jobs(),
                WorkerModel.failed_jobs: WorkerModel.failed_jobs + 1,
                WorkerModel.last_seen_at: released_at,
            },
            synchronize_session=False,
        )
    db.commit()
    db.expire_all()
    return updated == 1
