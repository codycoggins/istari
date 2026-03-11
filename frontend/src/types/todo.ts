export interface Todo {
  id: number;
  title: string;
  body?: string;
  status: "open" | "in_progress" | "blocked" | "complete" | "deferred";
  priority?: number;
  urgent?: boolean | null;
  important?: boolean | null;
  source?: string;
  source_link?: string;
  due_date?: string;
  today_date?: string | null;
  tags?: string[];
  project_id?: number | null;
  created_at: string;
  updated_at: string;
}
