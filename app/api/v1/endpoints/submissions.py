# app/api/v1/endpoints/submissions.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.schemas import SubmissionCreate, SubmissionResponse
from app.models.orm_models import SubmissionModel
from app.db.session import get_db
import uuid
from datetime import datetime
from app.core.dependencies import get_current_user
from app.models.orm_models import UserModel

#from app.main import submission_queue_manager
#from app.services.queue_manager import SubmissionQueueManager

router = APIRouter()

@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    submission: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    token = str(uuid.uuid4())
    created_at = datetime.utcnow()

    db_submission = SubmissionModel(
        token=token,
        language_id=submission.language_id,
        source_code=submission.source_code,
        stdin=submission.stdin,
        expected_output=submission.expected_output,
        compiler_options=submission.compiler_options,
        command_line_args=submission.command_line_args,
        time_limit=submission.time_limit,
        memory_limit=submission.memory_limit,
        status_id=1,  # In Queue
        created_at=created_at,
        user_id=current_user.id
    )

    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)

    # Добавление отправки в очередь
    from main import submission_queue_manager
    await submission_queue_manager.enqueue_submission(db_submission, db)

    return SubmissionResponse(
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
        compile_output=db_submission.compile_output
    )

@router.get("/{token}", response_model=SubmissionResponse)
async def get_submission(
    token: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    submission = db.query(SubmissionModel).filter(
        SubmissionModel.token == token,
        SubmissionModel.user_id == current_user.id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return SubmissionResponse(
        token=submission.token,
        status_id=submission.status_id,
        created_at=submission.created_at,
        finished_at=submission.finished_at,
        time=submission.time,
        memory=submission.memory,
        exit_code=submission.exit_code,
        exit_signal=submission.exit_signal,
        stdout=submission.stdout,
        stderr=submission.stderr,
        compile_output=submission.compile_output
    )
