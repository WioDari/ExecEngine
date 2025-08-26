#!/usr/bin/env python3

from app.db.session import engine,Base
from app.models import orm_models
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables_manager():
    logger.info("Creating tables for database")
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully!")
