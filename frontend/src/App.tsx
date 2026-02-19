import { useCallback, useRef } from "react";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { DigestPanel } from "./components/DigestPanel/DigestPanel";
import { NotificationInbox } from "./components/NotificationInbox/NotificationInbox";
import { TodoPanel } from "./components/TodoPanel/TodoPanel";
import { useDigests } from "./hooks/useDigests";
import { useNotifications } from "./hooks/useNotifications";
import { useSettings } from "./hooks/useSettings";
import { useTodos } from "./hooks/useTodos";

export default function App() {
  const { todos, isLoading, refresh, completeTodo } = useTodos();
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

  return (
    <div className="app-layout">
      <header
        className="app-header"
        style={{
          display: "flex",
          justifyContent: "flex-end",
          padding: "0.5rem 1rem",
          borderBottom: "1px solid #e0e0e0",
        }}
      >
        <NotificationInbox
          notifications={notifications}
          unreadCount={unreadCount}
          isLoading={notificationsLoading}
          onMarkRead={markRead}
          onMarkAllRead={markAllAsRead}
          onMarkCompleted={markCompleted}
        />
      </header>
      <main className="chat-area">
        <ChatPanel onTodoCreated={handleTodoCreated} />
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
          onAskPriorities={handleAskPriorities}
          settings={settings}
          onToggleFocusMode={handleToggleFocusMode}
        />
      </aside>
    </div>
  );
}
