import type { Notification } from "../types/notification";
import { apiFetch } from "./client";

export async function listNotifications(
  limit = 20,
  unreadOnly = false,
): Promise<{ notifications: Notification[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (unreadOnly) params.set("unread_only", "true");
  return apiFetch(`/notifications/?${params}`);
}

export async function getUnreadCount(): Promise<{ count: number }> {
  return apiFetch("/notifications/unread/count");
}

export async function markNotificationRead(id: number): Promise<Notification> {
  return apiFetch(`/notifications/${id}/read`, { method: "POST" });
}

export async function markAllRead(): Promise<{ count: number }> {
  return apiFetch("/notifications/read-all", { method: "POST" });
}
