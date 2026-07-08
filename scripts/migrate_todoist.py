#!/usr/bin/env python
"""One-time migration of Istari active projects/todos into Todoist.

Usage (from repo root, with the backend venv active):
    python scripts/migrate_todoist.py --dry-run   # preview — makes no writes
    python scripts/migrate_todoist.py             # perform the migration

Requires TODOIST_API_TOKEN in .env
(Todoist → Settings → Integrations → Developer). Idempotent: re-runs skip
projects/tasks that already exist.
"""

import argparse
import asyncio
import sys

from istari.config.settings import settings
from istari.db.session import async_session_factory
from istari.tools.todoist.client import TodoistClient, TodoistError
from istari.tools.todoist.migrate import run_migration


async def _run(dry_run: bool) -> int:
    token = settings.todoist_api_token
    if not token:
        print(
            "TODOIST_API_TOKEN is not set. Add it to .env and retry.",
            file=sys.stderr,
        )
        return 1

    async with async_session_factory() as session, TodoistClient(token) as client:
        try:
            summary = await run_migration(session, client, dry_run=dry_run)
        except TodoistError as exc:
            print(f"Migration failed: {exc}", file=sys.stderr)
            return 1

    print(summary.render())
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Istari data into Todoist.")
    parser.add_argument(
        "--dry-run", action="store_true", help="preview the plan without writing"
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.dry_run)))


if __name__ == "__main__":
    main()
