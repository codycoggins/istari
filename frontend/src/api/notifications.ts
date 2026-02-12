import type { Notification } from "../types/notification";
import { apiFetch } from "./client";

export async function listNotifications(): Promise<{ notifications: Notification[] }> {
  return apiFetch("/notifications/");
}
