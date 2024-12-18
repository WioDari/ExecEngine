# app/api/v1/endpoints/auth.py

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.session import get_db
from app.models.schemas import TokenData, AuthResponse, TokenResponse
from app.models.orm_models import ApiTokenModel
from app.services.user_service import get_user_by_username
from app.core.security import verify_password, create_access_token
from app.core.config import settings

router = APIRouter()

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/login/", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, username=user.username)
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": db_user.username}, expires_delta=access_token_expires)

    api_token = ApiTokenModel(
        token=access_token,
        user_id=db_user.id,
        expires_at=datetime.utcnow() + access_token_expires
    )
    db.add(api_token)
    db.commit()

    return TokenResponse(access_token=access_token, token_type="bearer")

@router.post("/authorize/", response_model=AuthResponse)
def authorize_token_validate(token_data: TokenData, db: Session = Depends(get_db)):
    token = token_data.token
    api_token = db.query(ApiTokenModel).filter(ApiTokenModel.token == token).first()
    if not api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    if api_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
    return AuthResponse(valid=True, user_id=api_token.user_id)
