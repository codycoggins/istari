# Istari

AI personal assistant for task management, information surfacing, and proactive scheduling. Privacy-first, read-only to external services, ADHD-optimized UX.
Developed in collaboration with Claude Code.

See [istari-project-outline.md](istari-project-outline.md) for the full project specification.

## What it does

- **Chat agent** — ReAct tool-calling loop (LiteLLM + GPT-4o); reasons across multiple turns, calling tools before responding
- **TODO management** — create, update, prioritize via chat or sidebar; Eisenhower matrix (Q1–Q4) with urgency/importance auto-classification
- **Memory** — explicit memory store with pgvector semantic search; post-turn extraction fires automatically after each conversation turn
- **Gmail & Calendar** — read-only OAuth2 access; proactive digest at 8am/2pm; on-demand via chat
- **Filesystem tools** — read files, search by content; runs on the host via the agent
- **MCP servers** — pluggable external tools (GitHub pre-configured); add servers in `mcp_servers.yml`
- **Notifications** — inbox with unread badge; proactive staleness alerts for stale TODOs
- **Backups** — daily encrypted `pg_dump` to configurable destination (iCloud Drive by default)
- **Sensitive content routing** — PII, financial, and personal content silently routed to local Ollama model

## Quick Start

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY (required for the chat agent)
# Optionally set OLLAMA_BASE_URL for local model routing

# 2. Start all services
./scripts/dev.sh        # full stack with hot reload
# or: docker compose up --build

# 3. Access the UI
open http://localhost:3000
```

## Required Configuration

### LLM keys (`.env`)

| Variable | Purpose | Required |
|---|---|---|
| `OPENAI_API_KEY` | Chat agent (GPT-4o) | Yes |
| `OLLAMA_BASE_URL` | Local model for sensitive content, classification | Optional |
| `ANTHROPIC_API_KEY` | Claude routing (if configured in `llm_routing.yml`) | Optional |
| `GOOGLE_API_KEY` | Gemini routing | Optional |

### Gmail & Calendar OAuth

```bash
# Place credentials.json from Google Cloud Console (OAuth Desktop App) in project root
python scripts/setup_gmail.py     # writes gmail_token.json
python scripts/setup_calendar.py  # writes calendar_token.json
```

Set `CALENDAR_BACKEND=google` in `.env` (default). Apple Calendar is implemented but blocked by MDM on managed Macs.

### Agent personality & user profile

Edit these files in `memory/` — changes take effect on the next message, no restart needed:

- `memory/SOUL.md` — agent personality (checked in; safe to customise)
- `memory/USER.md` — your name, preferences, context (gitignored; copy from `USER.md.example`)

## Development

### Full stack (recommended)

```bash
./scripts/dev.sh   # starts Docker Compose with hot reload for API + worker
```

Or manually with hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Backend (local)

```bash
cd backend
source .venv/bin/activate       # re-activate after every reboot
pip install -e ".[dev]"         # first time, or after dependency changes

uvicorn istari.api.main:app --reload   # API on :8000
python -m istari.worker.main           # worker (separate terminal)

pytest                     # run tests (256 passing)
ruff check src/ tests/     # lint
mypy src/                  # type check
```

### Frontend (local)

```bash
cd frontend
npm install
npm run dev       # Vite dev server on :3000 (proxies /api to :8000)
npm run lint
npm run typecheck
npm test
```

### Database

```bash
cd backend
alembic upgrade head                              # run migrations
alembic revision --autogenerate -m "description"  # create migration

./scripts/reset-db.sh   # drop + recreate + migrate (destructive)
./scripts/seed.sh       # seed dev data (placeholder)
```

### Backups

```bash
# Trigger a backup immediately (requires BACKUP_ENABLED=true + BACKUP_PASSPHRASE in .env)
cd backend && python -c "import asyncio; from istari.worker.jobs.backup import run_backup; asyncio.run(run_backup())"

# Restore from backup (prompts for passphrase)
./scripts/restore_db.sh /path/to/istari_20260101T020000Z.dump.enc
```

Set `BACKUP_DESTINATION_PATH` in `.env` to your preferred location (defaults to iCloud Drive on Mac). Runs daily at 2am via APScheduler. 7-day retention.

## Architecture

```
Frontend (React + Vite)  →  nginx  →  API (FastAPI)  →  PostgreSQL + pgvector
                                       Worker (APScheduler)  ↗
```

- **API service** — FastAPI: WebSocket chat, REST for todos/memory/notifications/digests/settings
- **Worker service** — APScheduler: Gmail digests (8am/2pm), TODO staleness (8am), DB backup (2am)
- **ReAct agent** — manual LiteLLM tool-calling loop; up to 8 turns; tools: todo, memory, gmail, calendar, filesystem, MCP
- **LLM routing** — `llm_routing.yml`; sensitive content → local Ollama; never hardcode model names in code
- **Database** — PostgreSQL + pgvector (pgvector/pgvector:pg16); vector column on `memories` for semantic search
- **MCP servers** — opt-in in `mcp_servers.yml`; spawned at startup; tools merged with built-ins automatically

API and worker are separate processes sharing the same Python package (`istari`). The worker communicates with the API via the database (notification rows), never in-process.

## MCP Servers

Add external tool servers in `backend/src/istari/config/mcp_servers.yml`:

```yaml
servers:
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
    enabled: false   # set true + add GITHUB_TOKEN to .env to activate
```

No code changes needed — tools load automatically at startup.
