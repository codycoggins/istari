#!/usr/bin/env bash
# Seed the Istari database with dev/test data.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a; source .env; set +a
fi

echo "Seeding dev data..."
cd backend
python -c "
from istari.config.settings import settings
print(f'Connected to: {settings.database_url}')
print('Seed logic not yet implemented — add seed data here.')
"

echo "Seeding complete."
