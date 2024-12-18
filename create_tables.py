#!/usr/bin/env python3

from app.db.session import engine,Base
from app.models import orm_models
import json

def create_tables_manager():
    print("[INFO] Creating tables for Database")
    Base.metadata.create_all(bind=engine)
    print("[INFO] All tables created successfully")
