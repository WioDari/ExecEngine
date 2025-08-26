# app/core/config.py

import configparser
import os
from pathlib import Path
from pydantic import BaseSettings

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

class Settings(BaseSettings):
    PROJECT_NAME: str = _parse_value(config['PROJECT BASIC SETTINGS']['PROJECT_NAME'])
    PROJECT_VERSION: str = _parse_value(config['PROJECT BASIC SETTINGS']['PROJECT_VERSION'])
    PROJECT_DESCRIPTION: str = _parse_value(config['PROJECT BASIC SETTINGS']['PROJECT_DESCRIPTION'])
    ENABLE_AUTO_GENERATED_DOCS: bool = _parse_value(config['PROJECT BASIC SETTINGS']['ENABLE_AUTO_GENERATED_DOCS'])
    
    DATABASE_HOST: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_HOST'])
    DATABASE_NAME: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_NAME'])
    DATABASE_USER: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_USER'])
    DATABASE_PASSWORD: str = _parse_value(config['CONNECTION SETTINGS']['DATABASE_PASSWORD'])
    RABBITMQ_HOST: str = _parse_value(config['CONNECTION SETTINGS']['RABBITMQ_HOST'])
    RABBITMQ_USER: str = _parse_value(config['CONNECTION SETTINGS']['RABBITMQ_USER'])
    RABBITMQ_PASSWORD: str = _parse_value(config['CONNECTION SETTINGS']['RABBITMQ_PASSWORD'])
    ADMIN_USERNAME: str = _parse_value(config['CONNECTION SETTINGS']['ADMIN_USERNAME'])
    ADMIN_PASSWORD: str = _parse_value(config['CONNECTION SETTINGS']['ADMIN_PASSWORD'])
    ADMIN_EMAIL: str = _parse_value(config['CONNECTION SETTINGS']['ADMIN_EMAIL'])
    ADMIN_NAME: str = _parse_value(config['CONNECTION SETTINGS']['ADMIN_NAME'])
    
    SECRET_KEY: str = _parse_value(config['SECRET KEY SETTINGS']['SECRET_KEY'])
    ALGORITHM: str = _parse_value(config['SECRET KEY SETTINGS']['ALGORITHM'])
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _parse_value(config['SECRET KEY SETTINGS']['ACCESS_TOKEN_EXPIRE_MINUTES'])
    
    MAX_CONCURRENT_SUBMISSIONS: int = _parse_value(config['BATCH SIZE AND CONCURENT SUBMISSIONS LIMITS']['MAX_CONCURRENT_SUBMISSIONS'])
    MAX_BATCH_SIZE: int = _parse_value(config['BATCH SIZE AND CONCURENT SUBMISSIONS LIMITS']['MAX_BATCH_SIZE'])
    
    DB_MAX_RETRIES: int = _parse_value(config['DB CONNECTION SETTINGS']['DB_MAX_RETRIES'])
    DB_MAX_TIMEOUT: int = _parse_value(config['DB CONNECTION SETTINGS']['DB_MAX_TIMEOUT'])
    
    DEFAULT_TIME_LIMIT: int = _parse_value(config['DEFAULT RESOURCE LIMITS']['DEFAULT_TIME_LIMIT'])
    DEFAULT_MEMORY_LIMIT: int = _parse_value(config['DEFAULT RESOURCE LIMITS']['DEFAULT_MEMORY_LIMIT'])
    DEFAULT_EXTRA_TIME: float = _parse_value(config['DEFAULT RESOURCE LIMITS']['DEFAULT_EXTRA_TIME'])
    DEFAULT_WALL_TIME_LIMIT: int = _parse_value(config['DEFAULT RESOURCE LIMITS']['DEFAULT_WALL_TIME_LIMIT'])
    DEFAULT_STACK_SIZE: int = _parse_value(config['DEFAULT RESOURCE LIMITS']['DEFAULT_STACK_SIZE'])
    DEFAULT_MAX_FILE_SIZE: int = _parse_value(config['DEFAULT RESOURCE LIMITS']['DEFAULT_MAX_FILE_SIZE'])
    
    MAX_TIME_LIMIT: int = _parse_value(config['MAX RESOURCE LIMITS']['MAX_TIME_LIMIT'])
    MAX_MEMORY_LIMIT: int = _parse_value(config['MAX RESOURCE LIMITS']['MAX_MEMORY_LIMIT'])
    MAX_EXTRA_TIME: float = _parse_value(config['MAX RESOURCE LIMITS']['MAX_EXTRA_TIME'])
    MAX_WALL_TIME_LIMIT: int = _parse_value(config['MAX RESOURCE LIMITS']['MAX_WALL_TIME_LIMIT'])
    MAX_STACK_SIZE: int = _parse_value(config['MAX RESOURCE LIMITS']['MAX_STACK_SIZE'])
    MAX_FILE_SIZE: int = _parse_value(config['MAX RESOURCE LIMITS']['MAX_FILE_SIZE'])
    
    ALLOW_ENABLE_NETWORK: bool = _parse_value(config['OTHER SETTINGS']['ALLOW_ENABLE_NETWORK'])
    ALWAYS_REDIRECT_STDERR_TO_STDOUT: bool = _parse_value(config['OTHER SETTINGS']['ALWAYS_REDIRECT_STDERR_TO_STDOUT'])
    ALLOW_COMMAND_LINE_ARGS: bool = _parse_value(config['OTHER SETTINGS']['ALLOW_COMMAND_LINE_ARGS'])
    ALLOW_COMPILER_OPTIONS: bool = _parse_value(config['OTHER SETTINGS']['ALLOW_COMPILER_OPTIONS'])

    class Config:
        env_file = ".env"

settings = Settings()
