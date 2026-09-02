import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Api } from "../api/client";
import { FIXTURE_RUN_ID } from "../api/fixtures";
import { useRunStream } from "./useRunStream";

// Reduced motion makes the hook reveal every trace at once instead of on its
// replay interval, keeping these deterministic (no fake timers racing polls).
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

describe("useRunStream", () => {
  const originalFetch = globalThis.fetch;
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    mockReducedMotion();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("replays the fixture trace and then the decision", async () => {
    vi.stubEnv("VITE_USE_FIXTURES", "1");
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("no network in tests"));
    const api = new Api("");

    const { result } = renderHook(() => useRunStream(FIXTURE_RUN_ID, api));

    await waitFor(() => expect(result.current.done).toBe(true));
    expect(result.current.traces.map((t) => t.node)).toEqual([
      "orchestrator",
      "inventory",
      "carrier",
      "exception",
      "synthesis",
    ]);
    expect(result.current.decision?.label).toBe("HOLD");
    expect(result.current.error).toBeNull();
  });

  it("surfaces an honest error rather than substituting fixture data on a live failure", async () => {
    // Live mode (no VITE_USE_FIXTURES): a rejecting fetch must surface as an
    // error, never as a silently-substituted fixture trace or decision.
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("network down"));
    const api = new Api("");

    const { result } = renderHook(() => useRunStream(FIXTURE_RUN_ID, api));

    await waitFor(() => expect(result.current.error).toMatch(/couldn.t load this run.s trace/i));
    expect(result.current.traces).toEqual([]);
    expect(result.current.decision).toBeNull();
  });

  it("holds no traces when nothing is selected", () => {
    const api = new Api("");
    const { result } = renderHook(() => useRunStream(null, api));
    expect(result.current.traces).toEqual([]);
    expect(result.current.decision).toBeNull();
  });
});
