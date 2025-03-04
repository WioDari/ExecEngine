# app/services/submission_service.py

import base64
import asyncio
import subprocess
import os
import tempfile
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.orm_models import SubmissionModel, LanguageModel
from app.core.config import settings
import logging
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

async def process_submission(submission: SubmissionModel, db: Session):
    try:
        submission = await run_in_threadpool(lambda: db.merge(submission))
        language = await run_in_threadpool(lambda:db.query(LanguageModel).filter(LanguageModel.id == submission.language_id).first())
        if not language:
            raise ValueError("Language not found.")

        source_code = base64.b64decode(submission.source_code).decode('utf-8')
        stdin_data = base64.b64decode(submission.stdin).decode('utf-8') if submission.stdin else None
        expected_output = base64.b64decode(submission.expected_output).decode('utf-8') if submission.expected_output else None

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file_path = os.path.join(tmpdir, language.source_file)
            with open(source_file_path, 'w') as f:
                f.write(source_code)

            env = {
                'VERSION': language.version,
                'SOURCE_FILE': language.source_file,
                'COMPILED_FILE': language.compiled_file or '',
            }

            compile_cmd = language.compile_cmd
            run_cmd = language.run_cmd
            
            compile_cmd = compile_cmd.replace("?",tmpdir) if compile_cmd else None
            run_cmd = run_cmd.replace("?",tmpdir) if run_cmd else None
            logger.info(compile_cmd)
            logger.info(run_cmd)
            
            for key, value in env.items():
                compile_cmd = compile_cmd.replace(f"${key}", value) if compile_cmd else None
                run_cmd = run_cmd.replace(f"${key}", value) if run_cmd else None

            if submission.compiler_options and compile_cmd:
                compile_cmd += f" {submission.compiler_options}"

            if submission.command_line_args and run_cmd:
                run_cmd += f" {submission.command_line_args}"

            if compile_cmd:
                compile_process = await asyncio.create_subprocess_shell(
                    compile_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir
                )
                stdout, stderr = await compile_process.communicate()
                compile_output = (stdout + stderr).decode('utf-8')
                logger.info(compile_output)
                if compile_process.returncode != 0:
                    submission.compile_output = base64.b64encode(compile_output.encode()).decode()
                    submission.status_id = 7  # Compilation Error
                    submission.finished_at = datetime.utcnow()
                    await run_in_threadpool(db.commit)
                    logger.error(f"Compilation error for submission {submission.token}")
                    print(base64.b64encode(compile_output.encode()).decode())
                    return

            run_process = await asyncio.create_subprocess_shell(
                run_cmd,
                stdin=asyncio.subprocess.PIPE if stdin_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir
            )
            start_time = datetime.utcnow()
            stdout, stderr = await run_process.communicate(input=stdin_data.encode() if stdin_data else None)
            end_time = datetime.utcnow()

            time_used = int((end_time - start_time).total_seconds() * 1000)  
            memory_used = 0 #add later  

            submission.time = time_used
            submission.memory = memory_used
            submission.stdout = base64.b64encode(stdout).decode()
            submission.stderr = base64.b64encode(stderr).decode()
            submission.exit_code = run_process.returncode
            submission.finished_at = datetime.utcnow()

            if run_process.returncode == 0:
                if expected_output and stdout.decode().strip() == expected_output.strip():
                    submission.status_id = 3  # Accepted
                else:
                    submission.status_id = 4  # Wrong Answer
            else:
                submission.status_id = 8  # Runtime Error
            logger.info(submission.status_id)
            await run_in_threadpool(db.commit)
            logger.info(f"Processed submission {submission.token}")

    except Exception as e:
        logger.exception(f"Error processing submission {submission.token}: {e}")
        submission.status_id = 9  # Internal Error
        submission.stderr = base64.b64encode(str(e).encode()).decode()
        submission.finished_at = datetime.utcnow()
        await run_in_threadpool(db.commit)
