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
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header
        style={{
          padding: "1rem",
          borderBottom: "1px solid #e0e0e0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1 style={{ fontSize: "1.25rem" }}>Istari</h1>
        <span
          style={{
            fontSize: "0.75rem",
            color: isConnected ? "#4caf50" : "#f44336",
          }}
        >
          {isConnected ? "Connected" : "Reconnecting..."}
        </span>
      </header>
      <MessageList messages={messages} />
      {isLoading && (
        <div style={{ padding: "0 1rem 0.5rem", color: "#888", fontSize: "0.875rem" }}>
          Istari is thinking...
        </div>
      )}
      <ChatInput onSend={sendMessage} disabled={!isConnected} />
    </div>
  );
}
