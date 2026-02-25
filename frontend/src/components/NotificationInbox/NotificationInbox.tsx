import { useState } from "react";
import type { Notification } from "../../types/notification";

interface NotificationInboxProps {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
  onMarkCompleted: (id: number) => void;
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}

export function NotificationInbox({
  notifications,
  unreadCount,
  isLoading,
  onMarkRead,
  onMarkAllRead,
  onMarkCompleted,
}: NotificationInboxProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      {/* Bell icon trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: isOpen ? "var(--bg-elevated)" : "none",
          border: `1px solid ${isOpen ? "var(--border-accent)" : "var(--border-subtle)"}`,
          borderRadius: "7px",
          padding: "0.375rem 0.5rem",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: "0.375rem",
          transition: "all 0.15s",
          position: "relative",
        }}
        onMouseEnter={(e) => {
          if (!isOpen) {
            e.currentTarget.style.borderColor = "var(--border-accent)";
            e.currentTarget.style.background = "var(--bg-elevated)";
          }
        }}
        onMouseLeave={(e) => {
          if (!isOpen) {
            e.currentTarget.style.borderColor = "var(--border-subtle)";
            e.currentTarget.style.background = "none";
          }
        }}
        aria-label="Notifications"
      >
        {/* Bell SVG */}
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke={unreadCount > 0 ? "var(--accent)" : "var(--text-secondary)"}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            style={{
              background: "var(--danger)",
              color: "#fff",
              borderRadius: "9999px",
              padding: "0 0.35rem",
              fontSize: "0.625rem",
              fontWeight: 700,
              lineHeight: "1.4",
              minWidth: "1rem",
              textAlign: "center",
            }}
          >
            {unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 0.5rem)",
            right: 0,
            width: "22rem",
            maxHeight: "24rem",
            overflowY: "auto",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "8px",
            boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            zIndex: 50,
          }}
        >
          {/* Panel header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.625rem 1rem",
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            <span
              style={{
                fontSize: "1rem",
                fontWeight: 700,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--text-muted)",
              }}
            >
              Notifications
            </span>
            {unreadCount > 0 && (
              <button
                onClick={onMarkAllRead}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--accent)",
                  cursor: "pointer",
                  fontSize: "0.6875rem",
                  fontFamily: "inherit",
                  opacity: 0.8,
                }}
              >
                Mark all read
              </button>
            )}
          </div>

          {isLoading && (
            <p
              style={{
                padding: "1rem",
                color: "var(--text-muted)",
                fontSize: "0.8125rem",
                margin: 0,
              }}
            >
              Loading...
            </p>
          )}

          {!isLoading && notifications.length === 0 && (
            <p
              style={{
                padding: "1rem",
                color: "var(--text-muted)",
                fontSize: "0.8125rem",
                margin: 0,
              }}
            >
              No notifications yet
            </p>
          )}

          {notifications.map((n) => (
            <div
              key={n.id}
              style={{
                padding: "0.625rem 1rem",
                borderBottom: "1px solid var(--border-subtle)",
                background: n.read ? "transparent" : "var(--bg-elevated)",
                display: "flex",
                alignItems: "flex-start",
                gap: "0.5rem",
                opacity: n.completed ? 0.45 : 1,
                transition: "opacity 0.15s",
              }}
            >
              <input
                type="checkbox"
                checked={n.completed}
                disabled={n.completed}
                onChange={() => onMarkCompleted(n.id)}
                style={{
                  marginTop: "0.2rem",
                  flexShrink: 0,
                  cursor: n.completed ? "default" : "pointer",
                  accentColor: "var(--accent)",
                }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p
                  style={{
                    fontSize: "0.8125rem",
                    margin: "0 0 0.2rem",
                    lineHeight: 1.4,
                    color: "var(--text-primary)",
                    textDecoration: n.completed ? "line-through" : "none",
                  }}
                >
                  {n.content}
                </p>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                  {formatTime(n.created_at)}
                </span>
              </div>
              {!n.read && (
                <button
                  onClick={() => onMarkRead(n.id)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--accent)",
                    cursor: "pointer",
                    fontSize: "0.6875rem",
                    fontFamily: "inherit",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                    opacity: 0.8,
                  }}
                >
                  Read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
