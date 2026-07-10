import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the product name", async () => {
    render(<App />);
    // Let the mount-time budget/scenarios/runs load (fixture-fallback, since
    // there is no network in tests) settle inside act before asserting.
    await act(async () => {});
    expect(screen.getByRole("heading", { name: /logistics agents/i })).toBeInTheDocument();
  });
});
