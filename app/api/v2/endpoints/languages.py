# app/api/v2/endpoints/languages.py

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from app.models.schemas import Language
from app.models.orm_models import LanguageModel
from app.db.session import get_db

router = APIRouter()

@router.get("/", response_model=List[Language])
async def get_languages(db: Session = Depends(get_db)):
    languages = db.query(LanguageModel).all()
    return languages

@router.get("/{language_id}", response_model=Language)
async def get_language(language_id: int = Path(...), db: Session = Depends(get_db)):
    language = db.query(LanguageModel).filter(LanguageModel.id == language_id).first()
    if not language:
        raise HTTPException(status_code=404, detail="Language not found.")
    return language
