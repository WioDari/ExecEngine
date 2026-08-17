from __future__ import annotations

import base64
import binascii
import io
import os
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

from app.execution.errors import ExecutionConfigurationError, TransientExecutionError

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")

def decode_base64(value: str, field_name: str, *, max_bytes: int | None = None):
    if not isinstance(value, str):
        raise ExecutionConfigurationError(f"{field_name} must be Base64 text")
    if max_bytes is not None:
        max_encoded_length = 4 * ((max_bytes + 2) // 3)
        if len(value) > max_encoded_length:
            raise ExecutionConfigurationError(f"{field_name} exceeds the size limit")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ExecutionConfigurationError(f"{field_name} is not valid Base64") from exc
    if max_bytes is not None and len(decoded) > max_bytes:
        raise ExecutionConfigurationError(f"{field_name} exceeds the size limit")
    return decoded

def decode_base64_text(
    value: str,
    field_name: str,
    *,
    max_bytes: int | None = None,
):
    try:
        return decode_base64(value, field_name, max_bytes=max_bytes).decode(
            "utf-8", errors="strict"
        )
    except UnicodeDecodeError as exc:
        raise ExecutionConfigurationError(f"{field_name} is not valid UTF-8") from exc

def safe_sandbox_path(root: Path, relative_name: str):
    if not isinstance(relative_name, str) or not relative_name or "\x00" in relative_name:
        raise ExecutionConfigurationError("Sandbox file name is invalid")
    normalized = relative_name.replace("\\", "/")
    if normalized.startswith("/") or _WINDOWS_DRIVE.match(normalized):
        raise ExecutionConfigurationError("Absolute sandbox paths are not allowed")
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ExecutionConfigurationError("Sandbox path traversal is not allowed")

    root_resolved = root.resolve(strict=False)
    destination = root.joinpath(*parts).resolve(strict=False)
    try:
        common = os.path.commonpath((str(root_resolved), str(destination)))
    except ValueError as exc:
        raise ExecutionConfigurationError("Sandbox path is outside the sandbox") from exc
    if common != str(root_resolved):
        raise ExecutionConfigurationError("Sandbox path is outside the sandbox")
    return destination

def write_text_file(root: Path, relative_name: str, contents: str):
    destination = safe_sandbox_path(root, relative_name)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(contents, encoding="utf-8", errors="strict")
        destination.chmod(0o600)
    except OSError as exc:
        raise TransientExecutionError(f"Failed to write sandbox file {relative_name}") from exc
    return destination

def read_text_file(path: Path, *, max_bytes: int):
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    try:
        if not path.is_file():
            return ""
        with path.open("rb") as stream:
            data = stream.read(max_bytes + 1)
    except OSError as exc:
        raise TransientExecutionError(f"Failed to read sandbox output {path.name}") from exc
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="replace")

def _zip_entry_mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0xFFFF

def _validate_zip_entry(info: zipfile.ZipInfo):
    mode = _zip_entry_mode(info)
    file_type = stat.S_IFMT(mode)
    if file_type == stat.S_IFLNK:
        raise ExecutionConfigurationError("additional_files must not contain symbolic links")
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ExecutionConfigurationError("additional_files contains a special file")

def extract_additional_files(
    encoded_archive: str,
    destination: Path,
    *,
    max_archive_bytes: int,
    max_extracted_bytes: int,
    max_files: int,
    reserved_paths: frozenset[str] = frozenset(),
):
    max_encoded_length = 4 * ((max_archive_bytes + 2) // 3)
    if len(encoded_archive) > max_encoded_length:
        raise ExecutionConfigurationError("additional_files archive exceeds the size limit")
    archive_bytes = decode_base64(
        encoded_archive,
        "additional_files",
        max_bytes=max_archive_bytes,
    )
    if len(archive_bytes) > max_archive_bytes:
        raise ExecutionConfigurationError("additional_files archive exceeds the size limit")

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ExecutionConfigurationError("additional_files is not a valid ZIP archive") from exc

    with archive:
        entries = archive.infolist()
        file_entries = [entry for entry in entries if not entry.is_dir()]
        if len(file_entries) > max_files:
            raise ExecutionConfigurationError("additional_files contains too many files")
        total_size = sum(entry.file_size for entry in file_entries)
        if total_size > max_extracted_bytes:
            raise ExecutionConfigurationError(
                "additional_files extracted contents exceed the size limit"
            )

        validated_entries = []
        file_paths: set[tuple[str, ...]] = set()
        all_paths: set[tuple[str, ...]] = set()
        normalized_reserved = {
            tuple(PurePosixPath(path.replace("\\", "/")).parts)
            for path in reserved_paths
        }
        for entry in entries:
            _validate_zip_entry(entry)
            target = safe_sandbox_path(destination, entry.filename)
            relative_parts = target.relative_to(destination.resolve(strict=False)).parts
            if relative_parts in all_paths:
                raise ExecutionConfigurationError(
                    f"additional_files contains duplicate path: {entry.filename}"
                )
            if relative_parts in normalized_reserved or any(
                (
                    len(relative_parts) > len(reserved)
                    and relative_parts[: len(reserved)] == reserved
                )
                or (
                    not entry.is_dir()
                    and len(reserved) > len(relative_parts)
                    and reserved[: len(relative_parts)] == relative_parts
                )
                for reserved in normalized_reserved
            ):
                raise ExecutionConfigurationError(
                    f"additional_files uses reserved path: {entry.filename}"
                )
            if any(relative_parts[:length] in file_paths for length in range(1, len(relative_parts))):
                raise ExecutionConfigurationError(
                    f"additional_files contains conflicting path: {entry.filename}"
                )
            if not entry.is_dir() and any(
                len(existing) > len(relative_parts)
                and existing[: len(relative_parts)] == relative_parts
                for existing in all_paths
            ):
                raise ExecutionConfigurationError(
                    f"additional_files contains conflicting path: {entry.filename}"
                )
            all_paths.add(relative_parts)
            if not entry.is_dir():
                file_paths.add(relative_parts)
            validated_entries.append((entry, target))

        total_written = 0
        for entry, target in validated_entries:
            try:
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    target.chmod(0o700)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with archive.open(entry, "r") as source, target.open("xb") as output:
                    while True:
                        chunk = source.read(64 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        total_written += len(chunk)
                        if (
                            written > entry.file_size
                            or total_written > max_extracted_bytes
                        ):
                            raise ExecutionConfigurationError(
                                "additional_files entry exceeds its declared size"
                            )
                        output.write(chunk)
                executable = bool(_zip_entry_mode(entry) & 0o111)
                target.chmod(0o700 if executable else 0o600)
            except (RuntimeError, NotImplementedError, zipfile.BadZipFile, EOFError) as exc:
                raise ExecutionConfigurationError(
                    f"additional_files entry cannot be decoded: {entry.filename}"
                ) from exc
            except FileExistsError as exc:
                raise ExecutionConfigurationError(
                    f"additional_files conflicts with sandbox path: {entry.filename}"
                ) from exc
            except OSError as exc:
                raise TransientExecutionError(
                    f"Failed to extract additional file {entry.filename}"
                ) from exc
