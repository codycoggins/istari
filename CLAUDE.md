# Istari — Claude Working Context

See `istari-project-outline.md` for the full project specification.

## Current Status
- **Project scaffolding: COMPLETE**
- All verification checks passing: `pip install`, imports, `ruff check`, `pytest`, `npm install`, `eslint`, `tsc --noEmit`, `vitest`
- **Next up: Phase 1 implementation** (see `istari-project-outline.md` Section 12)
  - PostgreSQL + pgvector schema (run `alembic revision --autogenerate` to generate initial migration)
  - LiteLLM integration + content classifier
  - Chat agent (LangGraph)
  - TODO CRUD (todo_manager tool + API routes)
  - Memory store (explicit memory only)
  - Phase 1 Web UI wiring (chat + TODO sidebar functional)

## Development Commands
- `cd backend && pip install -e ".[dev]"` — install backend package in editable mode with dev deps
- `cd backend && uvicorn istari.api.main:app --reload` — run API server with hot reload
- `cd backend && python -m istari.worker.main` — run worker
- `cd backend && pytest` — run backend tests
- `cd backend && ruff check src/ tests/` — lint backend
- `cd backend && mypy src/` — type check backend
- `cd backend && alembic upgrade head` — run DB migrations
- `cd backend && alembic revision --autogenerate -m "description"` — create new migration
- `cd frontend && npm install` — install frontend deps
- `cd frontend && npm run dev` — Vite dev server on :3000
- `cd frontend && npm run lint` — ESLint
- `cd frontend && npm run typecheck` — TypeScript check (`tsc --noEmit`)
- `cd frontend && npm test` — Vitest
- `docker compose up --build` — run all services
- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` — dev mode with hot reload
- `./scripts/dev.sh` — start full stack in dev mode (copies .env.example if needed)
- `./scripts/reset-db.sh` — drop + recreate + migrate database
- `./scripts/seed.sh` — seed dev data (placeholder)

## Architecture Decisions
- **src-layout**: `backend/src/istari/` — Python package installed via `pip install -e .`, both api and worker import as `from istari.X import ...`
- **Single pyproject.toml**: one Python package for backend; api + worker share >70% of code (agents, tools, models, llm)
- **hatchling** as build backend
- **Single Dockerfile**: `backend/Dockerfile` builds the package; docker-compose overrides CMD per service (uvicorn for api, `python -m` for worker)
- **Alembic migrations outside package**: `backend/migrations/` — operational artifacts, not importable code; `env.py` imports `istari.models`
- **YAML config inside package**: `istari/config/llm_routing.yml` and `schedules.yml` — included when package is installed
- **Pydantic Settings**: `istari/config/settings.py` merges .env secrets with YAML config
- **pgvector/pgvector:pg16** Docker image for PostgreSQL with vector support
- **Frontend**: standalone Vite + React 19 + TypeScript, communicates via API only, own Dockerfile (multi-stage: node build → nginx serve)
- **Enums use `enum.StrEnum`** (Python 3.12+)

## Key File Locations
- Backend entry points: `backend/src/istari/api/main.py` (FastAPI app), `backend/src/istari/worker/main.py` (APScheduler)
- Config: `backend/src/istari/config/settings.py`, `llm_routing.yml`, `schedules.yml`
- Models: `backend/src/istari/models/` — todo.py, memory.py, digest.py, notification.py, agent_run.py, user.py
- DB session: `backend/src/istari/db/session.py`
- Tools: `backend/src/istari/tools/` — base.py, gmail/, filesystem/, calendar/, git/, todo/, memory/, classifier/
- Agents: `backend/src/istari/agents/` — chat.py, proactive.py, memory.py
- LLM routing: `backend/src/istari/llm/router.py` + `config.py`
- API routes: `backend/src/istari/api/routes/` — chat.py, todos.py, notifications.py, memory.py, settings.py
- API deps: `backend/src/istari/api/deps.py`
- Worker jobs: `backend/src/istari/worker/jobs/` — gmail_digest.py, staleness.py, learning.py
- Frontend components: `frontend/src/components/Chat/`, `frontend/src/components/TodoPanel/`
- Frontend hooks: `frontend/src/hooks/useChat.ts`, `useTodos.ts`, `useNotifications.ts`
- Frontend API client: `frontend/src/api/client.ts`
- Tests: `backend/tests/` (conftest.py, unit/, integration/, fixtures/)
- Scripts: `scripts/dev.sh`, `scripts/reset-db.sh`, `scripts/seed.sh`
