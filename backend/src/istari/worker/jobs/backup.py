"""Encrypted database backup job — runs via APScheduler at 2am daily."""

import asyncio
import logging
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from subprocess import PIPE
from urllib.parse import urlparse

from istari.config.settings import settings

logger = logging.getLogger(__name__)


def _parse_db_credentials(database_url: str) -> tuple[str, str, str]:
    """Extract (username, password, dbname) from a SQLAlchemy database URL."""
    parsed = urlparse(database_url.replace("+asyncpg", ""))
    username = parsed.username or "postgres"
    password = parsed.password or ""
    dbname = (parsed.path or "").lstrip("/")
    return username, password, dbname


def _run_dump_and_encrypt(
    dump_cmd: list[str],
    enc_cmd: list[str],
    output_path: Path,
    passphrase: str,
    db_password: str = "",
) -> None:
    """Run pg_dump piped through openssl encryption (synchronous)."""
    env = os.environ.copy()
    env["BACKUP_PASSPHRASE"] = passphrase
    # PGPASSWORD in docker client env is forwarded into the container by
    # `docker exec -e PGPASSWORD` — never appears in ps aux inside the container.
    if db_password:
        env["PGPASSWORD"] = db_password

    dump = subprocess.Popen(dump_cmd, stdout=PIPE, env=env)
    enc = subprocess.Popen(enc_cmd, stdin=dump.stdout, env=env)

    # Close dump's stdout in parent so enc gets EOF when dump exits
    if dump.stdout:
        dump.stdout.close()

    enc.communicate()
    dump.wait()

    if dump.returncode != 0:
        raise RuntimeError(f"pg_dump failed with exit code {dump.returncode}")
    if enc.returncode != 0:
        raise RuntimeError(f"openssl enc failed with exit code {enc.returncode}")


def _prune_old_backups(dest: Path, retention_days: int) -> None:
    """Delete .dump.enc files older than retention_days."""
    cutoff = time.time() - retention_days * 86400
    pruned = 0
    for f in dest.glob("istari_*.dump.enc"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            logger.info("Pruned old backup: %s", f.name)
            pruned += 1
    if pruned:
        logger.info("Pruned %d old backup(s)", pruned)


async def run_backup() -> None:
    """Create an encrypted pg_dump backup and prune old backups."""
    if not settings.backup_enabled:
        logger.debug("Backup skipped — backup_enabled=false")
        return

    if not settings.backup_passphrase:
        logger.warning("Backup skipped — BACKUP_PASSPHRASE is not set")
        return

    if not settings.backup_destination_path:
        logger.warning("Backup skipped — BACKUP_DESTINATION_PATH is not set")
        return

    dest = Path(settings.backup_destination_path).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    username, db_password, dbname = _parse_db_credentials(settings.database_url)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"istari_{timestamp}.dump.enc"
    output_path = dest / filename

    if settings.backup_pg_container:
        dump_cmd = [
            "docker", "exec", "-e", "PGPASSWORD",
            settings.backup_pg_container,
            "pg_dump", "-U", username, "-Fc", dbname,
        ]
    else:
        # Direct pg_dump — requires pg client in worker environment
        sync_url = settings.database_url.replace("+asyncpg", "")
        dump_cmd = ["pg_dump", sync_url, "-Fc"]

    enc_cmd = [
        "openssl", "enc", "-aes-256-cbc", "-pbkdf2",
        "-pass", "env:BACKUP_PASSPHRASE",
        "-out", str(output_path),
    ]

    logger.info("Starting backup → %s", filename)
    start = time.monotonic()

    try:
        await asyncio.to_thread(
            _run_dump_and_encrypt,
            dump_cmd, enc_cmd, output_path, settings.backup_passphrase, db_password,
        )
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        if output_path.exists():
            output_path.unlink()
        return

    elapsed = time.monotonic() - start
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Backup complete: %s (%.2f MB, %.1fs)", filename, size_mb, elapsed)

    _prune_old_backups(dest, settings.backup_retention_days)


def backup_sync() -> None:
    """Sync wrapper for APScheduler."""
    asyncio.run(run_backup())
