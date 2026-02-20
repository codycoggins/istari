import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ChatPanel } from "../../src/components/Chat/ChatPanel";

/**
 * Tests for ChatPanel's onRegisterSend wiring.
 *
 * This class of bug: a parent creates a ref/callback to drive a child action,
 * but the child never calls onRegisterSend — so the ref stays null and the
 * action silently does nothing when triggered.
 *
 * Three things must all be true for the "What should I work on?" button to work:
 *   1. ChatPanel calls onRegisterSend with a function (not undefined, not a stub)
 *   2. That function delegates to the real sendMessage from useChat
 *   3. App passes onRegisterSend down to ChatPanel (tested in App.test.tsx)
 */

const mockSendMessage = vi.fn();

vi.mock("../../src/hooks/useChat", () => ({
  useChat: () => ({
    messages: [],
    isLoading: false,
    isConnected: true,
    sendMessage: mockSendMessage,
  }),
}));

describe("ChatPanel — onRegisterSend wiring", () => {
  beforeEach(() => {
    mockSendMessage.mockClear();
  });

  it("calls onRegisterSend with a function on mount", () => {
    const onRegisterSend = vi.fn();
    render(<ChatPanel onRegisterSend={onRegisterSend} />);

    expect(onRegisterSend).toHaveBeenCalledOnce();
    expect(typeof onRegisterSend.mock.calls[0][0]).toBe("function");
  });

  it("the registered function delegates to sendMessage", () => {
    let capturedSend: ((msg: string) => void) | undefined;
    render(<ChatPanel onRegisterSend={(fn) => { capturedSend = fn; }} />);

    capturedSend?.("What should I work on?");
    expect(mockSendMessage).toHaveBeenCalledWith("What should I work on?");
  });

  it("the registered function passes arbitrary messages through unchanged", () => {
    let capturedSend: ((msg: string) => void) | undefined;
    render(<ChatPanel onRegisterSend={(fn) => { capturedSend = fn; }} />);

    capturedSend?.("remind me to call the dentist");
    expect(mockSendMessage).toHaveBeenCalledWith("remind me to call the dentist");
  });

  it("does not throw when onRegisterSend is omitted", () => {
    expect(() => render(<ChatPanel />)).not.toThrow();
  });
});
