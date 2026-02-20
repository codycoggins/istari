import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../../src/App";

/**
 * App-level integration tests for action wiring.
 *
 * This class of bug: a button in a child component triggers a callback that
 * travels through prop-drilling to reach a sibling component's function — but
 * one link in the chain is missing, so the action silently does nothing.
 *
 * The "What should I work on?" button is the canonical example:
 *   TodoPanel.button → onAskPriorities (App) → chatSendRef.current() → ChatPanel.sendMessage
 *
 * If App never passes onRegisterSend to ChatPanel, chatSendRef stays null and
 * the button click reaches onAskPriorities but goes nowhere.
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

describe("App", () => {
  beforeEach(() => {
    mockSendMessage.mockClear();
  });

  it("renders the app layout", () => {
    render(<App />);
    expect(screen.getByText("Istari")).toBeInTheDocument();
    expect(screen.getByText("TODOs")).toBeInTheDocument();
  });

  it("'What should I work on?' button sends the message to chat", () => {
    render(<App />);
    fireEvent.click(screen.getByText("What should I work on?"));
    expect(mockSendMessage).toHaveBeenCalledWith("What should I work on?");
  });

  it("'What should I work on?' sends exactly the expected string", () => {
    render(<App />);
    fireEvent.click(screen.getByText("What should I work on?"));
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
    expect(mockSendMessage).toHaveBeenCalledWith("What should I work on?");
  });
});
