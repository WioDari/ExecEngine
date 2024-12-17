# app/services/user_service.py

from sqlalchemy.orm import Session
from typing import Optional
from app.models.orm_models import UserModel
from app.models.schemas import UserCreate
from app.core.security import hash_password

def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.email == email).first()

def create_user(db: Session, user: UserCreate) -> UserModel:
    db_user = UserModel(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        password_hash=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
