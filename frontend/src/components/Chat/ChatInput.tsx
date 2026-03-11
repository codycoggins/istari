import { useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  history?: string[]; // user messages, newest-first
}

export function ChatInput({ onSend, disabled, history = [] }: ChatInputProps) {
  const [input, setInput] = useState("");
  const [historyIndex, setHistoryIndex] = useState(-1); // -1 = current draft
  const [draft, setDraft] = useState(""); // saved input before history nav
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setInput("");
      setHistoryIndex(-1);
      setDraft("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    const el = inputRef.current;

    // Arrow Up — go back in history (most recent first)
    if (e.key === "ArrowUp" && history.length > 0) {
      e.preventDefault();
      const nextIndex = historyIndex + 1;
      if (nextIndex < history.length) {
        if (historyIndex === -1) setDraft(input);
        setHistoryIndex(nextIndex);
        setInput(history[nextIndex] ?? "");
      }
      return;
    }

    // Arrow Down — go forward / restore draft
    if (e.key === "ArrowDown" && historyIndex > -1) {
      e.preventDefault();
      const nextIndex = historyIndex - 1;
      setHistoryIndex(nextIndex);
      setInput(nextIndex === -1 ? draft : (history[nextIndex] ?? ""));
      return;
    }

    // Ctrl-A — move cursor to start of line
    if (e.ctrlKey && e.key === "a") {
      e.preventDefault();
      el?.setSelectionRange(0, 0);
      return;
    }

    // Ctrl-E — move cursor to end of line
    if (e.ctrlKey && e.key === "e") {
      e.preventDefault();
      el?.setSelectionRange(input.length, input.length);
      return;
    }

    // Ctrl-U — clear entire line
    if (e.ctrlKey && e.key === "u") {
      e.preventDefault();
      setInput("");
      setHistoryIndex(-1);
      return;
    }

    // Ctrl-K — kill from cursor to end of line
    if (e.ctrlKey && e.key === "k") {
      e.preventDefault();
      const pos = el?.selectionStart ?? input.length;
      setInput(input.slice(0, pos));
      return;
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
        onKeyDown={handleKeyDown}
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
