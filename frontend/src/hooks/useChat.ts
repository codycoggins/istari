import { useCallback, useEffect, useRef, useState } from "react";
import type { Message } from "../types/message";

interface UseChatOptions {
  onTodoCreated?: () => void;
  onMemoryCreated?: () => void;
}

export function useChat({ onTodoCreated, onMemoryCreated }: UseChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const reconnectAttemptsRef = useRef(0);
  const callbacksRef = useRef({ onTodoCreated, onMemoryCreated });
  callbacksRef.current = { onTodoCreated, onMemoryCreated };

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/chat/ws`);

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const msg: Message = {
        id: data.id,
        role: "assistant",
        content: data.content,
        createdAt: data.created_at,
        todoCreated: data.todo_created,
        memoryCreated: data.memory_created,
      };
      setMessages((prev) => [...prev, msg]);
      setIsLoading(false);

      if (data.todo_created || data.todo_updated) {
        callbacksRef.current.onTodoCreated?.();
      }
      if (data.memory_created) {
        callbacksRef.current.onMemoryCreated?.();
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      // Reconnect with exponential backoff
      const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000);
      reconnectAttemptsRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      wsRef.current.send(JSON.stringify({ message: content }));
    },
    [],
  );

  return { messages, isLoading, isConnected, sendMessage };
}
