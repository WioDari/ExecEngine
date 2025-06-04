# app/services/submission_service.py

import base64
import asyncio
import subprocess
import os
import tempfile
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.orm_models import SubmissionModel, LanguageModel
from app.core.config import settings
from starlette.concurrency import run_in_threadpool
from hmac import compare_digest

logger = logging.getLogger(__name__)

def b64_equal(str1: str, str2: str, text=True, normalize_lines=True):
    da = base64.standard_b64decode(str1)
    db = base64.standard_b64decode(str2)

    if text:
        da = da.decode('utf-8', errors='replace')
        db = db.decode('utf-8', errors='replace')
        if normalize_lines:
            da = da.replace('\r\n', '\n')
            db = db.replace('\r\n', '\n')
    return compare_digest(da.strip(), db.strip())

def strip_text(text: str | None) -> str | None:
    if text is None:
        return None

    try:
        return "\n".join(line.rstrip() for line in text.split("\n")).rstrip()
    except (AttributeError, TypeError, ValueError):
        return text


async def process_submission(submission: SubmissionModel, db: Session):
    try:
        submission = await run_in_threadpool(lambda: db.merge(submission))
        language = await run_in_threadpool(lambda:db.query(LanguageModel).filter(LanguageModel.id == submission.language_id).first())
        if not language:
            raise ValueError("Language not found.")

        source_code = base64.b64decode(submission.source_code).decode('utf-8')
        stdin_data = base64.b64decode(submission.stdin).decode('utf-8') if submission.stdin else None
        expected_output = base64.b64decode(submission.expected_output).decode('utf-8') if submission.expected_output else None
        redirect_stderr_to_stdout = "--stderr-to-stdout" if submission.redirect_stderr_to_stdout else ""
        enable_network = "--share-net" if submission.enable_network else ""
        submission.stack_size = 0

        #Creating the environment
        box_id = str(hash(submission.token) % (2 ** 9))

        init_cmd = f"isolate --init --dir=/opt/compilers --box-id={box_id}"
        proc = await asyncio.create_subprocess_shell(
            init_cmd,
            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.PIPE
        )
        print(init_cmd)
        stdout_init, stderr_init = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"isolate init failed: {stderr_init.decode()}")

        work_dir = stdout_init.decode().strip() or f"/var/local/lib/isolate/{box_id}"
        sandbox_dir = os.path.join(work_dir, "box")
        tmp_dir = os.path.join(work_dir, "tmp")

        source_file_path = os.path.join(sandbox_dir, language.source_file)
        with open(source_file_path, 'w') as f:
            f.write(source_code)

        input_file_path = os.path.join(sandbox_dir, "prog.in")
        if stdin_data:
            with open(input_file_path, 'w') as f_in:
                f_in.write(stdin_data)

        #Compilation process
        compile_cmd = language.compile_cmd or ""
        if compile_cmd:
            compile_cmd = compile_cmd.replace("?/", "")
            print(compile_cmd)
            if submission.compiler_options:
                compile_cmd += f" {submission.compiler_options}"
            iso_compile_cmd = (
                f"isolate --box-id={box_id} -p "
                f"--time=10 "
                f'-E PATH="/opt/compilers:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" '
                f"-E HOME=/tmp "
                f"-d /opt/compilers "
                f"--stderr=compile_stderr.txt "
                f"--stdout=compile_stdout.txt "
                f"--run -- {compile_cmd}"
            )
            print(iso_compile_cmd)
            compile_proc = await asyncio.create_subprocess_shell(
                iso_compile_cmd,
                cwd = sandbox_dir,
                stdout = asyncio.subprocess.PIPE,
                stderr = asyncio.subprocess.PIPE
            )
            compile_stdout_shell, compile_stderr_shell = await compile_proc.communicate()
            if compile_stderr_shell: logger.error("isolate run error: %s", compile_stderr_shell.decode('utf-8', errors='ignore'))

            compile_stderr_path = os.path.join(sandbox_dir, "compile_stderr.txt")
            compile_stdout_path = os.path.join(sandbox_dir, "compile_stdout.txt")
            compile_stderr_data = ""
            compile_stdout_data = ""
            if os.path.exists(compile_stderr_path):
                with open(compile_stderr_path, "r") as fs:
                    compile_stderr_data = fs.read()
            if os.path.exists(compile_stdout_path):
                with open(compile_stdout_path, "r") as fs:
                    compile_stdout_data = fs.read()

            if compile_proc.returncode != 0:
                submission.compile_output = base64.b64encode(
                    (compile_stdout_data + "\n" + compile_stderr_data).encode()
                ).decode()
                submission.status_id = 7 #Compilation Error
                submission.finished_at = datetime.utcnow()
                await run_in_threadpool(db.commit)

                #cleanup_cmd = f"/opt/compilers/isolate/bin/isolate --box-id={box_id} --cleanup"
                #await asyncio.create_subprocess_shell(cleanup_cmd)

                return

        #Run process
        run_cmd = language.run_cmd or ""
        run_cmd = run_cmd.replace("?/", "")
        if submission.command_line_args:
            run_cmd += f" {submission.command_line_args}"

        iso_run_cmd = (
            f"isolate --box-id={box_id} "
            f"{redirect_stderr_to_stdout} "
            f"{enable_network} "
            f"--time={submission.time_limit or 2} "
            f"--extra-time={submission.extra_time or 0.5} "
            f"--wall-time={submission.wall_time_limit or 3} "
            f"--mem={submission.memory_limit or 65536} "
            f"--fsize={submission.max_file_size or 1024} "
            f"--processes=8 "
            f'-E PATH="/opt/compilers:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" '
            f"-E HOME=/tmp "
            f"-d /opt/compilers "
            f"--stdin=prog.in "
            f"--stdout=prog.out "
            f"--stderr=prog.err "
            f"--meta=meta.txt "
            f"--run -- {run_cmd}"
        )
        print(iso_run_cmd)
        start_time = datetime.utcnow()
        run_process = await asyncio.create_subprocess_shell(
            iso_run_cmd,
            cwd = sandbox_dir,
            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.PIPE
        )
        run_stdout,run_stderr = await run_process.communicate()
        print(run_stdout, run_stderr, run_process.returncode)
        end_time = datetime.utcnow()

        output_file = os.path.join(sandbox_dir, "prog.out")
        err_file = os.path.join(sandbox_dir, "prog.err")
        meta_file = os.path.join(sandbox_dir, "meta.txt")

        stdout_data = ""
        stderr_data = ""
        if os.path.exists(output_file):
            with open(output_file, 'r') as f_out:
                stdout_data = f_out.read()
        if os.path.exists(err_file):
            with open(err_file, 'r') as f_err:
                stderr_data = f_err.read()

        #Parse meta.txt
        time_used_ms = int((end_time - start_time).total_seconds() * 1000)
        memory_used_kb = 0
        exit_code = 0
        exit_signal = None
        wall_time_ms = 0.0
        status = None
        if os.path.exists(meta_file):
            with open(meta_file, 'r') as fm:
                for line in fm:
                    if line.startswith("time:"):
                        val = float(line.split(":")[1].strip())
                        time_used_ms = val
                    elif line.startswith("max-rss:"):
                        val = int(line.split(":")[1].strip())
                        memory_used_kb = val
                    elif line.startswith("exitcode:"):
                        val = float(line.split(":")[1].strip())
                        exit_code = val
                    elif line.startswith("exitsig:"):
                        val = str(line.split(":")[1].strip())
                        exit_signal = val
                    elif line.startswith("time-wall:"):
                        val = float(line.split(":")[1].strip())
                        wall_time_ms = val
                    elif line.startswith("status:"):
                        val = str(line.split(":")[1].strip())
                        status = val

        submission.time = time_used_ms
        submission.wall_time = wall_time_ms
        submission.memory = memory_used_kb
        submission.stdout = base64.b64encode(stdout_data.encode()).decode()
        submission.stderr = base64.b64encode(stderr_data.encode()).decode()
        submission.exit_code = exit_code
        submission.exit_signal = exit_signal
        submission.finished_at = datetime.utcnow()

        #Status
        if run_process.returncode == 0:
            if expected_output and b64_equal(base64.b64encode(strip_text(stdout_data).encode()),
                                             base64.b64encode(strip_text(expected_output).encode())):
                submission.status_id = 3
            else:
                submission.status_id = 4
        else:
            if status == "TO":
                submission.status_id = 5
            elif status == "XX":
                submission.status_id = 9
            else:
                submission.status_id = 8

        await run_in_threadpool(db.commit)

        #cleanup_cmd = f"/opt/compilers/isolate/bin/isolate --box-id={box_id} --cleanup"
        #await asyncio.create_subprocess_shell(cleanup_cmd)

    except Exception as e:
        logger.exception(f"Error processing submission {submission.token}: {e}")
        submission.status_id = 9
        submission.stderr = base64.b64encode(str(e).encode()).decode()
        submission.finished_at = datetime.utcnow()
        await run_in_threadpool(db.commit)
