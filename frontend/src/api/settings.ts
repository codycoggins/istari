import { apiFetch } from "./client";

export async function getSettings(): Promise<{ settings: Record<string, string> }> {
  return apiFetch("/settings/");
}

export async function updateSetting(
  key: string,
  value: string,
): Promise<{ key: string; value: string }> {
  return apiFetch(`/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}
