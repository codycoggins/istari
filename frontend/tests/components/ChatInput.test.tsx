import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ChatInput } from "../../src/components/Chat/ChatInput";

describe("ChatInput — keyboard shortcuts", () => {
  const onSend = vi.fn();

  beforeEach(() => {
    onSend.mockClear();
  });

  // --- history navigation ---

  it("ArrowUp loads the most recent history entry", () => {
    // history is newest-first: index 0 = most recent ("third")
    render(<ChatInput onSend={onSend} history={["third", "second", "first"]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect((input as HTMLInputElement).value).toBe("third");
  });

  it("ArrowUp twice loads the second-most-recent entry", () => {
    render(<ChatInput onSend={onSend} history={["third", "second", "first"]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect((input as HTMLInputElement).value).toBe("second");
  });

  it("ArrowUp does not go past the oldest entry", () => {
    render(<ChatInput onSend={onSend} history={["only"]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    fireEvent.keyDown(input, { key: "ArrowUp" }); // already at limit
    expect((input as HTMLInputElement).value).toBe("only");
  });

  it("ArrowDown after ArrowUp restores the draft", () => {
    render(<ChatInput onSend={onSend} history={["older"]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");

    // type a draft
    fireEvent.change(input, { target: { value: "my draft" } });
    // navigate back
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect((input as HTMLInputElement).value).toBe("older");
    // navigate forward — should restore draft
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect((input as HTMLInputElement).value).toBe("my draft");
  });

  it("ArrowDown at index -1 does nothing", () => {
    render(<ChatInput onSend={onSend} history={["older"]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.change(input, { target: { value: "typed" } });
    fireEvent.keyDown(input, { key: "ArrowDown" }); // already at draft position
    expect((input as HTMLInputElement).value).toBe("typed");
  });

  it("ArrowUp does nothing when history is empty", () => {
    render(<ChatInput onSend={onSend} history={[]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.change(input, { target: { value: "hello" } });
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect((input as HTMLInputElement).value).toBe("hello");
  });

  // --- Ctrl-U: clear line ---

  it("Ctrl-U clears the input", () => {
    render(<ChatInput onSend={onSend} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.change(input, { target: { value: "some text" } });
    fireEvent.keyDown(input, { key: "u", ctrlKey: true });
    expect((input as HTMLInputElement).value).toBe("");
  });

  it("Ctrl-U resets history index", () => {
    render(<ChatInput onSend={onSend} history={["prev"]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect((input as HTMLInputElement).value).toBe("prev");
    fireEvent.keyDown(input, { key: "u", ctrlKey: true });
    expect((input as HTMLInputElement).value).toBe("");
    // ArrowDown should now do nothing (index reset to -1)
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect((input as HTMLInputElement).value).toBe("");
  });

  // --- submit resets history ---

  it("submitting a message resets history navigation", () => {
    render(<ChatInput onSend={onSend} history={["prev"]} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect((input as HTMLInputElement).value).toBe("prev");

    // submit via form
    fireEvent.change(input, { target: { value: "new message" } });
    fireEvent.submit(input.closest("form")!);
    expect(onSend).toHaveBeenCalledWith("new message");
    expect((input as HTMLInputElement).value).toBe("");

    // ArrowDown should now do nothing (index was reset)
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect((input as HTMLInputElement).value).toBe("");
  });

  // --- Ctrl-A and Ctrl-E: cursor movement ---
  // These call setSelectionRange on the input ref. We verify they don't throw
  // and don't alter the input text.

  it("Ctrl-A does not change input text", () => {
    render(<ChatInput onSend={onSend} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.change(input, { target: { value: "hello world" } });
    fireEvent.keyDown(input, { key: "a", ctrlKey: true });
    expect((input as HTMLInputElement).value).toBe("hello world");
  });

  it("Ctrl-E does not change input text", () => {
    render(<ChatInput onSend={onSend} />);
    const input = screen.getByPlaceholderText("Ask Istari…");
    fireEvent.change(input, { target: { value: "hello world" } });
    fireEvent.keyDown(input, { key: "e", ctrlKey: true });
    expect((input as HTMLInputElement).value).toBe("hello world");
  });

  // --- Ctrl-K: kill to end of line ---

  it("Ctrl-K removes text from cursor to end", () => {
    render(<ChatInput onSend={onSend} />);
    const input = screen.getByPlaceholderText("Ask Istari…") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "hello world" } });
    // jsdom sets selectionStart to end after change; set it to position 5
    input.setSelectionRange(5, 5);
    fireEvent.keyDown(input, { key: "k", ctrlKey: true });
    expect(input.value).toBe("hello");
  });

  it("Ctrl-K at start of line clears entire input", () => {
    render(<ChatInput onSend={onSend} />);
    const input = screen.getByPlaceholderText("Ask Istari…") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "clear me" } });
    input.setSelectionRange(0, 0);
    fireEvent.keyDown(input, { key: "k", ctrlKey: true });
    expect(input.value).toBe("");
  });
});
