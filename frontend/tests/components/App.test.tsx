import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "../../src/App";

describe("App", () => {
  it("renders the app layout", () => {
    render(<App />);
    expect(screen.getByText("Istari")).toBeInTheDocument();
    expect(screen.getByText("TODOs")).toBeInTheDocument();
  });
});
