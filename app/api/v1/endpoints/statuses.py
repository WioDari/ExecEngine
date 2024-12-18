# app/api/v1/endpoints/statuses.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.models.schemas import Status
from app.models.orm_models import StatusModel
from app.db.session import get_db

router = APIRouter()

@router.get("/", response_model=List[Status])
async def get_statuses(db: Session = Depends(get_db)):
    statuses = db.query(StatusModel).all()
    return statuses
