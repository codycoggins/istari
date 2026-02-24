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
  onAskPriorities?: () => void;
  settings?: Record<string, string>;
  onToggleFocusMode?: (enabled: boolean) => void;
}

export function TodoPanel({
  todos,
  isLoading,
  onComplete,
  onAskPriorities,
  settings,
  onToggleFocusMode,
}: TodoPanelProps) {
  const focusMode = settings?.focus_mode === "true";
  const quietStart = settings?.quiet_hours_start ?? "21";
  const quietEnd = settings?.quiet_hours_end ?? "7";
  const visibleTodos = todos.filter((t) => !isCompletedBeforeToday(t));

  return (
    <div style={{ padding: "1rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h2 style={{ fontSize: "1rem" }}>TODOs</h2>
        <button
          onClick={onAskPriorities}
          style={{ fontSize: "0.875rem", padding: "0.25rem 0.75rem" }}
        >
          What should I work on?
        </button>
      </div>
      {isLoading && <p style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</p>}
      {!isLoading && visibleTodos.length === 0 && (
        <p style={{ color: "#888", fontSize: "0.875rem" }}>No TODOs yet</p>
      )}
      {visibleTodos.map((todo) => (
        <TodoItem key={todo.id} todo={todo} onComplete={onComplete} />
      ))}

      {settings && (
        <div
          style={{
            marginTop: "1.5rem",
            paddingTop: "1rem",
            borderTop: "1px solid #e0e0e0",
          }}
        >
          <h3 style={{ fontSize: "0.875rem", marginBottom: "0.5rem" }}>Settings</h3>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontSize: "0.875rem",
              marginBottom: "0.5rem",
            }}
          >
            <input
              type="checkbox"
              checked={focusMode}
              onChange={(e) => onToggleFocusMode?.(e.target.checked)}
            />
            Focus mode
          </label>
          <p style={{ fontSize: "0.75rem", color: "#888" }}>
            Quiet hours: {quietStart}:00 – {quietEnd}:00
          </p>
        </div>
      )}
    </div>
  );
}
