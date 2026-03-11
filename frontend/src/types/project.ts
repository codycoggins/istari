import type { Todo } from "./todo";

export interface Project {
  id: number;
  name: string;
  description: string | null;
  goal: string | null;
  status: "active" | "paused" | "complete";
  next_action_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectWithTodos extends Project {
  todos: Todo[];
}
