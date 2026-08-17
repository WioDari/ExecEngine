import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.database import database_url_from_ini

logger = logging.getLogger(__name__)

DATABASE_URL = database_url_from_ini()
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def wait_for_db(
    *,
    max_retries: int | None = None,
    retry_interval: float | None = None,
):
    if max_retries is None or retry_interval is None:
        from app.core.config import settings

        max_retries = settings.DB_MAX_RETRIES if max_retries is None else max_retries
        retry_interval = settings.DB_MAX_TIMEOUT if retry_interval is None else retry_interval

    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database is ready")
            return
        except OperationalError as exc:
            logger.warning(
                "Database is not ready, retrying %s/%s: %s",
                attempt + 1,
                max_retries,
                exc,
            )
            time.sleep(retry_interval)

    raise RuntimeError("Database is not ready")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
