import { useCallback, useEffect, useState } from "react";
import type { Todo } from "../types/todo";
import { listTodos, completeTodo as apiCompleteTodo, reopenTodo as apiReopenTodo } from "../api/todos";

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

  return { todos, isLoading, refresh, completeTodo, reopenTodo };
}
