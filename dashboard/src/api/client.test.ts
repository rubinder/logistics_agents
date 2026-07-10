import { afterEach, describe, expect, it, vi } from "vitest";

import { Api } from "./client";
import { FIXTURE_BUDGET, FIXTURE_DECISION, FIXTURE_EVAL_REPORTS } from "./fixtures";

afterEach(() => vi.unstubAllGlobals());

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

  it("falls back to fixtures on a non-OK response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("not found", { status: 404 })),
    );
    const api = new Api("");
    const decision = await api.getDecision("some-run-id");
    expect(decision).toEqual(FIXTURE_DECISION);
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
});
