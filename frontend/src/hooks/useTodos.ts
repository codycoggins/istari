import { useCallback, useEffect, useState } from "react";
import type { Todo } from "../types/todo";
import { listTodos } from "../api/todos";

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

  return { todos, isLoading, refresh };
}
