import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";

export function ChatPanel() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header style={{ padding: "1rem", borderBottom: "1px solid #e0e0e0" }}>
        <h1 style={{ fontSize: "1.25rem" }}>Istari</h1>
      </header>
      <MessageList messages={[]} />
      <ChatInput onSend={() => {}} />
    </div>
  );
}
