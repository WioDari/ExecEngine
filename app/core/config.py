# app/core/config.py

from pydantic import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ExecEngine API"
    PROJECT_VERSION: str = "0.1.5"
    PROJECT_DESCRIPTION: str = "ExecEngine is designed to run untrusted code in web-centric environments and applications."
    
    DATABASE_HOST: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MAX_CONCURRENT_SUBMISSIONS: int = 5
    
    DB_MAX_RETRIES: int = 100
    DB_MAX_TIMEOUT: int = 3

    class Config:
        env_file = ".env"

settings = Settings()
