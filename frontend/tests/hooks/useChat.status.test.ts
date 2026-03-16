/**
 * Tests for the status message handling in useChat.
 *
 * Uses a manual WebSocket mock to simulate server-sent messages and
 * verifies that:
 *   - type=status messages update currentStatus without adding to messages[]
 *   - type=response messages clear currentStatus and add to messages[]
 *   - messages with no type field (old backend) behave like type=response
 *   - sendMessage clears currentStatus immediately
 */

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useChat } from "../../src/hooks/useChat";

// ── WebSocket mock ────────────────────────────────────────────────────────────

class MockWebSocket {
  static OPEN = 1;
  readyState = MockWebSocket.OPEN;
  onopen: ((e: Event) => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;

  send = vi.fn();
  close = vi.fn();

  /** Simulate the server sending a JSON payload. */
  simulateMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }

  /** Simulate connection open. */
  simulateOpen() {
    this.onopen?.({} as Event);
  }
}

let mockWs: MockWebSocket;

beforeEach(() => {
  mockWs = new MockWebSocket();
  const WsMock = vi.fn(() => mockWs) as unknown as typeof WebSocket;
  (WsMock as unknown as { OPEN: number }).OPEN = 1;
  vi.stubGlobal("WebSocket", WsMock);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderUseChat() {
  const { result } = renderHook(() => useChat());
  // Trigger onopen so isConnected=true
  act(() => mockWs.simulateOpen());
  return result;
}

function sendServerMessage(data: object) {
  act(() => mockWs.simulateMessage(data));
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useChat — status message handling", () => {
  it("type=status updates currentStatus and does NOT add to messages", () => {
    const result = renderUseChat();

    sendServerMessage({ type: "status", content: "Checking Gmail for unread messages..." });

    expect(result.current.currentStatus).toBe("Checking Gmail for unread messages...");
    expect(result.current.messages).toHaveLength(0);
    expect(result.current.isLoading).toBe(false); // status doesn't clear loading
  });

  it("type=response clears currentStatus and adds a chat message", () => {
    const result = renderUseChat();

    // First set a status
    sendServerMessage({ type: "status", content: "Thinking..." });
    expect(result.current.currentStatus).toBe("Thinking...");

    // Then send the final response
    sendServerMessage({
      type: "response",
      id: "msg-1",
      role: "assistant",
      content: "Here are your emails.",
      created_at: new Date().toISOString(),
      todo_created: false,
      todo_updated: false,
      memory_created: false,
    });

    expect(result.current.currentStatus).toBe("");
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("Here are your emails.");
    expect(result.current.isLoading).toBe(false);
  });

  it("message with no type field (old backend) is treated as a response", () => {
    const result = renderUseChat();

    sendServerMessage({
      id: "msg-2",
      role: "assistant",
      content: "Legacy response.",
      created_at: new Date().toISOString(),
      todo_created: false,
      todo_updated: false,
      memory_created: false,
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("Legacy response.");
    expect(result.current.currentStatus).toBe("");
    expect(result.current.isLoading).toBe(false);
  });

  it("sendMessage clears currentStatus", () => {
    const result = renderUseChat();

    // Simulate a status from a previous exchange still being shown
    sendServerMessage({ type: "status", content: "Old status..." });
    expect(result.current.currentStatus).toBe("Old status...");

    act(() => {
      result.current.sendMessage("new message");
    });

    expect(result.current.currentStatus).toBe("");
    expect(result.current.isLoading).toBe(true);
  });

  it("multiple status messages update currentStatus to the latest", () => {
    const result = renderUseChat();

    sendServerMessage({ type: "status", content: "Thinking..." });
    sendServerMessage({ type: "status", content: "Checking Gmail for unread messages..." });
    sendServerMessage({ type: "status", content: "Searching memory for 'dentist'..." });

    expect(result.current.currentStatus).toBe("Searching memory for 'dentist'...");
    expect(result.current.messages).toHaveLength(0);
  });
});

describe("useChat — history message handling", () => {
  it("type=history populates messages when state is empty (new tab / page refresh)", () => {
    const result = renderUseChat();

    sendServerMessage({
      type: "history",
      messages: [
        { id: "1", role: "user", content: "Hello", created_at: "2026-03-15T08:00:00Z" },
        { id: "2", role: "assistant", content: "Hi!", created_at: "2026-03-15T08:00:01Z" },
      ],
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].id).toBe("1");
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("Hello");
    expect(result.current.messages[0].createdAt).toBe("2026-03-15T08:00:00Z");
    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].content).toBe("Hi!");
  });

  it("type=history does NOT replace messages on same-session reconnect", () => {
    const result = renderUseChat();

    // Simulate a prior response already in state
    sendServerMessage({
      type: "response",
      id: "live-1",
      role: "assistant",
      content: "Already here.",
      created_at: "2026-03-15T07:59:00Z",
      todo_created: false,
      todo_updated: false,
      memory_created: false,
    });
    expect(result.current.messages).toHaveLength(1);

    // Reconnect delivers history — should be ignored
    sendServerMessage({
      type: "history",
      messages: [
        { id: "old-1", role: "user", content: "Old message", created_at: "2026-03-15T07:58:00Z" },
      ],
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].id).toBe("live-1");
  });

  it("type=history with empty messages array leaves state empty", () => {
    const result = renderUseChat();

    sendServerMessage({ type: "history", messages: [] });

    expect(result.current.messages).toHaveLength(0);
  });

  it("type=history does not affect isLoading or currentStatus", () => {
    const result = renderUseChat();

    sendServerMessage({
      type: "history",
      messages: [
        { id: "1", role: "user", content: "Hello", created_at: "2026-03-15T08:00:00Z" },
      ],
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.currentStatus).toBe("");
  });
});
