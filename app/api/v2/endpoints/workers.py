import logging
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_submission_publisher
from app.core.config import settings
from app.db.session import get_db
from app.models.orm_models import SubmissionModel, UserModel, WorkerModel


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_queue_stats(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    submission_publisher=Depends(get_submission_publisher),
):
    if not getattr(current_user, "privileged_user", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    try:
        snapshot = await submission_publisher.get_queue_snapshot()
        snapshot["available"] = True
    except Exception as exc:
        logger.exception("Failed to retrieve submission queue state: %s", exc)
        snapshot = {"available": False, "error": "Failed to retrieve submission queue state."}

    now = datetime.utcnow()
    online_after = now - timedelta(seconds=settings.WORKER_STALE_THRESHOLD)
    workers = db.query(WorkerModel).order_by(WorkerModel.id).all()
    worker_items = []
    for worker in workers:
        try:
            capabilities = (
                json.loads(worker.capabilities_json)
                if worker.capabilities_json
                else None
            )
        except (TypeError, json.JSONDecodeError):
            capabilities = None
        online = worker.last_seen_at >= online_after
        worker_items.append(
            {
                "id": worker.id,
                "hostname": worker.hostname,
                "pool": worker.pool,
                "version": worker.version,
                "concurrency": worker.concurrency,
                "active_jobs": worker.active_jobs,
                "started_at": worker.started_at,
                "last_seen_at": worker.last_seen_at,
                "completed_jobs": worker.completed_jobs,
                "failed_jobs": worker.failed_jobs,
                "isolate_version": worker.isolate_version,
                "capabilities": capabilities,
                "online": online,
            }
        )

    response = {
        "broker": snapshot,
        "db": {
        "submissions_in_queue": db.query(SubmissionModel).filter(
            SubmissionModel.status_id == 1
        ).count(),
        "submissions_processing": db.query(SubmissionModel).filter(
            SubmissionModel.status_id == 2
        ).count(),
        },
        "workers": worker_items,
        "summary": {
            "registered": len(worker_items),
            "online": sum(item["online"] for item in worker_items),
            "offline": sum(not item["online"] for item in worker_items),
            "active_jobs": sum(
                item["active_jobs"] for item in worker_items if item["online"]
            ),
            "stale_threshold_seconds": settings.WORKER_STALE_THRESHOLD,
        },
        "scope": "worker_registry_broker_and_submission_state",
        "worker_registry_available": True,
    }
    return response
