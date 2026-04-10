import { useCallback, useEffect, useRef, useState } from "react";
import type { Project } from "../types/project";
import {
  listProjects,
  updateProject as apiUpdateProject,
  type ProjectUpdatePayload,
} from "../api/projects";

const POLL_INTERVAL_MS = 30_000;

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listProjects("active");
      setProjects(data.projects);
      setError(null);
    } catch {
      setError("Failed to load projects.");
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setIsLoading(false));

    intervalRef.current = setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [refresh]);

  const updateProject = useCallback(
    async (id: number, updates: ProjectUpdatePayload) => {
      await apiUpdateProject(id, updates);
      await refresh();
    },
    [refresh],
  );

  return { projects, isLoading, error, refresh, updateProject };
}
