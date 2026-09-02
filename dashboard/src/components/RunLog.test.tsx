import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { LogEntry } from "../hooks/useRunLog";
import { RunLog } from "./RunLog";

function traceEntry(runId: string, node: string, output: unknown): LogEntry {
  return {
    key: `${runId}:${node}`,
    runId,
    kind: "trace",
    trace: {
      run_id: runId,
      node,
      input_json: "{}",
      output_json: typeof output === "string" ? output : JSON.stringify(output),
      latency_ms: 120,
      tokens: 1445,
      cost_usd: 0.0123,
      model: "claude-opus-4-8",
      created_at: "2026-09-02T00:00:00Z",
    },
  };
}

describe("RunLog", () => {
  it("renders a node's reasoning as prose", () => {
    render(
      <RunLog
        entries={[
          traceEntry("run-1", "inventory", {
            reasoning: "SKU-B has only 20 units of available capacity but the shipment brings 50.",
            capacity_ok: false,
          }),
        ]}
      />,
    );
    expect(screen.getByText(/only 20 units of available capacity/)).toBeInTheDocument();
  });

  it("shows non-reasoning fields as compact key lines", () => {
    render(
      <RunLog entries={[traceEntry("run-1", "inventory", { reasoning: "r", capacity_ok: false })]} />,
    );
    expect(screen.getByText(/capacity_ok/)).toBeInTheDocument();
  });

  it("falls back to raw output when output_json is not valid JSON", () => {
    render(<RunLog entries={[traceEntry("run-1", "inventory", "not json at all")]} />);
    expect(screen.getByText(/not json at all/)).toBeInTheDocument();
  });

  it("heads each run block with its run id", () => {
    render(
      <RunLog
        entries={[
          traceEntry("run-1", "orchestrator", { reasoning: "a" }),
          traceEntry("run-2", "orchestrator", { reasoning: "b" }),
        ]}
      />,
    );
    expect(screen.getByText("run-1")).toBeInTheDocument();
    expect(screen.getByText("run-2")).toBeInTheDocument();
  });

  it("heads a run only once for consecutive entries from that run", () => {
    render(
      <RunLog
        entries={[
          traceEntry("run-1", "orchestrator", { reasoning: "a" }),
          traceEntry("run-1", "inventory", { reasoning: "b" }),
        ]}
      />,
    );
    expect(screen.getAllByText("run-1")).toHaveLength(1);
  });

  it("renders a decision entry with its label and reasoning", () => {
    render(
      <RunLog
        entries={[
          {
            key: "run-1:__decision__",
            runId: "run-1",
            kind: "decision",
            decision: {
              label: "REROUTE",
              exceptions: [{ type: "OVERCAPACITY", detail: "DC-WEST over by 30" }],
              recommended_actions: ["Redirect to an alternate DC"],
              confidence: 0.92,
              reasoning: "Destination lacks capacity, so reroute.",
            },
          },
        ]}
      />,
    );
    expect(screen.getByText("REROUTE")).toBeInTheDocument();
    expect(screen.getByText(/Destination lacks capacity/)).toBeInTheDocument();
    expect(screen.getByText(/Redirect to an alternate DC/)).toBeInTheDocument();
  });

  it("does not print the final node's reasoning twice when the decision restates it", () => {
    // The synthesis node's output IS the decision, so the formatted decision
    // block that follows would otherwise repeat the same paragraph verbatim.
    const reasoning = "Quantity is short by twenty units, so hold.";
    render(
      <RunLog
        entries={[
          traceEntry("run-1", "synthesis", { reasoning, label: "HOLD" }),
          {
            key: "run-1:__decision__",
            runId: "run-1",
            kind: "decision",
            decision: {
              label: "HOLD",
              exceptions: [],
              recommended_actions: [],
              confidence: 0.9,
              reasoning,
            },
          },
        ]}
      />,
    );
    expect(screen.getAllByText(reasoning)).toHaveLength(1);
    // The node header still marks that the call happened.
    expect(screen.getByText("[synthesis]")).toBeInTheDocument();
  });

  it("keeps a node's reasoning when the decision says something different", () => {
    render(
      <RunLog
        entries={[
          traceEntry("run-1", "synthesis", { reasoning: "Node said this." }),
          {
            key: "run-1:__decision__",
            runId: "run-1",
            kind: "decision",
            decision: {
              label: "HOLD",
              exceptions: [],
              recommended_actions: [],
              confidence: 0.9,
              reasoning: "Decision said something else.",
            },
          },
        ]}
      />,
    );
    expect(screen.getByText("Node said this.")).toBeInTheDocument();
    expect(screen.getByText("Decision said something else.")).toBeInTheDocument();
  });

  it("renders an empty state when nothing has streamed yet", () => {
    render(<RunLog entries={[]} />);
    expect(screen.getByText(/nothing has streamed yet/i)).toBeInTheDocument();
  });
});
