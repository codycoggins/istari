#!/usr/bin/env bash
# Start the full Istari stack in prod mode (no debug ports exposed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "No .env file found. Copying from .env.example..."
  cp .env.example .env
  echo "Please edit .env with your API keys, then re-run this script."
  exit 1
fi

echo "Starting Istari (prod mode)..."
caffeinate -i docker compose -f docker-compose.yml up --build "$@"
