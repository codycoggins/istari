import type { Digest } from "../types/digest";
import { apiFetch } from "./client";

export async function listDigests(limit = 10): Promise<{ digests: Digest[] }> {
  return apiFetch(`/digests/?limit=${limit}`);
}

export async function markReviewed(id: number): Promise<Digest> {
  return apiFetch(`/digests/${id}/review`, { method: "POST" });
}
