export type MobileTab = "chat" | "tasks" | "projects";

interface MobileTabBarProps {
  activeTab: MobileTab;
  onChange: (tab: MobileTab) => void;
  openTodoCount?: number;
}

function ChatIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke={active ? "var(--accent)" : "var(--text-muted)"}
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function TasksIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke={active ? "var(--accent)" : "var(--text-muted)"}
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    >
      <line x1="9" y1="6" x2="21" y2="6" />
      <line x1="9" y1="12" x2="21" y2="12" />
      <line x1="9" y1="18" x2="21" y2="18" />
      <polyline points="3 6 4 7 6 5" />
      <polyline points="3 12 4 13 6 11" />
      <polyline points="3 18 4 19 6 17" />
    </svg>
  );
}

function ProjectsIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke={active ? "var(--accent)" : "var(--text-muted)"}
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    >
      <rect x="2" y="3" width="8" height="8" rx="1.5" />
      <rect x="14" y="3" width="8" height="8" rx="1.5" />
      <rect x="2" y="13" width="8" height="8" rx="1.5" />
      <rect x="14" y="13" width="8" height="8" rx="1.5" />
    </svg>
  );
}

export function MobileTabBar({ activeTab, onChange, openTodoCount = 0 }: MobileTabBarProps) {
  const tabs: Array<{
    id: MobileTab;
    label: string;
    icon: (active: boolean) => React.ReactNode;
    badge?: number;
  }> = [
    { id: "chat", label: "Chat", icon: (a) => <ChatIcon active={a} /> },
    {
      id: "tasks",
      label: "Tasks",
      icon: (a) => <TasksIcon active={a} />,
      badge: openTodoCount > 0 ? openTodoCount : undefined,
    },
    { id: "projects", label: "Projects", icon: (a) => <ProjectsIcon active={a} /> },
  ];

  return (
    <nav className="mobile-tab-bar" role="tablist">
      {tabs.map(({ id, label, icon, badge }) => {
        const active = activeTab === id;
        return (
          <button
            key={id}
            role="tab"
            aria-selected={active}
            aria-label={label}
            onClick={() => onChange(id)}
            className={`mobile-tab-btn${active ? " active" : ""}`}
          >
            <span className="mobile-tab-icon-wrap">
              {icon(active)}
              {badge != null && (
                <span className="mobile-tab-badge">
                  {badge > 99 ? "99+" : badge}
                </span>
              )}
            </span>
            <span className="mobile-tab-label">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
