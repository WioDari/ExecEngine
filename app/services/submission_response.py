# app/services/submission_response.py

from typing import Optional, Set, Dict, Any
from fastapi import HTTPException, status
from app.models.schemas import SubmissionResponse
from app.models.orm_models import SubmissionModel

ALLOWED_SUBMISSION_FIELDS = set(SubmissionResponse.__fields__.keys())

def parse_submission_fields(fields: Optional[str]) -> Optional[Set[str]]:
    if fields is None:
        return None
    
    requested_fields = {
        field.strip()
        for field in fields.split(',')
        if field.strip()
    }

    if not requested_fields:
        return None
    
    unknown_fields = requested_fields - ALLOWED_SUBMISSION_FIELDS
    if unknown_fields:
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = {
                "message" : "Unknown submission fields received.",
                "unknown_fields" : sorted(unknown_fields),
                # Still idk if i should put allowed fields here
                # "allowed_fields" : sorted(ALLOWED_SUBMISSION_FIELDS)
            },
        )
    
    return requested_fields

def serialize_submission(
    submission: SubmissionModel,
    fields: Optional[Set[str]] = None
) -> Dict[str, Any]:
    data = SubmissionResponse.from_orm(submission).dict()

    if fields is None:
        return data
    
    return {
        field: data[field]
        for field in data
        if field in fields
    }