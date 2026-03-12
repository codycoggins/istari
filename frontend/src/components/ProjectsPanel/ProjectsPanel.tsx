import { useState } from "react";
import type { Project } from "../../types/project";
import type { Todo } from "../../types/todo";
import type { ProjectUpdatePayload } from "../../api/projects";

const PROJECTS_COLLAPSED_KEY = "istari-projects-collapsed";

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
}: {
  project: Project;
  todos: Todo[];
  isSelected: boolean;
  onSelect: () => void;
  onUpdateStatus: (status: Project["status"]) => void;
}) {
  const [statusHovered, setStatusHovered] = useState(false);
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
      <div style={{ padding: "0.5rem 0.625rem" }}>
        {/* Project name row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.375rem",
            marginBottom: nextAction || project.goal ? "0.3rem" : 0,
          }}
        >
          <span
            style={{
              flex: 1,
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: isSelected ? "var(--accent)" : "var(--text-primary)",
              lineHeight: 1.3,
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {project.name}
          </span>

          {/* Todo count badge */}
          {activeTodos.length > 0 && (
            <span
              style={{
                fontSize: "0.5625rem",
                padding: "0.1rem 0.35rem",
                borderRadius: "3px",
                background: "var(--bg-surface)",
                color: "var(--text-muted)",
                border: "1px solid var(--border-subtle)",
                flexShrink: 0,
              }}
            >
              {activeTodos.length}
            </span>
          )}

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
              padding: "0.1rem 0.35rem",
              fontSize: "0.5625rem",
              fontWeight: 600,
              letterSpacing: "0.02em",
              cursor: "pointer",
              flexShrink: 0,
              transition: "background 0.15s",
            }}
          >
            {statusStyle.label}
          </button>
        </div>

        {/* Goal subtitle */}
        {project.goal && (
          <div
            style={{
              fontSize: "0.6875rem",
              color: "var(--text-muted)",
              lineHeight: 1.4,
              marginBottom: nextAction ? "0.3rem" : 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {project.goal}
          </div>
        )}

        {/* Next action */}
        {nextAction && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.3rem",
            }}
          >
            <span
              style={{
                fontSize: "0.5625rem",
                fontWeight: 700,
                color: "var(--accent)",
                flexShrink: 0,
              }}
            >
              →
            </span>
            <span
              style={{
                fontSize: "0.6875rem",
                color: "var(--text-secondary)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {nextAction.title}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function ProjectsPanel({
  projects,
  todos,
  isLoading,
  selectedProjectId,
  onSelectProject,
  onRefresh,
  onUpdateProject,
}: ProjectsPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(
    () => localStorage.getItem(PROJECTS_COLLAPSED_KEY) === "true",
  );

  if (!isLoading && projects.length === 0) return null;

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
        isLoading ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", margin: 0 }}>Loading...</p>
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
              />
            ))}
          </>
        )
      )}
    </div>
  );
}
