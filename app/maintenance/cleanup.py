from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models.orm_models import ApiTokenModel, CallbackDeliveryModel, SubmissionModel

TERMINAL_STATUS_IDS = frozenset(range(3, 10))
_SUBMISSIONS_LOCK_ID = 0x45584543
_API_TOKENS_LOCK_ID = 0x544F4B4E

@dataclass(frozen=True)
class CleanupResult:
    lock_acquired: bool
    deleted: int

def _try_transaction_lock(db: Session, lock_id: int):
    if db.get_bind().dialect.name != "postgresql":
        return True
    return bool(
        db.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": lock_id},
        ).scalar()
    )

def cleanup_submissions_batch(
    db: Session,
    retention_days: int,
    batch_size: int,
    *,
    now: datetime | None = None,
):
    if not _try_transaction_lock(db, _SUBMISSIONS_LOCK_ID):
        db.rollback()
        return CleanupResult(False, 0)
    cutoff = (now or datetime.utcnow()) - timedelta(days=retention_days)
    ids = list(
        db.scalars(
            select(SubmissionModel.id)
            .where(
                SubmissionModel.status_id.in_(TERMINAL_STATUS_IDS),
                SubmissionModel.finished_at.is_not(None),
                SubmissionModel.finished_at < cutoff,
                ~SubmissionModel.callback_deliveries.any(
                    CallbackDeliveryModel.status.in_(("pending", "retry", "processing"))
                ),
            )
            .order_by(SubmissionModel.id)
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        )
    )
    if ids:
        db.execute(
            delete(CallbackDeliveryModel).where(
                CallbackDeliveryModel.submission_id.in_(ids)
            )
        )
        db.execute(delete(SubmissionModel).where(SubmissionModel.id.in_(ids)))
    db.commit()
    return CleanupResult(True, len(ids))

def cleanup_api_tokens_batch(
    db: Session,
    batch_size: int,
    *,
    now: datetime | None = None,
):
    if not _try_transaction_lock(db, _API_TOKENS_LOCK_ID):
        db.rollback()
        return CleanupResult(False, 0)
    cutoff = now or datetime.utcnow()
    ids = list(
        db.scalars(
            select(ApiTokenModel.id)
            .where(ApiTokenModel.expires_at < cutoff)
            .order_by(ApiTokenModel.id)
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        )
    )
    if ids:
        db.execute(delete(ApiTokenModel).where(ApiTokenModel.id.in_(ids)))
    db.commit()
    return CleanupResult(True, len(ids))
