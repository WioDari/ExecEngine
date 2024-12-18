# app/db/session.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import orm_models
from pathlib import Path
import time
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = f"postgresql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOST}/{settings.DATABASE_NAME}"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def load_json(file_name):
    base_dir = Path(__file__).resolve().parent
    file_path = base_dir / file_name
    with open(file_path, "r", encoding="UTF-8") as f:
        return json.load(f)

def add_data_to_db():
    with SessionLocal() as session:
        """session.query(orm_models.StatusModel).delete()
        session.commit()
        session.query(orm_models.LanguageModel).delete()
        session.commit()
        session.query(orm_models.SubmissionModel).delete()
        session.commit()"""
        logger.info("Importing statuses and languages")
        statuses_data = load_json("statuses.json")
        languages_data = load_json("languages.json")
        for status_data in statuses_data:
            if session.query(orm_models.StatusModel).filter_by(id=status_data['id']).first():
                continue
            status = orm_models.StatusModel(
                id = status_data['id'],
                status_code = status_data['status_code'],
                status_full = status_data['status_full']
            )
            session.add(status)
        for language_data in languages_data:
            if session.query(orm_models.LanguageModel).filter_by(id=language_data['id']).first():
                continue
            language_data['NAME'] = language_data['NAME'].replace("$VERSION",language_data['VERSION'])
            if language_data['COMPILE_CMD']:
                language_data['COMPILE_CMD'] = language_data['COMPILE_CMD'].replace("$COMPILED_FILE",language_data['COMPILED_FILE'])
                language_data['COMPILE_CMD'] = language_data['COMPILE_CMD'].replace("$SOURCE_FILE",language_data['SOURCE_FILE'])
                language_data['COMPILE_CMD'] = language_data['COMPILE_CMD'].replace("$VERSION",language_data['VERSION'])
                language_data['RUN_CMD'] = language_data['RUN_CMD'].replace("$COMPILED_FILE",language_data['COMPILED_FILE'])
            language_data['RUN_CMD'] = language_data['RUN_CMD'].replace("$SOURCE_FILE",language_data['SOURCE_FILE'])
            
            language = orm_models.LanguageModel(
                id = language_data['id'],
                name = language_data['NAME'],
                version = language_data['VERSION'],
                source_file = language_data['SOURCE_FILE'],
                compiled_file = language_data['COMPILED_FILE'],
                compile_cmd = language_data['COMPILE_CMD'],
                run_cmd = language_data['RUN_CMD']
            )
            session.add(language)
        session.commit()
        logger.info("Data imported successfully")

def wait_for_db():
    max_retries=settings.DB_MAX_RETRIES
    timeout=settings.DB_MAX_TIMEOUT
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                logger.info("Database is ready!")
                add_data_to_db()
                return
        except OperationalError:
            logger.warning(f"Database is not ready, retrying {attempt+1}/{max_retries}...")
            time.sleep(timeout)
            
    logger.error("Database connection failed.")
    raise Exception("Database is not ready.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
