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

        #Initialize the environment
        box_id = str(hash(submission.token) % (2 ** 9))

        init_cmd = f"isolate --cg --init --box-id={box_id}"
        proc = await asyncio.create_subprocess_shell(
            init_cmd,
            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.PIPE
        )
        print(init_cmd)
        stdout_init, stderr_init = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"isolate init failed: {stderr_init.decode()}")

        work_dir = stdout_init.decode().strip() or f"/var/lib/isolate/{box_id}"
        sandbox_dir = os.path.join(work_dir, "box")
        tmp_dir = os.path.join(work_dir, "tmp")

        source_file_path = os.path.join(sandbox_dir, language.source_file)
        with open(source_file_path, 'w') as f:
            f.write(source_code)

        input_file_path = os.path.join(sandbox_dir, "prog.in")
        if stdin_data:
            with open(input_file_path, 'w') as f_in:
                f_in.write(stdin_data)
        else:
            with open(input_file_path, 'w') as f_in: pass

        #Unzip additional files
        if submission.additional_files:
            archive_path = f"{work_dir}/box/archive.zip"
            with open(archive_path, 'wb') as f_unzip: f_unzip.write(base64.b64decode(submission.additional_files))
            
            unzip_cmd = (
                f"isolate --cg --box-id={box_id} "
                f"--time=5 "
                f"--fsize={settings.MAX_FILE_SIZE} "
                f"--cg-mem={settings.MAX_MEMORY_LIMIT} "
                f"--stderr-to-stdout "
                f"--run -- /usr/bin/unzip -n -qq archive.zip"
            )
            proc = await asyncio.create_subprocess_shell(
                unzip_cmd,
                stdout = asyncio.subprocess.PIPE,
                stderr = asyncio.subprocess.PIPE
            )
            stdout_unzip, stderr_unzip = await proc.communicate()
            print(stdout_unzip, stderr_unzip)

        #Compilation process
        compile_cmd = language.compile_cmd or ""
        compile_used_memory_kb = 0
        if compile_cmd:
            compile_cmd = compile_cmd.replace("?/", "")
            print(compile_cmd)
            if submission.compiler_options: compile_cmd = compile_cmd.replace("$args", base64.b64decode(submission.compiler_options).decode('utf-8'))
            iso_compile_cmd = (
                f"isolate --cg --box-id={box_id} -p "
                f"--time={settings.MAX_TIME_LIMIT} "
                f"--wall-time={settings.MAX_WALL_TIME_LIMIT} "
                f"-p -n 0 "
                f'-E PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" '
                f"-E HOME=/tmp --dir=/etc:noexec "
                f"--stderr=compile_stderr.txt "
                f"--stdout=compile_stdout.txt "
                f"--meta=meta.txt "
                f"--run -- /bin/bash -c '{compile_cmd}'"
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
            
            show_meta_proc = await asyncio.create_subprocess_shell(
                "cat meta.txt",
                cwd = sandbox_dir,
                stdout = asyncio.subprocess.PIPE,
                stderr = asyncio.subprocess.PIPE
            )
            show_meta_proc_stdout, _ = await show_meta_proc.communicate()
            show_meta_proc_stdout = show_meta_proc_stdout.decode()
            show_meta_proc_stdout = show_meta_proc_stdout.strip("\n")
            show_meta_proc_stdout = show_meta_proc_stdout.split("\n")
            to_dict = lambda arr: dict(item.split(':') for item in arr)
            meta_compile_result = to_dict(show_meta_proc_stdout)
            compile_used_memory_kb = int(meta_compile_result['cg-mem'])
            
            reset_meta_proc = await asyncio.create_subprocess_shell(
                "sudo rm -rf meta.txt",
                cwd = sandbox_dir,
                stdout = asyncio.subprocess.PIPE,
                stderr = asyncio.subprocess.PIPE
            )

            if compile_proc.returncode != 0:
                submission.compile_output = base64.b64encode(
                    (compile_stdout_data + "\n" + compile_stderr_data).encode()
                ).decode()
                submission.status_id = 7 #Compilation Error
                submission.finished_at = datetime.utcnow()
                await run_in_threadpool(db.commit)

                cleanup_cmd = f"isolate --cg --box-id={box_id} --cleanup"
                await asyncio.create_subprocess_shell(cleanup_cmd)

                return

        #Run process
        run_cmd = language.run_cmd or ""
        run_cmd = run_cmd.replace("?/", "")
        if submission.command_line_args:
            run_cmd += f" {base64.b64decode(submission.command_line_args).decode('utf-8')}"

        iso_run_cmd = (
            f"isolate --cg --box-id={box_id} "
            f"{redirect_stderr_to_stdout} "
            f"{enable_network} "
            f"--time={submission.time_limit or 2} "
            f"--extra-time={submission.extra_time or 0.5} "
            f"--wall-time={submission.wall_time_limit or 3} "
            f"--cg-mem={submission.memory_limit or 65536} "
            f"-p -n 0 "
            f'-E PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" '
            f"-E HOME=/tmp --dir=/etc:noexec "
            f"--stdin=prog.in "
            f"--stdout=prog.out "
            f"--stderr=prog.err "
            f"--meta=meta.txt "
            f"--run -- /bin/bash -c '{run_cmd}'"
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
        show_meta_proc = await asyncio.create_subprocess_shell(
                "cat meta.txt",
                cwd = sandbox_dir,
                stdout = asyncio.subprocess.PIPE,
                stderr = asyncio.subprocess.PIPE
            )
        time_used_ms = int((end_time - start_time).total_seconds() * 1000)
        memory_used_kb_rss = settings.MAX_MEMORY_LIMIT + 1000
        memory_used_kb_cg = settings.MAX_MEMORY_LIMIT + 1000
        exit_code = 0
        exit_signal = None
        wall_time_ms = 0.0
        status = None
        if os.path.exists(meta_file):
            with open(meta_file, 'r') as fm:
                for line in fm:
                    print(line)
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split(":", 1)
                    if len(parts) != 2:
                        continue

                    key, value = parts[0].strip(), parts[1].strip()

                    if key == "time":
                        time_used_ms = float(value)
                    elif key == "time-wall":
                        wall_time_ms = float(value)
                    elif key == "max-rss":
                        memory_used_kb_rss = int(value)
                    elif key == "cg-mem":
                        memory_used_kb_cg = int(value)
                    elif key == "exitcode":
                        exit_code = int(value)
                    elif key == "exitsig":
                        exit_signal = value
                    elif key == "status":
                        status = value

        submission.time = time_used_ms
        submission.wall_time = wall_time_ms
        submission.memory = min(memory_used_kb_rss, memory_used_kb_cg)
        submission.stdout = base64.b64encode(stdout_data.encode()).decode() if len(stdout_data.strip()) != 0 else None
        submission.stderr = base64.b64encode(stderr_data.encode()).decode() if len(stderr_data.strip()) != 0 else None
        submission.exit_code = exit_code
        submission.exit_signal = exit_signal
        submission.finished_at = datetime.utcnow()

        #Status
        if run_process.returncode == 0:
            if expected_output is not None:
                if b64_equal(base64.b64encode(strip_text(stdout_data).encode()),
                             base64.b64encode(strip_text(expected_output).encode())):
                    submission.status_id = 3
                else:
                    submission.status_id = 4
            else:
                if stdout_data == "": 
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

        cleanup_cmd = f"isolate --cg --box-id={box_id} --cleanup"
        await asyncio.create_subprocess_shell(cleanup_cmd)

    except Exception as e:
        logger.exception(f"Error processing submission {submission.token}: {e}")
        submission.status_id = 9
        submission.stderr = base64.b64encode(str(e).encode()).decode()
        submission.finished_at = datetime.utcnow()
        await run_in_threadpool(db.commit)
