# Istari — AI Personal Assistant
### Project Outline v2
> Status: Pre-development planning document  
> Intended audience: Claude Code / Cursor for implementation guidance  
> Last updated: 2026-02-12

---

## 1. Project Overview

**Istari** is a personal AI assistant designed to help a single user (software engineer with ADHD) stay focused on the right tasks and surface relevant information at the right moment. Like the Istari of Tolkien's mythology — wizards sent to guide and advise, never to act in place of others — this assistant enhances the user's own initiative rather than replacing it.

The system is proactive, privacy-first, and read-only with respect to external services. It is the system of record for the user's TODOs, learns preferences over time, and surfaces context at the moment of action rather than requiring the user to go looking for it.

**Core value props:**
- Surfaces actionable items from Gmail and other sources without requiring the user to check manually
- Remembers TODOs and prompts at appropriate times — reducing the cognitive load of tracking follow-ups
- Finds information scattered across email, files, calendars, and repos when the user needs it
- Learns user patterns over time to improve prioritization and reduce noise

**Name rationale:** In Tolkien's lore, the Istari (order of wizards) were sent expressly *not* to use power on behalf of others, but to guide, counsel, and kindle initiative. They never act in place of the free peoples — they show up with the right knowledge or nudge at the right moment. This maps precisely onto the design philosophy of this assistant.

---

## 2. Design Principles

These principles are non-negotiable and should shape every architectural and UX decision:

1. **Privacy-first.** All data stays local or in user-controlled infrastructure. No third-party data storage beyond the services already used (Gmail, etc.).
2. **Read-only to the outside world.** The agent may read from external services but must never write, post, send, or modify anything externally. Internal database writes are fine. This constraint is enforced structurally at the tool layer — MCP tools have no write methods for external services.
3. **ADHD-optimized UX.** The assistant must not overwhelm. Specific behaviors:
   - Extremely low-friction TODO capture: one line in chat, no required fields, no structure imposed at capture time
   - Deliver context *at moment of action*, not in a separate dashboard requiring navigation
   - Be selective about proactive interruptions — quality over quantity; a bad notification trains the user to ignore the next one
   - `"What should I work on right now?"` is a first-class, always-available command
   - Never surface more than 1–3 items at a time in response to prioritization queries
4. **Modular architecture.** Components should be independently testable, replaceable, and extensible via MCP.
5. **Cost-conscious.** Target ≤$50/month in LLM API costs. Prefer local models (Ollama) for tasks where quality is sufficient. Sensitive data is routed to local models by default.
6. **Iterative.** This is a part-time project. MVP first, refine over time. Claude Code / Cursor handles most implementation; the developer acts as reviewer and occasional contributor.

---

## 3. Architecture Overview

### 3.1 High-Level Components

```
┌─────────────────────────────────────────────────┐
│                   Interface Layer                │
│   Web UI (React/TS)   │   Matrix/Element (future)│
└───────────────────────┬─────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
┌───────▼───────────────┐   ┌────────────▼───────────────┐
│   API Service          │   │   Worker Service            │
│   FastAPI (Python)     │   │   Proactive Agent +         │
│                        │   │   APScheduler (Python)      │
│   • Chat Agent         │   │                             │
│   • Memory/Recall      │   │   • Gmail digest (8am/2pm)  │
│     Agent              │   │   • TODO staleness check    │
│   • On-demand queries  │   │   • Pattern learning        │
│                        │   │   • Queues output as        │
│                        │   │     notifications in DB     │
└───────────┬────────────┘   └────────────┬───────────────┘
            │                             │
            │    ┌────────────────────┐   │
            └───►│  Content Classifier│◄──┘
                 │  (local — runs in  │
                 │  both services)    │
                 └─────────┬──────────┘
                           │
            ┌──────────────▼──────────────────┐
            │          Tool / MCP Layer        │
            │  Gmail │ FS │ Calendar │ Git │.. │
            └──────────────┬──────────────────┘
                           │
            ┌──────────────▼──────────────────┐
            │       Storage & Memory Layer     │
            │   PostgreSQL + pgvector          │
            └──────────────────────────────────┘
```

**Key architectural decision:** The API service and Worker service are **separate processes** in Docker Compose, sharing the PostgreSQL database. They never compete for the same event loop. The worker queues all proactive output as notification rows in the database; the API server reads and serves them. Long-running Ollama inference in the worker cannot block or slow the chat interface.

### 3.2 Language / Runtime Split

| Layer | Language | Rationale |
|---|---|---|
| API & agent backend | Python | LangGraph, LLM SDKs, data tooling |
| Web UI | TypeScript / React | Rich interactive frontend |
| MCP tools / connectors | Python (primary) | Consistency with backend |
| Infrastructure / scripts | Python or bash | As appropriate |

Multi-language is acceptable if the boundary is clean (API contract between frontend and backend).

---

## 4. Technology Stack

### 4.1 Core Dependencies

| Concern | Technology |
|---|---|
| Agent orchestration | LangGraph |
| API service | FastAPI (chat agent, memory/recall, on-demand queries) |
| Worker service | Python process + APScheduler (proactive agent, scheduled tasks) |
| Frontend | React + TypeScript (Vite) |
| Primary DB | PostgreSQL with pgvector extension (shared between API and worker) |
| LLM routing | LiteLLM (abstracts Ollama / Claude / Gemini behind one interface) |
| Extensibility | MCP (Model Context Protocol) |
| Containerization | Docker + Docker Compose (api, worker, postgres as separate services) |
| Version control | Git |

> **Note on Redis:** Redis is not required. The API and worker services communicate via the shared PostgreSQL database — the worker writes notifications/digests as rows; the API reads and serves them. This keeps the stack simpler and avoids an additional service to operate.

### 4.2 LLM Strategy

The system uses a **tiered model approach** to balance cost, performance, and privacy. Model selection per task type is configured in YAML — never hardcoded in agent logic.

| Tier | Models | Use Cases |
|---|---|---|
| Local (free, private) | Llama 3 / Mistral via Ollama | Summarization, classification, embeddings, content scanning, sensitive data tasks |
| Cloud free tier | Gemini (Google AI free tier) | Mid-complexity reasoning, drafting, non-sensitive tasks |
| Cloud paid | Claude API (Anthropic) | High-stakes reasoning, user-facing responses, complex multi-step tasks |

**Content classification runs locally.** The sensitivity classifier never sends content to a cloud API to decide whether it's safe to send to a cloud API.

**Cost target:** ≤$50/month across all paid APIs. Routing sensitive data to local models is the primary cost lever.

### 4.3 LLM Routing and Sensitivity Classification

Before any data is passed to an LLM, a **content classifier** (running on a small local model or rule-based heuristics — must be fast and cheap) inspects the content and flags it if it contains:

- Email body content
- Names and contact information
- Local file contents
- Financial information

**If classified as sensitive:**
- The agent prompts the user: *"This query involves sensitive content. Process locally (slower/lower quality) or allow cloud model (faster/better quality)?"*
- The user can set a **session-level override** ("local only for this session" / "cloud allowed this session") to avoid being prompted repeatedly

**If not classified as sensitive:**
- Routes automatically to the best available model for the task per config

This gives the user full control without requiring manual management of routing rules.

### 4.4 Future Messaging Layer

The web UI is the MVP interaction surface. Architecture must allow Matrix/Element to be added as a second interaction channel without restructuring the backend. The API layer is channel-agnostic from day one.

---

## 5. Data Sources & Integrations

Integrations are **read-only** to external services. Priority order for implementation:

| Priority | Source | Integration Approach |
|---|---|---|
| 1 | Gmail | Google OAuth2 + Gmail API (via MCP tool) |
| 2 | Local filesystem | Direct file access / search (via MCP tool) |
| 3 | Google Calendar / Apple Calendar | Google Calendar API or CalDAV (via MCP tool) |
| 4 | Git repos / GitHub | Git CLI or GitHub API (via MCP tool) |
| 5 | iMessage / texts | macOS AppleScript or Messages DB (later, privacy-sensitive) |

Each integration must be:
- Implemented as an MCP-compatible tool with no external write methods
- Independently testable with mocked/recorded API responses
- Gated behind a feature flag or config toggle so incomplete integrations don't block deployment

---

## 6. TODO System

### 6.1 Storage

Istari is the **system of record** for TODOs. There is no dependency on external task management tools (Things, Todoist, Notion, etc.). The user's existing tools have not served them well; Istari replaces the habit of opening a separate app with low-friction chat capture.

An **adapter interface** is defined from day one so a future sync target (e.g., Todoist as an export destination) can be added without rearchitecting. No external adapters are built in MVP.

### 6.2 Capture

TODO capture happens in the chat interface. The only required input is a single line of natural language — the sentence the user would say out loud. No fields, no structure, no form.

Example capture phrases (all valid, all equivalent from a UX standpoint):
- `"Remember to follow up with Alex about the contract"`
- `"TODO: review the infra PR"`
- `"remind me to pay the quarterly taxes"`

### 6.3 Metadata Model

All metadata beyond the title is **inferred silently by the agent in the background** after capture. The user is never prompted for structured fields.

| Field | Source | Notes |
|---|---|---|
| `title` | User input (required) | The one line the user typed |
| `priority` | Inferred by agent | From language cues ("urgent", "before Friday"), sender context, project importance — shown to user, editable |
| `tags` / `project` | Inferred by agent | Matched against known active projects and past patterns |
| `source_link` | Auto-attached | Set automatically when TODO originates from a Gmail thread, file, or git issue |
| `due_date` | Inferred if present | Extracted from natural language ("before Friday", "next week") |
| `body` | Enriched async | Agent may add context, related links, or notes after capture |

---

## 7. Agent Design

### 7.1 Chat Agent (Interactive / On-Demand)

Handles real-time user interactions. Key behaviors:

- `"What should I work on right now?"` → queries TODO store + calendar + recent digests, applies learned prioritization preferences, returns top 1–3 items with context
- `"Remember to [X]"` / `"TODO: [X]"` → single-line capture, enriched asynchronously, confirmed with a brief acknowledgment
- `"Help me with [TODO]"` → triggers context injection: searches email, filesystem, calendar for relevant info and surfaces it inline
- `"Check my Gmail for things that need action"` → on-demand inbox scan, returns actionable digest (not raw email dump)
- `"Actually, [correction]"` / `"Remember that [fact]"` → explicit memory write, overrides any conflicting inference
- Natural language TODO updates, queries, and prioritization requests

### 7.2 Proactive Agent (Background / Scheduled)

Runs on a configurable schedule. Must be interruptible and produce auditable logs.

**Scheduled behaviors:**

| Behavior | Schedule | Output |
|---|---|---|
| Gmail digest | 8am + 2pm daily | Actionable digest queued as notification in UI |
| TODO staleness check | Daily (batched into morning digest) | Stale TODOs surfaced alongside Gmail digest, not as a separate interrupt |
| Pattern learning update | Periodic + event-driven | Updates user preference model silently |

**Notification modes:**

| Mode | Behavior |
|---|---|
| Normal | Badge + push notification to UI when something is worth surfacing |
| Focus mode (manual toggle) | Badge accumulates silently — no push alerts |
| Quiet hours (default: after 9pm) | No notifications of any kind; morning digest is the reset point |

**Critical design constraint:** Proactive output is always *queued* — the agent never modifies the user's active view or interrupts mid-task. The user sees a badge and chooses when to engage.

### 7.3 Memory & Recall Agent

Handles retrieval and long-term learning. Three distinct memory types:

**Explicit memory** — things the user has directly stated:
- Stored immediately on capture with full confidence
- Triggered by phrases like "remember that...", "actually...", "always/never..."
- Takes precedence over any conflicting inferred preference

**Inferred preferences** — patterns learned from behavior:
- Prioritization style (what the user bumps up vs. defers)
- Time-of-day productivity patterns (when the user is most responsive/productive)
- Which projects and areas are currently active vs. on hold
- Each stored with a confidence score; score decays when contradicted by new behavior

**Episodic/contextual memory** — history of what has happened:
- Completed TODOs, reviewed digests, past sessions
- Used to improve recommendations and context injection
- Not surfaced directly to the user; informs agent reasoning

**Correction mechanism:** Any chat message phrased as a correction ("actually that's wrong", "remember that X is not the case") triggers an immediate memory update that overrides the relevant inference. The user never needs to navigate a settings panel to fix a wrong assumption.

**Memory visibility:** The user can request a summary of what Istari has learned via `/memory` command or a UI panel. The summary is presented in natural language ("I've noticed you tend to prioritize infrastructure work in the mornings and defer personal TODOs to evenings") — not as raw database rows. The user can correct or invalidate entries from this view.

---

## 8. Web UI Design

### 8.1 Layout

**Split layout:** chat on the left, structured panel on the right. The panel serves as at-a-glance awareness without requiring a separate navigation action.

This layout is chosen deliberately for the ADHD context: the TODO panel stays visible and current without the user having to "go check" somewhere. Context is ambient, not behind a click.

### 8.2 Phased UI Rollout

**Phase 1 UI (MVP — built alongside the chat agent):**
- Chat panel (primary interaction surface)
- TODO sidebar: list with status and priority visible at a glance
- Persistent `"What should I work on?"` button / keyboard shortcut — always accessible, never buried
- Basic notification badge on the panel header

**Phase 2 UI (built alongside the proactive agent):**
- Notification inbox: scrollable list of proactive agent output (digests, staleness alerts)
- Active digest panel: latest Gmail/calendar summary surfaced inline
- `/memory` summary view: what Istari has learned, in natural language

Sequencing matters: the digest panel and notification inbox are useless before the proactive agent exists to populate them. Don't build UI ahead of the backend that feeds it.

### 8.3 UX Constraints for Claude Code

- The `"What should I work on?"` button must always be visible — never hidden in a menu or below the fold
- Responses to prioritization queries must never return more than 3 items without explicit user request for more
- TODO capture confirmation should be brief (one line: "Got it — added to your list") — never a form or a follow-up question
- The split layout must be responsive enough to collapse the panel on smaller screens

---

## 9. Storage Schema (Conceptual)

```
todos
  id, title, body, status, priority (inferred|user_set), source, source_link,
  created_at, updated_at, last_prompted_at, due_date, tags[], embedding (vector)

memories
  id, type (explicit|inferred|episodic), content, confidence (0.0–1.0),
  created_at, last_referenced_at, last_contradicted_at, source, embedding (vector)

digests
  id, source (gmail|calendar|...), created_at, content_summary,
  items_json, reviewed (bool), reviewed_at

notifications
  id, type (digest|staleness|pattern), created_at, content, read (bool),
  read_at, suppressed_by (focus_mode|quiet_hours|null)

agent_runs
  id, agent_type, started_at, completed_at, status, output_summary, error

user_preferences
  key, value, confidence, updated_at, source (explicit|inferred)

user_settings
  key, value  -- quiet_hours_start, quiet_hours_end, focus_mode, digest_schedule, etc.
```

pgvector enables semantic search across todos, memories, and digested content without a separate vector DB. The `notifications` table replaces any need for Redis as a communication channel between the worker and API services.

---

## 10. MCP Tool Design

Each data source integration is packaged as an MCP-compatible tool server. This enables swapping implementations without touching agent code, testing tools in isolation, and future sharing / reuse.

**Read-only enforcement:** MCP tools expose no write methods for external services. This is a structural guarantee, not a policy.

| Tool | Description |
|---|---|
| `gmail_reader` | Search inbox, list unread, fetch thread, label-based filtering — OAuth2, read-only |
| `filesystem_search` | Search local files by name, content, recency, type |
| `calendar_reader` | List upcoming events, search by keyword, check free/busy |
| `todo_manager` | CRUD for internal TODO store (internal write — not external) |
| `memory_store` | Read/write/search the memory layer (internal write — not external) |
| `git_reader` | List recent commits, search repo content, PR status |
| `content_classifier` | Inspect content for sensitivity flags before LLM routing |

---

## 11. Project Structure (Proposed)

```
istari/
├── backend/
│   ├── api/               # FastAPI app — chat agent, on-demand queries, notification serving
│   │   └── main.py
│   ├── worker/            # Separate process — proactive agent + APScheduler
│   │   └── main.py        # Entry point: starts scheduler, runs independently of API
│   ├── agents/            # LangGraph agent definitions (shared by api + worker)
│   │   ├── chat.py
│   │   ├── proactive.py
│   │   └── memory.py
│   ├── tools/             # MCP tool implementations (shared by api + worker)
│   │   ├── gmail/
│   │   ├── filesystem/
│   │   ├── calendar/
│   │   ├── git/
│   │   └── classifier/    # Content sensitivity classifier
│   ├── models/            # DB models (SQLAlchemy) — shared by api + worker
│   ├── llm/               # LiteLLM config + routing logic
│   ├── config/            # App config (YAML + env)
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/      # Recorded API responses for offline testing
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   ├── TodoPanel/
│   │   │   ├── DigestPanel/         # Phase 2
│   │   │   └── NotificationInbox/   # Phase 2
│   │   ├── pages/
│   │   └── api/           # API client
│   └── tests/
├── docker-compose.yml     # Services: api, worker, postgres
├── .env.example
└── README.md
```

**Docker Compose services:**

| Service | What it runs | Can restart independently? |
|---|---|---|
| `postgres` | PostgreSQL + pgvector | Yes |
| `api` | FastAPI + chat agent | Yes — worker outage doesn't affect chat |
| `worker` | Proactive agent + APScheduler | Yes — can be paused/debugged without touching API |

---

## 12. Development Phases

### Phase 1 — Foundation (MVP)
- [ ] Project scaffolding: repo (`istari`), Docker Compose with `api` + `worker` + `postgres` services, FastAPI skeleton, worker skeleton, React/Vite skeleton
- [ ] PostgreSQL + pgvector setup with initial schema
- [ ] LiteLLM integration: Claude API + Ollama (Llama 3 / Mistral)
- [ ] Content classifier: local model or rule-based, sensitivity detection
- [ ] Chat Agent (LangGraph): conversation loop, TODO capture, memory writes
- [ ] `todo_manager` MCP tool (CRUD)
- [ ] `memory_store` MCP tool (explicit memory only)
- [ ] `"What should I work on right now?"` command (queries TODO store)
- [ ] **Phase 1 Web UI:** split layout, chat panel, TODO sidebar, persistent "What should I work on?" button
- [ ] User settings: quiet hours (default 9pm), focus mode toggle
- [ ] Unit test scaffolding + fixtures pattern

### Phase 2 — Gmail + Proactive Agent
- [ ] `gmail_reader` MCP tool (OAuth2, read-only)
- [ ] On-demand inbox scan + actionable digest via chat
- [ ] Proactive Agent + APScheduler in `worker` service: Gmail digest at 8am + 2pm
- [ ] TODO staleness detection (batched into morning digest)
- [ ] Notification queue + badge system
- [ ] Focus mode: badge-only, no push during active focus
- [ ] Quiet hours enforcement in scheduler
- [ ] **Phase 2 Web UI:** notification inbox, active digest panel

### Phase 3 — File System + Calendar + Vector Search
- [ ] `filesystem_search` MCP tool
- [ ] `calendar_reader` MCP tool (Google Calendar)
- [ ] Context injection at task start (searches across Gmail, filesystem, calendar)
- [ ] pgvector semantic search over ingested content
- [ ] Source link auto-attachment on TODO capture from integrated sources

### Phase 4 — Learning + Memory UI + Git
- [ ] `git_reader` MCP tool
- [ ] Inferred preference learning: prioritization style, time-of-day patterns, active projects
- [ ] Confidence scoring + decay on inferred memories
- [ ] `/memory` summary view (natural language summary of learned preferences)
- [ ] Improved `"What should I work on?"` using learned patterns
- [ ] Proactive recommendations based on preference model

### Phase 5 — Messaging Layer (Future)
- [ ] Matrix/Element integration as second interaction channel
- [ ] Channel-agnostic notification routing

---

## 13. Security & Privacy Requirements

- All credentials in environment variables or secrets manager — never committed to git
- Google OAuth2 tokens stored encrypted at rest
- No data sent to third-party services beyond explicitly integrated APIs (Gmail, Calendar, Claude API, Gemini)
- **Content classifier runs locally** — sensitivity detection never touches cloud APIs
- Sensitive data types (email bodies, names/contacts, local file contents, financial info) routed to local models by default; user can override per session
- Audit log of all agent reads from external services (what was accessed, when, why)
- Read-only constraint enforced structurally at MCP tool layer — no external write methods exist
- HTTPS for local web UI even in dev (self-signed cert acceptable)
- `.env.example` maintained with all required keys documented; `.env` in `.gitignore`

---

## 14. Testing Strategy

- **Unit tests:** All MCP tools, agent logic, classifier, and utility functions — pytest, all external API calls mocked
- **Integration tests:** Agent + tool interaction using recorded API response fixtures (no live credentials required)
- **E2E tests:** Key user flows via web UI — Playwright or Cypress (Phase 2+)
- **Coverage target:** ≥80% on backend core logic
- **CI:** GitHub Actions — tests run on every push; no merge without green tests

---

## 15. Open Decisions (To Resolve Before Each Phase)

| Decision | Status | Recommendation |
|---|---|---|
| Job scheduler: APScheduler vs. Celery | **Decided: APScheduler in worker service** | Worker is a separate process — APScheduler runs there. Migrate to Celery only if task queue complexity grows significantly. |
| Local model selection | Resolve before Phase 1 | Benchmark Llama 3.1 8B vs. 3.2 3B on target MacBook Pro — 8B for quality, 3B if latency unacceptable |
| Secrets management | Resolve before Phase 1 | `.env` for local dev with clear migration path to macOS Keychain or Vault for production |
| Hosting post-MVP | Resolve before Phase 3 | MacBook Pro now → home server or cloud later; design stateless backend from day one |
| TODO adapter interface | Define in Phase 1 | Create abstract `TodoStore` interface even if only one implementation exists — enables future sync targets (Todoist, Things) without rearchitecting |
| Sensitivity classifier implementation | Resolve before Phase 1 | Start with rule-based heuristics (regex for financial patterns, PII detection); graduate to small local model if recall is insufficient |

---

## 16. Reference Inspirations

The following open-source projects were studied during planning (not used as a code base):
- OpenClaw
- Clawdbot
- Maltbot

Before starting Phase 1, Claude Code should ask the developer whether any specific patterns or design decisions from these projects should be incorporated or explicitly avoided.

---

## 17. Conventions for Claude Code

- **API and worker are separate services** — the proactive agent and APScheduler live in `backend/worker/`, never embedded in the FastAPI app. Long-running LLM inference in the worker must never be able to block or slow the chat interface.
- **Worker communicates via the database, not in-process** — the worker writes notification/digest rows; the API reads them. No shared in-memory state between the two services.
- **Project name is `istari`** — use consistently for repo name, Python package name, Docker service names, and CLI references
- **Always ask before creating new top-level modules** — check if the functionality belongs in an existing one
- **Prefer composition over inheritance** in agent and tool design
- **All external API calls go through the MCP tool layer** — no direct API calls from agent code
- **Never hardcode model names** — always reference LiteLLM config YAML
- **Content classifier must be invoked before any data is passed to an LLM** — this is not optional
- **Proactive agent changes require explicit developer approval** — scheduling and notification logic has high UX impact
- **Every new MCP tool requires a mock/fixture** — tests must never require live credentials
- **TODO capture must never ask the user for structured input** — one line in, acknowledgment out
- **`"What should I work on?"` must always return ≤3 items** unless user explicitly requests more
- **Phase 2 UI components should not be scaffolded during Phase 1** — don't build what the backend can't yet feed
- **Consult the Open Decisions table** before implementing any component that depends on an unresolved decision — surface the decision to the developer first
