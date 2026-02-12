import { useState } from "react";
import type { Message } from "../types/message";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (_content: string) => {
    setIsLoading(true);
    // Chat implementation will be wired here
    setIsLoading(false);
  };

  return { messages, isLoading, sendMessage };
}
