# app/api/v2/endpoints/workers.py

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user
from app.models.orm_models import UserModel
from typing import Any
import aio_pika
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/")
async def get_queue_stats(current_user: UserModel = Depends(get_current_user)):
    if not getattr(current_user, "privileged_user", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    from main import submission_queue_manager
    queue_manager = submission_queue_manager

    channel = queue_manager.channel
    queue = await channel.declare_queue(queue_manager.queue_name, passive=True)
    message_count = queue.declaration_result.message_count
    max_length = None

    if queue.arguments and b'x-max-length' in queue.arguments:
        max_length = int(queue.arguments[b'x-max-length'])

    completed_tasks = getattr(queue_manager, "completed_tasks", 0)
    failed_tasks = getattr(queue_manager, "failed_tasks", 0)

    return JSONResponse({
        "queue_max_length": max_length,
        "queue_current_length": message_count,
        "tasks_completed": completed_tasks,
        "tasks_failed": failed_tasks,
    })