#!/usr/bin/env python3

import configparser
import os
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

def _parse_value(value: str):
    value = value.strip()
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    elif value.isdigit():
        return int(value)
    else:
        try:
            return float(value)
        except ValueError:
            return value

PROJECT_ROOT = Path(__file__).parent.parent.parent
INI_FILE_PATH = PROJECT_ROOT / "execengine.ini"

config = configparser.ConfigParser()
config.optionxform = str
config.read(INI_FILE_PATH, encoding="utf-8")

DATABASE_HOST: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_HOST'])
DATABASE_NAME: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_NAME'])
DATABASE_USER: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_USER'])
DATABASE_PASSWORD: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_PASSWORD'])

TABLE_NAME = "api_tokens"
TIME_COLUMN = "expires_at"
MINUTES_EXPIRE = _parse_value(config['SECRET KEY SETTINGS']['ACCESS_TOKEN_EXPIRE_MINUTES'])

DATABASE_URL = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"
engine = create_engine(DATABASE_URL)

def cleanup_api_tokens():
    cutoff_date = datetime.utcnow() - timedelta(minutes=MINUTES_EXPIRE)
    query = text(f"DELETE FROM {TABLE_NAME} WHERE {TIME_COLUMN} < :cutoff")

    with engine.begin() as conn:
        result = conn.execute(query, {"cutoff": cutoff_date})
        print(f"[{datetime.utcnow()}] Removed API Tokens: {result.rowcount}")

if __name__ == "__main__":
    cleanup_api_tokens()