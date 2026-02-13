import { useCallback, useRef } from "react";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { TodoPanel } from "./components/TodoPanel/TodoPanel";
import { useSettings } from "./hooks/useSettings";
import { useTodos } from "./hooks/useTodos";

export default function App() {
  const { todos, isLoading, refresh } = useTodos();
  const { settings, update: updateSetting } = useSettings();
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
      <main className="chat-area">
        <ChatPanel onTodoCreated={handleTodoCreated} />
      </main>
      <aside className="todo-sidebar">
        <TodoPanel
          todos={todos}
          isLoading={isLoading}
          onAskPriorities={handleAskPriorities}
          settings={settings}
          onToggleFocusMode={handleToggleFocusMode}
        />
      </aside>
    </div>
  );
}
