import type { Todo } from "../../types/todo";

interface TodoItemProps {
  todo: Todo;
  onComplete: (id: number) => void;
}

export function TodoItem({ todo, onComplete }: TodoItemProps) {
  const isComplete = todo.status === "complete";

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
        {todo.priority != null && (
          <span style={{ fontSize: "0.75rem", color: "#666" }}>
            Priority: {todo.priority}
          </span>
        )}
        {todo.status === "in_progress" && (
          <span style={{ fontSize: "0.75rem", color: "#3182ce" }}> In progress</span>
        )}
        {todo.status === "blocked" && (
          <span style={{ fontSize: "0.75rem", color: "#e53e3e" }}> Blocked</span>
        )}
      </div>
    </div>
  );
}
