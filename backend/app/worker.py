"""arq background worker entry point."""

import logging
from arq import run_worker
from arq.cron import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.services.sending.send_worker import send_email_task
from app.services.replies.gmail_poller import poll_replies_task

settings = get_settings()
logger = logging.getLogger(__name__)


async def startup(ctx):
    logger.info("Worker starting up...")


async def shutdown(ctx):
    logger.info("Worker shutting down...")


class WorkerSettings:
    functions = [send_email_task, poll_replies_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    cron_jobs = [
        # Poll every 5 minutes for VC replies
        cron(poll_replies_task, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})
    ]
    max_jobs = 20
    job_timeout = 300


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker(WorkerSettings)
