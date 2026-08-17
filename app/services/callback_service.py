from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.orm_models import CallbackDeliveryModel, SubmissionModel

def create_callback_delivery(
    db: Session,
    submission: SubmissionModel,
    event_type: str = "submission.completed",
    *,
    commit: bool = True,
):
    if not submission.callback_url:
        return None

    existing = (
        db.query(CallbackDeliveryModel)
        .filter(
            CallbackDeliveryModel.submission_id == submission.id,
            CallbackDeliveryModel.event_type == event_type,
        )
        .first()
    )
    if existing is not None:
        return existing

    delivery = CallbackDeliveryModel(
        delivery_id=str(uuid.uuid4()),
        submission_id=submission.id,
        callback_url=submission.callback_url,
        event_type=event_type,
        status="pending",
        attempt_count=0,
        next_attempt_at=datetime.utcnow(),
    )
    db.add(delivery)
    if commit:
        db.commit()
        db.refresh(delivery)
    else:
        db.flush()
    return delivery
