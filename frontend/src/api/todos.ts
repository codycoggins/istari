import type { Todo } from "../types/todo";
import { apiFetch } from "./client";

export async function listTodos(): Promise<{ todos: Todo[] }> {
  return apiFetch("/todos/");
}

export async function completeTodo(id: number): Promise<Todo> {
  return apiFetch(`/todos/${id}/complete`, { method: "POST" });
}
