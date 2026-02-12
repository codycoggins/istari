"""Worker entry point — starts APScheduler and runs background jobs."""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from istari.config.settings import settings

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    logger.info("Starting Istari worker")

    scheduler = BlockingScheduler()

    # Jobs will be registered here as they are implemented
    # e.g. scheduler.add_job(gmail_digest, CronTrigger.from_crontab("0 8 * * *"))

    logger.info("Worker scheduler starting")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker shutting down")


if __name__ == "__main__":
    main()
