import { useEffect, useRef } from "react";
import type { Message } from "../../types/message";

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "1.25rem 1.25rem 0.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.875rem",
      }}
    >
      {messages.length === 0 && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.75rem",
            color: "var(--text-muted)",
            paddingTop: "4rem",
          }}
        >
          <img
            src="/istari-icon.png"
            alt=""
            style={{ width: "52px", height: "52px", borderRadius: "14px", opacity: 0.3 }}
          />
          <p style={{ fontSize: "0.875rem" }}>Ask me anything</p>
        </div>
      )}

      {messages.map((msg) => (
        <div
          key={msg.id}
          style={{
            display: "flex",
            flexDirection: msg.role === "user" ? "row-reverse" : "row",
            alignItems: "flex-end",
            gap: "0.5rem",
          }}
        >
          {/* Istari avatar sigil */}
          {msg.role === "assistant" && (
            <div
              style={{
                width: "24px",
                height: "24px",
                borderRadius: "6px",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-accent)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontSize: "0.625rem",
                color: "var(--accent)",
              }}
            >
              ✦
            </div>
          )}

          {/* Message bubble */}
          <div
            style={{
              maxWidth: "78%",
              padding: "0.625rem 0.875rem",
              borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "4px 14px 14px 14px",
              background: msg.role === "user" ? "var(--bg-elevated)" : "var(--bg-surface)",
              border: `1px solid ${msg.role === "user" ? "var(--border-default)" : "var(--border-subtle)"}`,
              borderLeft: msg.role === "assistant" ? "2px solid var(--border-accent)" : undefined,
              fontSize: "0.875rem",
              lineHeight: 1.6,
              color: "var(--text-primary)",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {msg.content}
          </div>
        </div>
      ))}

      <div ref={bottomRef} />
    </div>
  );
}
