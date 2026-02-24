import type { Todo } from "../../types/todo";

interface TodoItemProps {
  todo: Todo;
  onComplete: (id: number) => void;
  onReopen: (id: number) => void;
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

export function TodoItem({ todo, onComplete, onReopen }: TodoItemProps) {
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
    </div>
  );
}
