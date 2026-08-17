from pydantic import BaseModel, SecretStr, root_validator, validator

from app.core.config_file import ini_value


_ini = ini_value


class Settings(BaseModel):
    PROJECT_NAME: str = _ini("PROJECT BASIC SETTINGS", "PROJECT_NAME")
    PROJECT_VERSION: str = _ini("PROJECT BASIC SETTINGS", "PROJECT_VERSION")
    PROJECT_DESCRIPTION: str = _ini("PROJECT BASIC SETTINGS", "PROJECT_DESCRIPTION")
    ENABLE_AUTO_GENERATED_DOCS: bool = _ini("PROJECT BASIC SETTINGS", "ENABLE_AUTO_GENERATED_DOCS")

    DATABASE_HOST: str = _ini("DATABASE SETTINGS", "DATABASE_HOST")
    DATABASE_PORT: int = _ini("DATABASE SETTINGS", "DATABASE_PORT")
    DATABASE_NAME: str = _ini("DATABASE SETTINGS", "DATABASE_NAME")
    DATABASE_USER: str = _ini("DATABASE SETTINGS", "DATABASE_USER")
    DATABASE_PASSWORD: SecretStr = _ini("DATABASE SETTINGS", "DATABASE_PASSWORD")

    RABBITMQ_HOST: str = _ini("RABBITMQ SETTINGS", "RABBITMQ_HOST")
    RABBITMQ_PORT: int = _ini("RABBITMQ SETTINGS", "RABBITMQ_PORT")
    RABBITMQ_USER: str = _ini("RABBITMQ SETTINGS", "RABBITMQ_USER")
    RABBITMQ_PASSWORD: SecretStr = _ini("RABBITMQ SETTINGS", "RABBITMQ_PASSWORD")

    SECRET_KEY: SecretStr = _ini("SECRET KEY SETTINGS", "SECRET_KEY")
    ALGORITHM: str = _ini("SECRET KEY SETTINGS", "ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _ini("SECRET KEY SETTINGS", "ACCESS_TOKEN_EXPIRE_MINUTES")

    MAX_CONCURRENT_SUBMISSIONS: int = _ini(
        "BATCH SIZE AND CONCURENT SUBMISSIONS LIMITS", "MAX_CONCURRENT_SUBMISSIONS"
    )
    MAX_BATCH_SIZE: int = _ini("BATCH SIZE AND CONCURENT SUBMISSIONS LIMITS", "MAX_BATCH_SIZE")

    DB_MAX_RETRIES: int = _ini("DB CONNECTION SETTINGS", "DB_MAX_RETRIES")
    DB_MAX_TIMEOUT: int = _ini("DB CONNECTION SETTINGS", "DB_MAX_TIMEOUT")
    DEFAULT_TIME_LIMIT: int = _ini("DEFAULT RESOURCE LIMITS", "DEFAULT_TIME_LIMIT")
    DEFAULT_MEMORY_LIMIT: int = _ini("DEFAULT RESOURCE LIMITS", "DEFAULT_MEMORY_LIMIT")
    DEFAULT_EXTRA_TIME: float = _ini("DEFAULT RESOURCE LIMITS", "DEFAULT_EXTRA_TIME")
    DEFAULT_WALL_TIME_LIMIT: int = _ini("DEFAULT RESOURCE LIMITS", "DEFAULT_WALL_TIME_LIMIT")
    DEFAULT_STACK_SIZE: int = _ini("DEFAULT RESOURCE LIMITS", "DEFAULT_STACK_SIZE")
    DEFAULT_MAX_FILE_SIZE: int = _ini("DEFAULT RESOURCE LIMITS", "DEFAULT_MAX_FILE_SIZE")

    MAX_TIME_LIMIT: int = _ini("MAX RESOURCE LIMITS", "MAX_TIME_LIMIT")
    MAX_MEMORY_LIMIT: int = _ini("MAX RESOURCE LIMITS", "MAX_MEMORY_LIMIT")
    MAX_EXTRA_TIME: float = _ini("MAX RESOURCE LIMITS", "MAX_EXTRA_TIME")
    MAX_WALL_TIME_LIMIT: int = _ini("MAX RESOURCE LIMITS", "MAX_WALL_TIME_LIMIT")
    MAX_STACK_SIZE: int = _ini("MAX RESOURCE LIMITS", "MAX_STACK_SIZE")
    MAX_FILE_SIZE: int = _ini("MAX RESOURCE LIMITS", "MAX_FILE_SIZE")

    ALLOW_ENABLE_NETWORK: bool = _ini("OTHER SETTINGS", "ALLOW_ENABLE_NETWORK")
    ALWAYS_REDIRECT_STDERR_TO_STDOUT: bool = _ini(
        "OTHER SETTINGS", "ALWAYS_REDIRECT_STDERR_TO_STDOUT"
    )
    ALLOW_COMMAND_LINE_ARGS: bool = _ini("OTHER SETTINGS", "ALLOW_COMMAND_LINE_ARGS")
    ALLOW_COMPILER_OPTIONS: bool = _ini("OTHER SETTINGS", "ALLOW_COMPILER_OPTIONS")
    ALLOW_WAIT: bool = _ini("OTHER SETTINGS", "ALLOW_WAIT")
    API_WAIT_TIMEOUT: float = _ini("OTHER SETTINGS", "API_WAIT_TIMEOUT")
    API_WAIT_POLL_INTERVAL: float = _ini("OTHER SETTINGS", "API_WAIT_POLL_INTERVAL")
    WORKER_STALE_THRESHOLD: float = _ini("WORKER SETTINGS", "WORKER_STALE_THRESHOLD")
    PROTECTED_SOFTWARE_CONFIGURATION: bool = _ini(
        "OTHER SETTINGS", "PROTECTED_SOFTWARE_CONFIGURATION"
    )
    PROTECTED_HARDWARE_CONFIGURATION: bool = _ini(
        "OTHER SETTINGS", "PROTECTED_HARDWARE_CONFIGURATION"
    )

    @validator(
        "DATABASE_USER",
        "RABBITMQ_USER",
        allow_reuse=True,
    )
    def validate_required_text(cls, value: str, field):
        value = value.strip()
        if not value:
            raise ValueError(f"{field.name} must not be empty")
        return value

    @validator(
        "DATABASE_PASSWORD",
        "RABBITMQ_PASSWORD",
        allow_reuse=True,
    )
    def validate_password(cls, value: SecretStr, field):
        raw_value = value.get_secret_value()
        if len(raw_value) < 16:
            raise ValueError(f"{field.name} must contain at least 16 characters")
        if raw_value.lower() in {"password", "changeme", "change-me", "admin"}:
            raise ValueError(f"{field.name} contains an insecure default value")
        return value

    @validator("SECRET_KEY", allow_reuse=True)
    def validate_secret_key(cls, value: SecretStr):
        raw_value = value.get_secret_value()
        if len(raw_value) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        if raw_value.lower().startswith(("change-me", "replace-me", "changeme")):
            raise ValueError("SECRET_KEY must be replaced with a randomly generated value")
        return value

    @root_validator(allow_reuse=True)
    def validate_distinct_credentials(cls, values):
        secret_fields = ("DATABASE_PASSWORD", "RABBITMQ_PASSWORD")
        secrets = [
            values[field].get_secret_value()
            for field in secret_fields
            if values.get(field) is not None
        ]
        if len(secrets) != len(set(secrets)):
            raise ValueError("Database and RabbitMQ passwords must be different")
        return values

    @root_validator(allow_reuse=True)
    def validate_wait_settings(cls, values):
        timeout = values.get("API_WAIT_TIMEOUT")
        interval = values.get("API_WAIT_POLL_INTERVAL")
        if timeout is not None and timeout <= 0:
            raise ValueError("API_WAIT_TIMEOUT must be positive")
        if interval is not None and interval <= 0:
            raise ValueError("API_WAIT_POLL_INTERVAL must be positive")
        if timeout is not None and interval is not None and interval > timeout:
            raise ValueError("API_WAIT_POLL_INTERVAL must not exceed API_WAIT_TIMEOUT")
        return values

    @validator("WORKER_STALE_THRESHOLD", allow_reuse=True)
    def validate_worker_stale_threshold(cls, value: float):
        if value <= 0:
            raise ValueError("WORKER_STALE_THRESHOLD must be positive")
        return value

    class Config:
        # Values are declared from INI at class construction time; validate
        # defaults so SecretStr and numeric fields are still converted safely.
        validate_all = True

settings = Settings()
