import { ChatPanel } from "./components/Chat/ChatPanel";
import { TodoPanel } from "./components/TodoPanel/TodoPanel";

export default function App() {
  return (
    <div className="app-layout">
      <main className="chat-area">
        <ChatPanel />
      </main>
      <aside className="todo-sidebar">
        <TodoPanel />
      </aside>
    </div>
  );
}
