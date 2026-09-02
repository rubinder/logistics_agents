import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Decision, TraceRecord } from "../api/types";
import { useRunLog } from "./useRunLog";

function trace(runId: string, node: string): TraceRecord {
  return {
    run_id: runId,
    node,
    input_json: "{}",
    output_json: JSON.stringify({ reasoning: `${node} reasoned` }),
    latency_ms: 100,
    tokens: 10,
    cost_usd: 0.001,
    model: "claude-haiku-4-5",
    created_at: "2026-09-02T00:00:00Z",
  };
}

const DECISION: Decision = {
  label: "HOLD",
  exceptions: [],
  recommended_actions: [],
  confidence: 0.9,
  reasoning: "held",
};

type Props = { traces: TraceRecord[]; decision: Decision | null };

function setup(initial: Props) {
  return renderHook(({ traces, decision }: Props) => useRunLog(traces, decision), {
    initialProps: initial,
  });
}

describe("useRunLog", () => {
  it("appends traces in the order the stream reveals them", () => {
    const a = trace("run-1", "orchestrator");
    const b = trace("run-1", "inventory");

    const { result, rerender } = setup({ traces: [a], decision: null });
    expect(result.current.map((e) => e.key)).toEqual(["run-1:orchestrator"]);

    // useRunStream reveals a growing prefix array, one record per interval.
    rerender({ traces: [a, b], decision: null });
    expect(result.current.map((e) => e.key)).toEqual(["run-1:orchestrator", "run-1:inventory"]);
  });

  it("keeps earlier runs when a new run starts streaming", () => {
    const first = trace("run-1", "orchestrator");
    const second = trace("run-2", "orchestrator");

    const { result, rerender } = setup({ traces: [first], decision: null });
    // Selecting another run resets useRunStream's array to that run's traces.
    rerender({ traces: [second], decision: null });

    expect(result.current.map((e) => e.runId)).toEqual(["run-1", "run-2"]);
  });

  it("does not re-append a run that is replayed a second time", () => {
    const a = trace("run-1", "orchestrator");
    const other = trace("run-2", "orchestrator");

    const { result, rerender } = setup({ traces: [a], decision: null });
    rerender({ traces: [other], decision: null });
    // Re-selecting run-1 replays it in the rail; the feed must not grow.
    rerender({ traces: [a], decision: null });

    expect(result.current.map((e) => e.key)).toEqual(["run-1:orchestrator", "run-2:orchestrator"]);
  });

  it("appends exactly one decision entry once the decision lands", () => {
    const a = trace("run-1", "synthesis");

    const { result, rerender } = setup({ traces: [a], decision: null });
    expect(result.current).toHaveLength(1);

    rerender({ traces: [a], decision: DECISION });
    rerender({ traces: [a], decision: DECISION });

    const decisions = result.current.filter((e) => e.kind === "decision");
    expect(decisions).toHaveLength(1);
    expect(decisions[0].runId).toBe("run-1");
    expect(decisions[0].decision).toEqual(DECISION);
  });

  it("starts empty", () => {
    const { result } = setup({ traces: [], decision: null });
    expect(result.current).toEqual([]);
  });
});
