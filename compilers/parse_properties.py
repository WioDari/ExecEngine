#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = PROJECT_ROOT / "compilers" / "tests"
REGISTRY_PATH = PROJECT_ROOT / "config" / "language_registry.json"
OUTPUT_PATH = PROJECT_ROOT / "config" / "languages.json"


def parse_properties(filepath: Path):
    props: dict[str, str] = {}
    for raw_line in filepath.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value.strip().strip('"')
    return props


def load_registry(registry_path: Path = REGISTRY_PATH):
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, list):
        raise ValueError("Language registry must be a JSON array")
    return registry


def expand_version_syntax(version: str, value: str):
    major = version.split(".", 1)[0]
    return value.replace("${VERSION%%.*}", major).replace("$VERSION", version)


def expand_property(value: str, version: str, source_file: str, compiled_file: str):
    expanded = expand_version_syntax(version, value)
    expanded = expanded.replace("$SOURCE_FILE", source_file)
    expanded = expanded.replace("$COMPILED_FILE", compiled_file)
    return expanded


def build_language(
    registry_entry: dict[str, Any],
    tests_dir: Path = TESTS_DIR,
):
    config_name = registry_entry["config"]
    version = registry_entry["version"]
    properties_path = tests_dir / config_name / "properties"
    if not properties_path.is_file():
        raise ValueError(f"Properties file not found for registry config: {config_name}")

    props = parse_properties(properties_path)
    versions = props.get("VERSIONS", "").split()
    if version not in versions:
        raise ValueError(
            f"Registry version {version!r} is not declared by {config_name}: {versions!r}"
        )

    source_file = expand_version_syntax(version, props.get("SOURCE_FILE", ""))
    compiled_file = expand_version_syntax(version, props.get("COMPILED_FILE", ""))
    compile_template = props.get("COMPILE_CMD", "").strip()
    run_template = props.get("RUN_CMD", "").strip()

    return {
        "NAME": expand_version_syntax(version, props.get("NAME", "")),
        "VERSION": version,
        "SOURCE_FILE": source_file,
        "COMPILED_FILE": compiled_file or None,
        "COMPILE_CMD": (
            expand_property(compile_template, version, source_file, compiled_file)
            if compile_template
            else None
        ),
        "RUN_CMD": expand_property(run_template, version, source_file, compiled_file),
        "id": registry_entry["id"],
        "slug": registry_entry["slug"],
        "pool": registry_entry["pool"],
        "enabled": registry_entry["enabled"],
    }


def generate_languages(
    registry_path: Path = REGISTRY_PATH,
    tests_dir: Path = TESTS_DIR,
):
    registry = load_registry(registry_path)
    languages = [build_language(entry, tests_dir) for entry in registry]
    return sorted(languages, key=lambda language: language["id"])


def write_languages(
    languages: list[dict[str, Any]],
    output_path: Path = OUTPUT_PATH,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(languages, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(rendered, encoding="utf-8")


def main():
    languages = generate_languages()
    write_languages(languages)
    print(f"Success: {len(languages)} language versions written to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
