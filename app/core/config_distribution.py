from __future__ import annotations

import configparser
import os
import shlex
from pathlib import Path


SOURCE_PATH = Path("/source/execengine.ini")
OUTPUT_ROOT = Path("/output")

ROLE_SECTIONS: dict[str, tuple[str, ...]] = {
    "api": (
        "PROJECT BASIC SETTINGS",
        "DATABASE SETTINGS",
        "RABBITMQ SETTINGS",
        "WORKER SETTINGS",
        "SECRET KEY SETTINGS",
        "LOGGING SETTINGS",
        "BATCH SIZE AND CONCURENT SUBMISSIONS LIMITS",
        "DB CONNECTION SETTINGS",
        "DEFAULT RESOURCE LIMITS",
        "MAX RESOURCE LIMITS",
        "OTHER SETTINGS",
    ),
    "worker": (
        "PROJECT BASIC SETTINGS",
        "DATABASE SETTINGS",
        "RABBITMQ SETTINGS",
        "WORKER SETTINGS",
        "LOGGING SETTINGS",
        "DB CONNECTION SETTINGS",
        "MAX RESOURCE LIMITS",
        "EXECUTION SECURITY LIMITS",
    ),
    "callback": (
        "DATABASE SETTINGS",
        "CALLBACK SETTINGS",
        "LOGGING SETTINGS",
        "DB CONNECTION SETTINGS",
    ),
    "maintenance": (
        "DATABASE SETTINGS",
        "MAINTENANCE SETTINGS",
        "LOGGING SETTINGS",
        "DB CONNECTION SETTINGS",
    ),
    "migrate": ("DATABASE SETTINGS", "LOGGING SETTINGS"),
    "bootstrap": (
        "DATABASE SETTINGS",
        "BOOTSTRAP ADMIN SETTINGS",
        "LOGGING SETTINGS",
    ),
}

REQUIRED_OPTIONS: dict[str, tuple[str, ...]] = {
    "PROJECT BASIC SETTINGS": (
        "PROJECT_NAME",
        "PROJECT_VERSION",
        "PROJECT_DESCRIPTION",
        "ENABLE_AUTO_GENERATED_DOCS",
    ),
    "DATABASE SETTINGS": (
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    ),
    "RABBITMQ SETTINGS": (
        "RABBITMQ_HOST",
        "RABBITMQ_PORT",
        "RABBITMQ_USER",
        "RABBITMQ_PASSWORD",
    ),
    "BOOTSTRAP ADMIN SETTINGS": (
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD",
        "ADMIN_EMAIL",
        "ADMIN_NAME",
    ),
    "SECRET KEY SETTINGS": (
        "SECRET_KEY",
        "ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
    ),
    "WORKER SETTINGS": (
        "WORKER_POOL",
        "WORKER_CONCURRENCY",
        "WORKER_BOX_ID_OFFSET",
        "WORKER_HEARTBEAT_INTERVAL",
        "WORKER_STALE_THRESHOLD",
        "WORKER_LEASE_DURATION",
        "WORKER_LEASE_RENEWAL_INTERVAL",
        "WORKER_REDELIVERY_BACKOFF",
    ),
    "CALLBACK SETTINGS": (
        "CALLBACK_POLL_INTERVAL",
        "CALLBACK_BATCH_SIZE",
        "CALLBACK_CONCURRENCY",
        "CALLBACK_HTTP_TIMEOUT",
        "CALLBACK_MAX_ATTEMPTS",
        "CALLBACK_LEASE_DURATION",
        "CALLBACK_RETRY_DELAYS",
    ),
    "MAINTENANCE SETTINGS": (
        "SUBMISSION_RETENTION_DAYS",
        "MAINTENANCE_DELETE_BATCH_SIZE",
        "MAINTENANCE_MAX_BATCHES_PER_RUN",
        "MAINTENANCE_SUBMISSIONS_INTERVAL",
        "MAINTENANCE_API_TOKENS_INTERVAL",
    ),
    "BATCH SIZE AND CONCURENT SUBMISSIONS LIMITS": (
        "MAX_CONCURRENT_SUBMISSIONS",
        "MAX_BATCH_SIZE",
    ),
    "DB CONNECTION SETTINGS": ("DB_MAX_RETRIES", "DB_MAX_TIMEOUT"),
    "DEFAULT RESOURCE LIMITS": (
        "DEFAULT_TIME_LIMIT",
        "DEFAULT_MEMORY_LIMIT",
        "DEFAULT_EXTRA_TIME",
        "DEFAULT_WALL_TIME_LIMIT",
        "DEFAULT_STACK_SIZE",
        "DEFAULT_MAX_FILE_SIZE",
    ),
    "MAX RESOURCE LIMITS": (
        "MAX_TIME_LIMIT",
        "MAX_MEMORY_LIMIT",
        "MAX_EXTRA_TIME",
        "MAX_WALL_TIME_LIMIT",
        "MAX_STACK_SIZE",
        "MAX_FILE_SIZE",
    ),
    "EXECUTION SECURITY LIMITS": (
        "MAX_ADDITIONAL_ARCHIVE_BYTES",
        "MAX_ADDITIONAL_EXTRACTED_BYTES",
        "MAX_ADDITIONAL_FILES",
        "MAX_CAPTURED_OUTPUT_BYTES",
        "ISOLATE_CLEANUP_TIMEOUT",
    ),
    "OTHER SETTINGS": (
        "ALLOW_ENABLE_NETWORK",
        "ALWAYS_REDIRECT_STDERR_TO_STDOUT",
        "ALLOW_COMMAND_LINE_ARGS",
        "ALLOW_COMPILER_OPTIONS",
        "ALLOW_WAIT",
        "API_WAIT_TIMEOUT",
        "API_WAIT_POLL_INTERVAL",
        "PROTECTED_SOFTWARE_CONFIGURATION",
        "PROTECTED_HARDWARE_CONFIGURATION",
    ),
    "LOGGING SETTINGS": ("LOG_LEVEL", "SQL_LOG_LEVEL"),
}

PRESENT_OPTIONS: dict[str, tuple[str, ...]] = {
    "WORKER SETTINGS": ("WORKER_ID",),
    "CALLBACK SETTINGS": ("CALLBACK_WORKER_ID",),
    "LOGGING SETTINGS": ("SQL_LOG_FILE",),
}

_PLACEHOLDER_PREFIXES = ("change", "replace", "set_", "generate_")


def read_configuration(path: Path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if not parser.read(path, encoding="utf-8"):
        raise RuntimeError(f"Configuration file not found: {path}")
    return parser


def _required(parser: configparser.ConfigParser, section: str, option: str):
    if not parser.has_section(section) or not parser.has_option(section, option):
        raise RuntimeError(f"Missing configuration option [{section}] {option}")
    value = parser.get(section, option).strip()
    if not value:
        raise RuntimeError(f"Configuration option [{section}] {option} must not be empty")
    return value


def _secret(parser: configparser.ConfigParser, section: str, option: str, minimum: int):
    value = _required(parser, section, option)
    if len(value) < minimum:
        raise RuntimeError(
            f"Configuration option [{section}] {option} must contain at least {minimum} characters"
        )
    if value.lower().startswith(_PLACEHOLDER_PREFIXES):
        raise RuntimeError(f"Configuration option [{section}] {option} must be replaced")
    return value


def validate_role_configuration(parser: configparser.ConfigParser, role: str):
    try:
        sections = ROLE_SECTIONS[role]
    except KeyError as exc:
        raise RuntimeError(f"Unknown configuration role: {role}") from exc

    for section in sections:
        if not parser.has_section(section):
            raise RuntimeError(f"Missing configuration section [{section}] for role {role}")
        for option in REQUIRED_OPTIONS.get(section, ()):
            _required(parser, section, option)
        for option in PRESENT_OPTIONS.get(section, ()):
            if not parser.has_option(section, option):
                raise RuntimeError(f"Missing configuration option [{section}] {option}")

    if "DATABASE SETTINGS" in sections:
        _secret(parser, "DATABASE SETTINGS", "DATABASE_PASSWORD", 16)
        try:
            port = int(_required(parser, "DATABASE SETTINGS", "DATABASE_PORT"))
        except ValueError as exc:
            raise RuntimeError("DATABASE_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise RuntimeError("DATABASE_PORT must be between 1 and 65535")

    if "RABBITMQ SETTINGS" in sections:
        _secret(parser, "RABBITMQ SETTINGS", "RABBITMQ_PASSWORD", 16)
        try:
            port = int(_required(parser, "RABBITMQ SETTINGS", "RABBITMQ_PORT"))
        except ValueError as exc:
            raise RuntimeError("RABBITMQ_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise RuntimeError("RABBITMQ_PORT must be between 1 and 65535")

    if "SECRET KEY SETTINGS" in sections:
        _secret(parser, "SECRET KEY SETTINGS", "SECRET_KEY", 32)

    if "BOOTSTRAP ADMIN SETTINGS" in sections:
        username = _required(parser, "BOOTSTRAP ADMIN SETTINGS", "ADMIN_USERNAME")
        if username.lower() == "admin":
            raise RuntimeError("ADMIN_USERNAME must not use the default 'admin' value")
        _secret(parser, "BOOTSTRAP ADMIN SETTINGS", "ADMIN_PASSWORD", 16)


def validate_source_configuration(parser: configparser.ConfigParser):
    for role in ROLE_SECTIONS:
        validate_role_configuration(parser, role)

    passwords = (
        parser.get("DATABASE SETTINGS", "DATABASE_PASSWORD").strip(),
        parser.get("RABBITMQ SETTINGS", "RABBITMQ_PASSWORD").strip(),
        parser.get("BOOTSTRAP ADMIN SETTINGS", "ADMIN_PASSWORD").strip(),
    )
    if len(passwords) != len(set(passwords)):
        raise RuntimeError("Database, RabbitMQ and administrator passwords must be different")


def role_configuration(
    source: configparser.ConfigParser, role: str
):
    result = configparser.ConfigParser(interpolation=None)
    result.optionxform = str
    for section in ROLE_SECTIONS[role]:
        result.add_section(section)
        for option, value in source.items(section):
            result.set(section, option, value)
    return result


def _render_ini(parser: configparser.ConfigParser):
    from io import StringIO

    output = StringIO()
    parser.write(output)
    return output.getvalue()


def _shell_value(value: str):
    return shlex.quote(value)


def infrastructure_scripts(source: configparser.ConfigParser):
    database = source["DATABASE SETTINGS"]
    rabbitmq = source["RABBITMQ SETTINGS"]
    return {
        "postgres": {
            "entrypoint.sh": "\n".join(
                (
                    "#!/bin/sh",
                    "set -eu",
                    f"export POSTGRES_USER={_shell_value(database['DATABASE_USER'])}",
                    f"export POSTGRES_PASSWORD={_shell_value(database['DATABASE_PASSWORD'])}",
                    f"export POSTGRES_DB={_shell_value(database['DATABASE_NAME'])}",
                    f"export PGPORT={_shell_value(database['DATABASE_PORT'])}",
                    'if [ "$#" -eq 0 ]; then set -- postgres; fi',
                    f'if [ "$1" = postgres ]; then set -- "$@" -p {_shell_value(database["DATABASE_PORT"])}; fi',
                    'exec /usr/local/bin/docker-entrypoint.sh "$@"',
                    "",
                )
            ),
            "healthcheck.sh": "\n".join(
                (
                    "#!/bin/sh",
                    "set -eu",
                    "exec pg_isready"
                    f" -U {_shell_value(database['DATABASE_USER'])}"
                    f" -d {_shell_value(database['DATABASE_NAME'])}"
                    f" -p {_shell_value(database['DATABASE_PORT'])}",
                    "",
                )
            ),
        },
        "rabbitmq": {
            "entrypoint.sh": "\n".join(
                (
                    "#!/bin/sh",
                    "set -eu",
                    f"export RABBITMQ_DEFAULT_USER={_shell_value(rabbitmq['RABBITMQ_USER'])}",
                    f"export RABBITMQ_DEFAULT_PASS={_shell_value(rabbitmq['RABBITMQ_PASSWORD'])}",
                    f"export RABBITMQ_NODE_PORT={_shell_value(rabbitmq['RABBITMQ_PORT'])}",
                    'if [ "$#" -eq 0 ]; then set -- rabbitmq-server; fi',
                    'exec /usr/local/bin/docker-entrypoint.sh "$@"',
                    "",
                )
            )
        },
    }


def _atomic_write(path: Path, content: str, mode: int):
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.chmod(mode)
    temporary.replace(path)


def distribute(source_path: Path = SOURCE_PATH, output_root: Path = OUTPUT_ROOT):
    source = read_configuration(source_path)
    validate_source_configuration(source)

    generated = {
        role: {"execengine.ini": _render_ini(role_configuration(source, role))}
        for role in ROLE_SECTIONS
    }
    generated.update(infrastructure_scripts(source))

    os.umask(0o077)
    for role, files in generated.items():
        role_directory = output_root / role
        if not role_directory.is_dir():
            raise RuntimeError(f"Configuration output volume is not mounted: {role_directory}")
        for name, content in files.items():
            mode = 0o555 if name.endswith(".sh") else 0o444
            _atomic_write(role_directory / name, content, mode)


def main():
    distribute()
    print("ExecEngine role configurations were generated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
