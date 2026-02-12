import { useCallback, useState } from "react";
import type { Message } from "../types/message";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(
    async (content: string) => {
      setIsLoading(true);
      // TODO: wire up chat API + WebSocket
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(false);
    },
    [],
  );

  return { messages, isLoading, sendMessage };
}
