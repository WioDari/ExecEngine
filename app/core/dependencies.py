# app/core/dependencies.py

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from app.db.session import get_db
from app.core.config import settings
from app.models.orm_models import ApiTokenModel, UserModel
from fastapi import Request

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v2/auth/login/")

def get_submission_publisher(request: Request):
    publisher = getattr(request.app.state, "submission_publisher", None)
    if publisher is None:
        raise RuntimeError("Submission publisher is not initialized")
    return publisher


def get_submission_waiter():
    from app.services.submission_waiter import SubmissionWaiter

    return SubmissionWaiter(
        timeout=settings.API_WAIT_TIMEOUT,
        poll_interval=settings.API_WAIT_POLL_INTERVAL,
    )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    db_user = db.query(UserModel).filter(UserModel.username == username).first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    api_token = db.query(ApiTokenModel).filter(ApiTokenModel.token == token).first()
    if not api_token or api_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired or is invalid.")

    return db_user
