#!/usr/bin/env bash
# Docker compose helper script (dev mode)
set -e

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.dev.yml"

case "$1" in
  up)
    echo "Starting containers..."
    $COMPOSE up -d --build

    echo "Preventing idle sleep and attaching logs (display/disk may still sleep)..."
    shift
    caffeinate -i $COMPOSE logs -f "$@"
    ;;

  down)
    echo "Stopping containers..."
    $COMPOSE down
    ;;

  logs)
    shift
    $COMPOSE logs -f "$@"
    ;;

  restart)
    $COMPOSE down
    $COMPOSE up -d --build
    ;;

  reset-db)
    echo "WARNING: deleting volumes"
    $COMPOSE down -v
    ;;

  *)
    echo "Usage:"
    echo "  ./dev.sh up"
    echo "  ./dev.sh down"
    echo "  ./dev.sh logs [service]"
    echo "  ./dev.sh restart"
    echo "  ./dev.sh reset-db"
    ;;
esac
