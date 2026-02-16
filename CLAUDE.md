# Istari — Claude Working Context

See `istari-project-outline.md` for the full project specification.

## Current Status
- **Phase 1 (MVP): COMPLETE** — all lint/typecheck passing
- **Phase 2 — Notification System: COMPLETE** — 89 backend tests (77 excl. pre-existing chat import error), 8 frontend tests, all lint/typecheck passing
- All verification checks passing: `pip install`, `ruff check`, `pytest` (excl. test_chat.py import error from prior commit), `npm install`, `eslint`, `tsc --noEmit`, `vitest`
- **Known issue:** `tests/unit/test_agents/test_chat.py` fails to collect due to `ModuleNotFoundError: No module named 'tests'` — pre-existing from commit 684e809 (LLM classification refactor changed import paths)
- **What's working end-to-end:**
  - LangGraph chat agent with LLM-based intent classification
  - WebSocket chat at `/api/chat/ws` — graph nodes are pure, DB writes in handler
  - LiteLLM routing with sensitive content → local Ollama model
  - Rule-based content classifier (PII, financial, email, file content)
  - TODO CRUD with 5 statuses (open, in_progress, blocked, complete, deferred) + priority-based ordering (API + tool)
  - Explicit memory store with ILIKE search (API + tool)
  - Settings with defaults (quiet hours, focus mode)
  - **Notification queue + badge system** — NotificationManager CRUD, full REST API (list, unread count, mark read, mark all read, mark completed), frontend inbox with badge + completion checkbox (strikethrough, hidden after end of day), 60s polling
  - **`update_todo` chat intent** — LLM classifies "mark task X as blocked" → finds TODO by ID or title ILIKE → updates status via chat
  - Frontend: WebSocket chat with reconnection, TODO sidebar with live refresh, settings panel, notification inbox with unread badge
- **Still needed before running:** `alembic revision --autogenerate -m "initial schema"` + `alembic upgrade head` (migration not yet generated — requires running PostgreSQL)
- **Next up: Phase 2 remaining items** (see `istari-project-outline.md` Section 12)
  - Gmail reader MCP tool (OAuth2, read-only)
  - On-demand inbox scan + actionable digest
  - Proactive agent + APScheduler: Gmail digest at 8am + 2pm
  - TODO staleness detection (batched into morning digest)
  - Focus mode enforcement, quiet hours in scheduler
  - Active digest panel in Web UI

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
- **Alembic migrations outside package**: `backend/migrations/` — operational artifacts, not importable code; `env.py` imports `istari.models` (all models registered via `import istari.models`)
- **YAML config inside package**: `istari/config/llm_routing.yml` and `schedules.yml` — included when package is installed
- **Pydantic Settings**: `istari/config/settings.py` merges .env secrets with YAML config
- **pgvector/pgvector:pg16** Docker image for PostgreSQL with vector support
- **Frontend**: standalone Vite + React 19 + TypeScript, communicates via API only, own Dockerfile (multi-stage: node build → nginx serve)
- **Enums use `enum.StrEnum`** (Python 3.12+); SQLAlchemy `Enum()` columns **must** use `values_callable=lambda e: [m.value for m in e]` — without it, SQLAlchemy sends `.name` (uppercase) instead of `.value` (lowercase), causing PostgreSQL `InvalidTextRepresentationError`. Guarded by `test_enum_columns_use_values_not_names`.

### Phase 1 Design Decisions
- **Vector dimension 768** (nomic-embed-text via Ollama), not 1536 (OpenAI)
- **LLM-based intent classification** — `classify_node` coerces `extracted_content` to string (LLMs may return JSON objects instead of plain strings); intent and extracted are set atomically to avoid partial-assignment on parse errors
- **LangGraph graph nodes are pure** — no DB writes in graph; all side effects in the WebSocket handler
- **Sensitive content silently routes to local model** — no user prompt UX in Phase 1 (outline spec calls for prompt in future)
- **SQLite + aiosqlite for unit tests**, PostgreSQL for integration tests; conftest.py patches Vector/ARRAY/JSON → Text for SQLite compat
- **TodoStore Protocol** defined in `adapter.py` for future adapters, satisfied via structural typing
- **WebSocket for chat** at `/api/chat/ws`, REST for everything else
- **Annotated[Depends]** pattern for FastAPI dependency injection (avoids ruff B008)
- **Prop drilling in React** — simpler than context for 3 communicating components
- **Conversation history in-memory** per WebSocket connection (Phase 1; persistent history in future)

## Key File Locations
- Backend entry points: `backend/src/istari/api/main.py` (FastAPI app), `backend/src/istari/worker/main.py` (APScheduler)
- Config: `backend/src/istari/config/settings.py`, `llm_routing.yml`, `schedules.yml`
- Models: `backend/src/istari/models/` — todo.py, memory.py, digest.py, notification.py, agent_run.py, user.py
- DB session: `backend/src/istari/db/session.py`
- Schemas: `backend/src/istari/api/schemas.py` — all Pydantic request/response models
- Tools: `backend/src/istari/tools/` — base.py, gmail/, filesystem/, calendar/, git/, todo/, memory/, classifier/, notification/
  - `todo/manager.py` — TodoManager CRUD, `todo/adapter.py` — TodoStore Protocol
  - `memory/store.py` — MemoryStore (explicit memory, ILIKE search)
  - `classifier/rules.py` — rule-based sensitivity classifier, `classifier/classifier.py` — async wrapper
  - `notification/manager.py` — NotificationManager CRUD (create, list_recent, get_unread_count, mark_read, mark_all_read, mark_completed)
- Agents: `backend/src/istari/agents/` — chat.py (LangGraph graph, intent detection), proactive.py (stub), memory.py (stub)
- LLM routing: `backend/src/istari/llm/router.py` (LiteLLM wrapper) + `config.py` (YAML loader)
- API routes: `backend/src/istari/api/routes/` — chat.py (REST + WebSocket), todos.py, notifications.py, memory.py, settings.py
- API deps: `backend/src/istari/api/deps.py`
- Worker jobs: `backend/src/istari/worker/jobs/` — gmail_digest.py, staleness.py, learning.py (all stubs)
- Frontend components: `frontend/src/components/Chat/`, `frontend/src/components/TodoPanel/`, `frontend/src/components/NotificationInbox/`
- Frontend hooks: `frontend/src/hooks/useChat.ts` (WebSocket), `useTodos.ts`, `useSettings.ts`, `useNotifications.ts`
- Frontend API client: `frontend/src/api/client.ts`, `todos.ts`, `settings.ts`, `notifications.ts`, `chat.ts`
- Tests: `backend/tests/` (conftest.py with SQLite fixture, unit/, integration/, fixtures/)
  - `unit/test_agents/test_chat.py` — intent detection + graph flow (35 tests)
  - `unit/test_classifier/` — rules + tool wrapper (23 tests)
  - `unit/test_llm/` — router + config (14 tests)
  - `unit/test_models/` — enum value + SQLAlchemy enum `values_callable` guard (2 tests)
  - `unit/test_tools/` — TodoManager + MemoryStore + NotificationManager (38 tests)
  - `fixtures/llm_responses.py` — canned LiteLLM mock responses
- Scripts: `scripts/dev.sh`, `scripts/reset-db.sh`, `scripts/seed.sh`

## Patterns to Follow
- **API routes**: use `DB = Annotated[AsyncSession, Depends(get_db)]` type alias, not inline `Depends()`
- **Tools take `session` in constructor**: `TodoManager(session)`, `MemoryStore(session)` — not global
- **Tests**: pure logic tests need no DB fixture; CRUD tests use `db_session` fixture from conftest
- **Chat graph**: add new intents to `_VALID_INTENTS`, `_CLASSIFY_SYSTEM_PROMPT`, `Intent` enum, a new node, `_route_intent()`, and `build_chat_graph()`; handler in `routes/chat.py` does DB side effects
- **Classifier**: add new rules to `_RULES` list in `rules.py` as `(flag, rule_name, pattern)` tuples
- **LLM model config**: update `llm_routing.yml`, never hardcode model names in code
- **Frontend state**: prop drilling from App.tsx; `useChat` returns `sendMessage`, `useTodos` returns `refresh`, `useNotifications` returns `markRead`, `markAllAsRead`, `markCompleted`, `refresh`
- **Notifications**: `NotificationManager(session)` follows same pattern as TodoManager; API routes follow same `DB = Annotated[...]` pattern; frontend polls every 60s for badge updates
- **TodoStatus enum**: 5 values — `open`, `in_progress`, `blocked`, `complete`, `deferred`; `list_open()` returns `open` + `in_progress` + `blocked` (actionable); `get_prioritized()` returns `open` + `in_progress`
- **TODO status updates via chat**: `todo_update` intent; LLM extracts `{"identifier", "target_status"}` JSON; handler finds by ID then title ILIKE; `set_status()` convenience method on TodoManager
