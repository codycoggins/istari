# Istari — Claude Working Context

See `istari-project-outline.md` for the full project specification.

## Current Status
- **Phases 1–9a complete** — ReAct agent, memory, Eisenhower matrix, MCP integration, security hardening, projects with full UI, proactive project staleness, deadlines + recurrence; cross-client chat history; **383 backend + 38 frontend tests passing**, no exclusions, ruff clean
- **Cross-client chat history (Phase 9a)** — `ConversationStore.load_history()` now returns `id`, `role`, `content`, `created_at` (single DB call, no extra method); `chat.py` strips to `role`+`content` for LLM context, sends `{"type":"history","messages":[...]}` frame to client immediately after `ws.accept()`; `useChat.ts` handles `type=history`: populates messages if state is empty (new tab/refresh), skips if state is non-empty (same-session reconnect)
- **Bug fix: agent hallucinating todo creation** — two-layer fix: (1) `_MEMORY_DIR` in `chat.py` path bug (same `parents[4]` issue as `settings.py`) meant SOUL.md was never loaded in Docker → added `site-packages` detection + `./memory:/app/memory` volume mount; (2) even with SOUL.md loaded the LLM still skipped tool calls → rewrote SOUL.md tool usage as positive "MUST call tool first" instructions + added `_looks_like_mutation()` safety net in `run_agent` that detects turn-1 mutation claims with no tool call and injects a correction prompt to force the tool call on the next turn
- **ProjectCard visual redesign** — restructured to mirror TodoItem's flex layout (content column + edit button at far right); status pill replaced with tag-style badge (same anatomy as quadrant badges: `0.625rem`, `0.4rem` padding); goal, count, next-action, and status all rendered as inline badges on a single tags row; next-action badge uses `border-accent` border + `accent-dim` bg; pencil edit button renamed state to `pencilHovered` to match TodoItem naming
- **Sidebar UX polish** — expand/collapse toggles (▾ chevron) on Projects, Tasks, and Settings panels; collapse state persisted to localStorage (`istari-projects-collapsed`, `istari-tasks-collapsed`, `istari-settings-collapsed`); Settings borderTop hidden when Tasks is collapsed; responsive sidebar width fix: drag-resize only applies on wide screens (>768px), narrow screens use CSS `width: 100%`; `window.matchMedia` mock added to `tests/setup.ts`
- **Apple Calendar:** EventKit blocked by MDM (Abacus IT / SentinelOne) — using `CALENDAR_BACKEND=google`; AppleCalendarReader code complete but unusable without IT whitelisting. All verification checks passing: `pip install`, `ruff check`, `pytest`, `npm install`, `eslint`, `tsc --noEmit`, `vitest`
- **mypy: 1 pre-existing unused-ignore in `tools/mcp/client.py`** — all other files clean. `ignore_missing_imports = true` in pyproject.toml suppresses library stub warnings (pgvector, google APIs, apscheduler). Use `dict[str, Any]` for dynamic/JSON dicts (not `dict[str, object]`). Run `mypy src/` to check your work.
- **What's working end-to-end:**
  - **ReAct tool-calling agent** — manual LiteLLM tool-calling loop replacing LangGraph; LLM reasons across multiple turns before producing a final response; WebSocket chat at `/api/chat/ws`; LiteLLM routing with sensitive content → local Ollama model; rule-based content classifier (PII, financial, email, file content)
  - TODO CRUD with 5 statuses (open, in_progress, blocked, complete, deferred) + priority-based ordering; explicit memory store with ILIKE search; settings with defaults (quiet hours, focus mode)
  - **Notification queue + badge system** — NotificationManager CRUD, full REST API (list, unread count, mark read, mark all read, mark completed), frontend inbox with badge + completion checkbox (strikethrough, hidden after end of day), 60s polling
  - **TODO tools** — `create_todos` (bulk; auto-classifies urgency/importance via LLM, asks user when uncertain), `list_todos` (filter: open/all/complete, shows quadrant labels), `update_todo_status` (by ID or ILIKE, bulk, synonym normalization), `update_todo_priority` (set urgent/important by ID or ILIKE), `get_priorities` (today's goals first, then fills to `priorities_max` via quadrant sort; `get_prioritized` supports `exclude_ids`), `set_today_focus` (mark task for today, soft cap 5), `get_today_focus` (list today's focused tasks)
  - **Todo context panel** — ⓘ button per task triggers mini-agent (`agents/todo_context.py`) that searches memory, Gmail, and calendar; renders markdown summary with hyperlinks inline below the task; `POST /todos/{id}/context` endpoint; `getTodoContext()` in frontend API
  - **Eisenhower matrix** — `urgent` and `important` nullable Boolean columns on `Todo`; `get_prioritized()` and `list_visible()` use SQLAlchemy `case()` for quadrant sort; `set_urgency_importance()` on TodoManager; frontend TODO sidebar shows color-coded Q1/Q2/Q3/Q4 badges (Do Now / Schedule / Contain / Drop); Q3 renamed from "Delegate" to "Contain" for IC/family context; "Other Goals" section heading appears below Today's Goals divider when today tasks are present
  - **Memory tools** — `remember`, `search_memory`; memory files `memory/SOUL.md` (personality) + `memory/USER.md` (profile, gitignored) read fresh each conversation
  - **Gmail/Calendar tools** — `check_email` (optional `max_results`; markdown links to threads), `check_calendar` (routes to Google or Apple via `CALENDAR_BACKEND`; markdown links to events via `html_link`); both wrap sync API in `asyncio.to_thread()`; separate token files, same `credentials.json`
  - **Filesystem tools** — `read_file(path)` (up to 8,000 chars, binary-safe, `~` expansion), `search_files(query, directory, extensions)` (content search, extension filter, 500-file scan cap)
  - **build_system_prompt(session, user_name, user_message)** — assembles SOUL.md → USER.md (or `user_name` fallback) → memories via pgvector cosine search, falling back to newest-20 via `list_explicit()`
  - **Persistent conversation history** — `ConversationMessage` table; last 40 turns loaded at connect, saved after each exchange; **post-turn memory extraction** fires as `asyncio.create_task()` (local model, temperature=0.0, case-insensitive dedup)
  - **LangGraph proactive agent** — background graph with `scan_gmail`, `check_staleness`, `summarize`, `queue_notifications` nodes; APScheduler runs `gmail_digest` (8am + 2pm) and `staleness_check` (8am); `get_stale(days)` finds TODOs not updated in N days
  - **Digest system** — DigestManager CRUD, REST API (`GET /digests/`, `POST /digests/{id}/review`), frontend DigestPanel with expand/collapse + source badges; **MCP integration** — `mcp_servers.yml` (opt-in); `MCPManager` spawns stdio subprocesses at lifespan, tools merged into `app.state.mcp_tools`; failed servers skip startup; GitHub server pre-configured (needs `GITHUB_TOKEN`)
  - **Today's Goals (daily focus)** — `today_date: date | None` column on `Todo`; self-cleaning (filter is `today_date == date.today()`, yesterday's selections vanish at midnight); `list_today()` + `set_today()` on `TodoManager`; `GET /todos/today` + `POST /todos/{id}/today` (toggle); gold target icon per task; "Today's Goals" section at top of `TodoPanel` with `N / 5` counter badge
  - **Projects layer (Phase 8a)** — `Project` model (active/paused/complete status, `next_action_id` FK→todos with `use_alter=True` for circular FK); `Todo.project_id` optional FK; `ProjectManager` (create, list_active, get_by_name ILIKE, set_next_action, set_status, get_stale); 5 agent tools: `create_project`, `list_projects`, `add_todo_to_project`, `set_next_action`, `suggest_next_action` (LLM read-only suggestion); REST API at `/projects/`; `get_priorities` now surfaces project next actions first then standalone todos; `memory/goals.md` (gitignored, `.example` template committed)
  - **Projects UI (Phase 8b)** — `ProjectsPanel` in sidebar: project cards with name, goal subtitle, next-action (gold `→`) marker, active-todo count badge, clickable status badge (cycles active→paused→complete); click card to filter TodoPanel to that project's todos; TodoPanel filter bar (All + per-project pills, 30s polling); `TodoItem` shows gold `→ next` badge on designated next action, subtle project-name pill on other project todos (hidden when filtered to a project); `TodoResponse` now includes `project_id`; `types/project.ts`, `api/projects.ts`, `hooks/useProjects.ts`
  - **Proactive project staleness (Phase 8c)** — `worker/jobs/project_staleness.py`; calls `ProjectManager.get_stale(days=settings.project_staleness_days)`; creates `project_staleness` notification per stale project with nudge text; scheduled Mon/Wed/Fri 8am in `schedules.yml`; respects quiet hours; `project_staleness_days: int = 7` in settings (override via `PROJECT_STALENESS_DAYS=N`); `get_priorities` agent tool now appends stale-project nudge when stale projects exist
  - **Deadlines + Recurrence (Phase 8d)** — `recurrence_rule: str | None` on `Todo` (RRULE format, e.g. `FREQ=WEEKLY;BYDAY=TH`); `python-dateutil` dep for RRULE parsing; `TodoManager.get_due_soon(days)` + `create_next_recurrence(todo)` (auto-spawned on complete); `deadline_urgent_days: int = 3` + `deadline_nudge_days: int = 3` in settings; `get_prioritized()` treats deadline-due todos as urgent in quadrant sort; `list_visible()` surfaces overdue todos before unclassified; `set_due_date` + `create_recurring_todo` agent tools; `list_todos` output includes due date tags + ↻ indicator; `worker/jobs/deadline_nudge.py` (daily 9am, respects quiet hours); frontend: due date badge in TodoItem tags row (red=overdue, amber=≤3 days, grey=future) + ↻ recurrence icon; migration `d4f6a8b2c1e3`
  - **User-facing tool errors** — `[TOOL_FAILED:{name}] ExcType: msg` format so LLM can't ignore them; `routes/chat.py` safety-net appends `⚠️ Some actions couldn't complete:` if `context.tool_errors` non-empty; **live status line** — `status_callback` on `run_agent()`, `_format_tool_status(tool_name, args)`, WS `{"type": "status"}`, frontend pulsing ✦
  - **Third-party logger suppression** — lifespan pins LiteLLM, Google, HTTP stack loggers to WARNING; parent name suppresses child loggers; `LOG_LEVEL` controls Istari loggers; `priorities_max: int = 5` in `settings.py` used by `get_priorities` + `GET /todos/prioritized` (set via `PRIORITIES_MAX=N`); `scan_gmail_node` uses `settings.gmail_max_results`; digest summary 7-9 bullets
  - Frontend: WebSocket chat with reconnection, TODO sidebar with live refresh (WebSocket signals + 15s polling + manual ↻ button in header), settings panel, notification inbox with unread badge, digest panel, **projects panel** (above todo panel, hidden when no active projects); full dark wizard aesthetic (deep navy + gold, Cinzel font); TODO inline edit modal with all fields + Save/Escape/backdrop-close; **markdown rendering** in assistant messages via `react-markdown` + `remark-gfm` (headers, bold, code blocks, lists, tables, blockquotes); user messages stay plain text; resizable sidebar (200–600px, persisted to `localStorage`); sidebar sections labeled "Today's Tasks" and "Other Tasks" (not "Goals" — that term is reserved for project-level strategic goals)
- **DB migrations:** up to date — most recent: `d4f6a8b2c1e3` (add recurrence_rule to todos); **Gmail setup:** `python scripts/setup_gmail.py` (place `credentials.json` in `secrets/`); **Calendar setup:** `python scripts/setup_calendar.py` (reuses same credentials); **slash commands:** `/test` runs full CI suite
- **Next up:** See `ROADMAP.md` at project root for the active roadmap and backlog.
- **Security hardening (Phase 7):** Docker networking (no exposed ports, internal bridge); auth via `itsdangerous` signed cookies + pure ASGI `AuthMiddleware` (`POST /api/auth/login|logout`, `GET /api/auth/me`; close code 4401; disabled when `APP_SECRET_KEY` unset); nginx security headers in `frontend/nginx.conf` (`X-Frame-Options`, `X-Content-Type-Options`, CSP); rate limiter (`_RateLimiter`, 20 msg/60s WS); `secrets/` dir (gitignored) for all OAuth tokens; `POSTGRES_PASSWORD` uses `:?` fail-loud; Ollama bound to `127.0.0.1:11434`

## Debugging Workflow
Claude is authorized to run these Docker commands directly without copy-paste:
- `docker compose logs --tail=50 api` / `docker compose logs --tail=50 worker` — tail recent logs
- `docker compose logs --since=5m api` — logs from the last N minutes
- `docker compose exec api python -c "..."` — run a one-liner inside the api container
- `docker compose ps` — check container health/status
- `docker compose restart api` / `docker compose restart worker` — restart a service

**Persistent log files** (volume-mounted to `./logs/`):
- `logs/api.log` — API server; `logs/worker.log` — background worker
- Logs survive container restarts; readable on host via `Read` tool
- RotatingFileHandler: 5 MB × 3 backups per service

**In-process error ring buffer:**
- `GET /api/debug/recent-errors` — returns last 50 WARNING+ log entries in JSON
- No file access needed; useful after a bad request without restarting

## Development Commands
- **Venv:** `source backend/.venv/bin/activate` — always activate before running backend commands; after creating/recreating the venv run `pip install -e ".[dev]"` to install all deps (including `google-auth`, `google-api-python-client`, etc.)
- `cd backend && pip install -e ".[dev]"` — install backend package in editable mode with dev deps
- `cd backend && uvicorn istari.api.main:app --reload` — run API server with hot reload
- `cd backend && python -m istari.worker.main` — run worker
- `cd backend && pytest` — run backend tests
- `cd backend && ruff check src/ tests/` — lint backend
- `cd backend && mypy src/` — type check backend
- `cd backend && alembic upgrade head` — run DB migrations (DATABASE_URL auto-loaded from .env via migrations/env.py)
- `cd backend && alembic current` — show current migration revision
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
- `ngrok start istari` — expose the app via the static domain `https://tippiest-nonpalatable-darin.ngrok-free.dev` (tunnels to port 3000; requires `COOKIE_SECURE=true` and auth configured in `.env`)

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
  - `project/manager.py` — ProjectManager CRUD (create, list_active, get_by_name, set_next_action, set_status, get_stale)
  - `mcp/client.py` — `MCPServerConfig`, `load_mcp_server_configs()`, `MCPManager` async context manager, `mcp_tool_to_agent_tool()`
- Agents: `backend/src/istari/agents/` — chat.py (ReAct agent loop + `build_tools`/`run_agent`), tools/ (todo.py, memory.py, gmail.py, calendar.py, base.py, **projects.py**), proactive.py (LangGraph proactive graph), memory.py (stub)
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
- **Agent tool imports**: move `Reader`/`settings` to top-level module imports in agent tool files (e.g. `agents/tools/gmail.py`, `agents/tools/calendar.py`) so `monkeypatch.setattr("istari.agents.tools.X.ClassName", ...)` works in tests. Keep optional/platform-specific imports (e.g. `AppleCalendarReader`) lazy inside the function. Lazy imports inside functions are untestable via monkeypatch.
- **ruff scope**: CI lints `src/` and `tests/` only — `migrations/versions/` has pre-existing violations in auto-generated boilerplate; running `ruff check migrations/` is noisy and not required to pass.
- **Optional tool param with settings default**: use `param: int = 0` where `0` means "fall back to settings value" — e.g. `limit = max_results or settings.gmail_max_results`. Avoids breaking callers that omit the param while letting the LLM override when needed.
- **postgres:5432 exposed in dev**: `docker-compose.dev.yml` already maps `5432:5432` — pgAdmin/TablePlus can connect to `localhost:5432` when running `./scripts/dev.sh`. No changes needed.
- **ruff RUF012**: class-level mutable defaults (list, dict) require `ClassVar` annotation — `SCOPES: ClassVar[list[str]] = [...]`
- **SQLAlchemy async + Pydantic**: always `await db.refresh(obj)` after `await db.commit()` before calling `model_validate(obj)` — commit expires all ORM attributes; accessing them outside the async context causes `MissingGreenlet` crash
- **LLM classification model**: use `mistral:7b-instruct-q8_0` for the `classification` task — Mistral reliably outputs structured JSON at temperature 0.0; llama3.1 can return empty strings at low temperature causing silent fallback to `chat` intent
- **Robust LLM JSON parsing**: `_extract_json()` in `chat.py` strips markdown fences (` ```json `) and finds the first `{...}` block — guards against models that wrap JSON in preamble text; always log raw response at DEBUG before parsing
- **Resizable sidebar pattern**: implement drag-resize with three refs (`isDragging`, `dragStartX`, `dragStartWidth`); `onMouseDown` on the handle sets refs, adds `col-resize` cursor + `userSelect: none` to `document.body`; `window` `mousemove`/`mouseup` listeners in a single `useEffect([], [])` that returns cleanup; save to `localStorage` in `mouseup` via functional `setState` (avoids stale closure). Delta direction: `dragStartX - e.clientX` widens the panel as you drag left.
- **Frontend prop-wiring pattern**: when a parent needs to call a function owned by a child, add `onRegisterSend?: (fn) => void` prop; child calls it in `useEffect([..., fn])`. Test all three layers: child calls the prop, the prop receives the real function, and an App-level test confirms end-to-end button → sendMessage
- **Frontend wiring tests**: mock `useChat` with `vi.mock("../../src/hooks/useChat", () => ({ useChat: () => ({ sendMessage: mockFn, ... }) }))` — see `ChatPanel.test.tsx` as canonical example
- **Backend logging**: `logging.basicConfig()` in FastAPI `lifespan` wires `LOG_LEVEL` env var; agent tool calls logged at INFO with `"Tool call | %-24s | %.0fms | %d chars returned"` format; tool arguments at DEBUG only (may contain PII); agent start/finish at INFO with elapsed time; `Status | ...` strings logged at DEBUG; noisy third-party loggers (LiteLLM, openai, h2, rustls, primp, etc.) pinned to WARNING in lifespan loop regardless of `LOG_LEVEL`; use `logger = logging.getLogger(__name__)` per module
- **build_system_prompt(session, user_name="", user_message="")**: async function in `agents/chat.py`; reads SOUL.md and USER.md via `_read_memory_file(filename)` (sync, returns "" if missing); falls back to USER.md → `user_name` setting for identity; when `user_message` provided uses `MemoryStore.search(user_message)` for semantic (pgvector cosine) memory injection, falls back to `list_explicit()[:20]` if search returns empty; called per-turn inside the `async_session_factory()` block in `routes/chat.py`; `GET /memory/search?q=` REST endpoint also available
- **ConversationStore**: `tools/conversation/store.py`; `load_history()` returns last 40 turns oldest-first; `save_turn(user, assistant)` adds two rows and flushes; loaded once at WebSocket connect, saved after each response before `send_json`
- **Memory extractor**: `agents/memory_extractor.py`; `extract_and_store(user_msg, asst_msg, session_factory)` — fire-and-forget; patches: `istari.agents.memory_extractor.completion` and `istari.agents.memory_extractor.MemoryStore` for tests; `# noqa: RUF006` on `asyncio.create_task()` call
- **SOUL.md / USER.md editing**: users edit `memory/SOUL.md` (personality) and `memory/USER.md` (profile) directly; changes take effect on next message with no restart; USER.md gitignored; USER.md.example committed as a template
- **ProjectManager pattern**: `ProjectManager(session)` follows same pattern as TodoManager; `get_by_name()` uses ILIKE; `get_stale(days)` subqueries `todos.updated_at`; `next_action_id` uses `use_alter=True` FK (circular ref with todos); `Project` + `Todo` have bidirectional relationship (`Todo.project` / `Project.todos` + `Project.next_action`)
- **Project agent tools**: `make_project_tools(session, context)` in `agents/tools/projects.py`; `suggest_next_action` calls LLM with chat_response task, returns suggestion text only (never auto-sets); `add_todo_to_project` and `set_next_action` accept ID or ILIKE query
- **goals.md**: `memory/goals.md` for user's strategic goals — gitignored, `.example` committed; future: inject into system prompt alongside SOUL.md/USER.md
- **Adding a new MCP server**: add an entry to `mcp_servers.yml` with `enabled: true` and required env vars; set the env var in `.env`; no code changes needed — tools auto-load at startup
- **MCP tool tests**: patch `istari.tools.mcp.client.stdio_client` and `istari.tools.mcp.client.ClientSession` with `@asynccontextmanager` functions via `monkeypatch.setattr`; use `monkeypatch.setattr("istari.tools.mcp.client._CONFIG_DIR", tmp_path)` to redirect config loading in unit tests
- **`docker exec` + pg_dump**: always pass `-U {username}` — without it pg_dump connects as the OS user (often `root`), which has no PostgreSQL role and fails. Pass the password via `docker exec -e PGPASSWORD container pg_dump -U user ...` where `PGPASSWORD` is set in the docker client's env; `-e PGPASSWORD` (no `=value`) forwards it into the container without exposing it in `ps aux`.
- **Parsing DATABASE_URL**: use `urlparse(database_url.replace("+asyncpg", ""))` to extract username/password/dbname — strip the driver suffix first or urlparse won't parse the scheme correctly.
- **Alembic .env loading**: `migrations/env.py` calls `load_dotenv()` (python-dotenv) at import time so `alembic current`, `alembic upgrade head`, etc. work without prefixing `DATABASE_URL=...` in the shell.
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
- **`_PROJECT_ROOT` in Docker**: `Path(__file__).resolve().parents[4]` resolves to `/usr/local/lib` in a regular (non-editable) Docker install, not the project root. Detect with `"site-packages" in str(Path(__file__).resolve())` and fall back to `Path.cwd()` (`WORKDIR=/app` in the container). Fixed in `settings.py` and `agents/chat.py`.
- **LiteLLM Ollama in Docker**: Must set both `OLLAMA_BASE_URL` AND `OLLAMA_API_BASE` to `http://host.docker.internal:11434` in docker-compose.yml — LiteLLM's `get_model_info` preflight reads `OLLAMA_API_BASE` specifically. Ollama models are also pre-registered in `litellm.model_cost` in `router.py` to skip the HTTP preflight entirely.
- **`secrets/` volume mount**: OAuth tokens live on the host at `secrets/`; both `api` and `worker` need `- ./secrets:/app/secrets` volume mount in docker-compose.yml or tokens are invisible inside containers.
- **Google OAuth `invalid_grant`**: Means the refresh token was revoked (not just expired) — re-run `setup_gmail.py` or `setup_calendar.py` to re-authorize. Normal token expiry is handled automatically by auto-refresh.
- **Glob tool skips gitignored files**: Don't conclude a file is missing because Glob returns nothing — `secrets/*.json` and other gitignored files won't appear. Use `docker compose exec api python -c "from pathlib import Path; print(Path('...').exists())"` to verify file presence inside the container.
