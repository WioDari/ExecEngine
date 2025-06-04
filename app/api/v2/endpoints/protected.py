# app/api/v2/endpoints/protected.py

from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.models.orm_models import UserModel
from app.models.schemas import UserResponse

router = APIRouter()

@router.get("/me/", response_model=UserResponse)
def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return current_user
