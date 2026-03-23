import { useEffect, useState } from "react";

const TASKS_COLLAPSED_KEY = "istari-tasks-collapsed";
const SETTINGS_COLLAPSED_KEY = "istari-settings-collapsed";
import type { Todo } from "../../types/todo";
import type { TodoUpdatePayload } from "../../api/todos";
import { listProjects } from "../../api/projects";
import type { Project } from "../../types/project";
import { TodoItem } from "./TodoItem";

function isCompletedBeforeToday(todo: Todo): boolean {
  if (todo.status !== "complete") return false;
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  return new Date(todo.updated_at) < midnight;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// ── Shared input style ────────────────────────────────────
const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.4rem 0.625rem",
  borderRadius: "5px",
  border: "1px solid var(--border-default)",
  background: "var(--bg-input)",
  color: "var(--text-primary)",
  fontSize: "0.875rem",
  fontFamily: "inherit",
  outline: "none",
  boxSizing: "border-box",
};

// ── Field wrapper ─────────────────────────────────────────
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div
        style={{
          fontSize: "0.625rem",
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
          marginBottom: "0.3rem",
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}

// ── Detail / edit panel ───────────────────────────────────
function TodoDetailPanel({
  todo,
  onClose,
  onSave,
}: {
  todo: Todo;
  onClose: () => void;
  onSave: (id: number, updates: TodoUpdatePayload) => Promise<void>;
}) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState({
    title: todo.title,
    body: todo.body ?? "",
    status: todo.status,
    priority: todo.priority != null ? String(todo.priority) : "",
    urgent: todo.urgent === true ? "true" : todo.urgent === false ? "false" : "",
    important: todo.important === true ? "true" : todo.important === false ? "false" : "",
    source: todo.source ?? "",
    source_link: todo.source_link ?? "",
    due_date: todo.due_date ? todo.due_date.slice(0, 10) : "",
    tags: (todo.tags ?? []).join(", "),
    project_id: todo.project_id != null ? String(todo.project_id) : "",
  });

  useEffect(() => {
    listProjects().then(({ projects: p }) => setProjects(p)).catch(() => {});
  }, []);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setIsSaving(true);
    setError(null);
    const payload: TodoUpdatePayload = {
      title: form.title.trim(),
      body: form.body.trim() || null,
      status: form.status,
      priority: form.priority ? parseInt(form.priority, 10) : null,
      urgent: form.urgent === "true" ? true : form.urgent === "false" ? false : null,
      important: form.important === "true" ? true : form.important === "false" ? false : null,
      source: form.source.trim() || null,
      source_link: form.source_link.trim() || null,
      due_date: form.due_date || null,
      tags: form.tags ? form.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      project_id: form.project_id ? parseInt(form.project_id, 10) : null,
    };
    try {
      await onSave(todo.id, payload);
      onClose();
    } catch {
      setError("Save failed — please try again.");
      setIsSaving(false);
    }
  };

  return (
    /* Backdrop */
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
      }}
    >
      {/* Panel */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "480px",
          maxHeight: "88vh",
          overflowY: "auto",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "10px",
          boxShadow: "0 16px 48px rgba(0,0,0,0.5)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.625rem",
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border-subtle)",
            flexShrink: 0,
          }}
        >
          <span style={{ color: "var(--accent)", fontSize: "0.875rem" }}>✦</span>
          <span
            style={{
              flex: 1,
              fontSize: "0.75rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
            }}
          >
            Edit Task
          </span>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              fontSize: "1rem",
              lineHeight: 1,
              padding: "0.1rem 0.25rem",
            }}
          >
            ✕
          </button>
        </div>

        {/* Form body */}
        <div
          style={{
            padding: "1.125rem 1.25rem",
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
          }}
        >
          {/* Title */}
          <Field label="Title">
            <input
              type="text"
              value={form.title}
              onChange={set("title")}
              style={inputStyle}
              autoFocus
            />
          </Field>

          {/* Status + Urgency/Importance row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
            <Field label="Status">
              <select value={form.status} onChange={set("status")} style={inputStyle}>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="blocked">Blocked</option>
                <option value="complete">Complete</option>
                <option value="deferred">Deferred</option>
              </select>
            </Field>
            <Field label="Urgent">
              <select value={form.urgent} onChange={set("urgent")} style={inputStyle}>
                <option value="">—</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </Field>
            <Field label="Important">
              <select value={form.important} onChange={set("important")} style={inputStyle}>
                <option value="">—</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </Field>
          </div>

          {/* Description */}
          <Field label="Description">
            <textarea
              value={form.body}
              onChange={set("body")}
              rows={3}
              placeholder="Add a description…"
              style={{ ...inputStyle, resize: "vertical", lineHeight: 1.5 }}
            />
          </Field>

          {/* Source + Source Link row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <Field label="Source">
              <input
                type="text"
                value={form.source}
                onChange={set("source")}
                placeholder="e.g. Slack, Email"
                style={inputStyle}
              />
            </Field>
            <Field label="Source Link">
              <input
                type="url"
                value={form.source_link}
                onChange={set("source_link")}
                placeholder="https://…"
                style={inputStyle}
              />
            </Field>
          </div>

          {/* Due Date + Priority # row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <Field label="Due Date">
              <input
                type="date"
                value={form.due_date}
                onChange={set("due_date")}
                style={inputStyle}
              />
            </Field>
            <Field label="Priority #">
              <input
                type="number"
                min={1}
                value={form.priority}
                onChange={set("priority")}
                placeholder="—"
                style={inputStyle}
              />
            </Field>
          </div>

          {/* Tags */}
          <Field label="Tags (comma-separated)">
            <input
              type="text"
              value={form.tags}
              onChange={set("tags")}
              placeholder="work, urgent, waiting"
              style={inputStyle}
            />
          </Field>

          {/* Project */}
          <Field label="Project">
            <select value={form.project_id} onChange={set("project_id")} style={inputStyle}>
              <option value="">— None —</option>
              {projects.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>

          {/* Timestamps (read-only) */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "0.75rem",
              paddingTop: "0.625rem",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            <Field label="Created">
              <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                {formatDate(todo.created_at)}
              </span>
            </Field>
            <Field label="Updated">
              <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                {formatDate(todo.updated_at)}
              </span>
            </Field>
          </div>

          {/* Error */}
          {error && (
            <p style={{ fontSize: "0.8125rem", color: "var(--q1)", margin: 0 }}>{error}</p>
          )}

          {/* Save button */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              onClick={handleSave}
              disabled={isSaving || !form.title.trim()}
              style={{
                padding: "0.5rem 1.25rem",
                borderRadius: "6px",
                border: `1px solid ${isSaving ? "var(--border-subtle)" : "var(--border-accent)"}`,
                background: isSaving ? "transparent" : "var(--accent-dim)",
                color: isSaving ? "var(--text-muted)" : "var(--accent)",
                fontSize: "0.875rem",
                fontWeight: 600,
                fontFamily: "inherit",
                cursor: isSaving ? "not-allowed" : "pointer",
                transition: "all 0.15s",
              }}
            >
              {isSaving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── TodoPanel ─────────────────────────────────────────────
interface TodoPanelProps {
  todos: Todo[];
  isLoading: boolean;
  onComplete: (id: number) => void;
  onReopen: (id: number) => void;
  onSave: (id: number, updates: TodoUpdatePayload) => Promise<void>;
  onToggleToday?: (id: number) => void;
  onAskPriorities?: () => void;
  onRefresh?: () => void;
  settings?: Record<string, string>;
  onToggleFocusMode?: (enabled: boolean) => void;
  projects?: Project[];
  projectFilter?: number | null;
  onSelectProject?: (id: number | null) => void;
}

export function TodoPanel({
  todos,
  isLoading,
  onComplete,
  onReopen,
  onSave,
  onToggleToday,
  onAskPriorities,
  onRefresh,
  settings,
  onToggleFocusMode,
  projects,
  projectFilter,
  onSelectProject,
}: TodoPanelProps) {
  const [editTodo, setEditTodo] = useState<Todo | null>(null);
  const [isTasksCollapsed, setIsTasksCollapsed] = useState<boolean>(
    () => localStorage.getItem(TASKS_COLLAPSED_KEY) === "true",
  );
  const [isSettingsCollapsed, setIsSettingsCollapsed] = useState<boolean>(
    () => localStorage.getItem(SETTINGS_COLLAPSED_KEY) === "true",
  );
  const focusMode = settings?.focus_mode === "true";
  const quietStart = settings?.quiet_hours_start ?? "21";
  const quietEnd = settings?.quiet_hours_end ?? "7";
  const todayStr = new Date().toISOString().slice(0, 10);
  const filteredByProject = projectFilter === 0
    ? todos.filter((t) => t.project_id == null)
    : projectFilter != null
    ? todos.filter((t) => t.project_id === projectFilter)
    : todos;
  const visibleTodos = filteredByProject.filter((t) => !isCompletedBeforeToday(t));
  const todayTodos = visibleTodos.filter((t) => t.today_date === todayStr);
  const remainingTodos = visibleTodos.filter((t) => t.today_date !== todayStr);

  const selectedProject = projects?.find((p) => p.id === projectFilter) ?? null;

  return (
    <>
      <div style={{ padding: "1rem 0.875rem", display: "flex", flexDirection: "column", gap: 0 }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: isTasksCollapsed ? 0 : "0.75rem",
            paddingBottom: "0.625rem",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <button
            onClick={() => {
              setIsTasksCollapsed((prev) => {
                const next = !prev;
                localStorage.setItem(TASKS_COLLAPSED_KEY, String(next));
                return next;
              });
            }}
            aria-label={isTasksCollapsed ? "Expand tasks" : "Collapse tasks"}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.3rem",
              background: "none",
              border: "none",
              padding: 0,
              cursor: "pointer",
              fontSize: "1rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
              fontFamily: "inherit",
            }}
          >
            <span
              style={{
                fontSize: "0.75rem",
                transition: "transform 0.2s",
                transform: isTasksCollapsed ? "rotate(-90deg)" : "rotate(0deg)",
                display: "inline-block",
              }}
            >
              ▾
            </span>
            Tasks
          </button>
          {!isTasksCollapsed && (
            <div style={{ display: "flex", gap: "0.375rem" }}>
              <button
                onClick={onRefresh}
                aria-label="Refresh tasks"
                disabled={isLoading}
                title="Refresh"
                style={{
                  background: "none",
                  border: "1px solid var(--border-default)",
                  borderRadius: "5px",
                  padding: "0.25rem 0.5rem",
                  cursor: isLoading ? "not-allowed" : "pointer",
                  fontSize: "0.75rem",
                  color: isLoading ? "var(--text-muted)" : "var(--text-secondary)",
                  fontFamily: "inherit",
                  lineHeight: 1,
                  transition: "all 0.15s",
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.borderColor = "var(--border-accent)";
                    e.currentTarget.style.color = "var(--accent)";
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-default)";
                  e.currentTarget.style.color = isLoading ? "var(--text-muted)" : "var(--text-secondary)";
                }}
              >
                ↻
              </button>
              <button
                onClick={onAskPriorities}
                style={{
                  background: "none",
                  border: "1px solid var(--border-default)",
                  borderRadius: "5px",
                  padding: "0.25rem 0.625rem",
                  cursor: "pointer",
                  fontSize: "0.6875rem",
                  color: "var(--text-secondary)",
                  fontFamily: "inherit",
                  transition: "all 0.15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-accent)";
                  e.currentTarget.style.color = "var(--accent)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-default)";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }}
              >
                Prioritize
              </button>
            </div>
          )}
        </div>

        {/* Task body — collapsed when isTasksCollapsed */}
        {!isTasksCollapsed && (
          <>
            {/* Project filter bar */}
            {projects && projects.length > 0 && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  flexWrap: "wrap",
                  marginBottom: "0.625rem",
                }}
              >
                <button
                  onClick={() => onSelectProject?.(null)}
                  style={{
                    background: projectFilter == null ? "var(--accent-dim)" : "none",
                    border: `1px solid ${projectFilter == null ? "var(--border-accent)" : "var(--border-subtle)"}`,
                    borderRadius: "4px",
                    padding: "0.15rem 0.5rem",
                    cursor: "pointer",
                    fontSize: "0.625rem",
                    fontWeight: 600,
                    color: projectFilter == null ? "var(--accent)" : "var(--text-muted)",
                    fontFamily: "inherit",
                    transition: "all 0.15s",
                  }}
                >
                  All
                </button>
                <button
                  onClick={() => onSelectProject?.(projectFilter === 0 ? null : 0)}
                  style={{
                    background: projectFilter === 0 ? "var(--accent-dim)" : "none",
                    border: `1px solid ${projectFilter === 0 ? "var(--border-accent)" : "var(--border-subtle)"}`,
                    borderRadius: "4px",
                    padding: "0.15rem 0.5rem",
                    cursor: "pointer",
                    fontSize: "0.625rem",
                    fontWeight: 600,
                    color: projectFilter === 0 ? "var(--accent)" : "var(--text-muted)",
                    fontFamily: "inherit",
                    transition: "all 0.15s",
                  }}
                >
                  No Project
                </button>
                {projects.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => onSelectProject?.(projectFilter === p.id ? null : p.id)}
                    title={p.goal ?? undefined}
                    style={{
                      background: projectFilter === p.id ? "var(--accent-dim)" : "none",
                      border: `1px solid ${projectFilter === p.id ? "var(--border-accent)" : "var(--border-subtle)"}`,
                      borderRadius: "4px",
                      padding: "0.15rem 0.5rem",
                      cursor: "pointer",
                      fontSize: "0.625rem",
                      fontWeight: 600,
                      color: projectFilter === p.id ? "var(--accent)" : "var(--text-muted)",
                      fontFamily: "inherit",
                      maxWidth: "100px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      transition: "all 0.15s",
                    }}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            )}

            {/* Today's Tasks section */}
            {!isLoading && todayTodos.length > 0 && (
              <>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    marginBottom: "0.5rem",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.625rem",
                      fontWeight: 700,
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      color: "var(--accent)",
                    }}
                  >
                    Today's Tasks
                  </span>
                  <span
                    style={{
                      fontSize: "0.625rem",
                      fontWeight: 700,
                      padding: "0.1rem 0.4rem",
                      borderRadius: "3px",
                      background: todayTodos.length >= 5 ? "var(--accent-dim)" : "var(--bg-elevated)",
                      color: todayTodos.length >= 5 ? "var(--accent)" : "var(--text-muted)",
                      border: `1px solid ${todayTodos.length >= 5 ? "var(--border-accent)" : "var(--border-subtle)"}`,
                    }}
                  >
                    {todayTodos.length} / 5
                  </span>
                </div>
                {todayTodos.map((todo) => {
                  const proj = projects?.find((p) => p.id === todo.project_id);
                  return (
                    <TodoItem
                      key={todo.id}
                      todo={todo}
                      onComplete={onComplete}
                      onReopen={onReopen}
                      onEdit={setEditTodo}
                      onToggleToday={onToggleToday}
                      projectName={projectFilter == null ? proj?.name : undefined}
                      isNextAction={proj?.next_action_id === todo.id}
                    />
                  );
                })}
                <hr
                  style={{
                    border: "none",
                    borderTop: "1px solid var(--border-subtle)",
                    margin: "0.625rem 0",
                  }}
                />
              </>
            )}

            {/* Todo list */}
            {isLoading && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "0.5rem 0" }}>
                Loading...
              </p>
            )}
            {!isLoading && visibleTodos.length === 0 && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "0.5rem 0" }}>
                {selectedProject ? `No tasks in "${selectedProject.name}"` : "No tasks yet"}
              </p>
            )}
            {!isLoading && todayTodos.length > 0 && remainingTodos.length > 0 && (
              <div style={{ marginBottom: "0.5rem" }}>
                <span
                  style={{
                    fontSize: "0.625rem",
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "var(--text-muted)",
                  }}
                >
                  Other Tasks
                </span>
              </div>
            )}
            {remainingTodos.map((todo) => {
              const proj = projects?.find((p) => p.id === todo.project_id);
              return (
                <TodoItem
                  key={todo.id}
                  todo={todo}
                  onComplete={onComplete}
                  onReopen={onReopen}
                  onEdit={setEditTodo}
                  onToggleToday={onToggleToday}
                  projectName={projectFilter == null ? proj?.name : undefined}
                  isNextAction={proj?.next_action_id === todo.id}
                />
              );
            })}
          </>
        )}

        {/* Settings section */}
        {settings && (
          <div
            style={{
              marginTop: isTasksCollapsed ? "0.625rem" : "1.25rem",
              paddingTop: "0.875rem",
              borderTop: isTasksCollapsed ? "none" : "1px solid var(--border-subtle)",
            }}
          >
            <button
              onClick={() => {
                setIsSettingsCollapsed((prev) => {
                  const next = !prev;
                  localStorage.setItem(SETTINGS_COLLAPSED_KEY, String(next));
                  return next;
                });
              }}
              aria-label={isSettingsCollapsed ? "Expand settings" : "Collapse settings"}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.3rem",
                background: "none",
                border: "none",
                padding: 0,
                cursor: "pointer",
                fontSize: "1rem",
                fontWeight: 700,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--text-muted)",
                fontFamily: "inherit",
                marginBottom: isSettingsCollapsed ? 0 : "0.625rem",
              }}
            >
              <span
                style={{
                  fontSize: "0.75rem",
                  transition: "transform 0.2s",
                  transform: isSettingsCollapsed ? "rotate(-90deg)" : "rotate(0deg)",
                  display: "inline-block",
                }}
              >
                ▾
              </span>
              Settings
            </button>
            {!isSettingsCollapsed && (
              <>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    fontSize: "0.8125rem",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    marginBottom: "0.5rem",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={focusMode}
                    onChange={(e) => onToggleFocusMode?.(e.target.checked)}
                    style={{ accentColor: "var(--accent)", cursor: "pointer" }}
                  />
                  Focus mode
                </label>
                <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", margin: 0 }}>
                  Quiet hours: {quietStart}:00 – {quietEnd}:00
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {editTodo && (
        <TodoDetailPanel
          todo={editTodo}
          onClose={() => setEditTodo(null)}
          onSave={onSave}
        />
      )}
    </>
  );
}
