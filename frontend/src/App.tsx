import { useCallback, useEffect, useRef, useState } from "react";
import { checkAuth } from "./api/auth";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { DigestPanel } from "./components/DigestPanel/DigestPanel";
import { LoginPage } from "./components/Login/LoginPage";
import { NotificationInbox } from "./components/NotificationInbox/NotificationInbox";
import { TodoPanel } from "./components/TodoPanel/TodoPanel";
import { useDigests } from "./hooks/useDigests";
import { useNotifications } from "./hooks/useNotifications";
import { useSettings } from "./hooks/useSettings";
import { useTodos } from "./hooks/useTodos";

export default function App() {
  // null = still checking, false = not authenticated, true = authenticated
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    checkAuth().then(setIsAuthenticated);
  }, []);

  const { todos, isLoading, refresh, completeTodo, reopenTodo, updateTodo } = useTodos();
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
  const chatSendRef = useRef<((msg: string) => void) | null>(null);

  const handleTodoCreated = useCallback(() => {
    refresh();
  }, [refresh]);

  const handleAskPriorities = useCallback(() => {
    chatSendRef.current?.("What should I work on?");
  }, []);

  const handleToggleFocusMode = useCallback(
    (enabled: boolean) => {
      updateSetting("focus_mode", String(enabled));
    },
    [updateSetting],
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

  return (
    <div className="app-layout">
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
      <div className="app-body">
        <main className="chat-area">
          <ChatPanel
            onTodoCreated={handleTodoCreated}
            onRegisterSend={(fn) => {
              chatSendRef.current = fn;
            }}
            onAuthFailure={() => setIsAuthenticated(false)}
          />
        </main>
        <aside className="todo-sidebar">
          <DigestPanel
            digests={digests}
            isLoading={digestsLoading}
            onMarkReviewed={markReviewed}
          />
          <TodoPanel
            todos={todos}
            isLoading={isLoading}
            onComplete={completeTodo}
            onReopen={reopenTodo}
            onSave={updateTodo}
            onAskPriorities={handleAskPriorities}
            settings={settings}
            onToggleFocusMode={handleToggleFocusMode}
          />
        </aside>
      </div>
    </div>
  );
}
