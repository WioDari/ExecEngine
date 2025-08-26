# app/api/v2/endpoints/about.py
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def info():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "creator": "Danila Fateenkov",
        "contact": "wiosnagd97@gmail.com"
    }
