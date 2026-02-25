import { useCallback, useEffect, useState } from "react";
import type { Todo } from "../types/todo";
import {
  listTodos,
  completeTodo as apiCompleteTodo,
  reopenTodo as apiReopenTodo,
  updateTodo as apiUpdateTodo,
  type TodoUpdatePayload,
} from "../api/todos";

export function useTodos() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(() => {
    listTodos()
      .then((data) => setTodos(data.todos))
      .catch(() => {})
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

  return { todos, isLoading, refresh, completeTodo, reopenTodo, updateTodo };
}
