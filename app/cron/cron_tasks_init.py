# app/cron/cron_tasks_init.py

from app.core.config import settings
from configparser import ConfigParser
from crontab import CronTab
import os

FREQUENCY_OF_CLEANING_API_TOKENS = int(settings.FREQUENCY_OF_CLEANING_API_TOKENS)
FREQUENCY_OF_CLEANING_SUBMISSIONS = int(settings.FREQUENCY_OF_CLEANING_SUBMISSIONS)

def clear_api_tokens_init(cron):
    SCRIPT_PATH = os.path.abspath("app/cron/clear_api_tokens.py")
    PYTHON_PATH = "/usr/bin/python3"
    LOG_PATH = os.path.abspath("app/logs/api_cleanup.log")

    for job in cron.find_comment("auto-cleanup-api-tokens"):
        cron.remove(job)
    job = cron.new(command=f"cd /app && {PYTHON_PATH} {SCRIPT_PATH} >> {LOG_PATH} 2>&1",
                   comment="auto-cleanup-api-tokens")
    if FREQUENCY_OF_CLEANING_API_TOKENS >= 1:
        job.minute.every(FREQUENCY_OF_CLEANING_API_TOKENS)
    else:
        job.minute.every(1)
    print(f"[INFO] Cron job set to run every {FREQUENCY_OF_CLEANING_API_TOKENS} minutes: {job.slices} {job.command}")

def clear_submissions_init(cron):
    SCRIPT_PATH = os.path.abspath("app/cron/clear_submissions.py")
    PYTHON_PATH = "/usr/bin/python3"
    LOG_PATH = os.path.abspath("app/logs/submissions_cleanup.log")

    for job in cron.find_comment("auto-cleanup-submissions"):
        cron.remove(job)
    job = cron.new(command=f"cd /app && {PYTHON_PATH} {SCRIPT_PATH} >> {LOG_PATH} 2>&1",
                   comment="auto-cleanup-submissions")
    if FREQUENCY_OF_CLEANING_SUBMISSIONS >= 1:
        job.setall(f"0 0 */{FREQUENCY_OF_CLEANING_SUBMISSIONS} * *")
    else:
        job.setall("0 0 * * *")
    print(f"[INFO] Cron job set to run every {FREQUENCY_OF_CLEANING_SUBMISSIONS} days: {job.slices} {job.command}")


def init_cron_scripts():
    cron = CronTab(user=True)
    clear_api_tokens_init(cron)
    clear_submissions_init(cron)
    cron.write()