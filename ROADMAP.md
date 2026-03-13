# Istari — Roadmap

## Completed Phases

| Phase | Summary                                                                                                              |
|-------|----------------------------------------------------------------------------------------------------------------------|
| 1 | MVP — WebSocket chat, ReAct agent, TODO CRUD, memory store, LiteLLM routing                                          |
| 2 | Notifications, Gmail integration, proactive worker agent                                                             |
| 3 | Apple Calendar support (blocked by MDM; Google Calendar in use)                                                      |
| 4 | Memory architecture — SOUL.md, USER.md, pgvector semantic search, conversation history                               |
| 5 | Eisenhower matrix — urgent/important classification, quadrant badges                                                 |
| 6 | MCP server integration — stdio subprocess model, GitHub server pre-configured                                        |
| 7 | Security hardening — auth middleware, Docker networking, nginx headers, rate limiting, credential audit              |
| 8a | Projects core — Project model, ProjectManager, agent tools, REST API, next-action designation                        |
| 8b | Projects UI — ProjectsPanel, TodoPanel filter bar, next-action badge, project pill on todo items, keyboard shortcuts |
| 8c | Proactive project staleness — worker job, Mon/Wed/Fri nudge notifications, stale-project surfacing in get_priorities |

---

## Phase 8: Projects Layer

**Goal:** Introduce a Projects layer between strategic goals and individual todos. Inspired by GTD: a project collects related todos and designates exactly one *next action* — the single todo that moves it forward. This makes "what should I work on?" meaningful at scale (10+ active projects, 50+ todos), enables shiny-object accountability ("that's interesting, but project X hasn't moved in a week"), and grounds proactive nudges in something meaningful rather than just schedule.

**Mental model:**
```
Strategic goal  →  memory/goals.md            (user edits, Istari reads)
  Project       →  DB table (~10 active)       (agent manages)
    Next action →  one designated Todo         (collaborative — Istari suggests, user confirms)
    Other todos →  supporting tasks
  Standalone    →  Todos without a project     (e.g. "do security training")
```

**Note on Jira:** Work project tracking stays in Jira. Istari is for personal/family/random work todos. A work project in Istari would be lightweight ("auth feature launch") with the next action pointing to a Jira ticket by reference, not syncing tickets as todos.

---

### 8a — Projects Core (Backend + Agent)

**Data model changes:**

New `Project` table:
```
id            int PK
name          str
description   str | None
goal          str | None        # which strategic goal this serves
status        enum: active | paused | complete
next_action_id  int FK → todos.id | None
created_at    datetime
updated_at    datetime
```

`Todo` table additions:
```
project_id    int FK → projects.id | None
```

Create Alembic migration for both changes.

**New file:** `memory/goals.md` — user-maintained list of strategic goals. Injected into system prompt alongside SOUL.md and USER.md. Commit a `memory/goals.md.example` as a template. Add to `.gitignore` (personal data).

**New tools module:** `backend/src/istari/tools/project/manager.py` — `ProjectManager(session)`
- `create(name, description, goal, status)` → Project
- `list_active()` → list[Project]
- `get(id)` → Project with related todos
- `set_next_action(project_id, todo_id)` → Project
- `set_status(project_id, status)` → Project
- `get_stale(days)` → list[Project] — projects where no associated todo has been updated in N days

**New agent tools:** `backend/src/istari/agents/tools/projects.py` — `make_project_tools(session, context)`
- `create_project(name, description, goal)` — creates project; prompts user to add todos
- `list_projects(status="active")` — shows each project with its next action
- `add_todo_to_project(todo_id_or_query, project_name_or_id)` — associates todo with project
- `set_next_action(project_name_or_id, todo_id_or_query)` — designates next action
- `suggest_next_action(project_name_or_id)` — LLM reviews project todos and suggests which should be next action; returns suggestion for user to confirm

Register in `build_tools()` in `agents/chat.py`.

**Behavior change — "what should I work on?":**
- Current: returns ranked list of todos by quadrant
- New: surfaces next actions across active projects first (one per project), then standalone high-priority todos
- Response format: "Here are your next actions across active projects: [project → next action]. Standalone priorities: [list]. Want to reason through any of these?"

**API routes:** `backend/src/istari/api/routes/projects.py`
- `GET /projects/` — list projects
- `POST /projects/` — create project
- `PATCH /projects/{id}` — update (name, description, goal, status)
- `POST /projects/{id}/next-action` — set next action todo
- `GET /projects/{id}/todos` — todos associated with project

**Tests:** `backend/tests/unit/test_tools/test_project_manager.py`

---

### 8b — Projects UI

**New component:** `frontend/src/components/ProjectsPanel/`
- List of active projects, each showing: name, goal, next action todo (highlighted), todo count
- Click project → filters todo sidebar to show only that project's todos
- "All" / per-project toggle at top of todo sidebar
- Visual treatment for next action todo: distinct badge or callout (e.g. gold "→ next" marker)
- Status toggle per project (active / paused / complete)

**Todo sidebar changes:**
- Optional project badge on each `TodoItem` (project name, small pill)
- Filter bar at top: All | by project

**App.tsx wiring:** ProjectsPanel alongside TodoPanel, same resizable pattern.

---

### 8c — Proactive Project Staleness

**New worker job:** `backend/src/istari/worker/jobs/project_staleness.py`
- Calls `ProjectManager.get_stale(days=7)` for projects with status=active
- For each stale project: generates a notification with nudge text
- Nudge format: "**[Project name]** is important to you but hasn't moved in {N} days. Want to figure out the next action?"
- Notification links to a suggested follow-up message the user can send (or Istari initiates the conversation if a future "push to chat" feature exists)

**Schedule:** Add to `schedules.yml` — run Mon/Wed/Fri morning (configurable). Respects quiet hours.

**Staleness threshold:** Configurable via settings (`project_staleness_days`, default 7).

**Connection to "what should I work on?":** When this query is made, also check for stale projects and surface them: "Also, these projects haven't moved recently: [list] — want to pick a next action for any of them?"

---

### 8d — Deadlines + Recurrence

**Todo model additions:**
```
due_date         date | None
recurrence_rule  str | None    # "daily" | "weekly" | "monthly" | "yearly" | None
                               # or RRULE string for more complex schedules
```

Design the `Todo` schema with these fields from Phase 8a migration so 8d is a non-breaking addition.

**Recurrence behavior:**
- When a recurring todo is marked complete, automatically create the next instance with `due_date = today + interval`
- New todo inherits `project_id`, `urgent`, `important`, `recurrence_rule` from parent
- Example: "change furnace filter" (monthly) → completes → new todo created due in 30 days

**Agent tools additions:**
- `set_due_date(todo_id_or_query, date)` — set or clear due date
- `create_recurring_todo(title, interval, project)` — creates first instance with recurrence rule

**Urgency from deadlines:**
- Todos with `due_date` within 3 days auto-elevate to urgent in `get_prioritized()` (overrides manual classification)
- Threshold configurable via settings (`deadline_urgent_days`, default 3)

**Proactive deadline nudges:**
- Worker job (or extend `project_staleness.py`): surface todos with `due_date` in next N days
- Format: "**[Todo]** is due in 2 days — is this still on track?"

**UI:**
- Due date displayed on `TodoItem` (subtle, color-coded: red if overdue, amber if soon)
- Overdue todos surfaced at top of quadrant sort

---

## Backlog (Phase 9+)

These are confirmed desirable but not yet sequenced:

- **Persist recent message history cross-clients** to help with client changes or messages not delivered because client disconnected.
- **Focus mode enforcement** — proactive agent respects focus mode; no non-urgent nudges during focus hours
- **Context compaction** — summarize conversation turns older than 40 before they're dropped from context window
- **Morning proactive prompt** — "You have 0 tasks focused for today — want me to suggest some?" (Today's Goals pre-population)
- **Pattern learning** — `learning.py` stub; learn which task types get done, which languish, preferred working hours; improve prioritization suggestions over time
- **goals.md injection** — read `memory/goals.md` into system prompt; Istari can cross-reference new tasks against stated goals
- **Matrix / Element integration** — alternative chat interface (from original project outline)
- **"Shiny object" check** — when user brings a new task in chat, Istari proactively asks which project it belongs to and whether it should displace the current next action
- UI - Light and dark mode.
- Tools - Add support for command line tools (whitelisted)
- Data Source  -Google Drive (use same google auth approach)
- Data Source Jira - atlassian acli command line https://developer.atlassian.com/cloud/acli/guides/install-macos/
- Data Source Obsidian?  (it is duplicative of file system) - see obsidian CLI, new
- Feature - Explore adding positive habits that user wishes to adopt, with tracking.
- Feature - Explore adding suggestions for fun activities

