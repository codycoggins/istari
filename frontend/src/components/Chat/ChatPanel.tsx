import { useEffect } from "react";
import { useChat } from "../../hooks/useChat";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";

interface ChatPanelProps {
  onTodoCreated?: () => void;
  onRegisterSend?: (fn: (msg: string) => void) => void;
}

export function ChatPanel({ onTodoCreated, onRegisterSend }: ChatPanelProps) {
  const { messages, isLoading, isConnected, sendMessage } = useChat({
    onTodoCreated,
  });

  useEffect(() => {
    onRegisterSend?.(sendMessage);
  }, [onRegisterSend, sendMessage]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Slim connection status bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "center",
          padding: "0.375rem 1rem",
          gap: "0.375rem",
          borderBottom: "1px solid var(--border-subtle)",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            flexShrink: 0,
            background: isConnected ? "var(--success)" : "var(--danger)",
            animation: isConnected ? "none" : "dot-pulse 1.5s ease-in-out infinite",
          }}
        />
        <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
          {isConnected ? "Connected" : "Reconnecting..."}
        </span>
      </div>

      <MessageList messages={messages} />

      {isLoading && (
        <div
          style={{
            padding: "0.375rem 1.25rem",
            display: "flex",
            alignItems: "center",
            gap: "0.375rem",
            flexShrink: 0,
            color: "var(--text-secondary)",
            fontSize: "0.8125rem",
          }}
        >
          <span style={{ color: "var(--accent)" }}>✦</span>
          Istari is thinking...
        </div>
      )}

      <ChatInput onSend={sendMessage} disabled={!isConnected} />
    </div>
  );
}
