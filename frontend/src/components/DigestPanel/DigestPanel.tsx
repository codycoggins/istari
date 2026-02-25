import { useState } from "react";
import type { Digest } from "../../types/digest";

interface DigestPanelProps {
  digests: Digest[];
  isLoading: boolean;
  onMarkReviewed: (id: number) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  gmail_digest: "Gmail",
  morning_digest: "Morning",
  todo_staleness: "Stale",
};

const SOURCE_COLORS: Record<string, { color: string; bg: string }> = {
  gmail_digest: { color: "var(--q1)", bg: "var(--q1-bg)" },
  morning_digest: { color: "var(--q2)", bg: "var(--q2-bg)" },
  todo_staleness: { color: "var(--q3)", bg: "var(--q3-bg)" },
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function DigestPanel({ digests, isLoading, onMarkReviewed }: DigestPanelProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (!isLoading && digests.length === 0) return null;

  return (
    <div
      style={{
        padding: "1rem 0.875rem 0.75rem",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <span
        style={{
          display: "block",
          fontSize: "1rem",
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
          marginBottom: "0.625rem",
        }}
      >
        Digests
      </span>

      {isLoading && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>Loading...</p>
      )}

      {digests.map((d) => {
        const sourceStyle = SOURCE_COLORS[d.source] ?? {
          color: "var(--q4)",
          bg: "var(--q4-bg)",
        };
        const isExpanded = expanded.has(d.id);

        return (
          <div
            key={d.id}
            style={{
              marginBottom: "0.375rem",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              overflow: "hidden",
              opacity: d.reviewed ? 0.45 : 1,
              transition: "opacity 0.15s",
            }}
          >
            <div
              style={{
                padding: "0.4rem 0.625rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                cursor: "pointer",
                background: "var(--bg-elevated)",
              }}
              onClick={() => toggle(d.id)}
            >
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  background: sourceStyle.bg,
                  color: sourceStyle.color,
                  fontWeight: 600,
                  flexShrink: 0,
                }}
              >
                {SOURCE_LABELS[d.source] ?? d.source}
              </span>
              <span
                style={{
                  flex: 1,
                  fontSize: "0.6875rem",
                  color: "var(--text-secondary)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {formatTime(d.created_at)}
              </span>
              <span style={{ fontSize: "0.5rem", color: "var(--text-muted)", flexShrink: 0 }}>
                {isExpanded ? "▲" : "▼"}
              </span>
            </div>

            {isExpanded && (
              <div
                style={{
                  padding: "0.625rem 0.75rem",
                  borderTop: "1px solid var(--border-subtle)",
                  background: "var(--bg-surface)",
                }}
              >
                <div
                  style={{
                    whiteSpace: "pre-wrap",
                    fontSize: "0.8125rem",
                    lineHeight: 1.6,
                    color: "var(--text-secondary)",
                    marginBottom: "0.5rem",
                  }}
                >
                  {d.content_summary}
                </div>
                {!d.reviewed ? (
                  <button
                    onClick={() => onMarkReviewed(d.id)}
                    style={{
                      background: "none",
                      border: "1px solid var(--border-default)",
                      borderRadius: "4px",
                      padding: "0.2rem 0.625rem",
                      cursor: "pointer",
                      fontSize: "0.6875rem",
                      color: "var(--text-secondary)",
                      fontFamily: "inherit",
                      transition: "all 0.15s",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "var(--border-accent)";
                      e.currentTarget.style.color = "var(--accent)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "var(--border-default)";
                      e.currentTarget.style.color = "var(--text-secondary)";
                    }}
                  >
                    Mark reviewed
                  </button>
                ) : (
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                    Reviewed
                  </span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
