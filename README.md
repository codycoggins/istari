# Istari

AI personal assistant for task management, information surfacing, and proactive scheduling. Privacy-first, read-only to external services, ADHD-optimized UX.

See [istari-project-outline.md](istari-project-outline.md) for the full project specification.

## Quick Start

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 2. Start all services
docker compose up

# 3. Access the UI
open http://localhost:3000
```

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run API server with hot reload
uvicorn istari.api.main:app --reload

# Run worker
python -m istari.worker.main

# Run tests
pytest

# Lint + type check
ruff check src/ tests/
mypy src/
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # Vite dev server on :3000
npm run lint      # ESLint
npm run typecheck # TypeScript check
npm test          # Vitest
```

### Database

```bash
# Run migrations
cd backend
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Reset database
./scripts/reset-db.sh
```

### Docker Compose

```bash
# Production-like
docker compose up --build

# Dev mode (hot reload, debug logging)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Architecture

- **API service** — FastAPI: chat agent, on-demand queries, notification serving
- **Worker service** — APScheduler: proactive agent, Gmail digests, TODO staleness checks
- **Frontend** — React + TypeScript (Vite): split-panel chat + TODO UI
- **Database** — PostgreSQL + pgvector: shared between API and worker

API and worker are separate processes sharing the same Python package (`istari`). The worker communicates with the API via the database (notification rows), never in-process.
