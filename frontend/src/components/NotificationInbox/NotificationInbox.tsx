import { useState } from "react";
import type { Notification } from "../../types/notification";

interface NotificationInboxProps {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
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
}: NotificationInboxProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: "none",
          border: "1px solid #e0e0e0",
          borderRadius: "0.375rem",
          padding: "0.375rem 0.75rem",
          cursor: "pointer",
          fontSize: "0.875rem",
          display: "flex",
          alignItems: "center",
          gap: "0.375rem",
        }}
      >
        Notifications
        {unreadCount > 0 && (
          <span
            style={{
              background: "#e53e3e",
              color: "#fff",
              borderRadius: "9999px",
              padding: "0.125rem 0.5rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              minWidth: "1.25rem",
              textAlign: "center",
            }}
          >
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 0.5rem)",
            right: 0,
            width: "22rem",
            maxHeight: "24rem",
            overflowY: "auto",
            background: "#fff",
            border: "1px solid #e0e0e0",
            borderRadius: "0.5rem",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            zIndex: 50,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.75rem 1rem",
              borderBottom: "1px solid #e0e0e0",
            }}
          >
            <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={onMarkAllRead}
                style={{
                  background: "none",
                  border: "none",
                  color: "#3182ce",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                }}
              >
                Mark all read
              </button>
            )}
          </div>

          {isLoading && (
            <p style={{ padding: "1rem", color: "#888", fontSize: "0.875rem" }}>
              Loading...
            </p>
          )}

          {!isLoading && notifications.length === 0 && (
            <p style={{ padding: "1rem", color: "#888", fontSize: "0.875rem" }}>
              No notifications yet
            </p>
          )}

          {notifications.map((n) => (
            <div
              key={n.id}
              style={{
                padding: "0.625rem 1rem",
                borderBottom: "1px solid #f0f0f0",
                background: n.read ? "transparent" : "#f7fafc",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "0.5rem",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: "0.8125rem", margin: 0, lineHeight: 1.4 }}>
                  {n.content}
                </p>
                <span style={{ fontSize: "0.6875rem", color: "#999" }}>
                  {formatTime(n.created_at)}
                </span>
              </div>
              {!n.read && (
                <button
                  onClick={() => onMarkRead(n.id)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#3182ce",
                    cursor: "pointer",
                    fontSize: "0.6875rem",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}
                >
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
