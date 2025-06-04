# app/api/v2/endpoints/isolate.py

from fastapi import APIRouter, HTTPException
import asyncio
import subprocess

router = APIRouter()

@router.get("/")
async def isolate_info():
    cmd = "isolate --version"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    isolate_version, err = await proc.communicate()

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500, 
            detail=f"isolate exited with code {proc.returncode}, error={err.decode('utf-8')}"
        )

    return {
        "isolate_version": isolate_version.decode("utf-8")
    }
