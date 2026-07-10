import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Api } from "../api/client";
import { FIXTURE_RUN_ID } from "../api/fixtures";
import { RunView } from "./RunView";

// Reduced-motion so useRunStream reveals every trace at once instead of on
// its replay interval, keeping this test deterministic (no fake timers /
// racing intervals against findBy's polling).
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

describe("RunView", () => {
  const originalFetch = globalThis.fetch;
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    // No network in tests: fetch always rejects, so the Api's fixture
    // fallback kicks in for every call (getTrace, getDecision, ...).
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("no network in tests"));
    mockReducedMotion();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
  });

  it("replays the fixture trace onto the rail and shows the decision", async () => {
    const api = new Api("");
    render(<RunView runId={FIXTURE_RUN_ID} api={api} />);

    for (const node of ["orchestrator", "inventory", "carrier", "exception", "synthesis"]) {
      const matches = await screen.findAllByText(new RegExp(node, "i"), undefined, { timeout: 5000 });
      expect(matches.length).toBeGreaterThan(0);
    }

    const stamp = await screen.findByRole("status", undefined, { timeout: 5000 });
    expect(stamp).toHaveTextContent(/HOLD/);
  });

  it("shows a prompt when no run is selected", () => {
    const api = new Api("");
    render(<RunView runId={null} api={api} />);
    expect(screen.getByText(/select a run/i)).toBeInTheDocument();
  });
});
