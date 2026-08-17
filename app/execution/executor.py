from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime
from hmac import compare_digest
from pathlib import Path
from time import monotonic

from app.core.execution_config import ExecutionSettings, execution_settings
from app.execution.box_pool import BoxPool
from app.execution.errors import ExecutionConfigurationError
from app.execution.files import (
    decode_base64_text,
    extract_additional_files,
    read_text_file,
    safe_sandbox_path,
    write_text_file,
)
from app.execution.isolate import IsolateRunOptions, IsolateRunner
from app.execution.meta import IsolateMeta, read_isolate_meta

logger = logging.getLogger(__name__)

ACCEPTED_STATUS_ID = 3
WRONG_ANSWER_STATUS_ID = 4
TIME_LIMIT_STATUS_ID = 5
MEMORY_LIMIT_STATUS_ID = 6
COMPILATION_ERROR_STATUS_ID = 7
RUNTIME_ERROR_STATUS_ID = 8
INTERNAL_ERROR_STATUS_ID = 9

@dataclass(frozen=True)
class LanguageRuntime:
    slug: str
    enabled: bool
    source_file: str
    compile_cmd: str | None
    run_cmd: str

@dataclass(frozen=True)
class ExecutionRequest:
    token: str
    language: LanguageRuntime
    source_code: str
    stdin: str | None
    expected_output: str | None
    compiler_options: str | None
    command_line_args: str | None
    additional_files: str | None
    time_limit: float
    extra_time: float
    wall_time_limit: float
    memory_limit_kb: int
    stack_size_limit_kb: int
    file_size_limit_kb: int
    redirect_stderr_to_stdout: bool
    enable_network: bool

@dataclass(frozen=True)
class ExecutionResult:
    status_id: int
    stdout: str | None = None
    stderr: str | None = None
    compile_output: str | None = None
    time: float = 0.0
    wall_time: float = 0.0
    memory: int = 0
    exit_code: int | None = None
    exit_signal: int | None = None
    finished_at: datetime | None = None

    @classmethod
    def internal_error(cls, diagnostic: str) -> "ExecutionResult":
        return cls(
            status_id=INTERNAL_ERROR_STATUS_ID,
            stderr=diagnostic,
            finished_at=datetime.utcnow(),
        )

def _optional_base64_text(
    value: str | None,
    field_name: str,
    *,
    max_bytes: int | None = None,
):
    return (
        decode_base64_text(value, field_name, max_bytes=max_bytes)
        if value is not None
        else None
    )

def _positive_number(value, field_name: str, *, allow_zero: bool = False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ExecutionConfigurationError(f"{field_name} must be {qualifier}")
    minimum_ok = value >= 0 if allow_zero else value > 0
    if not minimum_ok:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ExecutionConfigurationError(f"{field_name} must be {qualifier}")
    return value

def build_execution_request(submission, language):
    if language is None:
        raise ExecutionConfigurationError("Language runtime is missing")
    if not language.enabled:
        raise ExecutionConfigurationError("Language runtime is disabled")
    if not language.run_cmd or not language.source_file or not language.slug:
        raise ExecutionConfigurationError("Language runtime manifest is incomplete")

    file_size_limit_kb = int(
        _positive_number(submission.max_file_size, "max_file_size")
    )
    request_file_limit = file_size_limit_kb * 1024

    return ExecutionRequest(
        token=str(submission.token),
        language=LanguageRuntime(
            slug=str(language.slug),
            enabled=bool(language.enabled),
            source_file=str(language.source_file),
            compile_cmd=str(language.compile_cmd) if language.compile_cmd else None,
            run_cmd=str(language.run_cmd),
        ),
        source_code=decode_base64_text(
            submission.source_code,
            "source_code",
            max_bytes=request_file_limit,
        ),
        stdin=_optional_base64_text(
            submission.stdin,
            "stdin",
            max_bytes=request_file_limit,
        ),
        expected_output=_optional_base64_text(
            submission.expected_output,
            "expected_output",
            max_bytes=request_file_limit,
        ),
        compiler_options=_optional_base64_text(
            submission.compiler_options, "compiler_options"
        ),
        command_line_args=_optional_base64_text(
            submission.command_line_args, "command_line_args"
        ),
        additional_files=submission.additional_files,
        time_limit=float(_positive_number(submission.time_limit, "time_limit")),
        extra_time=float(
            _positive_number(submission.extra_time, "extra_time", allow_zero=True)
        ),
        wall_time_limit=float(
            _positive_number(submission.wall_time_limit, "wall_time_limit")
        ),
        memory_limit_kb=int(
            _positive_number(submission.memory_limit, "memory_limit")
        ),
        stack_size_limit_kb=int(
            _positive_number(submission.stack_size, "stack_size")
        ),
        file_size_limit_kb=file_size_limit_kb,
        redirect_stderr_to_stdout=bool(submission.redirect_stderr_to_stdout),
        enable_network=bool(submission.enable_network),
    )

def _runtime_command(command: str, user_arguments: str | None, *, replace_args: bool):
    normalized = command.replace("?/", "")
    if replace_args:
        return normalized.replace("$args", user_arguments or "")
    if user_arguments:
        return f"{normalized} {user_arguments}"
    return normalized

def _normalize_output(value: str):
    return "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").split("\n")).rstrip().strip()

def _matches_expected(actual: str, expected: str):
    return compare_digest(_normalize_output(actual), _normalize_output(expected))

def _result_status(completed_returncode: int, meta: IsolateMeta, request: ExecutionRequest, stdout: str):
    if meta.status == "TO":
        return TIME_LIMIT_STATUS_ID
    if meta.status in {"ML", "MO"}:
        return MEMORY_LIMIT_STATUS_ID
    if meta.status == "XX":
        return INTERNAL_ERROR_STATUS_ID
    program_failed = (
        completed_returncode != 0
        or meta.exit_code not in {None, 0}
        or meta.exit_signal not in {None, 0}
    )
    if program_failed:
        if meta.memory >= request.memory_limit_kb:
            return MEMORY_LIMIT_STATUS_ID
        return RUNTIME_ERROR_STATUS_ID
    if request.expected_output is not None:
        return (
            ACCEPTED_STATUS_ID
            if _matches_expected(stdout, request.expected_output)
            else WRONG_ANSWER_STATUS_ID
        )
    return ACCEPTED_STATUS_ID if stdout == "" else WRONG_ANSWER_STATUS_ID

def _read_output(directory: Path, name: str, settings: ExecutionSettings):
    return read_text_file(
        safe_sandbox_path(directory, name),
        max_bytes=settings.max_captured_output_bytes,
    )

async def execute_request(
    request: ExecutionRequest,
    *,
    box_pool: BoxPool,
    runner: IsolateRunner,
    settings: ExecutionSettings = execution_settings,
):
    async with runner.sandbox(box_pool) as sandbox:
        logger.info(
            "event=execution.sandbox.initialized token=%s language=%s box_id=%s",
            request.token,
            request.language.slug,
            sandbox.box_id,
        )
        write_text_file(sandbox.directory, request.language.source_file, request.source_code)
        write_text_file(sandbox.directory, "prog.in", request.stdin or "")
        if request.additional_files:
            extract_additional_files(
                request.additional_files,
                sandbox.directory,
                max_archive_bytes=settings.max_additional_archive_bytes,
                max_extracted_bytes=settings.max_additional_extracted_bytes,
                max_files=settings.max_additional_files,
                reserved_paths=frozenset(
                    {
                        request.language.source_file,
                        "prog.in",
                        "prog.out",
                        "prog.err",
                        "run.meta",
                        "compile.stdout",
                        "compile.stderr",
                        "compile.meta",
                    }
                ),
            )

        compile_memory = 0
        if request.language.compile_cmd:
            compile_started = monotonic()
            logger.info(
                "event=execution.compile.started token=%s language=%s box_id=%s",
                request.token,
                request.language.slug,
                sandbox.box_id,
            )
            compile_command = _runtime_command(
                request.language.compile_cmd,
                request.compiler_options,
                replace_args=True,
            )
            compile_completed = await runner.run(
                sandbox,
                compile_command,
                IsolateRunOptions(
                    time_limit=settings.max_time_limit,
                    extra_time=0,
                    wall_time_limit=settings.max_wall_time_limit,
                    memory_limit_kb=settings.max_memory_limit,
                    stack_size_limit_kb=request.stack_size_limit_kb,
                    file_size_limit_kb=settings.max_file_size,
                    stdin_file=None,
                    stdout_file="compile.stdout",
                    stderr_file="compile.stderr",
                    meta_file="compile.meta",
                ),
            )
            compile_meta = read_isolate_meta(
                safe_sandbox_path(sandbox.directory, "compile.meta"), required=True
            )
            compile_memory = compile_meta.memory
            compile_stdout = _read_output(sandbox.directory, "compile.stdout", settings)
            compile_stderr = _read_output(sandbox.directory, "compile.stderr", settings)
            compile_failed = (
                compile_completed.returncode != 0
                or compile_meta.exit_code not in {None, 0}
                or compile_meta.exit_signal not in {None, 0}
                or compile_meta.status is not None
            )
            logger.info(
                "event=execution.compile.completed token=%s language=%s box_id=%s "
                "success=%s duration_ms=%d host_returncode=%s exit_code=%s "
                "exit_signal=%s isolate_status=%s memory_kb=%s",
                request.token,
                request.language.slug,
                sandbox.box_id,
                not compile_failed,
                round((monotonic() - compile_started) * 1000),
                compile_completed.returncode,
                compile_meta.exit_code,
                compile_meta.exit_signal,
                compile_meta.status,
                compile_meta.memory,
            )
            if compile_failed:
                compile_output = "\n".join(
                    part for part in (compile_stdout, compile_stderr) if part
                )
                return ExecutionResult(
                    status_id=COMPILATION_ERROR_STATUS_ID,
                    compile_output=compile_output or None,
                    memory=compile_memory,
                    exit_code=compile_meta.exit_code,
                    exit_signal=compile_meta.exit_signal,
                    finished_at=datetime.utcnow(),
                )

        run_command = _runtime_command(
            request.language.run_cmd,
            request.command_line_args,
            replace_args=False,
        )
        run_started = monotonic()
        logger.info(
            "event=execution.run.started token=%s language=%s box_id=%s "
            "time_limit=%s wall_time_limit=%s memory_limit_kb=%s network=%s",
            request.token,
            request.language.slug,
            sandbox.box_id,
            request.time_limit,
            request.wall_time_limit,
            request.memory_limit_kb,
            request.enable_network,
        )
        run_completed = await runner.run(
            sandbox,
            run_command,
            IsolateRunOptions(
                time_limit=request.time_limit,
                extra_time=request.extra_time,
                wall_time_limit=request.wall_time_limit,
                memory_limit_kb=request.memory_limit_kb,
                stack_size_limit_kb=request.stack_size_limit_kb,
                file_size_limit_kb=request.file_size_limit_kb,
                stdin_file="prog.in",
                stdout_file="prog.out",
                stderr_file="prog.err",
                meta_file="run.meta",
                redirect_stderr_to_stdout=request.redirect_stderr_to_stdout,
                enable_network=request.enable_network,
            ),
        )
        run_meta = read_isolate_meta(
            safe_sandbox_path(sandbox.directory, "run.meta"), required=True
        )
        stdout = _read_output(sandbox.directory, "prog.out", settings)
        stderr = _read_output(sandbox.directory, "prog.err", settings)
        status_id = _result_status(
            run_completed.returncode, run_meta, request, stdout
        )
        logger.info(
            "event=execution.run.completed token=%s language=%s box_id=%s "
            "status_id=%s duration_ms=%d host_returncode=%s exit_code=%s "
            "exit_signal=%s isolate_status=%s cpu_time=%s wall_time=%s memory_kb=%s",
            request.token,
            request.language.slug,
            sandbox.box_id,
            status_id,
            round((monotonic() - run_started) * 1000),
            run_completed.returncode,
            run_meta.exit_code,
            run_meta.exit_signal,
            run_meta.status,
            run_meta.time,
            run_meta.wall_time,
            run_meta.memory,
        )
        return ExecutionResult(
            status_id=status_id,
            stdout=stdout or None,
            stderr=stderr or None,
            time=run_meta.time if run_meta.time is not None else run_completed.elapsed_seconds,
            wall_time=(
                run_meta.wall_time
                if run_meta.wall_time is not None
                else run_completed.elapsed_seconds
            ),
            memory=max(compile_memory, run_meta.memory),
            exit_code=(
                run_meta.exit_code
                if run_meta.exit_code is not None
                else run_completed.returncode
            ),
            exit_signal=run_meta.exit_signal,
            finished_at=datetime.utcnow(),
        )

async def execute_submission(
    submission,
    language,
    *,
    box_pool: BoxPool,
    runner: IsolateRunner,
    settings: ExecutionSettings = execution_settings,
):
    request = build_execution_request(submission, language)
    return await execute_request(
        request,
        box_pool=box_pool,
        runner=runner,
        settings=settings,
    )

def _encode_optional(value: str | None):
    if value is None:
        return None
    return base64.b64encode(value.encode("utf-8")).decode("ascii")

def apply_execution_result(submission, result: ExecutionResult):
    for field_name, value in execution_result_values(result).items():
        setattr(submission, field_name, value)

def execution_result_values(result: ExecutionResult):
    return {
        "status_id": result.status_id,
        "stdout": _encode_optional(result.stdout),
        "stderr": _encode_optional(result.stderr),
        "compile_output": _encode_optional(result.compile_output),
        "time": result.time,
        "wall_time": result.wall_time,
        "memory": result.memory,
        "exit_code": result.exit_code,
        "exit_signal": result.exit_signal,
        "finished_at": result.finished_at or datetime.utcnow(),
    }
