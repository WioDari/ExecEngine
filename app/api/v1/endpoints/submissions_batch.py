# app/api/v1/endpoints/submissions_batch.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.schemas import BatchSubmissionCreate, BatchSubmissionResponse, SubmissionResponse
from app.models.orm_models import SubmissionModel, BatchModel
from app.db.session import get_db
import uuid
from datetime import datetime
from typing import List
from app.core.dependencies import get_current_user
from app.models.orm_models import UserModel
#from app.main import submission_queue_manager
from app.services.queue_manager import SubmissionQueueManager

router = APIRouter()

@router.post("/", response_model=BatchSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_submission(
    batch_submission: BatchSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
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
            memory_limit=subm.memory_limit,
            status=1,  # In Queue
            created_at=created_at,
            batch_id=db_batch.id,
            user_id=current_user.id
        )

        db.add(db_submission)
        db.commit()
        db.refresh(db_submission)

        # Добавление отправки в очередь
        await submission_queue_manager.enqueue_submission(db_submission, db)

    return BatchSubmissionResponse(
        batch_token=batch_token,
        submission_tokens=submission_tokens
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
    for submission in submissions:
        response.append(SubmissionResponse(
            token=submission.token,
            status=submission.status,
            created_at=submission.created_at,
            finished_at=submission.finished_at,
            time=submission.time,
            memory=submission.memory,
            exit_code=submission.exit_code,
            exit_signal=submission.exit_signal,
            stdout=submission.stdout,
            stderr=submission.stderr,
            compile_output=submission.compile_output
        ))

    return response
