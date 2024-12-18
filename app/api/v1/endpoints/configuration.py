# app/api/v1/endpoints/configuration.py

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ServerConfiguration
import asyncio
import subprocess

router = APIRouter()

@router.get("/", response_model=ServerConfiguration, status_code=status.HTTP_200_OK)
async def server_info():
    try:
        cmd = subprocess.run(['lscpu'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True).stdout
        lines = cmd.split('\n')
        configs = {}
        for line in lines:
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                configs[key] = val
        return {"configuration": configs}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))
