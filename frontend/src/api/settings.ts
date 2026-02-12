import { apiFetch } from "./client";

export async function getSettings(): Promise<{ settings: Record<string, string> }> {
  return apiFetch("/settings/");
}
