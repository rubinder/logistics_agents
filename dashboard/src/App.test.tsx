import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

// Reduced motion reveals the whole replay at once, so the log fills without
// racing useRunStream's interval.
function mockReducedMotion() {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: true,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

describe("App", () => {
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    mockReducedMotion();
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("renders the product name", async () => {
    render(<App />);
    // Let the mount-time budget/scenarios/runs load (fixture-fallback, since
    // there is no network in tests) settle inside act before asserting.
    await act(async () => {});
    expect(screen.getByRole("heading", { name: /logistics agents/i })).toBeInTheDocument();
  });

  it("opens on the Trace tab", async () => {
    render(<App />);
    await act(async () => {});
    expect(screen.getByRole("tab", { name: /trace/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /log/i })).toHaveAttribute("aria-selected", "false");
  });

  it("keeps the accumulated log when switching tabs away and back", async () => {
    // getTrace deliberately does not fall back to fixtures on error (a live
    // failure must surface honestly), so ask for fixtures explicitly.
    vi.stubEnv("VITE_USE_FIXTURES", "1");
    const user = userEvent.setup();
    render(<App />);
    await act(async () => {});

    const logTab = screen.getByRole("tab", { name: /log/i });
    // The feed fills from the shared stream while the Trace tab is on screen.
    await waitFor(() => expect(logTab).toHaveTextContent(/\d/));

    await user.click(logTab);
    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveTextContent(/orchestrator/i);
    const filledCount = logTab.textContent;

    await user.click(screen.getByRole("tab", { name: /trace/i }));
    await user.click(screen.getByRole("tab", { name: /log/i }));

    // Same entries, not a re-accumulated or emptied feed.
    expect(screen.getByRole("tab", { name: /log/i }).textContent).toBe(filledCount);
    expect(screen.getByRole("tabpanel")).toHaveTextContent(/orchestrator/i);
  });
});
