import type { Todo } from "../../types/todo";

interface TodoItemProps {
  todo: Todo;
}

export function TodoItem({ todo }: TodoItemProps) {
  return (
    <div
      style={{
        padding: "0.5rem",
        marginBottom: "0.5rem",
        borderRadius: "4px",
        border: "1px solid #e0e0e0",
      }}
    >
      <div style={{ fontWeight: 500 }}>{todo.title}</div>
      {todo.priority != null && (
        <span style={{ fontSize: "0.75rem", color: "#666" }}>Priority: {todo.priority}</span>
      )}
    </div>
  );
}
