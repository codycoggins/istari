import type { Todo } from "../../types/todo";

interface TodoItemProps {
  todo: Todo;
  onComplete: (id: number) => void;
}

function getQuadrant(urgent?: boolean | null, important?: boolean | null) {
  if (urgent === true && important === true) return { label: "Do Now", color: "#c53030" };
  if (important === true) return { label: "Schedule", color: "#2b6cb0" };
  if (urgent === true) return { label: "Delegate", color: "#c05621" };
  if (urgent === false && important === false) return { label: "Drop", color: "#718096" };
  return null;
}

export function TodoItem({ todo, onComplete }: TodoItemProps) {
  const isComplete = todo.status === "complete";
  const quadrant = getQuadrant(todo.urgent, todo.important);

  return (
    <div
      style={{
        padding: "0.5rem",
        marginBottom: "0.5rem",
        borderRadius: "4px",
        border: "1px solid #e0e0e0",
        display: "flex",
        alignItems: "flex-start",
        gap: "0.5rem",
        opacity: isComplete ? 0.6 : 1,
      }}
    >
      <input
        type="checkbox"
        checked={isComplete}
        disabled={isComplete}
        onChange={() => onComplete(todo.id)}
        style={{ marginTop: "0.2rem", flexShrink: 0 }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontWeight: 500,
            textDecoration: isComplete ? "line-through" : "none",
          }}
        >
          {todo.title}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", flexWrap: "wrap", marginTop: quadrant || todo.priority != null || todo.status === "in_progress" || todo.status === "blocked" ? "0.2rem" : 0 }}>
          {quadrant && (
            <span
              style={{
                fontSize: "0.65rem",
                padding: "0.1rem 0.4rem",
                borderRadius: "3px",
                background: quadrant.color,
                color: "white",
                fontWeight: 600,
                letterSpacing: "0.02em",
                flexShrink: 0,
              }}
            >
              {quadrant.label}
            </span>
          )}
          {todo.priority != null && (
            <span style={{ fontSize: "0.75rem", color: "#666" }}>
              Priority: {todo.priority}
            </span>
          )}
          {todo.status === "in_progress" && (
            <span style={{ fontSize: "0.75rem", color: "#3182ce" }}>In progress</span>
          )}
          {todo.status === "blocked" && (
            <span style={{ fontSize: "0.75rem", color: "#e53e3e" }}>Blocked</span>
          )}
        </div>
      </div>
    </div>
  );
}
