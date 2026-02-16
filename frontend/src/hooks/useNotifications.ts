import { useState, useEffect, useCallback, useRef } from "react";
import type { Notification } from "../types/notification";
import {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllRead as apiMarkAllRead,
} from "../api/notifications";

const POLL_INTERVAL_MS = 60_000;

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [listData, countData] = await Promise.all([
        listNotifications(),
        getUnreadCount(),
      ]);
      setNotifications(listData.notifications);
      setUnreadCount(countData.count);
    } catch {
      // silently ignore — network errors are transient
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

  const markRead = useCallback(
    async (id: number) => {
      await markNotificationRead(id);
      await refresh();
    },
    [refresh],
  );

  const markAllAsRead = useCallback(async () => {
    await apiMarkAllRead();
    await refresh();
  }, [refresh]);

  return { notifications, unreadCount, isLoading, markRead, markAllAsRead, refresh };
}
