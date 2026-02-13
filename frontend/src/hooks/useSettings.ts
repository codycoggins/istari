import { useCallback, useEffect, useState } from "react";
import { getSettings, updateSetting } from "../api/settings";

export function useSettings() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getSettings()
      .then((data) => setSettings(data.settings))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const update = useCallback(async (key: string, value: string) => {
    await updateSetting(key, value);
    setSettings((prev) => ({ ...prev, [key]: value }));
  }, []);

  return { settings, isLoading, update };
}
