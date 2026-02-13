import { useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setInput("");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: "flex",
        padding: "1rem",
        borderTop: "1px solid #e0e0e0",
        gap: "0.5rem",
      }}
    >
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Message Istari..."
        disabled={disabled}
        style={{
          flex: 1,
          padding: "0.5rem",
          borderRadius: "4px",
          border: "1px solid #ccc",
          opacity: disabled ? 0.5 : 1,
        }}
      />
      <button type="submit" disabled={disabled} style={{ padding: "0.5rem 1rem" }}>
        Send
      </button>
    </form>
  );
}
