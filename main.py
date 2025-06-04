# main.py

import asyncio
from fastapi import FastAPI
from app.api.v2.endpoints import (
    about_router,
    languages_router,
    statuses_router,
    submissions_router,
    submissions_batch_router,
    configuration_router,
    auth_router,
    users_router,
    protected_router,
    isolate_router,
    workers_router
)
from app.core.config import settings
from app.db.session import wait_for_db
from app.core.logger import setup_logging
from app.services.queue_manager import SubmissionQueueManager
from create_tables import create_tables_manager

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION
)

submission_queue_manager = SubmissionQueueManager(max_concurrent=settings.MAX_CONCURRENT_SUBMISSIONS)

@app.on_event("startup")
async def startup_event():
    wait_for_db()
    create_tables_manager()
    print("[INFO] Starting API...")
    await submission_queue_manager.start()

@app.on_event("shutdown")
async def shutdown_event():
    await submission_queue_manager.stop()

app.include_router(about_router, prefix="/v2/about", tags=["About"])
app.include_router(languages_router, prefix="/v2/languages", tags=["Languages"])
app.include_router(statuses_router, prefix="/v2/statuses", tags=["Statuses"])
app.include_router(submissions_router, prefix="/v2/submissions", tags=["Submissions"])
app.include_router(submissions_batch_router, prefix="/v2/submissions/batch", tags=["Batch Submissions"])
app.include_router(configuration_router, prefix="/v2/configuration", tags=["Configuration"])
app.include_router(auth_router, prefix="/v2/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/v2/users", tags=["Users"])
app.include_router(protected_router, prefix="/v2/protected", tags=["Protected"])
app.include_router(isolate_router, prefix="/v2/isolate", tags=["Isolate"])
app.include_router(workers_router, prefix="/v2/workers", tags=["Workers"])
