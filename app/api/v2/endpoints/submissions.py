# app/api/v2/endpoints/submissions.py

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.dependencies import (
    get_current_user,
    get_submission_publisher,
    get_submission_waiter,
)
from app.db.session import get_db
from app.messaging.submission_publisher import SubmissionPublishError
from app.models.orm_models import CallbackDeliveryModel, LanguageModel, SubmissionModel, UserModel
from app.models.schemas import CallbackDeliveryResponse, SubmissionCreate, SubmissionResponse
from app.services.submission_response import parse_submission_fields, serialize_submission
from app.services.submission_waiter import (
    SubmissionWaitCancelled,
    SubmissionWaitNotFound,
    SubmissionWaitTimeout,
    SubmissionWaiter,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    submission: SubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    wait: bool = Query(False, description="Wait for the result instead of returning a token"),
    current_user: UserModel = Depends(get_current_user),
    submission_publisher=Depends(get_submission_publisher),
    submission_waiter: SubmissionWaiter = Depends(get_submission_waiter),
):
    if wait and not settings.ALLOW_WAIT:
        logger.warning(
            "event=submission.rejected reason=wait_disabled user_id=%s language_id=%s",
            current_user.id,
            submission.language_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Synchronous waiting is disabled by server settings.",
        )

    token = str(uuid.uuid4())
    created_at = datetime.utcnow()
    
    language = await run_in_threadpool(lambda:db.query(LanguageModel).filter(LanguageModel.id == submission.language_id).first())
    if not language:
        logger.warning(
            "event=submission.rejected reason=language_not_found user_id=%s language_id=%s",
            current_user.id,
            submission.language_id,
        )
        raise HTTPException(status_code=422, detail=f"Language with id {submission.language_id} does not exist.")
    if not language.enabled:
        logger.warning(
            "event=submission.rejected reason=language_disabled user_id=%s language_id=%s",
            current_user.id,
            submission.language_id,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Language with id {submission.language_id} is disabled.",
        )

    db_submission = SubmissionModel(
        token=token,
        language_id=submission.language_id,
        source_code=submission.source_code,
        stdin=submission.stdin,
        expected_output=submission.expected_output,
        compiler_options=submission.compiler_options,
        command_line_args=submission.command_line_args,
        time_limit=submission.time_limit,
        extra_time=submission.extra_time,
        wall_time_limit=submission.wall_time_limit,
        memory_limit=submission.memory_limit,
        stack_size=submission.stack_size,
        redirect_stderr_to_stdout=submission.redirect_stderr_to_stdout,
        enable_network=submission.enable_network,
        max_file_size=submission.max_file_size,
        additional_files=submission.additional_files,
        callback_url=submission.callback_url,
        status_id=1,  # In Queue
        created_at=created_at,
        user_id=current_user.id
    )

    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    logger.info(
        "event=submission.accepted token=%s user_id=%s language=%s pool=%s wait=%s",
        db_submission.token,
        current_user.id,
        language.slug,
        language.pool,
        wait,
    )
    
    try:
        await submission_publisher.publish_submission(
            submission_token=db_submission.token,
            language_slug=language.slug,
            pool=language.pool,
        )
    except SubmissionPublishError as exc:
        logger.error(
            "event=submission.enqueue_failed token=%s language=%s pool=%s",
            db_submission.token,
            language.slug,
            language.pool,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Submission was persisted but could not be enqueued.",
                "submission_token": db_submission.token,
            },
        ) from exc

    if wait:
        try:
            await submission_waiter.wait_for_terminal(
                db_submission.token,
                disconnected=request.is_disconnected,
            )
        except SubmissionWaitTimeout as exc:
            logger.warning(
                "event=submission.wait_timed_out token=%s user_id=%s",
                db_submission.token,
                current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "message": "Timed out waiting for submission result; the job is still running.",
                    "submission_token": db_submission.token,
                },
            ) from exc
        except SubmissionWaitCancelled as exc:
            logger.info(
                "event=submission.wait_cancelled token=%s user_id=%s",
                db_submission.token,
                current_user.id,
            )
            raise HTTPException(
                status_code=499,
                detail={
                    "message": "Client disconnected; the job is still running.",
                    "submission_token": db_submission.token,
                },
            ) from exc
        except SubmissionWaitNotFound as exc:
            logger.error(
                "event=submission.wait_not_found token=%s user_id=%s",
                db_submission.token,
                current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Submission was removed while waiting for its result.",
                    "submission_token": db_submission.token,
                },
            ) from exc
        await run_in_threadpool(db.refresh, db_submission)
        logger.info(
            "event=submission.wait_completed token=%s status_id=%s",
            db_submission.token,
            db_submission.status_id,
        )

    return SubmissionResponse.from_orm(db_submission)

@router.get("/{token}", response_model=Dict[str, Any])
async def get_submission(
    token: str,
    fields: Optional[str] = Query(None,description="Comma-separated list of fields to return."),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    submission = db.query(SubmissionModel).filter(
        SubmissionModel.token == token,
        SubmissionModel.user_id == current_user.id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    requested_fields = parse_submission_fields(fields)
    return serialize_submission(submission, requested_fields)


@router.delete("/{token}")
async def delete_submission(
    token: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if not getattr(current_user, "privileged_user", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only privileged users can delete submissions."
        )
    
    submission = db.query(SubmissionModel).filter(
        SubmissionModel.token == token
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    
    db.delete(submission)
    db.commit()
    return {"message" : f"Submission {token} removed successfully!"}

@router.get("/{token}/callbacks", response_model=list[CallbackDeliveryResponse])
async def get_submission_callbacks(
    token: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    submission = db.query(SubmissionModel).filter(
        SubmissionModel.token == token
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    if not getattr(current_user, "privileged_user", False) and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to callbacks for this submission."
        )

    deliveries = db.query(CallbackDeliveryModel).filter(
        CallbackDeliveryModel.submission_id == submission.id
    ).order_by(
        CallbackDeliveryModel.created_at.desc()
    ).all()

    return deliveries
