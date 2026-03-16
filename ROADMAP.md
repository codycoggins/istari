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
| 8d | Deadlines + Recurrence — due_date UI badges, RRULE recurrence, auto-spawn next instance on complete, deadline urgency sort, daily nudge worker job |
| 9a | Cross-client chat history — `load_history()` returns full metadata; WS sends `type=history` frame on connect; frontend hydrates on new tab/refresh, skips on same-session reconnect |

---

## Backlog (Phase 10+)

These are confirmed desirable but not yet sequenced:

- Bug - When using mail tool, the hyperlinks are only displayed occasionally.
- **Revisit LLM selections** — config/llm_routing.yml
- **Disable files tool** — Running from docker, files tools doesn't work.
- **Context compaction** — summarize conversation turns older than 40 before they're dropped from context window
- **Focus mode enforcement** — proactive agent respects focus mode; no non-urgent nudges during focus hours
- **Morning proactive prompt** — "You have 0 tasks focused for today — want me to suggest some?" (Today's Goals pre-population)
- **Pattern learning** — `learning.py` stub; learn which task types get done, which languish, preferred working hours; improve prioritization suggestions over time
- **goals.md injection** — read `memory/goals.md` into system prompt; Istari can cross-reference new tasks against stated goals
- **Matrix / Element integration** — chat app alternative to web interface
- **Bash Tools** — Add support for command line tools (whitelisted)
- **Google Drive Data Source** (use same google auth approach)
- **Obsidian Data Source**  (it is duplicative of file system) - see obsidian CLI, new
- Feature - Explore adding positive habits that user wishes to adopt, with tracking.
- Feature - Explore adding suggestions for fun activities
- **"Shiny object" check** — when user brings a new task in chat, Istari proactively asks which project it belongs to and whether it should displace the current next action
- **Light and dark mode** - UI
- Data Source Jira - atlassian acli command line https://developer.atlassian.com/cloud/acli/guides/install-macos/

