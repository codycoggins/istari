# Phase 8d — Deadlines + Recurrence: Implementation Plan

## Context
- `due_date: DateTime(timezone=True)` already exists on the Todo model and schemas
- Need to add `recurrence_rule: str | None` (RRULE format, e.g. `FREQ=WEEKLY;BYDAY=TH`)
- `python-dateutil` needed for RRULE parsing (not currently in deps)
- Auto-urgency: todos due within `deadline_urgent_days` (3) treated as urgent in sort
- Proactive deadline nudge worker job (daily 9am)
- UI: due date badge in tags row (red=overdue, amber=≤3 days, grey=future), ↻ icon for recurrence

## File Changes

### 1. `backend/pyproject.toml`
Add `python-dateutil>=2.9` to dependencies.

### 2. Migration `backend/migrations/versions/<hash>_add_recurrence_to_todos.py`
Add `recurrence_rule VARCHAR(100) NULLABLE` column to todos table.

### 3. `backend/src/istari/models/todo.py`
Add:
```python
recurrence_rule: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

### 4. `backend/src/istari/config/settings.py`
Add:
```python
deadline_urgent_days: int = 3  # todos due within N days auto-elevate to urgent
```

### 5. `backend/src/istari/tools/todo/manager.py`
- **`get_due_soon(days: int) -> list[Todo]`**: all non-complete todos with `due_date` within `days` days (includes overdue). Used by worker job.
- **`create_next_recurrence(todo: Todo) -> Todo`**: parse RRULE via `dateutil.rrule.rrulestr`, calculate next occurrence after today, create new Todo copying title, project_id, urgent, important, recurrence_rule.
- **Modify `get_prioritized()`**: add `deadline_urgent` expression (due_date <= now + deadline_urgent_days) to the quadrant case() so deadline-due todos sort as Q1 (if important) or Q3 (if not).
- **Modify `list_visible()`**: add overdue sort priority so overdue todos sort above unclassified (slot between Q3 and unclassified).

### 6. `backend/src/istari/api/schemas.py`
Add `recurrence_rule: str | None = None` to `TodoUpdate` and `TodoResponse`.

### 7. `backend/src/istari/api/routes/todos.py`
In `complete_todo`: after marking complete, check `todo.recurrence_rule` — if set, call `mgr.create_next_recurrence(todo)` and commit. Response still returns the completed todo (not the new one).

### 8. `backend/src/istari/agents/tools/todo.py`
Add two new tools to `make_todo_tools()`:
- **`set_due_date(query, due_date)`**: find by ID or ILIKE, set due_date (YYYY-MM-DD format, or "" to clear). Parse date with `datetime.date.fromisoformat`.
- **`create_recurring_todo(title, recurrence_rule, start_date)`**: create todo with title + recurrence_rule (RRULE string); if start_date given parse as due_date; else first occurrence calculated from today.

Also update `list_todos` output to include due date when present, and update `get_priorities` to flag overdue/due-soon todos.

### 9. `backend/src/istari/worker/jobs/deadline_nudge.py` (new file)
Pattern from `project_staleness.py`:
- `check_deadline_todos()`: calls `TodoManager.get_due_soon(days=deadline_nudge_days)`, creates `deadline_nudge` notification per todo.
- `deadline_nudge_sync()`: sync wrapper for APScheduler.

### 10. `backend/src/istari/config/schedules.yml`
Add:
```yaml
deadline_nudge:
  cron: "0 9 * * *"
  description: Deadline nudge notifications (daily 9am)
```

### 11. `backend/src/istari/worker/main.py`
Import `deadline_nudge_sync` and register with `respect_quiet_hours`.

### 12. `frontend/src/types/todo.ts`
Add `recurrence_rule?: string | null`.

### 13. `frontend/src/components/TodoPanel/TodoItem.tsx`
In the tags row (showTags), add:
- Due date badge: if `todo.due_date`, parse date, show "Overdue" (red) / "Due today" (amber) / "Due Mar 15" (amber if ≤3 days, grey if future)
- ↻ recurrence icon/badge: if `todo.recurrence_rule`, show small "↻" indicator next to due date

### 14. Tests
- `backend/tests/unit/test_tools/test_todo_manager.py`: tests for `get_due_soon`, `create_next_recurrence`, and deadline auto-urgency in `get_prioritized`.
- `backend/tests/unit/test_agents/test_agent_tools.py`: tests for `set_due_date` and `create_recurring_todo` tools.
- `backend/tests/unit/test_worker/test_deadline_nudge.py` (new): tests for the worker job.

## Verification
1. `cd backend && pytest` — all tests pass
2. `cd backend && ruff check src/ tests/` — clean
3. `cd backend && mypy src/` — clean
4. `cd frontend && npm test` — all tests pass
5. `cd frontend && npm run lint && npm run typecheck` — clean
6. Manual: create a weekly-Thursday todo with a due date, complete it, verify new instance created with next Thursday's due date
