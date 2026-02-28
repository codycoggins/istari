#!/usr/bin/env bash
# restore_db.sh — decrypt and restore an Istari database backup
#
# Usage:
#   ./scripts/restore_db.sh /path/to/istari_20250101T020000Z.dump.enc
#
# Reads the backup passphrase interactively.
# DB credentials are read from .env (POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB).
# Set CONTAINER="" to restore directly via DATABASE_URL instead.

set -euo pipefail

BACKUP_FILE="${1:-}"
CONTAINER="${CONTAINER:-istari-postgres-1}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Load DB credentials from .env
DB_USER="istari"
DB_NAME="istari"
DB_PASSWORD=""
if [[ -f "$ENV_FILE" ]]; then
  DB_USER="$(grep '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' || echo "istari")"
  DB_PASSWORD="$(grep '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' || echo "")"
  DB_NAME="$(grep '^POSTGRES_DB=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' || echo "istari")"
fi

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
    | PGPASSWORD="$DB_PASSWORD" docker exec -e PGPASSWORD -i "$CONTAINER" \
        pg_restore -U "$DB_USER" --clean --if-exists -d "$DB_NAME"
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
