from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.orm_models import CallbackDeliveryModel, SubmissionModel


@dataclass(frozen=True)
class CallbackClaim:
    id: int
    delivery_id: str
    callback_url: str
    event_type: str
    attempt_count: int
    lock_token: str


def claim_due_callbacks(
    db: Session,
    worker_id: str,
    batch_size: int,
    lease_duration: float,
    *,
    now: datetime | None = None,
):
    claimed_at = now or datetime.utcnow()
    locked_until = claimed_at + timedelta(seconds=lease_duration)
    due = or_(
        and_(
            CallbackDeliveryModel.status.in_(("pending", "retry")),
            CallbackDeliveryModel.next_attempt_at <= claimed_at,
        ),
        and_(
            CallbackDeliveryModel.status == "processing",
            or_(
                CallbackDeliveryModel.locked_until.is_(None),
                CallbackDeliveryModel.locked_until <= claimed_at,
            ),
        ),
    )
    rows = (
        db.query(CallbackDeliveryModel)
        .filter(due)
        .order_by(CallbackDeliveryModel.created_at, CallbackDeliveryModel.id)
        .with_for_update(skip_locked=True)
        .limit(batch_size)
        .all()
    )
    claims: list[CallbackClaim] = []
    for row in rows:
        lock_token = str(uuid.uuid4())
        row.status = "processing"
        row.attempt_count += 1
        row.locked_by = worker_id
        row.lock_token = lock_token
        row.locked_until = locked_until
        claims.append(
            CallbackClaim(
                id=row.id,
                delivery_id=row.delivery_id,
                callback_url=row.callback_url,
                event_type=row.event_type,
                attempt_count=row.attempt_count,
                lock_token=lock_token,
            )
        )
    db.commit()
    return tuple(claims)


def load_callback_request(db: Session, claim: CallbackClaim):
    row = (
        db.query(SubmissionModel, CallbackDeliveryModel)
        .join(CallbackDeliveryModel, CallbackDeliveryModel.submission_id == SubmissionModel.id)
        .filter(
            CallbackDeliveryModel.id == claim.id,
            CallbackDeliveryModel.lock_token == claim.lock_token,
        )
        .first()
    )
    if row is None:
        return None
    submission, delivery = row
    payload = {
        "event": claim.event_type,
        "delivery_id": claim.delivery_id,
        "created_at": delivery.created_at.isoformat() + "Z",
        "submission": {
            "token": submission.token,
            "status_id": submission.status_id,
            "stdout": submission.stdout,
            "stderr": submission.stderr,
            "compile_output": submission.compile_output,
            "time": submission.time,
            "wall_time": submission.wall_time,
            "memory": submission.memory,
            "exit_code": submission.exit_code,
            "exit_signal": submission.exit_signal,
            "finished_at": (
                submission.finished_at.isoformat() + "Z"
                if submission.finished_at
                else None
            ),
        },
    }
    return (
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        {
            "Content-Type": "application/json",
            "X-ExecEngine-Event": claim.event_type,
            "X-ExecEngine-Delivery-Id": claim.delivery_id,
        },
    )


def mark_callback_delivered(
    db: Session,
    claim: CallbackClaim,
    http_status: int,
    *,
    now: datetime | None = None,
):
    delivered_at = now or datetime.utcnow()
    updated = _owned_claim(db, claim).update(
        {
            CallbackDeliveryModel.status: "delivered",
            CallbackDeliveryModel.delivered_at: delivered_at,
            CallbackDeliveryModel.last_http_status: http_status,
            CallbackDeliveryModel.last_error: None,
            CallbackDeliveryModel.locked_by: None,
            CallbackDeliveryModel.lock_token: None,
            CallbackDeliveryModel.locked_until: None,
        },
        synchronize_session=False,
    )
    db.commit()
    db.expire_all()
    return updated == 1


def mark_callback_failed(
    db: Session,
    claim: CallbackClaim,
    error: str,
    max_attempts: int,
    retry_delays: Sequence[float],
    *,
    http_status: int | None = None,
    now: datetime | None = None,
):
    failed_at = now or datetime.utcnow()
    terminal = claim.attempt_count >= max_attempts
    values = {
        CallbackDeliveryModel.status: "failed" if terminal else "retry",
        CallbackDeliveryModel.next_attempt_at: (
            failed_at
            if terminal
            else failed_at
            + timedelta(
                seconds=retry_delays[min(claim.attempt_count - 1, len(retry_delays) - 1)]
            )
        ),
        CallbackDeliveryModel.last_http_status: http_status,
        CallbackDeliveryModel.last_error: error[:4000],
        CallbackDeliveryModel.locked_by: None,
        CallbackDeliveryModel.lock_token: None,
        CallbackDeliveryModel.locked_until: None,
    }
    updated = _owned_claim(db, claim).update(values, synchronize_session=False)
    db.commit()
    db.expire_all()
    return updated == 1


def _owned_claim(db: Session, claim: CallbackClaim):
    return db.query(CallbackDeliveryModel).filter(
        CallbackDeliveryModel.id == claim.id,
        CallbackDeliveryModel.status == "processing",
        CallbackDeliveryModel.lock_token == claim.lock_token,
    )
