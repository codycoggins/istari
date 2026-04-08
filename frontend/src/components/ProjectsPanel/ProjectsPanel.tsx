import { useState, useEffect } from "react";
import type { Project } from "../../types/project";
import type { Todo } from "../../types/todo";
import type { ProjectUpdatePayload } from "../../api/projects";

const PROJECTS_COLLAPSED_KEY = "istari-projects-collapsed";

// ── Detail / edit panel ───────────────────────────────────
function ProjectDetailPanel({
  project,
  onClose,
  onSave,
  isNarrow,
}: {
  project: Project;
  onClose: () => void;
  onSave: (id: number, updates: ProjectUpdatePayload) => Promise<void>;
  isNarrow?: boolean;
}) {
  const [form, setForm] = useState({
    name: project.name,
    description: project.description ?? "",
    goal: project.goal ?? "",
    status: project.status,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const set =
    (field: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setIsSaving(true);
    setError(null);
    const payload: ProjectUpdatePayload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      goal: form.goal.trim() || null,
      status: form.status,
    };
    try {
      await onSave(project.id, payload);
      onClose();
    } catch {
      setError("Save failed — please try again.");
      setIsSaving(false);
    }
  };

  const fieldStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: "0.375rem",
  };
  const labelStyle: React.CSSProperties = {
    fontSize: "0.6875rem",
    fontWeight: 600,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: "var(--text-muted)",
  };
  const inputStyle: React.CSSProperties = {
    background: "var(--bg-elevated)",
    border: "1px solid var(--border-default)",
    borderRadius: "6px",
    padding: "0.5rem 0.75rem",
    color: "var(--text-primary)",
    fontSize: "0.875rem",
    fontFamily: "inherit",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };
  const textareaStyle: React.CSSProperties = {
    ...inputStyle,
    resize: "vertical",
    minHeight: "5rem",
  };

  const header = (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.625rem",
        padding: "1rem 1.25rem",
        borderBottom: "1px solid var(--border-subtle)",
        flexShrink: 0,
      }}
    >
      <span style={{ color: "var(--accent)", fontSize: "0.875rem" }}>✦</span>
      <span
        style={{
          flex: 1,
          fontSize: "0.75rem",
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
        }}
      >
        Edit Project
      </span>
      <button
        onClick={onClose}
        aria-label="Close"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--text-muted)",
          fontSize: "1rem",
          lineHeight: 1,
          padding: "0.1rem 0.25rem",
        }}
      >
        ✕
      </button>
    </div>
  );

  const formBody = (
    <div
      style={{
        padding: "1.125rem 1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <div style={fieldStyle}>
        <label style={labelStyle}>Name</label>
        <input
          type="text"
          value={form.name}
          onChange={set("name")}
          style={inputStyle}
          autoFocus
        />
      </div>
      <div style={fieldStyle}>
        <label style={labelStyle}>Goal</label>
        <textarea
          value={form.goal}
          onChange={set("goal")}
          style={textareaStyle}
          placeholder="What does success look like?"
        />
      </div>
      <div style={fieldStyle}>
        <label style={labelStyle}>Description</label>
        <textarea
          value={form.description}
          onChange={set("description")}
          style={textareaStyle}
          placeholder="Additional context or notes…"
        />
      </div>
      <div style={fieldStyle}>
        <label style={labelStyle}>Status</label>
        <select value={form.status} onChange={set("status")} style={inputStyle}>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="complete">Complete</option>
        </select>
      </div>
      {error && (
        <p style={{ color: "var(--q1)", fontSize: "0.8125rem", margin: 0 }}>{error}</p>
      )}
    </div>
  );

  const footer = (
    <div
      className="bottom-sheet-footer"
      style={{
        padding: "0.875rem 1.25rem",
        borderTop: "1px solid var(--border-subtle)",
        display: "flex",
        justifyContent: "flex-end",
        gap: "0.625rem",
        flexShrink: 0,
      }}
    >
      <button
        onClick={onClose}
        style={{
          padding: "0.5rem 1rem",
          borderRadius: "6px",
          border: "1px solid var(--border-default)",
          background: "transparent",
          color: "var(--text-secondary)",
          fontSize: "0.875rem",
          fontFamily: "inherit",
          cursor: "pointer",
        }}
      >
        Cancel
      </button>
      <button
        onClick={handleSave}
        disabled={isSaving || !form.name.trim()}
        style={{
          padding: "0.5rem 1.25rem",
          borderRadius: "6px",
          border: `1px solid ${isSaving ? "var(--border-subtle)" : "var(--border-accent)"}`,
          background: isSaving ? "transparent" : "var(--accent-dim)",
          color: isSaving ? "var(--text-muted)" : "var(--accent)",
          fontSize: "0.875rem",
          fontWeight: 600,
          fontFamily: "inherit",
          cursor: isSaving ? "not-allowed" : "pointer",
          transition: "all 0.15s",
        }}
      >
        {isSaving ? "Saving…" : "Save"}
      </button>
    </div>
  );

  if (isNarrow) {
    return (
      <div className="bottom-sheet-overlay" onClick={onClose}>
        <div className="bottom-sheet" onClick={(e) => e.stopPropagation()}>
          <div className="bottom-sheet-handle" />
          {header}
          <div className="bottom-sheet-body">{formBody}</div>
          {footer}
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "480px",
          maxHeight: "88vh",
          overflowY: "auto",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "10px",
          boxShadow: "0 16px 48px rgba(0,0,0,0.5)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {header}
        {formBody}
        {footer}
      </div>
    </div>
  );
}

const STATUS_CYCLE: Array<Project["status"]> = ["active", "paused", "complete"];

const STATUS_STYLE: Record<Project["status"], { color: string; bg: string; label: string }> = {
  active: { color: "var(--q2)", bg: "var(--q2-bg)", label: "Active" },
  paused: { color: "var(--text-muted)", bg: "var(--bg-elevated)", label: "Paused" },
  complete: { color: "var(--q4)", bg: "var(--q4-bg)", label: "Done" },
};

interface ProjectsPanelProps {
  projects: Project[];
  todos: Todo[];
  isLoading: boolean;
  error?: string | null;
  isNarrow?: boolean;
  selectedProjectId: number | null;
  onSelectProject: (id: number | null) => void;
  onRefresh?: () => void;
  onUpdateProject?: (id: number, updates: ProjectUpdatePayload) => Promise<void>;
}

function ProjectCard({
  project,
  todos,
  isSelected,
  onSelect,
  onUpdateStatus,
  onEdit,
}: {
  project: Project;
  todos: Todo[];
  isSelected: boolean;
  onSelect: () => void;
  onUpdateStatus: (status: Project["status"]) => void;
  onEdit: (project: Project) => void;
}) {
  const [statusHovered, setStatusHovered] = useState(false);
  const [pencilHovered, setPencilHovered] = useState(false);
  const projectTodos = todos.filter((t) => t.project_id === project.id);
  const activeTodos = projectTodos.filter(
    (t) => t.status !== "complete" && t.status !== "deferred",
  );
  const nextAction = project.next_action_id
    ? todos.find((t) => t.id === project.next_action_id)
    : null;
  const statusStyle = STATUS_STYLE[project.status];

  function cycleStatus(e: React.MouseEvent) {
    e.stopPropagation();
    const idx = STATUS_CYCLE.indexOf(project.status);
    onUpdateStatus(STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length] as Project["status"]);
  }

  const hasTagsRow = !!(project.goal || activeTodos.length > 0 || nextAction);

  return (
    <div
      onClick={onSelect}
      style={{
        marginBottom: "0.375rem",
        borderRadius: "6px",
        border: `1px solid ${isSelected ? "var(--border-accent)" : "var(--border-subtle)"}`,
        background: isSelected ? "var(--accent-dim)" : "var(--bg-elevated)",
        cursor: "pointer",
        transition: "border-color 0.15s, background 0.15s",
        overflow: "hidden",
      }}
    >
      {/* Outer row: content column + edit button */}
      <div
        style={{
          padding: "0.5rem 0.625rem",
          display: "flex",
          alignItems: "flex-start",
          gap: "0.5rem",
        }}
      >
        {/* Content column */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Name */}
          <span
            style={{
              display: "block",
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: isSelected ? "var(--accent)" : "var(--text-primary)",
              lineHeight: 1.3,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              marginBottom: hasTagsRow ? "0.3rem" : 0,
            }}
          >
            {project.name}
          </span>

          {/* Tags row: status + count + goal + next-action */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "0.3rem",
            }}
          >
            {/* Status badge (clickable to cycle) */}
            <button
              onClick={cycleStatus}
              onMouseEnter={() => setStatusHovered(true)}
              onMouseLeave={() => setStatusHovered(false)}
              title="Click to change status"
              style={{
                background: statusHovered ? "var(--bg-surface)" : statusStyle.bg,
                color: statusStyle.color,
                border: "none",
                borderRadius: "3px",
                padding: "0.1rem 0.4rem",
                fontSize: "0.625rem",
                fontWeight: 600,
                letterSpacing: "0.02em",
                cursor: "pointer",
                flexShrink: 0,
                transition: "background 0.15s",
                fontFamily: "inherit",
              }}
            >
              {statusStyle.label}
            </button>

            {/* Todo count badge */}
            {activeTodos.length > 0 && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  background: "var(--bg-surface)",
                  color: "var(--text-muted)",
                  flexShrink: 0,
                }}
              >
                {activeTodos.length}
              </span>
            )}

            {/* Goal badge */}
            {project.goal && (
              <span
                style={{
                  fontSize: "0.625rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "3px",
                  background: "var(--bg-surface)",
                  color: "var(--text-muted)",
                  border: "1px solid var(--border-subtle)",
                  maxWidth: "10rem",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flexShrink: 1,
                  minWidth: 0,
                }}
                title={project.goal}
              >
                {project.goal}
              </span>
            )}

            {/* Next-action badge */}
            {nextAction && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.2rem",
                  border: "1px solid var(--border-accent)",
                  color: "var(--accent)",
                  background: "var(--accent-dim)",
                  borderRadius: "3px",
                  padding: "0.1rem 0.4rem",
                  fontSize: "0.625rem",
                  fontWeight: 600,
                  maxWidth: "12rem",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flexShrink: 1,
                  minWidth: 0,
                }}
              >
                → {nextAction.title}
              </span>
            )}
          </div>
        </div>

        {/* Edit button — far right */}
        <button
          onClick={(e) => { e.stopPropagation(); onEdit(project); }}
          onMouseEnter={() => setPencilHovered(true)}
          onMouseLeave={() => setPencilHovered(false)}
          aria-label="Edit project"
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
    </div>
  );
}

export function ProjectsPanel({
  projects,
  todos,
  isLoading,
  error,
  isNarrow,
  selectedProjectId,
  onSelectProject,
  onRefresh,
  onUpdateProject,
}: ProjectsPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(
    () => localStorage.getItem(PROJECTS_COLLAPSED_KEY) === "true",
  );
  const [editProject, setEditProject] = useState<Project | null>(null);

  function toggleCollapsed() {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(PROJECTS_COLLAPSED_KEY, String(next));
      return next;
    });
  }

  return (
    <div
      style={{
        padding: "0.875rem 0.875rem 0.75rem",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: isCollapsed ? 0 : "0.625rem",
        }}
      >
        <button
          onClick={toggleCollapsed}
          aria-label={isCollapsed ? "Expand projects" : "Collapse projects"}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.3rem",
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            fontSize: "1rem",
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--text-muted)",
            fontFamily: "inherit",
          }}
        >
          <span
            style={{
              fontSize: "0.75rem",
              transition: "transform 0.2s",
              transform: isCollapsed ? "rotate(-90deg)" : "rotate(0deg)",
              display: "inline-block",
            }}
          >
            ▾
          </span>
          Projects
        </button>
        {!isCollapsed && (
          <button
            onClick={onRefresh}
            aria-label="Refresh projects"
            disabled={isLoading}
            title="Refresh"
            style={{
              background: "none",
              border: "1px solid var(--border-default)",
              borderRadius: "5px",
              padding: "0.25rem 0.5rem",
              cursor: isLoading ? "not-allowed" : "pointer",
              fontSize: "0.75rem",
              color: isLoading ? "var(--text-muted)" : "var(--text-secondary)",
              fontFamily: "inherit",
              lineHeight: 1,
              transition: "all 0.15s",
            }}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.borderColor = "var(--border-accent)";
                e.currentTarget.style.color = "var(--accent)";
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border-default)";
              e.currentTarget.style.color = isLoading ? "var(--text-muted)" : "var(--text-secondary)";
            }}
          >
            ↻
          </button>
        )}
      </div>

      {/* Project cards */}
      {!isCollapsed && (
        error ? (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", margin: 0 }}>
            <span style={{ fontSize: "0.8125rem", color: "var(--q1)" }}>{error}</span>
            <button
              onClick={onRefresh}
              style={{
                background: "none",
                border: "1px solid var(--border-default)",
                borderRadius: "4px",
                padding: "0.2rem 0.5rem",
                fontSize: "0.75rem",
                color: "var(--text-secondary)",
                fontFamily: "inherit",
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          </div>
        ) : isLoading ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", margin: 0 }}>Loading...</p>
        ) : projects.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", margin: 0 }}>No projects yet.</p>
        ) : (
          <>
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                todos={todos}
                isSelected={selectedProjectId === project.id}
                onSelect={() =>
                  onSelectProject(selectedProjectId === project.id ? null : project.id)
                }
                onUpdateStatus={(status) => onUpdateProject?.(project.id, { status })}
                onEdit={setEditProject}
              />
            ))}
          </>
        )
      )}

      {editProject && (
        <ProjectDetailPanel
          project={editProject}
          onClose={() => setEditProject(null)}
          onSave={async (id, updates) => {
            await onUpdateProject?.(id, updates);
            setEditProject(null);
          }}
          isNarrow={isNarrow}
        />
      )}
    </div>
  );
}
