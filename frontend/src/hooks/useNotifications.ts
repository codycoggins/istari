import { useState, useEffect } from "react";
import type { Notification } from "../types/notification";
import { listNotifications } from "../api/notifications";

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    listNotifications()
      .then((data) => setNotifications(data.notifications))
      .finally(() => setIsLoading(false));
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return { notifications, unreadCount, isLoading };
}
