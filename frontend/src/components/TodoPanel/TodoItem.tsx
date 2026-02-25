import { useState } from "react";
import type { Todo } from "../../types/todo";

interface TodoItemProps {
  todo: Todo;
  onComplete: (id: number) => void;
  onReopen: (id: number) => void;
  onEdit: (todo: Todo) => void;
}

function getQuadrant(urgent?: boolean | null, important?: boolean | null) {
  if (urgent === true && important === true)
    return { label: "Do Now", color: "var(--q1)", bg: "var(--q1-bg)" };
  if (important === true)
    return { label: "Schedule", color: "var(--q2)", bg: "var(--q2-bg)" };
  if (urgent === true)
    return { label: "Delegate", color: "var(--q3)", bg: "var(--q3-bg)" };
  if (urgent === false && important === false)
    return { label: "Drop", color: "var(--q4)", bg: "var(--q4-bg)" };
  return null;
}

export function TodoItem({ todo, onComplete, onReopen, onEdit }: TodoItemProps) {
  const [pencilHovered, setPencilHovered] = useState(false);
  const isComplete = todo.status === "complete";
  const quadrant = getQuadrant(todo.urgent, todo.important);
  const showTags = !isComplete && (quadrant || todo.status === "in_progress" || todo.status === "blocked");

  return (
    <div
      style={{
        padding: "0.5rem 0.625rem",
        marginBottom: "0.3125rem",
        borderRadius: "6px",
        border: "1px solid var(--border-subtle)",
        background: isComplete ? "transparent" : "var(--bg-elevated)",
        display: "flex",
        alignItems: "flex-start",
        gap: "0.5rem",
        opacity: isComplete ? 0.4 : 1,
        transition: "opacity 0.15s",
      }}
    >
      <input
        type="checkbox"
        checked={isComplete}
        onChange={() => (isComplete ? onReopen(todo.id) : onComplete(todo.id))}
        style={{
          marginTop: "0.175rem",
          flexShrink: 0,
          cursor: "pointer",
          accentColor: "var(--accent)",
          width: "13px",
          height: "13px",
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: "0.8125rem",
            lineHeight: 1.4,
            textDecoration: isComplete ? "line-through" : "none",
            color: isComplete ? "var(--text-secondary)" : "var(--text-primary)",
          }}
        >
          {todo.title}
        </div>

        {showTags && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.3rem",
              flexWrap: "wrap",
              marginTop: "0.3rem",
            }}
          >
            {quadrant && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  background: quadrant.bg,
                  color: quadrant.color,
                  fontWeight: 600,
                  letterSpacing: "0.02em",
                  flexShrink: 0,
                }}
              >
                {quadrant.label}
              </span>
            )}
            {todo.status === "in_progress" && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  color: "var(--q2)",
                  background: "var(--q2-bg)",
                  fontWeight: 600,
                }}
              >
                In progress
              </span>
            )}
            {todo.status === "blocked" && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  color: "var(--q1)",
                  background: "var(--q1-bg)",
                  fontWeight: 600,
                }}
              >
                Blocked
              </span>
            )}
          </div>
        )}
      </div>

      {/* Pencil / edit button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onEdit(todo);
        }}
        onMouseEnter={() => setPencilHovered(true)}
        onMouseLeave={() => setPencilHovered(false)}
        aria-label="Edit task"
        style={{
          background: "none",
          border: "none",
          padding: "0.1rem",
          cursor: "pointer",
          flexShrink: 0,
          color: pencilHovered ? "var(--accent)" : "var(--text-muted)",
          transition: "color 0.15s",
          lineHeight: 1,
          marginTop: "0.05rem",
        }}
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </button>
    </div>
  );
}
