import { useCallback, useEffect, useRef, useState } from "react";

const SIDEBAR_WIDTH_KEY = "istari-sidebar-width";
const SIDEBAR_MIN = 200;
const SIDEBAR_MAX = 600;
const SIDEBAR_DEFAULT = 300;
import { checkAuth } from "./api/auth";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { DigestPanel } from "./components/DigestPanel/DigestPanel";
import { LoginPage } from "./components/Login/LoginPage";
import { MobileTabBar, type MobileTab } from "./components/MobileTabBar/MobileTabBar";
import { NotificationInbox } from "./components/NotificationInbox/NotificationInbox";
import { ProjectsPanel } from "./components/ProjectsPanel/ProjectsPanel";
import { TodoPanel } from "./components/TodoPanel/TodoPanel";
import { useDigests } from "./hooks/useDigests";
import { useNotifications } from "./hooks/useNotifications";
import { useProjects } from "./hooks/useProjects";
import { useSettings } from "./hooks/useSettings";
import { useTodos } from "./hooks/useTodos";

export default function App() {
  // null = still checking, false = not authenticated, true = authenticated
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    checkAuth().then(setIsAuthenticated);
  }, []);

  const { todos, isLoading, error: todosError, refresh, completeTodo, reopenTodo, updateTodo, toggleTodayFocus } = useTodos();
  const {
    notifications,
    unreadCount,
    isLoading: notificationsLoading,
    markRead,
    markAllAsRead,
    markCompleted,
  } = useNotifications();
  const { settings, update: updateSetting } = useSettings();
  const { digests, isLoading: digestsLoading, markReviewed } = useDigests();
  const { projects, isLoading: projectsLoading, error: projectsError, refresh: refreshProjects, updateProject } = useProjects();
  const [projectFilter, setProjectFilter] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<MobileTab>("chat");
  const chatSendRef = useRef<((msg: string) => void) | null>(null);

  const openTodoCount = todos.filter(
    (t) => t.status === "open" || t.status === "in_progress" || t.status === "blocked",
  ).length;

  // ── Narrow-screen detection (disables drag resize below 768px) ──
  const [isNarrow, setIsNarrow] = useState<boolean>(
    () => window.matchMedia("(max-width: 768px)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = (e: MediaQueryListEvent) => setIsNarrow(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // ── Resizable sidebar ──────────────────────────────────
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    const stored = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    return stored ? Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, parseInt(stored, 10))) : SIDEBAR_DEFAULT;
  });
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = sidebarWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [sidebarWidth]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = dragStartX.current - e.clientX; // dragging left = wider
      const next = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, dragStartWidth.current + delta));
      setSidebarWidth(next);
    };
    const onMouseUp = () => {
      if (!isDragging.current) return;
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      setSidebarWidth((w) => {
        localStorage.setItem(SIDEBAR_WIDTH_KEY, String(w));
        return w;
      });
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  const handleTodoCreated = useCallback(() => {
    refresh();
  }, [refresh]);

  const handleAskPriorities = useCallback(() => {
    chatSendRef.current?.("What should I work on?");
  }, []);

  const handleRegisterSend = useCallback((fn: (msg: string) => void) => {
    chatSendRef.current = fn;
  }, []);

  const handleToggleFocusMode = useCallback(
    (enabled: boolean) => {
      updateSetting("focus_mode", String(enabled));
    },
    [updateSetting],
  );

  // On mobile, selecting a project also switches to the tasks tab
  const handleSelectProject = useCallback(
    (id: number | null) => {
      setProjectFilter(id);
      if (isNarrow && id !== null) setActiveTab("tasks");
    },
    [isNarrow],
  );

  if (isAuthenticated === null) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          background: "var(--bg-base)",
          color: "var(--text-muted)",
          fontFamily: "'Cinzel', serif",
          letterSpacing: "0.12em",
        }}
      >
        ✦
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage onSuccess={() => setIsAuthenticated(true)} />;
  }

  const appHeader = (
    <header
      className="app-header"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.5rem 1.25rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
        <img
          src="/istari-icon.png"
          alt="Istari"
          style={{ width: "28px", height: "28px", borderRadius: "7px" }}
        />
        <span
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "1.125rem",
            fontWeight: 500,
            letterSpacing: "0.14em",
            color: "var(--accent)",
          }}
        >
          ISTARI
        </span>
      </div>
      <NotificationInbox
        notifications={notifications}
        unreadCount={unreadCount}
        isLoading={notificationsLoading}
        onMarkRead={markRead}
        onMarkAllRead={markAllAsRead}
        onMarkCompleted={markCompleted}
      />
    </header>
  );

  const tasksTabContent = (
    <>
      <DigestPanel
        digests={digests}
        isLoading={digestsLoading}
        onMarkReviewed={markReviewed}
      />
      <TodoPanel
        todos={todos}
        isLoading={isLoading}
        error={todosError}
        isNarrow={isNarrow}
        onComplete={completeTodo}
        onReopen={reopenTodo}
        onSave={updateTodo}
        onToggleToday={toggleTodayFocus}
        onAskPriorities={handleAskPriorities}
        onRefresh={refresh}
        settings={settings}
        onToggleFocusMode={handleToggleFocusMode}
        projects={projects}
        projectFilter={projectFilter}
        onSelectProject={handleSelectProject}
      />
    </>
  );

  const projectsTabContent = (
    <ProjectsPanel
      projects={projects}
      todos={todos}
      isLoading={projectsLoading}
      error={projectsError}
      isNarrow={isNarrow}
      selectedProjectId={projectFilter}
      onSelectProject={handleSelectProject}
      onRefresh={refreshProjects}
      onUpdateProject={updateProject}
    />
  );

  const sidebarContent = (
    <>
      <DigestPanel
        digests={digests}
        isLoading={digestsLoading}
        onMarkReviewed={markReviewed}
      />
      <ProjectsPanel
        projects={projects}
        todos={todos}
        isLoading={projectsLoading}
        error={projectsError}
        isNarrow={isNarrow}
        selectedProjectId={projectFilter}
        onSelectProject={setProjectFilter}
        onRefresh={refreshProjects}
        onUpdateProject={updateProject}
      />
      <TodoPanel
        todos={todos}
        isLoading={isLoading}
        error={todosError}
        isNarrow={isNarrow}
        onComplete={completeTodo}
        onReopen={reopenTodo}
        onSave={updateTodo}
        onToggleToday={toggleTodayFocus}
        onAskPriorities={handleAskPriorities}
        onRefresh={refresh}
        settings={settings}
        onToggleFocusMode={handleToggleFocusMode}
        projects={projects}
        projectFilter={projectFilter}
        onSelectProject={setProjectFilter}
      />
    </>
  );

  const chatContent = (
    <ChatPanel
      onTodoCreated={handleTodoCreated}
      onRegisterSend={handleRegisterSend}
      onAuthFailure={() => setIsAuthenticated(false)}
    />
  );

  if (isNarrow) {
    return (
      <div className="app-layout">
        {appHeader}
        <div className="mobile-tab-content">
          {activeTab === "chat" && chatContent}
          {activeTab === "tasks" && tasksTabContent}
          {activeTab === "projects" && projectsTabContent}
        </div>
        <MobileTabBar
          activeTab={activeTab}
          onChange={setActiveTab}
          openTodoCount={openTodoCount}
        />
      </div>
    );
  }

  return (
    <div className="app-layout">
      {appHeader}
      <div className="app-body">
        <main className="chat-area">
          {chatContent}
        </main>
        <aside className="todo-sidebar" style={{ width: sidebarWidth }}>
          {/* Drag handle */}
          <div
            onMouseDown={handleResizeMouseDown}
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              bottom: 0,
              width: "5px",
              cursor: "col-resize",
              zIndex: 10,
            }}
            className="sidebar-resize-handle"
          />
          {sidebarContent}
        </aside>
      </div>
    </div>
  );
}
