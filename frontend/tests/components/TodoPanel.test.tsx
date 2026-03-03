import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TodoPanel } from "../../src/components/TodoPanel/TodoPanel";

const todayStr = new Date().toISOString().slice(0, 10);

const mockTodos = [
  {
    id: 1,
    title: "Buy groceries",
    status: "open" as const,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: 2,
    title: "Review PR",
    status: "open" as const,
    priority: 1,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
  },
];

describe("TodoPanel", () => {
  it("renders loading state", () => {
    render(<TodoPanel todos={[]} isLoading={true} />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders empty state", () => {
    render(<TodoPanel todos={[]} isLoading={false} />);
    expect(screen.getByText("No tasks yet")).toBeInTheDocument();
  });

  it("renders todos", () => {
    render(<TodoPanel todos={mockTodos} isLoading={false} />);
    expect(screen.getByText("Buy groceries")).toBeInTheDocument();
    expect(screen.getByText("Review PR")).toBeInTheDocument();
  });

  it("calls onAskPriorities when button clicked", () => {
    const onAsk = vi.fn();
    render(<TodoPanel todos={[]} isLoading={false} onAskPriorities={onAsk} />);
    fireEvent.click(screen.getByText("Prioritize"));
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

  it("renders Today's Goals section when tasks are focused for today", () => {
    const todayTodo = {
      id: 3,
      title: "Write report",
      status: "open" as const,
      today_date: todayStr,
      created_at: "2024-01-03T00:00:00Z",
      updated_at: "2024-01-03T00:00:00Z",
    };
    render(<TodoPanel todos={[todayTodo, ...mockTodos]} isLoading={false} />);
    expect(screen.getByText("Today's Goals")).toBeInTheDocument();
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
  });

  it("does not render Today's Goals section when no tasks are focused", () => {
    render(<TodoPanel todos={mockTodos} isLoading={false} />);
    expect(screen.queryByText("Today's Goals")).not.toBeInTheDocument();
  });

  it("calls onToggleToday when target icon is clicked", () => {
    const onToggleToday = vi.fn();
    const todayTodo = {
      id: 3,
      title: "Write report",
      status: "open" as const,
      today_date: todayStr,
      created_at: "2024-01-03T00:00:00Z",
      updated_at: "2024-01-03T00:00:00Z",
    };
    render(
      <TodoPanel
        todos={[todayTodo]}
        isLoading={false}
        onToggleToday={onToggleToday}
      />,
    );
    fireEvent.click(screen.getByLabelText("Remove from today"));
    expect(onToggleToday).toHaveBeenCalledWith(3);
  });
});
