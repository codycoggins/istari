import type { Todo } from "../../types/todo";
import { TodoItem } from "./TodoItem";

function isCompletedBeforeToday(todo: Todo): boolean {
  if (todo.status !== "complete") return false;
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  return new Date(todo.updated_at) < midnight;
}

interface TodoPanelProps {
  todos: Todo[];
  isLoading: boolean;
  onComplete: (id: number) => void;
  onReopen: (id: number) => void;
  onAskPriorities?: () => void;
  settings?: Record<string, string>;
  onToggleFocusMode?: (enabled: boolean) => void;
}

export function TodoPanel({
  todos,
  isLoading,
  onComplete,
  onReopen,
  onAskPriorities,
  settings,
  onToggleFocusMode,
}: TodoPanelProps) {
  const focusMode = settings?.focus_mode === "true";
  const quietStart = settings?.quiet_hours_start ?? "21";
  const quietEnd = settings?.quiet_hours_end ?? "7";
  const visibleTodos = todos.filter((t) => !isCompletedBeforeToday(t));

  return (
    <div style={{ padding: "1rem 0.875rem", display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.75rem",
          paddingBottom: "0.625rem",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <span
          style={{
            fontSize: "0.625rem",
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--text-muted)",
          }}
        >
          Tasks
        </span>
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

      {/* Todo list */}
      {isLoading && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "0.5rem 0" }}>
          Loading...
        </p>
      )}
      {!isLoading && visibleTodos.length === 0 && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "0.5rem 0" }}>
          No tasks yet
        </p>
      )}
      {visibleTodos.map((todo) => (
        <TodoItem key={todo.id} todo={todo} onComplete={onComplete} onReopen={onReopen} />
      ))}

      {/* Settings section */}
      {settings && (
        <div
          style={{
            marginTop: "1.25rem",
            paddingTop: "0.875rem",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <span
            style={{
              display: "block",
              fontSize: "0.625rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
              marginBottom: "0.625rem",
            }}
          >
            Settings
          </span>
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
          <p
            style={{
              fontSize: "0.6875rem",
              color: "var(--text-muted)",
              margin: 0,
            }}
          >
            Quiet hours: {quietStart}:00 – {quietEnd}:00
          </p>
        </div>
      )}
    </div>
  );
}
