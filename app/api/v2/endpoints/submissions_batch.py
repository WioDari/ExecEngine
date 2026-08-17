import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

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
from app.models.orm_models import BatchModel, LanguageModel, SubmissionModel, UserModel
from app.models.schemas import BatchSubmissionCreate, BatchSubmissionResponse, SubmissionResponse
from app.services.submission_response import parse_submission_fields, serialize_submission
from app.services.submission_waiter import (
    SubmissionWaitCancelled,
    SubmissionWaitNotFound,
    SubmissionWaitTimeout,
    SubmissionWaiter,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_batch_languages(db: Session, language_ids: set[int]):
    languages = db.query(LanguageModel).filter(LanguageModel.id.in_(language_ids)).all()
    by_id = {language.id: language for language in languages}
    missing = sorted(language_ids - set(by_id))
    if missing:
        logger.warning(
            "event=batch.rejected reason=languages_not_found language_ids=%s",
            missing,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "One or more languages do not exist.",
                "language_ids": missing,
            },
        )
    disabled = sorted(language_id for language_id, language in by_id.items() if not language.enabled)
    if disabled:
        logger.warning(
            "event=batch.rejected reason=languages_disabled language_ids=%s",
            disabled,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "One or more languages are disabled.",
                "language_ids": disabled,
            },
        )
    return by_id


async def _publish_batch(submission_publisher, jobs):
    return await asyncio.gather(
        *(
            submission_publisher.publish_submission(
                submission_token=submission.token,
                language_slug=language.slug,
                pool=language.pool,
            )
            for submission, language in jobs
        ),
        return_exceptions=True,
    )


@router.post("/", response_model=BatchSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_submission(
    batch_submission: BatchSubmissionCreate,
    request: Request,
    wait: bool = Query(False, description="Wait for batch results"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    submission_publisher=Depends(get_submission_publisher),
    submission_waiter: SubmissionWaiter = Depends(get_submission_waiter),
):
    if wait and not settings.ALLOW_WAIT:
        logger.warning(
            "event=batch.rejected reason=wait_disabled user_id=%s size=%s",
            current_user.id,
            len(batch_submission.submissions),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Synchronous waiting is disabled by server settings.",
        )
    if len(batch_submission.submissions) > settings.MAX_BATCH_SIZE:
        logger.warning(
            "event=batch.rejected reason=size_limit user_id=%s size=%s max_size=%s",
            current_user.id,
            len(batch_submission.submissions),
            settings.MAX_BATCH_SIZE,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Size of batch submission must not exceed {settings.MAX_BATCH_SIZE}.",
        )

    language_ids = {submission.language_id for submission in batch_submission.submissions}
    languages = _validate_batch_languages(db, language_ids)
    batch_token = str(uuid.uuid4())
    created_at = datetime.utcnow()
    db_batch = BatchModel(batch_token=batch_token, created_at=created_at)

    submissions: list[SubmissionModel] = []
    try:
        db.add(db_batch)
        db.flush()
        for item in batch_submission.submissions:
            db_submission = SubmissionModel(
                token=str(uuid.uuid4()),
                language_id=item.language_id,
                source_code=item.source_code,
                stdin=item.stdin,
                expected_output=item.expected_output,
                compiler_options=item.compiler_options,
                command_line_args=item.command_line_args,
                time_limit=item.time_limit,
                extra_time=item.extra_time,
                wall_time_limit=item.wall_time_limit,
                memory_limit=item.memory_limit,
                stack_size=item.stack_size,
                redirect_stderr_to_stdout=item.redirect_stderr_to_stdout,
                enable_network=item.enable_network,
                max_file_size=item.max_file_size,
                additional_files=item.additional_files,
                callback_url=item.callback_url,
                status_id=1,
                created_at=created_at,
                batch_id=db_batch.id,
                user_id=current_user.id,
            )
            submissions.append(db_submission)
        db.add_all(submissions)
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info(
        "event=batch.accepted batch_token=%s user_id=%s size=%s language_ids=%s wait=%s",
        batch_token,
        current_user.id,
        len(submissions),
        sorted(language_ids),
        wait,
    )

    tokens = [submission.token for submission in submissions]
    jobs = [(submission, languages[submission.language_id]) for submission in submissions]
    publish_results = await _publish_batch(submission_publisher, jobs)
    failed_tokens = [
        token
        for token, result in zip(tokens, publish_results)
        if isinstance(result, Exception)
    ]
    if failed_tokens:
        for token, result in zip(tokens, publish_results):
            if isinstance(result, Exception):
                logger.error(
                    "event=batch.enqueue_failed batch_token=%s token=%s error_type=%s",
                    batch_token,
                    token,
                    type(result).__name__,
                )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "The batch was persisted, but one or more submissions could not be enqueued.",
                "batch_token": batch_token,
                "submission_tokens": tokens,
                "failed_submission_tokens": failed_tokens,
            },
        )
    logger.info(
        "event=batch.enqueued batch_token=%s size=%s",
        batch_token,
        len(tokens),
    )

    results = None
    if wait:
        try:
            await submission_waiter.wait_many(
                tokens,
                disconnected=request.is_disconnected,
            )
        except SubmissionWaitTimeout as exc:
            logger.warning(
                "event=batch.wait_timed_out batch_token=%s pending_count=%s",
                batch_token,
                len(exc.pending_tokens),
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "message": "Timed out waiting for batch results; pending jobs are still running.",
                    "batch_token": batch_token,
                    "submission_tokens": tokens,
                    "pending_submission_tokens": list(exc.pending_tokens),
                },
            ) from exc
        except SubmissionWaitCancelled as exc:
            logger.info(
                "event=batch.wait_cancelled batch_token=%s size=%s",
                batch_token,
                len(tokens),
            )
            raise HTTPException(
                status_code=499,
                detail={
                    "message": "Client disconnected; batch jobs are still running.",
                    "batch_token": batch_token,
                    "submission_tokens": tokens,
                },
            ) from exc
        except SubmissionWaitNotFound as exc:
            logger.error(
                "event=batch.wait_not_found batch_token=%s missing_count=%s",
                batch_token,
                len(exc.missing_tokens),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "One or more submissions were removed while waiting.",
                    "batch_token": batch_token,
                    "missing_submission_tokens": list(exc.missing_tokens),
                },
            ) from exc

        await run_in_threadpool(db.expire_all)
        refreshed = db.query(SubmissionModel).filter(SubmissionModel.token.in_(tokens)).all()
        by_token = {submission.token: submission for submission in refreshed}
        results = [SubmissionResponse.from_orm(by_token[token]) for token in tokens]
        logger.info(
            "event=batch.wait_completed batch_token=%s status_ids=%s",
            batch_token,
            [result.status_id for result in results],
        )

    return BatchSubmissionResponse(
        batch_token=batch_token,
        submission_tokens=tokens,
        results=results,
    )


@router.get("/{batch_token}", response_model=List[Dict[str, Any]])
async def get_batch_submissions(
    batch_token: str,
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to return."),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    batch = db.query(BatchModel).filter(BatchModel.batch_token == batch_token).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch submission not found.")

    submissions = db.query(SubmissionModel).filter(
        SubmissionModel.batch_id == batch.id,
        SubmissionModel.user_id == current_user.id,
    ).all()
    requested_fields = parse_submission_fields(fields)
    return [serialize_submission(submission, requested_fields) for submission in submissions]


@router.delete("/{batch_token}")
async def delete_batch_submission(
    batch_token: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    if not getattr(current_user, "privileged_user", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only privileged users can delete submissions.",
        )

    batch = db.query(BatchModel).filter(BatchModel.batch_token == batch_token).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch submission not found.")

    submissions_count = db.query(SubmissionModel).filter(
        SubmissionModel.batch_id == batch.id
    ).delete()
    db.delete(batch)
    db.commit()
    return {
        "message": f"Batch submission {batch_token} removed successfully!",
        "submissions_count": submissions_count,
    }
