# app/api/v2/endpoints/about.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def info():
    return {
        "name": "ExecEngine",
        "version": "0.1.6",
        "creator": "Danila Fateenkov",
        "contact": "wiosnagd97@gmail.com"
    }
