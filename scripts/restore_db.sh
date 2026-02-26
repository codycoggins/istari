#!/usr/bin/env bash
# restore_db.sh — decrypt and restore an Istari database backup
#
# Usage:
#   ./scripts/restore_db.sh /path/to/istari_20250101T020000Z.dump.enc
#
# Reads the passphrase interactively (not echoed).
# Set CONTAINER="" to use pg_restore directly with $DATABASE_URL instead.

set -euo pipefail

BACKUP_FILE="${1:-}"
CONTAINER="${CONTAINER:-istari-postgres-1}"

if [[ -z "$BACKUP_FILE" ]]; then
  echo "Usage: $0 <backup-file.dump.enc>" >&2
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Error: file not found: $BACKUP_FILE" >&2
  exit 1
fi

read -r -s -p "Backup passphrase: " PASSPHRASE
echo

echo "Decrypting and restoring from: $BACKUP_FILE"

if [[ -n "$CONTAINER" ]]; then
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$PASSPHRASE" -in "$BACKUP_FILE" \
    | docker exec -i "$CONTAINER" pg_restore --clean --if-exists -d istari
else
  # Direct restore — requires pg_restore in PATH and DATABASE_URL set
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "Error: CONTAINER is empty and DATABASE_URL is not set" >&2
    exit 1
  fi
  SYNC_URL="${DATABASE_URL/+asyncpg/}"
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$PASSPHRASE" -in "$BACKUP_FILE" \
    | pg_restore --clean --if-exists -d "$SYNC_URL"
fi

echo "Restore complete."
