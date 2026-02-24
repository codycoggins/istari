import { useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setInput("");
    }
  };

  const canSend = !disabled && input.trim().length > 0;

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: "flex",
        alignItems: "center",
        padding: "0.75rem 1rem",
        gap: "0.625rem",
        borderTop: "1px solid var(--border-subtle)",
        background: "var(--bg-surface)",
        flexShrink: 0,
      }}
    >
      <input
        ref={inputRef}
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask Istari…"
        disabled={disabled}
        style={{
          flex: 1,
          padding: "0.5625rem 0.875rem",
          borderRadius: "8px",
          border: "1px solid var(--border-default)",
          background: "var(--bg-input)",
          color: "var(--text-primary)",
          fontSize: "0.875rem",
          fontFamily: "inherit",
          outline: "none",
          opacity: disabled ? 0.5 : 1,
          transition: "border-color 0.15s",
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = "var(--border-accent)";
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = "var(--border-default)";
        }}
      />
      <button
        type="submit"
        disabled={!canSend}
        style={{
          padding: "0.5625rem 1rem",
          borderRadius: "8px",
          border: `1px solid ${canSend ? "var(--border-accent)" : "var(--border-subtle)"}`,
          background: canSend ? "var(--accent-dim)" : "transparent",
          color: canSend ? "var(--accent)" : "var(--text-muted)",
          fontSize: "0.875rem",
          fontWeight: 500,
          fontFamily: "inherit",
          cursor: canSend ? "pointer" : "not-allowed",
          transition: "all 0.15s",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        Send
      </button>
    </form>
  );
}
