"""Worker entry point — starts APScheduler and runs background jobs."""

import datetime
import functools
import logging
from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from istari.config.settings import settings

logger = logging.getLogger(__name__)


def _in_quiet_hours() -> bool:
    """Check if the current hour falls within quiet hours."""
    now_hour = datetime.datetime.now(datetime.UTC).hour
    start = settings.quiet_hours_start
    end = settings.quiet_hours_end
    if start > end:
        # Wraps midnight, e.g. 21:00 - 07:00
        return now_hour >= start or now_hour < end
    return start <= now_hour < end


def respect_quiet_hours(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that skips job execution during quiet hours."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if _in_quiet_hours():
            logger.info("Skipping %s — quiet hours active", fn.__name__)
            return None
        return fn(*args, **kwargs)

    return wrapper


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    logger.info("Starting Istari worker")

    from istari.worker.jobs.gmail_digest import gmail_digest_sync
    from istari.worker.jobs.staleness import staleness_sync

    scheduler = BlockingScheduler()

    schedules = settings.schedules.get("jobs", {})

    # Gmail digest — morning and afternoon
    morning_cron = schedules.get("gmail_digest_morning", {}).get("cron", "0 8 * * *")
    afternoon_cron = schedules.get("gmail_digest_afternoon", {}).get("cron", "0 14 * * *")
    staleness_cron = schedules.get("staleness_check", {}).get("cron", "0 8 * * *")

    scheduler.add_job(
        respect_quiet_hours(gmail_digest_sync),
        CronTrigger.from_crontab(morning_cron),
        id="gmail_digest_morning",
    )
    scheduler.add_job(
        respect_quiet_hours(gmail_digest_sync),
        CronTrigger.from_crontab(afternoon_cron),
        id="gmail_digest_afternoon",
    )
    scheduler.add_job(
        respect_quiet_hours(staleness_sync),
        CronTrigger.from_crontab(staleness_cron),
        id="staleness_check",
    )

    logger.info(
        "Worker scheduler starting with %d jobs (quiet hours %d:00-%d:00)",
        len(scheduler.get_jobs()),
        settings.quiet_hours_start,
        settings.quiet_hours_end,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker shutting down")


if __name__ == "__main__":
    main()
