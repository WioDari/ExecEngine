# app/api/v2/endpoints/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.schemas import UserCreate, UserResponse
from app.services.user_service import get_user_by_username, get_user_by_email, create_user
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.orm_models import UserModel

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    if not getattr(current_user, "privileged_user", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only privileged users can create new users."
        )
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered.")
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    new_user = create_user(db, user=user)
    return new_user
