import { apiFetch } from "./client";

export async function getConversations() {
  return apiFetch("/chat/");
}
