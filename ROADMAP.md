# Istari — Roadmap

Feature lifecycle

Stage 1. Tasks that need refinement

In backlog grooming, we move to stage 2

Stage 2. Planned and sequenced work

Stage 3. Implementation

After implementation, we move **Completed Work** to the file `COMPLETED.md` at project root.


## 1. Tasks that need refinement 

- Bug - When using mail tool, the hyperlinks are only displayed occasionally.
- In task panel, next to "All" add "No Project" link which would filter task list to items without a project
- **Revisit LLM selections** — config/llm_routing.yml
- **Disable files tool** — Running from docker, files tools doesn't work.
- **Ideas** — Plan ideas tracking, per project.  Could use tasks.  
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

## 2. Planned and sequenced work

(None)
