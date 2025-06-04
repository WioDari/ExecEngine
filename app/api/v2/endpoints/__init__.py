# app/api/v2/endpoints/__init__.py

from .about import router as about_router
from .languages import router as languages_router
from .statuses import router as statuses_router
from .submissions import router as submissions_router
from .submissions_batch import router as submissions_batch_router
from .configuration import router as configuration_router
from .auth import router as auth_router
from .users import router as users_router
from .protected import router as protected_router
from .isolate import router as isolate_router
from .workers import router as workers_router

__all__ = [
    "about_router",
    "languages_router",
    "statuses_router",
    "submissions_router",
    "submissions_batch_router",
    "configuration_router",
    "auth_router",
    "users_router",
    "protected_router",
    "isolate_router",
    "workers_router"
]
