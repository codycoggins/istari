import type { Message } from "../../types/message";

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
      {messages.length === 0 && (
        <p style={{ color: "#888", textAlign: "center", marginTop: "2rem" }}>
          Start a conversation with Istari
        </p>
      )}
      {messages.map((msg) => (
        <div key={msg.id} style={{ marginBottom: "0.75rem" }}>
          <strong>{msg.role === "user" ? "You" : "Istari"}: </strong>
          <span>{msg.content}</span>
        </div>
      ))}
    </div>
  );
}
