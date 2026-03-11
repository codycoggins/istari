import { apiFetch } from "./client";
import type { Project, ProjectWithTodos } from "../types/project";

export interface ProjectUpdatePayload {
  name?: string;
  description?: string | null;
  goal?: string | null;
  status?: "active" | "paused" | "complete";
}

export async function listProjects(status = "active"): Promise<{ projects: Project[] }> {
  return apiFetch(`/projects/?status=${status}`);
}

export async function getProject(id: number): Promise<ProjectWithTodos> {
  return apiFetch(`/projects/${id}`);
}

export async function createProject(data: {
  name: string;
  description?: string;
  goal?: string;
}): Promise<Project> {
  return apiFetch("/projects/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProject(id: number, updates: ProjectUpdatePayload): Promise<Project> {
  return apiFetch(`/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function setNextAction(projectId: number, todoId: number | null): Promise<Project> {
  return apiFetch(`/projects/${projectId}/next-action`, {
    method: "POST",
    body: JSON.stringify({ todo_id: todoId }),
  });
}
