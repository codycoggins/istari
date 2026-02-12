export interface Todo {
  id: number;
  title: string;
  body?: string;
  status: "active" | "completed" | "deferred";
  priority?: number;
  source?: string;
  sourceLink?: string;
  dueDate?: string;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}
