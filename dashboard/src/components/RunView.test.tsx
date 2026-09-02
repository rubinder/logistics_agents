import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FIXTURE_DECISION, FIXTURE_RUN_ID, FIXTURE_TRACES } from "../api/fixtures";
import { RunView } from "./RunView";

// RunView is presentational: `App` owns the stream (so the Log tab can share
// it) and passes the replay down. The streaming behavior these props come
// from is covered in ../hooks/useRunStream.test.ts.
describe("RunView", () => {
  it("renders every revealed trace and the decision stamp", () => {
    render(
      <RunView
        runId={FIXTURE_RUN_ID}
        traces={FIXTURE_TRACES}
        decision={FIXTURE_DECISION}
        error={null}
      />,
    );

    for (const node of ["orchestrator", "inventory", "carrier", "exception", "synthesis"]) {
      expect(screen.getAllByText(new RegExp(node, "i")).length).toBeGreaterThan(0);
    }

    expect(screen.getByRole("status")).toHaveTextContent(/HOLD/);
  });

  it("shows a prompt when no run is selected", () => {
    render(<RunView runId={null} traces={[]} decision={null} error={null} />);
    expect(screen.getByText(/select a run/i)).toBeInTheDocument();
  });

  it("shows the error state instead of any trace content", () => {
    render(
      <RunView
        runId={FIXTURE_RUN_ID}
        traces={[]}
        decision={null}
        error="Couldn't load this run's trace."
      />,
    );

    expect(screen.getByText(/couldn.t load this run.s trace/i)).toBeInTheDocument();
    expect(screen.queryByText(/orchestrator/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("waits for the first trace rather than rendering an empty table", () => {
    render(<RunView runId={FIXTURE_RUN_ID} traces={[]} decision={null} error={null} />);
    expect(screen.getByText(/waiting for the first trace/i)).toBeInTheDocument();
  });
});
