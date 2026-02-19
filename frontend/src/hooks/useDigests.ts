import { useCallback, useEffect, useRef, useState } from "react";
import type { Digest } from "../types/digest";
import { listDigests, markReviewed as apiMarkReviewed } from "../api/digests";

const POLL_INTERVAL_MS = 60_000;

export function useDigests() {
  const [digests, setDigests] = useState<Digest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listDigests();
      setDigests(data.digests);
    } catch {
      // silently ignore
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

  const markReviewed = useCallback(
    async (id: number) => {
      await apiMarkReviewed(id);
      await refresh();
    },
    [refresh],
  );

  return { digests, isLoading, markReviewed, refresh };
}
