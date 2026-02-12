import { useState, useEffect } from "react";
import type { Todo } from "../types/todo";
import { listTodos } from "../api/todos";

export function useTodos() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    listTodos()
      .then((data) => setTodos(data.todos))
      .finally(() => setIsLoading(false));
  }, []);

  return { todos, isLoading };
}
