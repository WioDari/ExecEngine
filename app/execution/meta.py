from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from app.execution.errors import TransientExecutionError

@dataclass(frozen=True)
class IsolateMeta:
    time: float | None = None
    wall_time: float | None = None
    max_rss: int | None = None
    cg_memory: int | None = None
    exit_code: int | None = None
    exit_signal: int | None = None
    status: str | None = None

    @property
    def memory(self):
        values = [value for value in (self.max_rss, self.cg_memory) if value is not None]
        return min(values) if values else 0

def _non_negative_float(value: str, key: str):
    try:
        parsed = float(value)
    except ValueError as exc:
        raise TransientExecutionError(f"Invalid isolate meta value for {key}") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise TransientExecutionError(f"Negative isolate meta value for {key}")
    return parsed

def _non_negative_int(value: str, key: str):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise TransientExecutionError(f"Invalid isolate meta value for {key}") from exc
    if parsed < 0:
        raise TransientExecutionError(f"Negative isolate meta value for {key}")
    return parsed

def parse_isolate_meta(text: str):
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise TransientExecutionError("Malformed isolate meta output")
        key = key.strip()
        if key in values:
            raise TransientExecutionError(f"Duplicate isolate meta key: {key}")
        values[key] = value.strip()

    return IsolateMeta(
        time=_non_negative_float(values["time"], "time") if "time" in values else None,
        wall_time=(
            _non_negative_float(values["time-wall"], "time-wall")
            if "time-wall" in values
            else None
        ),
        max_rss=(
            _non_negative_int(values["max-rss"], "max-rss")
            if "max-rss" in values
            else None
        ),
        cg_memory=(
            _non_negative_int(values["cg-mem"], "cg-mem")
            if "cg-mem" in values
            else None
        ),
        exit_code=(
            _non_negative_int(values["exitcode"], "exitcode")
            if "exitcode" in values
            else None
        ),
        exit_signal=(
            _non_negative_int(values["exitsig"], "exitsig")
            if "exitsig" in values
            else None
        ),
        status=values.get("status"),
    )

def read_isolate_meta(path: Path, *, required: bool = False):
    try:
        if not path.is_file():
            if required:
                raise TransientExecutionError("isolate did not create its meta file")
            return IsolateMeta()
        return parse_isolate_meta(path.read_text(encoding="utf-8", errors="strict"))
    except UnicodeError as exc:
        raise TransientExecutionError("isolate meta file is not valid UTF-8") from exc
    except OSError as exc:
        raise TransientExecutionError("Failed to read isolate meta file") from exc
