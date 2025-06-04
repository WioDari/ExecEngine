# app/core/config.py

from pydantic import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ExecEngine API"
    PROJECT_VERSION: str = "0.1.6"
    PROJECT_DESCRIPTION: str = "ExecEngine is designed to run untrusted code in web-centric environments and applications."
    
    DATABASE_HOST: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    RABBITMQ_HOST: str
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    MAX_CONCURRENT_SUBMISSIONS: int = 5
    MAX_BATCH_SIZE: int = 50
    
    DB_MAX_RETRIES: int = 100
    DB_MAX_TIMEOUT: int = 3
    
    DEFAULT_TIME_LIMIT: int = 2
    DEFAULT_MEMORY_LIMIT: int = 32000
    DEFAULT_EXTRA_TIME: float = 0.5
    DEFAULT_WALL_TIME_LIMIT: int = 3
    DEFAULT_STACK_SIZE: int = 32000
    DEFAULT_MAX_FILE_SIZE: int = 1024
    
    MAX_TIME_LIMIT: int = 10
    MAX_MEMORY_LIMIT: int = 128000
    MAX_EXTRA_TIME: float = 6.0
    MAX_WALL_TIME_LIMIT: int = 11
    MAX_STACK_SIZE: int = 64000
    MAX_FILE_SIZE: int = 2048
    
    ALLOW_ENABLE_NETWORK: bool = True
    ALWAYS_REDIRECT_STDERR_TO_STDOUT: bool = False
    ALLOW_COMMAND_LINE_ARGS: bool = True
    ALLOW_COMPILER_OPTIONS: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
