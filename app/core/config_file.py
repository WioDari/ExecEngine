from __future__ import annotations

import configparser
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME_INI_FILE_PATH = Path("/run/execengine/execengine.ini")
PROJECT_INI_FILE_PATH = PROJECT_ROOT / "execengine.ini"


def configuration_path():
    if RUNTIME_INI_FILE_PATH.is_file():
        return RUNTIME_INI_FILE_PATH
    return PROJECT_INI_FILE_PATH


def parse_ini_value(value: str):
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


@lru_cache(maxsize=4)
def read_ini(path: str):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if not parser.read(path, encoding="utf-8"):
        raise RuntimeError(f"Configuration file not found: {path}")
    return parser


def load_ini():
    return read_ini(str(configuration_path()))


def ini_value(section: str, key: str):
    parser = load_ini()
    try:
        return parse_ini_value(parser[section][key])
    except KeyError as exc:
        raise RuntimeError(f"Missing configuration option [{section}] {key}") from exc
