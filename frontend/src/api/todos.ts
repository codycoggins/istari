import type { Todo } from "../types/todo";
import { apiFetch } from "./client";

export interface TodoUpdatePayload {
  title: string;
  body: string | null;
  status: string;
  priority: number | null;
  urgent: boolean | null;
  important: boolean | null;
  source: string | null;
  source_link: string | null;
  due_date: string | null;
  tags: string[];
}

export async function listTodos(): Promise<{ todos: Todo[] }> {
  return apiFetch("/todos/");
}

export async function completeTodo(id: number): Promise<Todo> {
  return apiFetch(`/todos/${id}/complete`, { method: "POST" });
}

export async function reopenTodo(id: number): Promise<Todo> {
  return apiFetch(`/todos/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "open" }),
  });
}

export async function updateTodo(id: number, updates: TodoUpdatePayload): Promise<Todo> {
  return apiFetch(`/todos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}
