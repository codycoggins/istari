import { useCallback, useEffect, useState } from "react";
import type { Todo } from "../types/todo";
import {
  listTodos,
  completeTodo as apiCompleteTodo,
  reopenTodo as apiReopenTodo,
  updateTodo as apiUpdateTodo,
  toggleTodayFocus as apiToggleTodayFocus,
  type TodoUpdatePayload,
} from "../api/todos";

export function useTodos() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setError(null);
    listTodos()
      .then((data) => {
        setTodos(data.todos);
        setError(null);
      })
      .catch(() => setError("Failed to load tasks."))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15_000);
    return () => clearInterval(id);
  }, [refresh]);

  const completeTodo = useCallback(
    async (id: number) => {
      await apiCompleteTodo(id);
      refresh();
    },
    [refresh],
  );

  const reopenTodo = useCallback(
    async (id: number) => {
      await apiReopenTodo(id);
      refresh();
    },
    [refresh],
  );

  const updateTodo = useCallback(
    async (id: number, updates: TodoUpdatePayload) => {
      await apiUpdateTodo(id, updates);
      refresh();
    },
    [refresh],
  );

  const toggleTodayFocus = useCallback(
    async (id: number) => {
      await apiToggleTodayFocus(id);
      refresh();
    },
    [refresh],
  );

  return { todos, isLoading, error, refresh, completeTodo, reopenTodo, updateTodo, toggleTodayFocus };
}
