#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from compilers.parse_properties import generate_languages, parse_properties, write_languages
except ModuleNotFoundError:
    from parse_properties import generate_languages, parse_properties, write_languages


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPILERS_ROOT = PROJECT_ROOT / "compilers"
DOCKERFILE = COMPILERS_ROOT / "Dockerfile"
TESTS_DIR = COMPILERS_ROOT / "tests"
REGISTRY_PATH = PROJECT_ROOT / "config" / "language_registry.json"
OUTPUT_PATH = PROJECT_ROOT / "config" / "languages.json"

ALLOWED_POOLS = frozenset({"full", "native", "script", "jvm", "dotnet", "heavy", "utility"})
REQUIRED_REGISTRY_FIELDS = frozenset({"id", "slug", "config", "version", "pool", "enabled"})
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

LEGACY_SLUG_BY_ID = {
    1: "assembly-nasm-2-16",
    2: "bash-5-3",
    3: "basic-fbc-1-10",
    4: "c-gcc-14",
    5: "csharp-dotnet-8",
    6: "cpp-gcc-14",
    7: "d-dmd-2",
    8: "dart-3",
    9: "fsharp-dotnet-8",
    10: "fortran-gcc-14",
    11: "go-1-24",
    12: "haskell-ghc-9",
    13: "java-openjdk-22",
    14: "javascript-node-21",
    15: "kotlin-2",
    16: "lua-5-4",
    17: "ocaml-5",
    18: "objective-c-gcc-14",
    19: "octave-10",
    20: "php-8-4",
    21: "pascal-fpc-3",
    22: "perl-5",
    23: "prolog-gnu-1",
    24: "pypy-2-7",
    25: "pypy-3-11",
    26: "python-2-7",
    27: "python-3-13",
    28: "r-4-5",
    29: "ruby-3-4",
    30: "rust-1-88",
    31: "sqlite-3-50",
    32: "scala-3",
    33: "swift-6",
    34: "text",
    35: "typescript-5",
    36: "visual-basic-dotnet-8",
    37: "c-clang-21",
    38: "cpp-clang-21",
    39: "executable",
    40: "csharp-mono-6",
    41: "pascalabc-mono-3",
}

VERSION_MAP = {
    "GCC_VERSIONS": ("gcc", "g++", "fortran", "objective-c"),
    "PYTHON_VERSIONS": ("python",),
    "PYPY_PYTHON_VERSIONS": ("pypy",),
    "NASM_VERSIONS": ("nasm",),
    "PHP_VERSIONS": ("php",),
    "BASH_VERSIONS": ("bash",),
    "JAVA_VERSIONS": ("java",),
    "RUBY_VERSIONS": ("ruby",),
    "NODE_VERSIONS": ("node",),
    "PASCAL_VERSIONS": ("fpc",),
    "DART_VERSIONS": ("dart",),
    "GO_VERSIONS": ("go",),
    "RUST_VERSIONS": ("rust",),
    "KOTLIN_VERSIONS": ("kotlin",),
    "SWIFT_VERSIONS": ("swift",),
    "DOTNET_VERSIONS": ("csharp", "fsharp", "vbnet"),
    "R_VERSIONS": ("r",),
    "SCALA_VERSIONS": ("scala",),
    "D_VERSIONS": ("d",),
    "FBC_VERSIONS": ("fbc",),
    "LUA_VERSIONS": ("lua",),
    "HASKELL_VERSIONS": ("haskell",),
    "SQLITE_VERSION": ("sqlite",),
    "PROLOG_VERSIONS": ("prolog",),
    "OCAML_VERSIONS": ("ocaml",),
    "OCTAVE_VERSIONS": ("octave",),
    "TYPESCRIPT_VERSIONS": ("typescript",),
    "CLANG_VERSIONS": ("clang", "clang++"),
    "MONO_VERSIONS": ("csharp-mono",),
    "PASCALABC_VERSION": ("pascalabc",),
}

COMPILED_CONFIGS = {
    "nasm", "fbc", "clang", "clang++", "gcc", "g++", "fortran",
    "objective-c", "csharp", "csharp-mono", "fsharp", "vbnet", "d",
    "dart", "fpc", "go", "haskell", "java", "kotlin", "ocaml",
    "pascalabc", "prolog", "rust", "scala", "swift", "typescript",
}


def parse_envs(text: str):
    envs: dict[str, list[str]] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("ENV "):
            body = line[4:]
            while body.rstrip().endswith("\\"):
                body = body.rstrip()[:-1] + " "
                index += 1
                body += lines[index].strip()
            parts = body.split()
            if len(parts) >= 2:
                envs[parts[0]] = parts[1:]
        index += 1
    return envs


def load_registry(errors: list[str]):
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot read language registry: {exc}")
        return []
    if not isinstance(registry, list):
        errors.append("Language registry must be a JSON array")
        return []
    return registry


def load_configs(errors: list[str]):
    configs: dict[str, dict[str, str]] = {}
    for path in TESTS_DIR.glob("*/properties"):
        if (path.parent / ".skip").exists():
            continue
        try:
            configs[path.parent.name] = parse_properties(path)
        except OSError as exc:
            errors.append(f"Cannot read {path}: {exc}")
    return configs


def validate_properties(configs: dict[str, dict[str, str]], errors: list[str]):
    required_keys = {
        "NAME", "VERSIONS", "SOURCE_FILE", "COMPILED_FILE", "COMPILE_CMD", "RUN_CMD"
    }
    for name, props in sorted(configs.items()):
        missing = required_keys - props.keys()
        if missing:
            errors.append(f"{name}: missing properties: {', '.join(sorted(missing))}")
            continue

        source = props["SOURCE_FILE"]
        if source and "$" not in source and not (TESTS_DIR / name / source).is_file():
            errors.append(f"{name}: test source does not exist: {source}")

        command_text = props["RUN_CMD"] + " " + props["COMPILE_CMD"]
        if re.search(r"(?<!\$)SOURCE_FILE", command_text):
            errors.append(f"{name}: literal SOURCE_FILE found; expected $SOURCE_FILE")

        if name in COMPILED_CONFIGS:
            if not props["COMPILE_CMD"]:
                errors.append(f"{name}: compiled language has empty COMPILE_CMD")
            elif "$args" not in props["COMPILE_CMD"]:
                errors.append(f"{name}: COMPILE_CMD has no $args placeholder")


def validate_docker_versions(
    configs: dict[str, dict[str, str]],
    docker_envs: dict[str, list[str]],
    errors: list[str],
):
    for env_name, config_names in VERSION_MAP.items():
        expected = docker_envs.get(env_name)
        if not expected:
            errors.append(f"Dockerfile: missing ENV {env_name}")
            continue
        for config_name in config_names:
            props = configs.get(config_name)
            if props is None:
                errors.append(f"Missing configuration directory: tests/{config_name}")
                continue
            actual = props.get("VERSIONS", "").split()
            if actual != expected:
                errors.append(
                    f"{config_name}: VERSIONS={actual!r}, Dockerfile {env_name}={expected!r}"
                )

    mono_versions = docker_envs.get("MONO_VERSIONS", [])
    if mono_versions:
        mono_path = f"/usr/local/mono-{mono_versions[0]}/bin/mono"
        pascalabc = configs.get("pascalabc", {})
        if mono_path not in pascalabc.get("COMPILE_CMD", ""):
            errors.append("pascalabc: COMPILE_CMD does not use the configured Mono version")
        if mono_path not in pascalabc.get("RUN_CMD", ""):
            errors.append("pascalabc: RUN_CMD does not use the configured Mono version")


def validate_registry(
    registry: list[dict[str, Any]],
    configs: dict[str, dict[str, str]],
    errors: list[str],
):
    seen_ids: set[int] = set()
    seen_slugs: set[str] = set()
    registry_variants: set[tuple[str, str]] = set()
    id_to_slug: dict[int, str] = {}

    for index, entry in enumerate(registry):
        label = f"registry entry #{index + 1}"
        if not isinstance(entry, dict):
            errors.append(f"{label}: expected an object")
            continue

        missing = REQUIRED_REGISTRY_FIELDS - entry.keys()
        if missing:
            errors.append(f"{label}: missing fields: {', '.join(sorted(missing))}")
            continue

        language_id = entry["id"]
        slug = entry["slug"]
        config_name = entry["config"]
        version = entry["version"]
        pool = entry["pool"]
        enabled = entry["enabled"]

        if type(language_id) is not int or language_id <= 0:
            errors.append(f"{label}: id must be a positive integer")
        elif language_id in seen_ids:
            errors.append(f"{label}: duplicate id {language_id}")
        else:
            seen_ids.add(language_id)
            if isinstance(slug, str):
                id_to_slug[language_id] = slug

        if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
            errors.append(f"{label}: invalid slug {slug!r}")
        elif slug in seen_slugs:
            errors.append(f"{label}: duplicate slug {slug!r}")
        else:
            seen_slugs.add(slug)

        if not isinstance(config_name, str) or config_name not in configs:
            errors.append(f"{label}: unknown config {config_name!r}")
            continue
        if not isinstance(version, str) or version not in configs[config_name].get("VERSIONS", "").split():
            errors.append(f"{label}: version {version!r} is not declared by config {config_name!r}")
        else:
            variant = (config_name, version)
            if variant in registry_variants:
                errors.append(f"{label}: duplicate runtime variant {config_name}@{version}")
            registry_variants.add(variant)

        if pool not in ALLOWED_POOLS:
            errors.append(f"{label}: pool {pool!r} is not in {sorted(ALLOWED_POOLS)!r}")
        if type(enabled) is not bool:
            errors.append(f"{label}: enabled must be a boolean")

    for language_id, expected_slug in LEGACY_SLUG_BY_ID.items():
        actual_slug = id_to_slug.get(language_id)
        if actual_slug != expected_slug:
            errors.append(
                f"public language id {language_id} must remain {expected_slug!r}, got {actual_slug!r}"
            )

    config_variants = {
        (config_name, version)
        for config_name, props in configs.items()
        for version in props.get("VERSIONS", "").split()
    }
    for config_name, version in sorted(config_variants - registry_variants):
        errors.append(f"Runtime variant has no registry entry: {config_name}@{version}")
    for config_name, version in sorted(registry_variants - config_variants):
        errors.append(f"Registry variant has no properties entry: {config_name}@{version}")


def validate_generated_languages(languages: list[dict[str, Any]], errors: list[str]):
    unresolved = re.compile(r"\$(VERSION|SOURCE_FILE|COMPILED_FILE)")
    for language in languages:
        for field in ("NAME", "SOURCE_FILE", "COMPILED_FILE", "COMPILE_CMD", "RUN_CMD"):
            value = language.get(field) or ""
            if unresolved.search(value):
                errors.append(
                    f"{language['slug']}: unresolved placeholder in {field}: {value}"
                )


def validate_and_generate():
    errors: list[str] = []
    registry = load_registry(errors)
    configs = load_configs(errors)
    docker_envs = parse_envs(DOCKERFILE.read_text(encoding="utf-8"))

    validate_properties(configs, errors)
    validate_docker_versions(configs, docker_envs, errors)
    validate_registry(registry, configs, errors)

    languages: list[dict[str, Any]] = []
    if not errors:
        try:
            languages = generate_languages(REGISTRY_PATH, TESTS_DIR)
        except (KeyError, OSError, TypeError, ValueError) as exc:
            errors.append(f"Cannot generate language manifest: {exc}")
        else:
            validate_generated_languages(languages, errors)

    if not errors:
        write_languages(languages, OUTPUT_PATH)
    return errors, languages


def main():
    errors, languages = validate_and_generate()
    if errors:
        print("Configuration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(languages)} registered runtime variants; generated {OUTPUT_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
