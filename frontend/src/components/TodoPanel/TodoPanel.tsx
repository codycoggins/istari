import type { Todo } from "../../types/todo";
import { TodoItem } from "./TodoItem";

export function TodoPanel() {
  const todos: Todo[] = [];

  return (
    <div style={{ padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ fontSize: "1rem" }}>TODOs</h2>
        <button style={{ fontSize: "0.875rem", padding: "0.25rem 0.75rem" }}>
          What should I work on?
        </button>
      </div>
      {todos.length === 0 && <p style={{ color: "#888", fontSize: "0.875rem" }}>No TODOs yet</p>}
      {todos.map((todo) => (
        <TodoItem key={todo.id} todo={todo} />
      ))}
    </div>
  );
}
