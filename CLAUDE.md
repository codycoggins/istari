# Istari — Claude Working Context

See `istari-project-outline.md` for the full project specification.

## Current Status
- Project scaffolding: **in progress — ~80% complete**
- Root config files: DONE (.gitignore, .env.example, docker-compose.yml, docker-compose.dev.yml, README.md, .github/workflows/ci.yml)
- Backend Python package (`backend/src/istari/`): DONE — all modules created as stubs
- Frontend React/Vite app (`frontend/`): DONE — all components, hooks, types, API layer created as stubs
- **REMAINING WORK (not yet done):**
  1. `scripts/dev.sh`, `scripts/reset-db.sh`, `scripts/seed.sh` — not created yet
  2. `backend/tests/conftest.py` — not created yet
  3. Placeholder test in `backend/tests/` — not created yet
  4. `backend/tests/unit/` and `backend/tests/integration/` — directories exist but no files
  5. `backend/tests/fixtures/` subdirs (gmail/, calendar/, git/) — directories exist but no .gitkeep
  6. Update this CLAUDE.md with dev commands (this update)
  7. **Verification**: `pip install -e ".[dev]"`, import checks, `pytest`, `npm install && npm run dev` — not yet run

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
- `cd frontend && npm run typecheck` — TypeScript check
- `cd frontend && npm test` — Vitest
- `docker compose up --build` — run all services
- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` — dev mode with hot reload

## Architecture Decisions
- **src-layout**: `backend/src/istari/` — Python package installed via `pip install -e .`, both api and worker import as `from istari.X import ...`
- **Single pyproject.toml**: one Python package for backend; api + worker share >70% of code (agents, tools, models, llm)
- **Single Dockerfile**: `backend/Dockerfile` builds the package; docker-compose overrides CMD per service (uvicorn for api, python -m for worker)
- **Alembic migrations outside package**: `backend/migrations/` — operational artifacts, not importable code; `env.py` imports `istari.models`
- **YAML config inside package**: `istari/config/llm_routing.yml` and `schedules.yml` — included when package is installed
- **Pydantic Settings**: `istari/config/settings.py` merges .env secrets with YAML config
- **hatchling** as build backend (pyproject.toml)
- **pgvector/pgvector:pg16** Docker image for PostgreSQL with vector support
- **Frontend**: standalone Vite + React 19 + TypeScript, communicates via API only, own Dockerfile (multi-stage: node build → nginx serve)

## Key File Locations
- Backend entry points: `backend/src/istari/api/main.py` (FastAPI app), `backend/src/istari/worker/main.py` (APScheduler)
- Models: `backend/src/istari/models/` — todo.py, memory.py, digest.py, notification.py, agent_run.py, user.py
- Tools: `backend/src/istari/tools/` — gmail/, filesystem/, calendar/, git/, todo/, memory/, classifier/
- Agents: `backend/src/istari/agents/` — chat.py, proactive.py, memory.py
- LLM routing: `backend/src/istari/llm/router.py` + `config.py`, configured via `config/llm_routing.yml`
- API routes: `backend/src/istari/api/routes/` — chat.py, todos.py, notifications.py, memory.py, settings.py
- Frontend components: `frontend/src/components/Chat/`, `frontend/src/components/TodoPanel/`
- Frontend hooks: `frontend/src/hooks/useChat.ts`, `useTodos.ts`, `useNotifications.ts`
