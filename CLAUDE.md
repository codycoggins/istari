# Istari — Claude Working Context

See `istari-project-outline.md` for the full project specification.

## Current Status
- **Phase 1 (MVP): COMPLETE**
- **Phase 2 — Notification + Gmail + Proactive Agent: COMPLETE**
- **Phase 3: ReAct tool-calling agent + Apple Calendar impl COMPLETE**
- **Phase 4: Memory architecture COMPLETE** — 206 backend tests, ruff clean
- **Phase 5: Eisenhower matrix COMPLETE**
- **Phase 6: MCP server integration COMPLETE** — 240 backend tests (all passing, no exclusions), ruff clean
- **Apple Calendar status:** EventKit blocked by corporate MDM profile (Abacus IT / SentinelOne). Using `CALENDAR_BACKEND=google` instead. AppleCalendarReader code is complete but unusable in this environment without IT whitelisting.
- All verification checks passing: `pip install`, `ruff check`, `pytest` (excl. test_chat.py), `npm install`, `eslint`, `tsc --noEmit`, `vitest`
- **All 273 tests passing** with no exclusions — `test_chat.py` rewritten for ReAct architecture
- **mypy: PASSING** — `mypy src/` returns 0 errors. `ignore_missing_imports = true` in pyproject.toml suppresses library stub warnings (pgvector, google APIs, apscheduler). Use `dict[str, Any]` for dynamic/JSON dicts (not `dict[str, object]`). Run `mypy src/` to check your work.
- **What's working end-to-end:**
  - **ReAct tool-calling agent** — LangGraph replaced with a manual LiteLLM tool-calling loop; LLM reasons across multiple turns, calling tools as needed before producing a final response
  - WebSocket chat at `/api/chat/ws`
  - LiteLLM routing with sensitive content → local Ollama model
  - Rule-based content classifier (PII, financial, email, file content)
  - TODO CRUD with 5 statuses (open, in_progress, blocked, complete, deferred) + priority-based ordering (API + tool)
  - Explicit memory store with ILIKE search (API + tool)
  - Settings with defaults (quiet hours, focus mode)
  - **Notification queue + badge system** — NotificationManager CRUD, full REST API (list, unread count, mark read, mark all read, mark completed), frontend inbox with badge + completion checkbox (strikethrough, hidden after end of day), 60s polling
  - **TODO tools** — `create_todos` (bulk; auto-classifies urgency/importance via LLM, asks user when uncertain), `list_todos` (filter: open/all/complete, shows quadrant labels), `update_todo_status` (by ID or ILIKE, bulk, synonym normalization), `update_todo_priority` (set urgent/important by ID or ILIKE), `get_priorities` (Q1→Q2→Q3→unclassified→Q4 sort + quadrant labels)
  - **Eisenhower matrix** — `urgent` and `important` nullable Boolean columns on `Todo`; `get_prioritized()` and `list_visible()` use SQLAlchemy `case()` for quadrant sort; `set_urgency_importance()` on TodoManager; frontend TODO sidebar shows color-coded Q1/Q2/Q3/Q4 badges (Do Now / Schedule / Delegate / Drop)
  - **Memory tools** — `remember`, `search_memory`
  - **Gmail/Calendar tools** — `check_email`, `check_calendar` (routes to Google or Apple based on `CALENDAR_BACKEND` setting)
  - **Filesystem tools** — `read_file(path)` (up to 8,000 chars, binary-safe, `~` expansion), `search_files(query, directory, extensions)` (content search, extension filter, 500-file scan cap)
  - **Memory files** — `memory/SOUL.md` (agent personality, checked in), `memory/USER.md` (user profile, gitignored); read fresh on every conversation start; no DB sync needed
  - **build_system_prompt(session)** — assembles prompt from SOUL.md → USER.md (or `user_name` fallback) → top 20 stored memories; replaces hardcoded `_SYSTEM_PROMPT_TEMPLATE`
  - **Persistent conversation history** — `ConversationMessage` table; `ConversationStore.load_history()` returns last 40 turns in chronological order; loaded once at WebSocket connect, saved after each exchange
  - **Post-turn memory extraction** — `memory_extractor.extract_and_store()` fires as `asyncio.create_task()` after each response; LLM extracts memorable facts → stored to `Memory` table (case-insensitive dedup); uses `memory_extraction` LLM task (local model, temperature=0.0)
  - **Gmail reader tool** — OAuth2 read-only, `list_unread()`, `search()`, `get_thread()` via `asyncio.to_thread()`
  - **Calendar reader tool** — OAuth2 read-only, `list_upcoming(days)`, `search()`, `get_event()` via `asyncio.to_thread()`; separate token file from Gmail but reuses same `credentials.json`
  - **LangGraph proactive agent** — background graph with `scan_gmail`, `check_staleness`, `summarize` (LLM), `queue_notifications` nodes; routing by task_type
  - **Worker jobs** — APScheduler with `gmail_digest` (8am + 2pm) and `staleness_check` (8am) from `schedules.yml`; quiet hours enforcement decorator
  - **TODO staleness detection** — `get_stale(days)` finds open/in_progress TODOs not updated in N days
  - **Digest system** — DigestManager CRUD, REST API (`GET /digests/`, `POST /digests/{id}/review`), frontend DigestPanel with expand/collapse + source badges
  - **MCP server integration** — `mcp_servers.yml` (opt-in, `enabled: false` by default); `MCPManager` spawns stdio subprocesses at lifespan start, stores tools in `app.state.mcp_tools`; `build_tools()` merges them after built-ins; failed servers log warning + skip (never crash startup); GitHub server pre-configured (`@modelcontextprotocol/server-github`, needs `GITHUB_TOKEN`)
  - Frontend: WebSocket chat with reconnection, TODO sidebar with live refresh (WebSocket signals + 15s polling), settings panel, notification inbox with unread badge, digest panel; full dark wizard aesthetic (deep navy + gold, Cinzel font); TODO inline edit modal with all fields + Save/Escape/backdrop-close
- **DB migrations:** all tables exist and are up to date (digests, conversation_messages, eisenhower fields all applied)
- **Gmail setup:** Run `python scripts/setup_gmail.py` after placing `credentials.json` in `secrets/` (Google Cloud OAuth Desktop App) — writes `secrets/gmail_token.json`
- **Calendar setup:** Run `python scripts/setup_calendar.py` — reuses same `secrets/credentials.json`, writes `secrets/calendar_token.json`
- **Next up:**
  - pgvector semantic search for memories (column exists, search not wired up)
  - Focus mode enforcement in proactive agent
  - Frontend logging panel or log streaming for visibility into agent tool calls
  - Context compaction — summarize conversation turns older than 40 before they're dropped
- **Security hardening (Phase 7 — in progress):**
  1. **Docker networking** — COMPLETE: removed `ports` from `postgres` and `api`; explicit `internal` bridge network; `scripts/prod.sh` uses base compose only
  2. **Authentication** — COMPLETE: `itsdangerous` signed cookies; `AuthMiddleware` (pure ASGI); `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`; WS checks `ws.cookies` before accept; close code 4401 triggers frontend login wall; auth disabled when `APP_SECRET_KEY` unset
  3. **nginx security headers** — COMPLETE: extracted to `frontend/nginx.conf`; `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, CSP whitelist; HSTS omitted (nginx can't detect HTTPS vs HTTP)
  4. **Rate limiting on LLM endpoints** — COMPLETE: per-connection sliding-window rate limiter (`_RateLimiter`, deque + `time.monotonic`); 20 msg/60s on WebSocket; REST endpoints skipped (not needed for local use)
  5. **Audit credential files + fix default password** — COMPLETE: `secrets/` directory (gitignored); `credentials.json`, `gmail_token.json`, `calendar_token.json` all moved under `secrets/`; `POSTGRES_PASSWORD:-changeme` replaced with `:?` fail-loud syntax in docker-compose.yml; setup scripts updated
  6. **Ollama exposure audit** — verify Ollama binds to `127.0.0.1` not `0.0.0.0`; document `OLLAMA_HOST=127.0.0.1` in `.env.example`

## Development Commands
- **Venv:** `source backend/.venv/bin/activate` — always activate before running backend commands; after creating/recreating the venv run `pip install -e ".[dev]"` to install all deps (including `google-auth`, `google-api-python-client`, etc.)
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
- `./scripts/prod.sh` — start full stack in prod mode
- `./scripts/reset-db.sh` — drop + recreate + migrate database
- `./scripts/seed.sh` — seed dev data (placeholder)
- `python scripts/setup_gmail.py` — OAuth2 Gmail setup (requires `credentials.json` from Google Cloud Console)
- `python scripts/setup_calendar.py` — OAuth2 Calendar setup (reuses same `credentials.json`; writes separate `calendar_token.json`)
- `cd backend && python -c "import asyncio; from istari.worker.jobs.backup import run_backup; asyncio.run(run_backup())"` — trigger a backup immediately (requires `BACKUP_ENABLED=true` and `BACKUP_PASSPHRASE` set in `.env`)
- `./scripts/restore_db.sh <file.dump.enc>` — decrypt and restore a backup (prompts for passphrase)

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

### ReAct Tool-Calling Agent (replacing Phase 1 intent classification)
- **Architecture**: LangGraph ReAct loop — `agent_node` (LLM with tools) ↔ `tools_node` (executes calls) → repeat until final response
- **Why**: linear classify→act cannot do multi-step reasoning (e.g., read file → extract items → create todos); tool calling handles bulk ops, synonyms, pattern matching naturally
- **Tool registration**: `@tool`-decorated async functions in `agents/tools/` — each group (todo, memory, gmail, calendar, filesystem) in its own module; agent built from a flat list of all tools
- **DB injection**: tools need `AsyncSession`; session is provided via closure at WebSocket connect time (wrap tool functions with session before passing to agent)
- **MCP path**: `mcp` package (not LangChain) — `ClientSession` from `mcp`; `StdioServerParameters`+`stdio_client` from `mcp.client.stdio`; tools stored in `app.state.mcp_tools` at lifespan; accessed in routes via `getattr(ws.app.state, "mcp_tools", [])`
- **Model requirement**: tool calling needs a capable model — `gpt-4o` for primary agent; local models for summarization/classification subtasks only
- **Status synonyms**: normalize in tool layer before DB write — "done/finished/completed" → complete, "started/working on" → in_progress, "stuck/waiting" → blocked, "postpone/later/skip" → deferred
- **Old `chat.py` agent**: replaced entirely; `proactive.py` (worker) is unaffected and stays as-is
- **What stays**: WebSocket transport, all Manager classes (TodoManager, GmailReader, etc.), frontend, LiteLLM routing

### Memory Architecture Decisions (Phase 4)
- **SOUL.md and USER.md are files, not DB rows** — single source of truth; user edits them directly; no sync layer needed; read fresh on each conversation start (not cached at import time)
- **Memory directory**: `memory/` at project root — `memory/SOUL.md` (personality), `memory/USER.md` (user profile); later: `memory/YYYY-MM-DD.md` daily notes
- **SOUL.md replaces hardcoded system prompt personality** — `_build_system_prompt()` reads the file; falls back to a minimal default if file missing
- **USER.md replaces `user_name` setting for identity** — injected after SOUL.md as a "user context" block; `user_name` setting kept for backwards compat but USER.md takes precedence when present
- **System prompt injection order**: SOUL.md content → tool usage guidelines (in code) → USER.md content → top N curated memories from DB → (per-turn: semantically relevant memories added later)
- **Gitignore USER.md by default** — contains personal data; SOUL.md may be checked in (it's agent config, not personal data)
- **Post-turn extraction is async fire-and-forget** — does not block the WebSocket response; runs as `asyncio.create_task()`; failures logged but not surfaced to user
- **Conversation history persistence**: `ConversationMessage(id, session_id, role, content, created_at)` table; load last 40 turns on reconnect; context compaction (summarize turns > 40) deferred to later phase

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
- Config: `backend/src/istari/config/settings.py`, `llm_routing.yml`, `schedules.yml`, `mcp_servers.yml` (MCP server list — add servers here with `enabled: true`)
- Memory files (project root): `memory/SOUL.md` (agent personality), `memory/USER.md` (user profile — gitignored)
- Models: `backend/src/istari/models/` — todo.py, memory.py, digest.py, notification.py, agent_run.py, user.py
- DB session: `backend/src/istari/db/session.py`
- Schemas: `backend/src/istari/api/schemas.py` — all Pydantic request/response models
- Tools: `backend/src/istari/tools/` — base.py, gmail/, filesystem/, calendar/, git/, todo/, memory/, classifier/, notification/, digest/
  - `todo/manager.py` — TodoManager CRUD (list_open, list_visible, get_stale, get_prioritized, set_status), `todo/adapter.py` — TodoStore Protocol
  - `memory/store.py` — MemoryStore (explicit memory, ILIKE search)
  - `classifier/rules.py` — rule-based sensitivity classifier, `classifier/classifier.py` — async wrapper
  - `notification/manager.py` — NotificationManager CRUD (create, list_recent, get_unread_count, mark_read, mark_all_read, mark_completed)
  - `gmail/reader.py` — GmailReader (list_unread, search, get_thread) with OAuth2 token
  - `calendar/reader.py` — CalendarReader (Google, OAuth2); `apple_calendar/reader.py` — AppleCalendarReader (EventKit, no auth); `CalendarEvent` dataclass shared between both
  - `digest/manager.py` — DigestManager CRUD (create, list_recent, mark_reviewed)
  - `mcp/client.py` — `MCPServerConfig`, `load_mcp_server_configs()`, `MCPManager` async context manager, `mcp_tool_to_agent_tool()`
- Agents: `backend/src/istari/agents/` — chat.py (ReAct agent loop + `build_tools`/`run_agent`), tools/ (todo.py, memory.py, gmail.py, calendar.py, base.py), proactive.py (LangGraph proactive graph), memory.py (stub)
- LLM routing: `backend/src/istari/llm/router.py` (LiteLLM wrapper) + `config.py` (YAML loader)
- API routes: `backend/src/istari/api/routes/` — chat.py (REST + WebSocket), todos.py, notifications.py, digests.py, memory.py, settings.py
- API deps: `backend/src/istari/api/deps.py`
- Worker jobs: `backend/src/istari/worker/jobs/` — gmail_digest.py, staleness.py, backup.py (implemented); learning.py (stub)
- Frontend components: `frontend/src/components/Chat/`, `frontend/src/components/TodoPanel/`, `frontend/src/components/NotificationInbox/`, `frontend/src/components/DigestPanel/`
- Frontend hooks: `frontend/src/hooks/useChat.ts` (WebSocket), `useTodos.ts`, `useSettings.ts`, `useNotifications.ts`, `useDigests.ts`
- Frontend API client: `frontend/src/api/client.ts`, `todos.ts`, `settings.ts`, `notifications.ts`, `digests.ts`, `chat.ts`
- Tests: `backend/tests/` (conftest.py with SQLite fixture, unit/, integration/, fixtures/)
  - `unit/test_agents/test_chat.py` — old intent graph tests (35 tests, pre-existing import error — superceded by new tests)
  - `unit/test_agents/test_agent_tools.py` — ReAct tool tests: normalize_status, create/update/list/priorities, memory, schema validation, run_agent mocked loop (32 tests)
  - `unit/test_agents/test_proactive.py` — proactive agent node tests (10 tests)
  - `unit/test_classifier/` — rules + tool wrapper (23 tests)
  - `unit/test_llm/` — router + config (14 tests)
  - `unit/test_models/` — enum value + SQLAlchemy enum `values_callable` guard (2 tests)
  - `unit/test_tools/` — TodoManager + MemoryStore + NotificationManager + GmailReader + CalendarReader + DigestManager + MCPClient (73 tests)
  - `unit/test_worker/` — worker job tests + quiet hours (5 tests)
  - `fixtures/llm_responses.py` — canned LiteLLM mock responses
- Auth: `backend/src/istari/api/auth.py` (token sign/verify), `api/middleware/auth.py` (ASGI middleware), `api/routes/auth.py` (login/logout/me); frontend: `frontend/src/api/auth.ts`, `frontend/src/components/Login/LoginPage.tsx`
- Scripts: `scripts/dev.sh` (hot reload, debug ports open), `scripts/prod.sh` (no debug ports), `scripts/reset-db.sh`, `scripts/seed.sh`, `scripts/setup_gmail.py`, `scripts/setup_calendar.py`, `scripts/restore_db.sh`

## Patterns to Follow
- **API routes**: use `DB = Annotated[AsyncSession, Depends(get_db)]` type alias, not inline `Depends()`
- **Tools take `session` in constructor**: `TodoManager(session)`, `MemoryStore(session)` — not global
- **Tests**: pure logic tests need no DB fixture; CRUD tests use `db_session` fixture from conftest
- **Adding a new agent tool**: create an `async def my_tool(...)` closure inside a `make_*_tools(session, context)` factory function in `agents/tools/`; add an `AgentTool(name, description, parameters, fn)` to the returned list; add the factory to `build_tools()` in `agents/chat.py`. No other changes needed.
- **AgentTool parameters**: use JSON Schema "parameters" object format (`{"type": "object", "properties": {...}, "required": [...]}`) — same as OpenAI function calling. Keep descriptions concise (under 100 chars) to avoid E501.
- **Status synonym normalization**: `normalize_status()` in `agents/tools/base.py` maps "done/finished" → complete, "started/working on" → in_progress, "stuck/waiting" → blocked, "postpone/later" → deferred; called in `update_todo_status` before DB write.
- **Bulk ILIKE update pattern**: `update_todo_status(query, status)` fetches ALL todos matching `ILIKE %query%` and updates each; numeric ID takes precedence over pattern match.
- **DB session in tools**: tools receive `session` via closure (not dependency injection) — `make_*_tools(session, context)` factory binds the session; `context` (AgentContext dataclass) tracks side effects (todo_created, todo_updated, memory_created) for frontend refresh signals.
- **run_agent**: in `agents/chat.py`; calls LiteLLM `completion("chat_response", messages, tools=schemas, tool_choice="auto")`; loops until no tool_calls in response; max 8 turns; returns final content string.
- **user_name setting**: `USER_NAME=` in `.env` → injected into agent system prompt as "The user's name is {name}" — enables queries like "find action items assigned to Cody"
- **Classifier**: add new rules to `_RULES` list in `rules.py` as `(flag, rule_name, pattern)` tuples
- **LLM model config**: update `llm_routing.yml`, never hardcode model names in code
- **Frontend state**: prop drilling from App.tsx; `useChat` returns `sendMessage`, `useTodos` returns `refresh`, `useNotifications` returns `markRead`, `markAllAsRead`, `markCompleted`, `refresh`
- **Notifications**: `NotificationManager(session)` follows same pattern as TodoManager; API routes follow same `DB = Annotated[...]` pattern; frontend polls every 60s for badge updates
- **TodoStatus enum**: 5 values — `open`, `in_progress`, `blocked`, `complete`, `deferred`; `list_open()` returns `open` + `in_progress` + `blocked` (actionable); `get_prioritized()` returns `open` + `in_progress`
- **Eisenhower matrix**: `urgent: bool | None` and `important: bool | None` on `Todo`; quadrant sort via SQLAlchemy `case()` (Q1=1, Q2=2, Q3=3, unclassified=4, Q4=5); `set_urgency_importance(todo_id, urgent, important)` on TodoManager; `_QUADRANT_LABELS` dict in `agents/tools/todo.py` maps `(urgent, important)` tuples → label strings; `todo_classification` LLM task (local, temp=0.0)
- **TODO status updates via chat**: `todo_update` intent; LLM extracts `{"identifier", "target_status"}` JSON; handler finds by ID then title ILIKE; `set_status()` convenience method on TodoManager
- **Gmail scan via chat**: `gmail_scan` intent; handler creates GmailReader, calls list_unread/search, summarizes via LLM
- **Proactive agent**: LangGraph `StateGraph` in `proactive.py`; nodes are pure, worker jobs persist results via `NotificationManager`; routing by `task_type` (gmail_digest, morning_digest, staleness_only)
- **Worker quiet hours**: `respect_quiet_hours(fn)` decorator checks `settings.quiet_hours_start/end` before running; jobs read cron from `schedules.yml`
- **Digests**: `DigestManager(session)` follows same pattern as NotificationManager; API routes follow same `DB = Annotated[...]` pattern; frontend DigestPanel polls every 60s via `useDigests` hook
- **GmailReader / CalendarReader**: both wrap sync Google API in `asyncio.to_thread()`; token loaded from path at construction; expired tokens auto-refreshed and re-saved. CalendarReader reuses same `credentials.json` OAuth app but writes to `calendar_token.json`.
- **Filesystem tools**: `make_filesystem_tools()` needs no args (no session, no context); `read_file` expands `~` via `Path.expanduser()`, relative paths resolve from `Path.home()`; truncates at 8,000 chars; binary files return error string (not exception). `search_files` uses `search_text_in_files()` from `tools/filesystem/search.py`; scans up to 500 files, returns up to 10 results with preview line.
- **AppleCalendarReader**: EventKit via `pyobjc-framework-EventKit` (optional dep `pip install -e ".[apple]"`); macOS only; no token file — OS permission stored in system. macOS 14+ needs `requestFullAccessToEventsWithCompletion_`, older uses `requestAccessToEntityType_completion_`. Search fetches wide window (±30/90 days) and filters locally (EventKit has no server-side text search). Authorization status 3 = full access. Tests mock entire `EventKit` and `Foundation` modules via `monkeypatch.setitem(sys.modules, ...)`.
- **calendar_backend setting**: `CALENDAR_BACKEND=apple` or `google` (default) — routes `check_calendar` agent tool; `scripts/setup_apple_calendar.py` triggers the OS permission dialog on first use.
- **Google API tool tests**: mock both `Credentials.from_authorized_user_file` and `googleapiclient.discovery.build` at the tool's module path (not google's); create a fake token file via `tmp_path`; set `mock_creds.expired = False`. See `test_gmail_reader.py` as canonical example.
- **routes/chat.py elif variable names**: don't reuse the same variable name (e.g. `reader`) across `elif` branches — mypy infers type from first assignment and flags later branches as incompatible. Use distinct names (`gmail_reader`, `cal_reader`, etc.)
- **ruff RUF012**: class-level mutable defaults (list, dict) require `ClassVar` annotation — `SCOPES: ClassVar[list[str]] = [...]`
- **SQLAlchemy async + Pydantic**: always `await db.refresh(obj)` after `await db.commit()` before calling `model_validate(obj)` — commit expires all ORM attributes; accessing them outside the async context causes `MissingGreenlet` crash
- **LLM classification model**: use `mistral:7b-instruct-q8_0` for the `classification` task — Mistral reliably outputs structured JSON at temperature 0.0; llama3.1 can return empty strings at low temperature causing silent fallback to `chat` intent
- **Robust LLM JSON parsing**: `_extract_json()` in `chat.py` strips markdown fences (` ```json `) and finds the first `{...}` block — guards against models that wrap JSON in preamble text; always log raw response at DEBUG before parsing
- **Frontend prop-wiring pattern**: when a parent needs to call a function owned by a child, add `onRegisterSend?: (fn) => void` prop; child calls it in `useEffect([..., fn])`. Test all three layers: child calls the prop, the prop receives the real function, and an App-level test confirms end-to-end button → sendMessage
- **Frontend wiring tests**: mock `useChat` with `vi.mock("../../src/hooks/useChat", () => ({ useChat: () => ({ sendMessage: mockFn, ... }) }))` — see `ChatPanel.test.tsx` as canonical example
- **Backend logging**: `logging.basicConfig()` in FastAPI `lifespan` wires `LOG_LEVEL` env var; agent tool calls logged at INFO with `"Tool call | %-24s | %.0fms | %d chars returned"` format; tool arguments at DEBUG only (may contain PII); agent start/finish at INFO with elapsed time; use `logger = logging.getLogger(__name__)` per module
- **build_system_prompt(session, user_name="")**: async function in `agents/chat.py`; reads SOUL.md and USER.md via `_read_memory_file(filename)` (sync, returns "" if missing); falls back to USER.md → `user_name` setting for identity; loads `MemoryStore.list_explicit()` for injection; called inside the `async_session_factory()` block in `routes/chat.py`
- **ConversationStore**: `tools/conversation/store.py`; `load_history()` returns last 40 turns oldest-first; `save_turn(user, assistant)` adds two rows and flushes; loaded once at WebSocket connect, saved after each response before `send_json`
- **Memory extractor**: `agents/memory_extractor.py`; `extract_and_store(user_msg, asst_msg, session_factory)` — fire-and-forget; patches: `istari.agents.memory_extractor.completion` and `istari.agents.memory_extractor.MemoryStore` for tests; `# noqa: RUF006` on `asyncio.create_task()` call
- **SOUL.md / USER.md editing**: users edit `memory/SOUL.md` (personality) and `memory/USER.md` (profile) directly; changes take effect on next message with no restart; USER.md gitignored; USER.md.example committed as a template
- **Adding a new MCP server**: add an entry to `mcp_servers.yml` with `enabled: true` and required env vars; set the env var in `.env`; no code changes needed — tools auto-load at startup
- **MCP tool tests**: patch `istari.tools.mcp.client.stdio_client` and `istari.tools.mcp.client.ClientSession` with `@asynccontextmanager` functions via `monkeypatch.setattr`; use `monkeypatch.setattr("istari.tools.mcp.client._CONFIG_DIR", tmp_path)` to redirect config loading in unit tests
- **`docker exec` + pg_dump**: always pass `-U {username}` — without it pg_dump connects as the OS user (often `root`), which has no PostgreSQL role and fails. Pass the password via `docker exec -e PGPASSWORD container pg_dump -U user ...` where `PGPASSWORD` is set in the docker client's env; `-e PGPASSWORD` (no `=value`) forwards it into the container without exposing it in `ps aux`.
- **Parsing DATABASE_URL**: use `urlparse(database_url.replace("+asyncpg", ""))` to extract username/password/dbname — strip the driver suffix first or urlparse won't parse the scheme correctly.
- **Worker maintenance jobs skip `respect_quiet_hours`**: digest/staleness use the decorator because they're user-facing; backup does not — 2am is inside quiet hours (21:00–07:00) but maintenance must run regardless.
- **Docker DATABASE_URL must use service name, not localhost**: `.env` has `localhost:5432` for local dev; inside Docker `localhost` resolves to the container itself. Override in `docker-compose.yml` with `environment: DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}` — the `environment` block takes precedence over `env_file`.
- **Docker Ollama URL must use `host.docker.internal`**: `.env` has `OLLAMA_BASE_URL=http://localhost:11434` for local dev; inside Docker `localhost` is the container. Override in `docker-compose.yml` with `OLLAMA_BASE_URL: http://host.docker.internal:11434` on both `api` and `worker` services. `host.docker.internal` is a Docker Desktop built-in that resolves to the Mac host from any container.
- **nginx WebSocket proxying requires Upgrade headers**: without `proxy_set_header Upgrade $http_upgrade` and `proxy_set_header Connection "upgrade"`, nginx serves the SPA fallback (index.html, 200 + ~435 bytes) for WebSocket requests instead of proxying them — the telltale sign is `GET /api/chat/ws HTTP/1.1" 200 435` in nginx logs. Also set `proxy_read_timeout 86400` to prevent nginx closing idle WebSocket connections.
- **`tsc -b` vs `tsc --noEmit` behave differently**: `npm run typecheck` uses `--noEmit` (lenient); Docker build uses `tsc -b` (project references, emits files, stricter). `allowImportingTsExtensions` is only valid with `noEmit`; Vitest config must live in a separate `vitest.config.ts` (importing from `vitest/config`) so `vite.config.ts` stays clean for `tsc -b`.
- **Browser 304 cache can mask Docker proxy failures**: REST calls returning 304 may be served from browser cache even when nginx isn't proxying `/api` at all — WebSocket connections don't cache and reveal the true state. Hard-refresh (`Cmd+Shift+R`) after fixing nginx config.
- **httpx.ASGITransport for FastAPI tests**: use `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")` — the old `httpx.AsyncClient(app=app)` positional form is deprecated; see `tests/unit/test_api/test_auth.py` as canonical example
- **Pure ASGI middleware**: prefer `class MyMiddleware` with `async def __call__(self, scope, receive, send)` over `BaseHTTPMiddleware` — no response buffering, works correctly with WebSocket upgrades; check `scope["type"] == "websocket"` to pass WS through and let endpoint handle its own auth; parse cookies from headers with `SimpleCookie()` from `http.cookies`
- **WebSocket close code 4401**: application-reserved codes 4000–4999 signal app-level errors; 4401 = auth failure — backend does `await ws.accept(); await ws.close(code=4401)`; frontend checks `event.code === 4401` in `ws.onclose` and calls `onAuthFailure` instead of triggering reconnect
- **Auth enabled/disabled pattern**: `APP_SECRET_KEY` empty → middleware and `/me` pass everything through (dev convenience); set both `APP_SECRET_KEY` and `APP_PASSWORD` in `.env` to enforce auth; use `secrets.compare_digest` for constant-time password comparison; `response.delete_cookie` must pass the same `httponly`, `secure`, `samesite`, `path` kwargs as `set_cookie` or the browser won't honour the deletion
- **`.env.example` is not readable via `Read` tool or `cat`**: permission denied by Claude Code settings; use `git diff HEAD .env.example` to inspect its contents
