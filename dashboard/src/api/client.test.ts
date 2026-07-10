import { afterEach, describe, expect, it, vi } from "vitest";

import { Api, TriggerError } from "./client";
import {
  FIXTURE_BUDGET,
  FIXTURE_DECISION,
  FIXTURE_EVAL_REPORTS,
  FIXTURE_TRACES,
  FIXTURE_TRIGGER_RESULT,
} from "./fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("Api", () => {
  it("returns parsed data on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ cap_usd: 5, spent_usd: 1, remaining_usd: 4 }), {
            status: 200,
          }),
      ),
    );
    const api = new Api("");
    const budget = await api.getBudget();
    expect(budget.remaining_usd).toBe(4);
    expect(api.usingFixtures).toBe(false);
  });

  it("falls back to fixtures when the API errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );
    const api = new Api("");
    const budget = await api.getBudget();
    expect(budget).toEqual(FIXTURE_BUDGET);
    expect(api.usingFixtures).toBe(true);
  });

  it("getDecision returns null on a 404 (no decision persisted yet)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("not found", { status: 404 })),
    );
    const api = new Api("");
    const decision = await api.getDecision("some-run-id");
    expect(decision).toBeNull();
    expect(api.usingFixtures).toBe(false);
  });

  it("getDecision throws on a non-404 error response in live mode (no fixture fallback)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );
    const api = new Api("");
    await expect(api.getDecision("some-run-id")).rejects.toThrow();
  });

  it("getDecision serves the fixture in explicit fixtures mode", async () => {
    vi.stubEnv("VITE_USE_FIXTURES", "1");
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const api = new Api("");
    const decision = await api.getDecision("some-run-id");
    expect(decision).toEqual(FIXTURE_DECISION);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(api.usingFixtures).toBe(true);
  });

  it("getTrace throws on a 500 in live mode (no fixture fallback)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );
    const api = new Api("");
    await expect(api.getTrace("some-run-id")).rejects.toThrow();
  });

  it("getTrace serves the fixture in explicit fixtures mode", async () => {
    vi.stubEnv("VITE_USE_FIXTURES", "1");
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const api = new Api("");
    const traces = await api.getTrace("some-run-id");
    expect(traces).toEqual(FIXTURE_TRACES);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(api.usingFixtures).toBe(true);
  });

  it("returns eval report fixtures (no live endpoint yet)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("should not be called");
      }),
    );
    const api = new Api("");
    const reports = await api.getEvalReports();
    expect(reports).toEqual(FIXTURE_EVAL_REPORTS);
    expect(api.usingFixtures).toBe(true);
  });

  it("triggerRun propagates a TriggerError with the API detail on a 402", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "budget exhausted" }), {
            status: 402,
          }),
      ),
    );
    const api = new Api("");
    await expect(api.triggerRun("quantity-mismatch")).rejects.toMatchObject({
      status: 402,
      message: "budget exhausted",
    });
    await expect(api.triggerRun("quantity-mismatch")).rejects.toBeInstanceOf(TriggerError);
  });

  it("triggerRun returns the fixture without calling fetch in explicit fixtures mode", async () => {
    vi.stubEnv("VITE_USE_FIXTURES", "1");
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const api = new Api("");
    const result = await api.triggerRun("quantity-mismatch");
    expect(result).toEqual(FIXTURE_TRIGGER_RESULT);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(api.usingFixtures).toBe(true);
  });
});
