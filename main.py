from contextlib import asynccontextmanager
from pathlib import Path
import logging
from time import monotonic

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

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
    workers_router,
)
from app.core.config import settings
from app.core.config_distribution import validate_role_configuration
from app.core.config_file import load_ini
from app.core.logger import setup_logging
from app.db.session import wait_for_db
from app.messaging.submission_publisher import SubmissionPublisher


setup_logging("api")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
MANUAL_DOCS_FILE = PUBLIC_DIR / "docs.html"


async def log_http_request(request: Request, call_next):
    started = monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "event=http.request.failed method=%s path=%s duration_ms=%d",
            request.method,
            request.url.path,
            round((monotonic() - started) * 1000),
        )
        raise
    logger.info(
        "event=http.request.completed method=%s path=%s status_code=%s duration_ms=%d",
        request.method,
        request.url.path,
        response.status_code,
        round((monotonic() - started) * 1000),
    )
    return response


async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
):
    errors = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error.get("loc", ()))
        errors.append(
            f"field={field} type={error.get('type', 'unknown')} "
            f"message={error.get('msg', 'validation failed')}"
        )
    logger.warning(
        "event=http.request.validation_failed method=%s path=%s errors=%s",
        request.method,
        request.url.path,
        " | ".join(errors),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors())},
    )


def register_routers(app: FastAPI):
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


async def healthz(request: Request):
    publisher = getattr(request.app.state, "submission_publisher", None)
    if publisher is None or not publisher.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API publisher is not ready.",
        )
    return {"status": "ok", "role": "api"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API initialization...")

    validate_role_configuration(load_ini(), "api")
    wait_for_db()

    publisher = SubmissionPublisher()
    await publisher.start()
    app.state.submission_publisher = publisher

    logger.info("API started successfully. Submission publisher is connected.")

    try:
        yield
    finally:
        logger.info("Shutting down API...")

        publisher = getattr(app.state, "submission_publisher", None)
        if publisher is not None:
            await publisher.stop()

        logger.info("API shutdown completed.")


def create_application():
    auto_docs_enabled = bool(settings.ENABLE_AUTO_GENERATED_DOCS)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description=settings.PROJECT_DESCRIPTION,
        openapi_url="/api/openapi.json",
        docs_url="/docs" if auto_docs_enabled else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.middleware("http")(log_http_request)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)

    register_routers(app)
    app.add_api_route("/healthz", healthz, methods=["GET"], include_in_schema=False)

    if not auto_docs_enabled:
        @app.get("/docs", include_in_schema=False)
        async def render_docs():
            if not MANUAL_DOCS_FILE.exists():
                raise HTTPException(status_code=404, detail="Manual docs file not found")
            return FileResponse(MANUAL_DOCS_FILE)
    else:
        @app.get("/docs/manual", include_in_schema=False)
        async def render_manual_docs():
            if not MANUAL_DOCS_FILE.exists():
                raise HTTPException(status_code=404, detail="Manual docs file not found")
            return FileResponse(MANUAL_DOCS_FILE)

    return app


app = create_application()
