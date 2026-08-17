from __future__ import annotations

from dataclasses import dataclass

from app.core.config_file import ini_value


@dataclass(frozen=True)
class ExecutionSettings:
    max_time_limit: int
    max_memory_limit: int
    max_wall_time_limit: int
    max_file_size: int
    max_additional_archive_bytes: int
    max_additional_extracted_bytes: int
    max_additional_files: int
    max_captured_output_bytes: int
    isolate_cleanup_timeout: float

    @classmethod
    def from_ini(cls) -> "ExecutionSettings":
        return cls(
            max_time_limit=int(ini_value("MAX RESOURCE LIMITS", "MAX_TIME_LIMIT")),
            max_memory_limit=int(ini_value("MAX RESOURCE LIMITS", "MAX_MEMORY_LIMIT")),
            max_wall_time_limit=int(
                ini_value("MAX RESOURCE LIMITS", "MAX_WALL_TIME_LIMIT")
            ),
            max_file_size=int(ini_value("MAX RESOURCE LIMITS", "MAX_FILE_SIZE")),
            max_additional_archive_bytes=int(
                ini_value("EXECUTION SECURITY LIMITS", "MAX_ADDITIONAL_ARCHIVE_BYTES")
            ),
            max_additional_extracted_bytes=int(
                ini_value("EXECUTION SECURITY LIMITS", "MAX_ADDITIONAL_EXTRACTED_BYTES")
            ),
            max_additional_files=int(
                ini_value("EXECUTION SECURITY LIMITS", "MAX_ADDITIONAL_FILES")
            ),
            max_captured_output_bytes=int(
                ini_value("EXECUTION SECURITY LIMITS", "MAX_CAPTURED_OUTPUT_BYTES")
            ),
            isolate_cleanup_timeout=float(
                ini_value("EXECUTION SECURITY LIMITS", "ISOLATE_CLEANUP_TIMEOUT")
            ),
        )


execution_settings = ExecutionSettings.from_ini()
