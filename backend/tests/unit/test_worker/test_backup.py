"""Tests for the encrypted database backup job."""

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_TO_THREAD = "istari.worker.jobs.backup.asyncio.to_thread"
_DB_URL = "postgresql+asyncpg://istari:secret@localhost:5432/istari"


def test_parse_db_credentials_standard_url():
    from istari.worker.jobs.backup import _parse_db_credentials

    user, pw, db = _parse_db_credentials(_DB_URL)
    assert user == "istari"
    assert pw == "secret"
    assert db == "istari"


def test_parse_db_credentials_no_password():
    from istari.worker.jobs.backup import _parse_db_credentials

    user, pw, db = _parse_db_credentials("postgresql://localhost/testdb")
    assert user == "postgres"
    assert pw == ""
    assert db == "testdb"


def test_parse_db_credentials_strips_asyncpg():
    from istari.worker.jobs.backup import _parse_db_credentials

    _, _, db = _parse_db_credentials("postgresql+asyncpg://u:p@host/mydb")
    assert db == "mydb"


@pytest.mark.asyncio
async def test_backup_skips_when_disabled():
    with patch("istari.worker.jobs.backup.settings") as mock_settings:
        mock_settings.backup_enabled = False

        from istari.worker.jobs.backup import run_backup

        await run_backup()


@pytest.mark.asyncio
async def test_backup_skips_when_no_passphrase():
    with patch("istari.worker.jobs.backup.settings") as mock_settings:
        mock_settings.backup_enabled = True
        mock_settings.backup_passphrase = ""

        from istari.worker.jobs.backup import run_backup

        await run_backup()


@pytest.mark.asyncio
async def test_backup_skips_when_no_destination():
    with patch("istari.worker.jobs.backup.settings") as mock_settings:
        mock_settings.backup_enabled = True
        mock_settings.backup_passphrase = "secret"
        mock_settings.backup_destination_path = ""

        from istari.worker.jobs.backup import run_backup

        await run_backup()


@pytest.mark.asyncio
async def test_backup_success(tmp_path: Path):
    with patch("istari.worker.jobs.backup.settings") as mock_settings:
        mock_settings.backup_enabled = True
        mock_settings.backup_passphrase = "secret"
        mock_settings.backup_destination_path = str(tmp_path)
        mock_settings.backup_pg_container = "istari-postgres-1"
        mock_settings.database_url = _DB_URL
        mock_settings.backup_retention_days = 7

        def fake_dump(dump_cmd, enc_cmd, output_path, passphrase, db_password=""):
            assert dump_cmd == [
                "docker", "exec", "-e", "PGPASSWORD",
                "istari-postgres-1",
                "pg_dump", "-U", "istari", "-Fc", "istari",
            ]
            assert passphrase == "secret"
            assert db_password == "secret"
            output_path.write_bytes(b"fake encrypted dump")

        with patch(_TO_THREAD, new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = lambda fn, *args, **kwargs: (
                fake_dump(*args, **kwargs) or None
            )

            from istari.worker.jobs.backup import run_backup

            await run_backup()

        files = list(tmp_path.glob("istari_*.dump.enc"))
        assert len(files) == 1
        assert files[0].read_bytes() == b"fake encrypted dump"


@pytest.mark.asyncio
async def test_backup_uses_direct_pg_dump_when_no_container(tmp_path: Path):
    with patch("istari.worker.jobs.backup.settings") as mock_settings:
        mock_settings.backup_enabled = True
        mock_settings.backup_passphrase = "secret"
        mock_settings.backup_destination_path = str(tmp_path)
        mock_settings.backup_pg_container = ""
        mock_settings.database_url = _DB_URL
        mock_settings.backup_retention_days = 7

        captured: dict = {}

        def fake_dump(dump_cmd, enc_cmd, output_path, passphrase, db_password=""):
            captured["dump_cmd"] = dump_cmd
            output_path.write_bytes(b"x")

        with patch(_TO_THREAD, new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = lambda fn, *args, **kwargs: (
                fake_dump(*args, **kwargs) or None
            )

            from istari.worker.jobs.backup import run_backup

            await run_backup()

        assert captured["dump_cmd"][0] == "pg_dump"
        assert "+asyncpg" not in captured["dump_cmd"][1]


@pytest.mark.asyncio
async def test_backup_failure_cleans_up_partial_file(tmp_path: Path):
    with patch("istari.worker.jobs.backup.settings") as mock_settings:
        mock_settings.backup_enabled = True
        mock_settings.backup_passphrase = "secret"
        mock_settings.backup_destination_path = str(tmp_path)
        mock_settings.backup_pg_container = "istari-postgres-1"
        mock_settings.database_url = _DB_URL
        mock_settings.backup_retention_days = 7

        def failing_dump(dump_cmd, enc_cmd, output_path, passphrase, db_password=""):
            output_path.write_bytes(b"partial")
            raise RuntimeError("pg_dump failed with exit code 1")

        with patch(_TO_THREAD, new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = lambda fn, *args, **kwargs: (
                failing_dump(*args, **kwargs) or None
            )

            from istari.worker.jobs.backup import run_backup

            await run_backup()

        files = list(tmp_path.glob("istari_*.dump.enc"))
        assert len(files) == 0


def test_prune_old_backups(tmp_path: Path):
    from istari.worker.jobs.backup import _prune_old_backups

    old_file = tmp_path / "istari_20250101T020000Z.dump.enc"
    old_file.write_bytes(b"old")
    old_mtime = time.time() - 9 * 86400
    os.utime(old_file, (old_mtime, old_mtime))

    new_file = tmp_path / "istari_20250110T020000Z.dump.enc"
    new_file.write_bytes(b"new")

    _prune_old_backups(tmp_path, retention_days=7)

    assert not old_file.exists()
    assert new_file.exists()


def test_prune_does_not_touch_other_files(tmp_path: Path):
    from istari.worker.jobs.backup import _prune_old_backups

    other_file = tmp_path / "some_other_file.dump.enc"
    other_file.write_bytes(b"other")
    os.utime(other_file, (time.time() - 30 * 86400,) * 2)

    _prune_old_backups(tmp_path, retention_days=7)

    assert other_file.exists()


def test_run_dump_and_encrypt_raises_on_dump_failure(tmp_path: Path):
    from istari.worker.jobs.backup import _run_dump_and_encrypt

    output_path = tmp_path / "test.dump.enc"
    dump_cmd = ["sh", "-c", "exit 1"]
    enc_cmd = ["sh", "-c", "cat > /dev/null"]

    with pytest.raises(RuntimeError, match="pg_dump failed"):
        _run_dump_and_encrypt(dump_cmd, enc_cmd, output_path, "pass")
