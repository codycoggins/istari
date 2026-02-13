import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TodoPanel } from "../../src/components/TodoPanel/TodoPanel";

const mockTodos = [
  {
    id: 1,
    title: "Buy groceries",
    status: "active" as const,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  {
    id: 2,
    title: "Review PR",
    status: "active" as const,
    priority: 1,
    createdAt: "2024-01-02T00:00:00Z",
    updatedAt: "2024-01-02T00:00:00Z",
  },
];

describe("TodoPanel", () => {
  it("renders loading state", () => {
    render(<TodoPanel todos={[]} isLoading={true} />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders empty state", () => {
    render(<TodoPanel todos={[]} isLoading={false} />);
    expect(screen.getByText("No TODOs yet")).toBeInTheDocument();
  });

  it("renders todos", () => {
    render(<TodoPanel todos={mockTodos} isLoading={false} />);
    expect(screen.getByText("Buy groceries")).toBeInTheDocument();
    expect(screen.getByText("Review PR")).toBeInTheDocument();
  });

  it("shows priority for todos that have one", () => {
    render(<TodoPanel todos={mockTodos} isLoading={false} />);
    expect(screen.getByText("Priority: 1")).toBeInTheDocument();
  });

  it("calls onAskPriorities when button clicked", () => {
    const onAsk = vi.fn();
    render(<TodoPanel todos={[]} isLoading={false} onAskPriorities={onAsk} />);
    fireEvent.click(screen.getByText("What should I work on?"));
    expect(onAsk).toHaveBeenCalledOnce();
  });

  it("renders settings when provided", () => {
    const settings = { focus_mode: "false", quiet_hours_start: "22", quiet_hours_end: "8" };
    render(<TodoPanel todos={[]} isLoading={false} settings={settings} />);
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Focus mode")).toBeInTheDocument();
    expect(screen.getByText("Quiet hours: 22:00 – 8:00")).toBeInTheDocument();
  });

  it("toggles focus mode", () => {
    const onToggle = vi.fn();
    const settings = { focus_mode: "false" };
    render(
      <TodoPanel
        todos={[]}
        isLoading={false}
        settings={settings}
        onToggleFocusMode={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onToggle).toHaveBeenCalledWith(true);
  });
});
