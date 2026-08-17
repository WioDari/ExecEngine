# app/core/logger.py

import logging

from app.core.config_file import ini_value


_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def _configured_level(option: str):
    name = str(ini_value("LOGGING SETTINGS", option)).strip().upper()
    try:
        return _LEVELS[name]
    except KeyError as exc:
        allowed = ", ".join(_LEVELS)
        raise RuntimeError(
            f"Invalid [LOGGING SETTINGS] {option}: {name!r}; expected one of {allowed}"
        ) from exc


def setup_logging(service: str = "application"):
    application_level = _configured_level("LOG_LEVEL")
    sql_level = _configured_level("SQL_LOG_LEVEL")
    log_format = (
        f"%(asctime)s [%(levelname)s] service={service} "
        "logger=%(name)s %(message)s"
    )
    logging.basicConfig(
        level=application_level,
        format=log_format,
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(application_level)
    formatter = logging.Formatter(log_format)
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(sql_level)

    for handler in tuple(sqlalchemy_logger.handlers):
        if getattr(handler, "_execengine_sql_handler", False):
            sqlalchemy_logger.removeHandler(handler)
            handler.close()

    sql_log_file = str(ini_value("LOGGING SETTINGS", "SQL_LOG_FILE")).strip()
    if sql_log_file:
        file_handler = logging.FileHandler(sql_log_file)
        sql_formatter = logging.Formatter(
            f"%(asctime)s [%(levelname)s] service={service} "
            "logger=%(name)s %(message)s"
        )
        file_handler.setFormatter(sql_formatter)
        file_handler.setLevel(sql_level)
        file_handler._execengine_sql_handler = True
        sqlalchemy_logger.addHandler(file_handler)
        sqlalchemy_logger.propagate = False
    else:
        sqlalchemy_logger.propagate = True
