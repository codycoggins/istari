import { useState } from "react";
import type { Digest } from "../../types/digest";

interface DigestPanelProps {
  digests: Digest[];
  isLoading: boolean;
  onMarkReviewed: (id: number) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  gmail_digest: "Gmail",
  morning_digest: "Morning Digest",
  todo_staleness: "Stale TODOs",
};

const SOURCE_COLORS: Record<string, string> = {
  gmail_digest: "#d53f8c",
  morning_digest: "#2b6cb0",
  todo_staleness: "#c05621",
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

  return (
    <div style={{ padding: "1rem" }}>
      <h2 style={{ fontSize: "1rem", marginBottom: "1rem" }}>Digests</h2>
      {isLoading && <p style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</p>}
      {!isLoading && digests.length === 0 && (
        <p style={{ color: "#888", fontSize: "0.875rem" }}>No digests yet</p>
      )}
      {digests.map((d) => (
        <div
          key={d.id}
          style={{
            marginBottom: "0.75rem",
            border: "1px solid #e0e0e0",
            borderRadius: "4px",
            overflow: "hidden",
            opacity: d.reviewed ? 0.6 : 1,
          }}
        >
          <div
            style={{
              padding: "0.5rem 0.75rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              cursor: "pointer",
              background: "#fafafa",
            }}
            onClick={() => toggle(d.id)}
          >
            <span
              style={{
                fontSize: "0.7rem",
                padding: "0.1rem 0.4rem",
                borderRadius: "3px",
                background: SOURCE_COLORS[d.source] ?? "#718096",
                color: "white",
                fontWeight: 600,
              }}
            >
              {SOURCE_LABELS[d.source] ?? d.source}
            </span>
            <span style={{ flex: 1, fontSize: "0.8rem", color: "#555" }}>
              {formatTime(d.created_at)}
            </span>
            <span style={{ fontSize: "0.75rem", color: "#999" }}>
              {expanded.has(d.id) ? "▲" : "▼"}
            </span>
          </div>
          {expanded.has(d.id) && (
            <div style={{ padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}>
              <div style={{ whiteSpace: "pre-wrap", marginBottom: "0.5rem" }}>
                {d.content_summary}
              </div>
              {!d.reviewed && (
                <button
                  onClick={() => onMarkReviewed(d.id)}
                  style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem" }}
                >
                  Mark reviewed
                </button>
              )}
              {d.reviewed && (
                <span style={{ fontSize: "0.75rem", color: "#888" }}>Reviewed</span>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
