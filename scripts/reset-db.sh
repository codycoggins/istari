#!/usr/bin/env bash
# Drop, recreate, and migrate the Istari database.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

# Source .env for DB credentials
if [ -f .env ]; then
  set -a; source .env; set +a
fi

DB_USER="${POSTGRES_USER:-istari}"
DB_NAME="${POSTGRES_DB:-istari}"

echo "Dropping database $DB_NAME..."
docker compose exec postgres dropdb -U "$DB_USER" --if-exists "$DB_NAME"

echo "Creating database $DB_NAME..."
docker compose exec postgres createdb -U "$DB_USER" "$DB_NAME"

echo "Running migrations..."
cd backend
alembic upgrade head

echo "Database reset complete."
