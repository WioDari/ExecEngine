from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Awaitable, Callable

from app.execution.box_pool import BoxPool
from app.execution.errors import (
    ExecutionConfigurationError,
    IsolateCleanupError,
    TransientExecutionError,
)

logger = logging.getLogger(__name__)

_SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

@dataclass(frozen=True)
class Sandbox:
    box_id: int
    root: Path
    directory: Path

@dataclass(frozen=True)
class IsolateCompletedProcess:
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float

@dataclass(frozen=True)
class IsolateRunOptions:
    time_limit: float
    wall_time_limit: float
    memory_limit_kb: int
    file_size_limit_kb: int
    stdin_file: str | None
    stdout_file: str
    stderr_file: str
    meta_file: str
    stack_size_limit_kb: int | None = None
    extra_time: float = 0.0
    redirect_stderr_to_stdout: bool = False
    enable_network: bool = False

class IsolateRunner:
    def __init__(
        self,
        *,
        cleanup_timeout: float,
        max_host_output_bytes: int,
        process_factory: Callable[..., Awaitable] = asyncio.create_subprocess_exec,
    ):
        if cleanup_timeout <= 0:
            raise ValueError("cleanup_timeout must be positive")
        if max_host_output_bytes < 1:
            raise ValueError("max_host_output_bytes must be positive")
        self.cleanup_timeout = cleanup_timeout
        self.max_host_output_bytes = max_host_output_bytes
        self.process_factory = process_factory

    async def _communicate(self, arguments: list[str], *, cwd: Path | None = None):
        try:
            process = await self.process_factory(
                *arguments,
                cwd=str(cwd) if cwd is not None else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ExecutionConfigurationError("isolate executable is not installed") from exc
        except OSError as exc:
            raise TransientExecutionError("Failed to start isolate") from exc

        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.kill()
            await process.communicate()
            raise
        return process.returncode, stdout, stderr

    def _decode_host_output(self, value: bytes):
        return value[: self.max_host_output_bytes].decode("utf-8", errors="replace")

    async def init(self, box_id: int):
        arguments = ["isolate", "--cg", "--init", f"--box-id={box_id}"]
        returncode, stdout, stderr = await self._communicate(arguments)
        if returncode != 0:
            diagnostic = self._decode_host_output(stderr).strip()
            logger.error(
                "event=isolate.init_failed box_id=%s returncode=%s diagnostic=%s",
                box_id,
                returncode,
                diagnostic or "unknown error",
            )
            raise TransientExecutionError(
                f"isolate init failed for box {box_id}: {diagnostic or 'unknown error'}"
            )
        output = self._decode_host_output(stdout).strip()
        root = Path(output.splitlines()[0]) if output else Path(f"/var/lib/isolate/{box_id}")
        if not root.is_absolute():
            raise TransientExecutionError("isolate init returned a non-absolute sandbox path")
        logger.debug("event=isolate.initialized box_id=%s root=%s", box_id, root)
        return Sandbox(box_id=box_id, root=root, directory=root / "box")

    async def cleanup(self, box_id: int):
        arguments = ["isolate", "--cg", "--cleanup", f"--box-id={box_id}"]
        try:
            returncode, _stdout, stderr = await asyncio.wait_for(
                self._communicate(arguments), timeout=self.cleanup_timeout
            )
        except asyncio.TimeoutError as exc:
            raise IsolateCleanupError(f"isolate cleanup timed out for box {box_id}") from exc
        if returncode != 0:
            diagnostic = self._decode_host_output(stderr).strip()
            raise IsolateCleanupError(
                f"isolate cleanup failed for box {box_id}: {diagnostic or 'unknown error'}"
            )
        logger.debug("event=isolate.cleaned box_id=%s", box_id)

    @asynccontextmanager
    async def sandbox(self, box_pool: BoxPool):
        box_id = await box_pool.acquire()
        body_error: BaseException | None = None
        try:
            sandbox = await self.init(box_id)
            yield sandbox
        except BaseException as exc:
            body_error = exc
            raise
        finally:
            cleanup_error = None
            try:
                cleanup_task = asyncio.create_task(self.cleanup(box_id))
                await asyncio.shield(cleanup_task)
            except Exception as exc:
                cleanup_error = exc
                logger.exception("event=isolate.cleanup_failed box_id=%s", box_id)

            if cleanup_error is None:
                box_pool.release(box_id)
            else:
                box_pool.discard(box_id)
                if body_error is None:
                    if isinstance(cleanup_error, IsolateCleanupError):
                        raise cleanup_error
                    raise IsolateCleanupError(
                        f"isolate cleanup failed for box {box_id}"
                    ) from cleanup_error

    async def run(
        self,
        sandbox: Sandbox,
        command: str,
        options: IsolateRunOptions,
    ):
        arguments = [
            "isolate",
            "--cg",
            f"--box-id={sandbox.box_id}",
            f"--time={options.time_limit}",
            f"--extra-time={options.extra_time}",
            f"--wall-time={options.wall_time_limit}",
            f"--cg-mem={options.memory_limit_kb}",
            f"--fsize={options.file_size_limit_kb}",
            "-p",
            "-n",
            "0",
            "-E",
            f"PATH={_SAFE_PATH}",
            "-E",
            "HOME=/tmp",
            "--dir=/etc:noexec",
        ]
        if options.redirect_stderr_to_stdout:
            arguments.append("--stderr-to-stdout")
        if options.enable_network:
            arguments.append("--share-net")
        if options.stack_size_limit_kb:
            arguments.append(f"--stack={options.stack_size_limit_kb}")
        if options.stdin_file:
            arguments.append(f"--stdin={options.stdin_file}")
        arguments.extend(
            [
                f"--stdout={options.stdout_file}",
                f"--stderr={options.stderr_file}",
                f"--meta={options.meta_file}",
                "--run",
                "--",
                "/bin/bash",
                "-c",
                command,
            ]
        )

        logger.debug(
            "event=isolate.run.started box_id=%s time_limit=%s wall_time_limit=%s "
            "memory_limit_kb=%s file_size_limit_kb=%s network=%s",
            sandbox.box_id,
            options.time_limit,
            options.wall_time_limit,
            options.memory_limit_kb,
            options.file_size_limit_kb,
            options.enable_network,
        )
        started_at = monotonic()
        returncode, stdout, stderr = await self._communicate(
            arguments, cwd=sandbox.directory
        )
        elapsed_seconds = monotonic() - started_at
        logger.debug(
            "event=isolate.run.completed box_id=%s returncode=%s duration_ms=%d",
            sandbox.box_id,
            returncode,
            round(elapsed_seconds * 1000),
        )
        return IsolateCompletedProcess(
            returncode=returncode,
            stdout=self._decode_host_output(stdout),
            stderr=self._decode_host_output(stderr),
            elapsed_seconds=elapsed_seconds,
        )
