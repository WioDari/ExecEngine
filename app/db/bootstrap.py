from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm_models import LanguageModel, StatusModel, UserModel

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATUS_MANIFEST_PATH = PROJECT_ROOT / "app" / "db" / "statuses.json"
LANGUAGE_MANIFEST_PATH = PROJECT_ROOT / "config" / "languages.json"

class BootstrapConflictError(RuntimeError):
    """Raised when reference data would reassign a stable public identity."""

@dataclass(frozen=True)
class AdminSpec:
    username: str
    password: str
    email: str
    full_name: str

@dataclass
class BootstrapStats:
    statuses_created: int = 0
    statuses_updated: int = 0
    languages_created: int = 0
    languages_updated: int = 0
    admin_created: bool = False

def _load_json_array(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise RuntimeError(f"Manifest must contain a JSON array of objects: {path}")
    return data


def load_statuses():
    return _load_json_array(STATUS_MANIFEST_PATH)


def load_languages():
    return _load_json_array(LANGUAGE_MANIFEST_PATH)


def upsert_statuses(session: Session, statuses: Iterable[dict], stats: BootstrapStats):
    for item in statuses:
        status = session.get(StatusModel, item["id"])
        if status is None:
            status = StatusModel(id=item["id"])
            session.add(status)
            stats.statuses_created += 1
        else:
            stats.statuses_updated += 1
        status.status_code = item["status_code"]
        status.status_full = item["status_full"]

def upsert_languages(session: Session, languages: Iterable[dict], stats: BootstrapStats):
    for item in languages:
        language_id = item["id"]
        slug = item["slug"]
        language_by_id = session.get(LanguageModel, language_id)
        language_by_slug = session.execute(
            select(LanguageModel).where(LanguageModel.slug == slug)
        ).scalar_one_or_none()

        if language_by_id is not None and language_by_id.slug != slug:
            raise BootstrapConflictError(
                f"Public language id {language_id} is assigned to slug "
                f"{language_by_id.slug!r}, expected {slug!r}"
            )
        if language_by_slug is not None and language_by_slug.id != language_id:
            raise BootstrapConflictError(
                f"Language slug {slug!r} is assigned to public id "
                f"{language_by_slug.id}, expected {language_id}"
            )

        language = language_by_id or language_by_slug
        if language is None:
            language = LanguageModel(id=language_id, slug=slug)
            session.add(language)
            stats.languages_created += 1
        else:
            stats.languages_updated += 1

        language.pool = item["pool"]
        language.enabled = item["enabled"]
        language.name = item["NAME"]
        language.version = item["VERSION"]
        language.source_file = item["SOURCE_FILE"]
        language.compiled_file = item["COMPILED_FILE"]
        language.compile_cmd = item["COMPILE_CMD"]
        language.run_cmd = item["RUN_CMD"]

def ensure_admin(
    session: Session,
    admin: AdminSpec,
    password_hasher: Callable[[str], str] | None = None,
):
    existing_username = session.execute(
        select(UserModel).where(UserModel.username == admin.username)
    ).scalar_one_or_none()
    existing_email = session.execute(
        select(UserModel).where(UserModel.email == admin.email)
    ).scalar_one_or_none()

    if existing_username is not None:
        if existing_username.email != admin.email:
            raise BootstrapConflictError(
                f"Bootstrap administrator {admin.username!r} already exists with another email"
            )
        if not existing_username.privileged_user:
            raise BootstrapConflictError(
                f"User {admin.username!r} exists but is not privileged; refusing implicit promotion"
            )
        return False

    if existing_email is not None:
        raise BootstrapConflictError(
            f"Bootstrap administrator email {admin.email!r} belongs to another user"
        )

    if password_hasher is None:
        from passlib.context import CryptContext

        password_hasher = CryptContext(
            schemes=["bcrypt"], deprecated="auto"
        ).hash

    session.add(
        UserModel(
            username=admin.username,
            email=admin.email,
            full_name=admin.full_name,
            password_hash=password_hasher(admin.password),
            privileged_user=True,
        )
    )
    return True

def bootstrap_reference_data(
    session: Session,
    statuses: Iterable[dict],
    languages: Iterable[dict],
    admin: AdminSpec | None = None,
    password_hasher: Callable[[str], str] | None = None,
):
    stats = BootstrapStats()
    upsert_statuses(session, statuses, stats)
    session.flush()
    upsert_languages(session, languages, stats)
    session.flush()
    if admin is not None:
        stats.admin_created = ensure_admin(session, admin, password_hasher)
        session.flush()
    return stats

def run_bootstrap(include_admin: bool = True):
    from app.core.config_distribution import validate_role_configuration
    from app.core.config_file import load_ini
    from app.db.session import SessionLocal

    validate_role_configuration(load_ini(), "bootstrap" if include_admin else "migrate")
    admin = None
    if include_admin:
        admin = _admin_from_ini()

    with SessionLocal.begin() as session:
        stats = bootstrap_reference_data(
            session,
            statuses=load_statuses(),
            languages=load_languages(),
            admin=admin,
        )

    logger.info(
        "Bootstrap complete: statuses created=%s updated=%s; "
        "languages created=%s updated=%s; admin_created=%s",
        stats.statuses_created,
        stats.statuses_updated,
        stats.languages_created,
        stats.languages_updated,
        stats.admin_created,
    )
    return stats

def _required_ini(section: str, name: str):
    from app.core.config_file import ini_value

    value = str(ini_value(section, name)).strip()
    if not value:
        raise RuntimeError(f"Required configuration option is not set: [{section}] {name}")
    return value

def _admin_from_ini():
    section = "BOOTSTRAP ADMIN SETTINGS"
    username = _required_ini(section, "ADMIN_USERNAME")
    password = _required_ini(section, "ADMIN_PASSWORD")
    if username.lower() == "admin":
        raise RuntimeError("ADMIN_USERNAME must not use the default 'admin' value")
    if len(password) < 16:
        raise RuntimeError("ADMIN_PASSWORD must contain at least 16 characters")
    if password.lower() in {"password", "changeme", "change-me", "admin"}:
        raise RuntimeError("ADMIN_PASSWORD contains an insecure default value")
    database_password = _required_ini("DATABASE SETTINGS", "DATABASE_PASSWORD")
    if database_password and password == database_password:
        raise RuntimeError("Database and administrator passwords must be different")
    return AdminSpec(
        username=username,
        password=password,
        email=_required_ini(section, "ADMIN_EMAIL"),
        full_name=_required_ini(section, "ADMIN_NAME"),
    )

def main():
    parser = argparse.ArgumentParser(description="Idempotently bootstrap ExecEngine reference data")
    parser.add_argument(
        "--skip-admin",
        action="store_true",
        help="Upsert statuses and languages without creating the bootstrap administrator",
    )
    args = parser.parse_args()
    from app.core.logger import setup_logging

    setup_logging("bootstrap")
    run_bootstrap(include_admin=not args.skip_admin)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
