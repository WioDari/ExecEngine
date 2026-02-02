# app/api/v2/endpoints/configuration.py

from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import ServerConfiguration, SoftwareConfiguration
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.orm_models import UserModel
import asyncio
import subprocess

router = APIRouter()

@router.get("/hardware", response_model=ServerConfiguration, status_code=status.HTTP_200_OK)
async def hardware_info(current_user: UserModel = Depends(get_current_user)):
    if settings.PROTECTED_HARDWARE_CONFIGURATION:
        if not getattr(current_user, "privileged_user", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only privileged users can see information about server configuration."
            )
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

@router.get("/software", response_model=SoftwareConfiguration, status_code=status.HTTP_200_OK)
async def software_info(current_user: UserModel = Depends(get_current_user)):
    if settings.PROTECTED_SOFTWARE_CONFIGURATION:
        if not getattr(current_user, "privileged_user", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only privileged users can see information about API-service configuration."
            )
    try:
        software_configs = SoftwareConfiguration(
            max_concurent_submissions=settings.MAX_CONCURRENT_SUBMISSIONS,
            default_time_limit=settings.DEFAULT_TIME_LIMIT,
            default_memory_limit=settings.DEFAULT_MEMORY_LIMIT,
            default_extra_time=settings.DEFAULT_EXTRA_TIME,
            default_wall_time_limit=settings.DEFAULT_WALL_TIME_LIMIT,
            default_stack_size=settings.DEFAULT_STACK_SIZE,
            default_max_file_size=settings.DEFAULT_MAX_FILE_SIZE,
            max_time_limit=settings.MAX_TIME_LIMIT,
            max_memory_limit=settings.MAX_MEMORY_LIMIT,
            max_extra_time=settings.MAX_EXTRA_TIME,
            max_wall_time_limit=settings.MAX_WALL_TIME_LIMIT,
            max_stack_size=settings.MAX_STACK_SIZE,
            max_file_size=settings.MAX_FILE_SIZE,
            allow_enable_network=settings.ALLOW_ENABLE_NETWORK,
            always_redirect_stderr_to_stdout=settings.ALWAYS_REDIRECT_STDERR_TO_STDOUT,
            allow_command_line_args=settings.ALLOW_COMMAND_LINE_ARGS,
            allow_compiler_options=settings.ALLOW_COMPILER_OPTIONS
        )
        return software_configs
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))