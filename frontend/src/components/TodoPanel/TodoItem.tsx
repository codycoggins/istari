import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Todo } from "../../types/todo";
import { getTodoContext } from "../../api/todos";

interface TodoItemProps {
  todo: Todo;
  onComplete: (id: number) => void;
  onReopen: (id: number) => void;
  onEdit: (todo: Todo) => void;
  onToggleToday?: (id: number) => void;
  projectName?: string;
  isNextAction?: boolean;
}

function getQuadrant(urgent?: boolean | null, important?: boolean | null) {
  if (urgent === true && important === true)
    return { label: "Do Now", color: "var(--q1)", bg: "var(--q1-bg)" };
  if (important === true)
    return { label: "Schedule", color: "var(--q2)", bg: "var(--q2-bg)" };
  if (urgent === true)
    return { label: "Contain", color: "var(--q3)", bg: "var(--q3-bg)" };
  if (urgent === false && important === false)
    return { label: "Drop", color: "var(--q4)", bg: "var(--q4-bg)" };
  return null;
}

function getDueDateInfo(dueDateStr?: string | null) {
  if (!dueDateStr) return null;
  const due = new Date(dueDateStr);
  const now = new Date();
  const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dueMidnight = new Date(due.getFullYear(), due.getMonth(), due.getDate());
  const diffMs = dueMidnight.getTime() - todayMidnight.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  const label = due.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  if (diffDays < 0) {
    return { text: `Overdue ${Math.abs(diffDays)}d`, color: "var(--q1)", bg: "var(--q1-bg)" };
  }
  if (diffDays === 0) {
    return { text: "Due today", color: "var(--q3)", bg: "var(--q3-bg)" };
  }
  if (diffDays <= 3) {
    return { text: `Due ${label}`, color: "var(--q3)", bg: "var(--q3-bg)" };
  }
  return { text: `Due ${label}`, color: "var(--text-muted)", bg: "var(--bg-surface)" };
}

export function TodoItem({ todo, onComplete, onReopen, onEdit, onToggleToday, projectName, isNextAction }: TodoItemProps) {
  const [pencilHovered, setPencilHovered] = useState(false);
  const [targetHovered, setTargetHovered] = useState(false);
  const [contextHovered, setContextHovered] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextText, setContextText] = useState<string | null>(null);
  const isComplete = todo.status === "complete";
  const todayStr = new Date().toISOString().slice(0, 10);
  const isToday = todo.today_date === todayStr;
  const quadrant = getQuadrant(todo.urgent, todo.important);
  const dueInfo = getDueDateInfo(todo.due_date);
  const showTags = !isComplete && (quadrant || todo.status === "in_progress" || todo.status === "blocked" || projectName || isNextAction || dueInfo || todo.recurrence_rule);

  async function handleContextClick(e: React.MouseEvent) {
    e.stopPropagation();
    if (contextOpen) {
      setContextOpen(false);
      return;
    }
    setContextOpen(true);
    if (contextText !== null) return; // already fetched
    setContextLoading(true);
    try {
      const result = await getTodoContext(todo.id);
      setContextText(result.context);
    } catch {
      setContextText("Failed to gather context. Please try again.");
    } finally {
      setContextLoading(false);
    }
  }

  return (
    <div
      style={{
        marginBottom: "0.3125rem",
        borderRadius: "6px",
        border: "1px solid var(--border-subtle)",
        background: isComplete ? "transparent" : "var(--bg-elevated)",
        opacity: isComplete ? 0.4 : 1,
        transition: "opacity 0.15s",
        overflow: "hidden",
      }}
    >
    <div
      style={{
        padding: "0.5rem 0.625rem",
        display: "flex",
        alignItems: "flex-start",
        gap: "0.5rem",
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
            {isNextAction && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  color: "var(--accent)",
                  background: "var(--accent-dim)",
                  fontWeight: 600,
                  border: "1px solid var(--border-accent)",
                }}
              >
                → next
              </span>
            )}
            {projectName && !isNextAction && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  color: "var(--text-muted)",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  maxWidth: "120px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  display: "inline-block",
                }}
                title={projectName}
              >
                {projectName}
              </span>
            )}
            {dueInfo && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  color: dueInfo.color,
                  background: dueInfo.bg,
                  fontWeight: 600,
                  flexShrink: 0,
                }}
              >
                {dueInfo.text}
              </span>
            )}
            {todo.recurrence_rule && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.3rem",
                  borderRadius: "3px",
                  color: "var(--text-muted)",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  flexShrink: 0,
                }}
                title={todo.recurrence_rule}
              >
                ↻
              </span>
            )}
          </div>
        )}
      </div>

      {/* Target / focus-today button */}
      {!isComplete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleToday?.(todo.id);
          }}
          onMouseEnter={() => setTargetHovered(true)}
          onMouseLeave={() => setTargetHovered(false)}
          aria-label={isToday ? "Remove from today" : "Focus today"}
          style={{
            background: "none",
            border: "none",
            padding: "0.1rem",
            cursor: "pointer",
            flexShrink: 0,
            color: isToday
              ? "var(--accent)"
              : targetHovered
                ? "var(--text-secondary)"
                : "var(--text-muted)",
            transition: "color 0.15s",
            lineHeight: 1,
            marginTop: "0.05rem",
          }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill={isToday ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="6" />
            <circle cx="12" cy="12" r="2" />
          </svg>
        </button>
      )}

      {/* Context button */}
      {!isComplete && (
        <button
          onClick={handleContextClick}
          onMouseEnter={() => setContextHovered(true)}
          onMouseLeave={() => setContextHovered(false)}
          aria-label="Get context for task"
          title="Gather context"
          style={{
            background: "none",
            border: "none",
            padding: "0.1rem",
            cursor: "pointer",
            flexShrink: 0,
            color: contextOpen
              ? "var(--accent)"
              : contextHovered
                ? "var(--text-secondary)"
                : "var(--text-muted)",
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
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
        </button>
      )}

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

    {/* Inline context panel */}
    {contextOpen && (
      <div
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "0.625rem 0.875rem 0.75rem",
          fontSize: "0.75rem",
          lineHeight: 1.6,
          color: "var(--text-secondary)",
        }}
      >
        {contextLoading ? (
          <div style={{ display: "flex", alignItems: "center", gap: "0.375rem", color: "var(--text-muted)" }}>
            <span style={{ color: "var(--accent)", animation: "sigil-pulse 1.4s ease-in-out infinite", display: "inline-block" }}>
              ✦
            </span>
            Gathering context...
          </div>
        ) : (
          <div className="markdown-body context-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {contextText ?? ""}
            </ReactMarkdown>
          </div>
        )}
      </div>
    )}
    </div>
  );
}
