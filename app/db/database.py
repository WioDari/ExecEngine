from __future__ import annotations

from sqlalchemy.engine import URL

from app.core.config_file import ini_value

def database_url_from_ini():
    try:
        port = int(ini_value("DATABASE SETTINGS", "DATABASE_PORT"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("DATABASE_PORT must be an integer") from exc

    return URL.create(
        drivername="postgresql+psycopg2",
        username=str(ini_value("DATABASE SETTINGS", "DATABASE_USER")).strip(),
        password=str(ini_value("DATABASE SETTINGS", "DATABASE_PASSWORD")),
        host=str(ini_value("DATABASE SETTINGS", "DATABASE_HOST")).strip(),
        port=port,
        database=str(ini_value("DATABASE SETTINGS", "DATABASE_NAME")).strip(),
    )
