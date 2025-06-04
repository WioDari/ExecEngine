# app/api/v2/endpoints/submissions_batch.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.models.schemas import BatchSubmissionCreate, BatchSubmissionResponse, SubmissionResponse
from app.models.orm_models import SubmissionModel, BatchModel
from app.db.session import get_db
import uuid
from datetime import datetime
from typing import List
from app.core.dependencies import get_current_user
from app.models.orm_models import UserModel
from app.core.config import settings
from app.services.submission_service import process_submission

router = APIRouter()

@router.post("/", response_model=BatchSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_submission(
    batch_submission: BatchSubmissionCreate,
    wait: bool = Query(False, description="Wait for batch results"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if len(batch_submission.submissions) > settings.MAX_BATCH_SIZE:
        raise HTTPException(status_code=422, detail=f"Size of batch submission must be less than {settings.MAX_BATCH_SIZE}.")
    batch_token = str(uuid.uuid4())
    created_at = datetime.utcnow()

    db_batch = BatchModel(
        batch_token=batch_token,
        created_at=created_at
    )

    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)

    submission_tokens = []
    results = []

    for subm in batch_submission.submissions:
        token = str(uuid.uuid4())
        submission_tokens.append(token)

        db_submission = SubmissionModel(
            token=token,
            language_id=subm.language_id,
            source_code=subm.source_code,
            stdin=subm.stdin,
            expected_output=subm.expected_output,
            compiler_options=subm.compiler_options,
            command_line_args=subm.command_line_args,
            time_limit=subm.time_limit,
            extra_time=subm.extra_time,
            wall_time_limit=subm.wall_time_limit,
            memory_limit=subm.memory_limit,
            stack_size=subm.stack_size,
            redirect_stderr_to_stdout=subm.redirect_stderr_to_stdout,
            enable_network=subm.enable_network,
            max_file_size=subm.max_file_size,
            status_id=1,  # In Queue
            created_at=created_at,
            batch_id=db_batch.id,
            user_id=current_user.id
        )

        db.add(db_submission)
        db.commit()
        db.refresh(db_submission)
        
        if wait:
            db_submission.status_id = 2
            db.commit()
            await process_submission(db_submission, db)
            db.refresh(db_submission)
            results.append(SubmissionResponse(
                token=db_submission.token,
                status_id=db_submission.status_id,
                created_at=db_submission.created_at,
                finished_at=db_submission.finished_at,
                time=db_submission.time,
                memory=db_submission.memory,
                exit_code=db_submission.exit_code,
                exit_signal=db_submission.exit_signal,
                stdout=db_submission.stdout,
                stderr=db_submission.stderr,
                compile_output=db_submission.compile_output,
                source_code=db_submission.source_code,
                stdin=db_submission.stdin,
                expected_output=db_submission.expected_output,
                compiler_options=db_submission.compile_output,
                command_line_args=db_submission.command_line_args
            ))
        else:
            from main import submission_queue_manager
            await submission_queue_manager.enqueue_submission(db_submission, db)

    return BatchSubmissionResponse(
        batch_token=batch_token,
        submission_tokens=submission_tokens,
        results=results or None
    )

@router.get("/{batch_token}", response_model=List[SubmissionResponse])
async def get_batch_submissions(
    batch_token: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    batch = db.query(BatchModel).filter(
        BatchModel.batch_token == batch_token
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    submissions = db.query(SubmissionModel).filter(
        SubmissionModel.batch_id == batch.id,
        SubmissionModel.user_id == current_user.id
    ).all()

    response = []
    for db_submission in submissions:
        response.append(SubmissionResponse(
            token=db_submission.token,
            status_id=db_submission.status_id,
            created_at=db_submission.created_at,
            finished_at=db_submission.finished_at,
            time=db_submission.time,
            memory=db_submission.memory,
            exit_code=db_submission.exit_code,
            exit_signal=db_submission.exit_signal,
            stdout=db_submission.stdout,
            stderr=db_submission.stderr,
            compile_output=db_submission.compile_output,
            source_code=db_submission.source_code,
            stdin=db_submission.stdin,
            expected_output=db_submission.expected_output,
            compiler_options=db_submission.compile_output,
            command_line_args=db_submission.command_line_args
        ))

    return response
