import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FIXTURE_DECISION, FIXTURE_TRACES } from "../api/fixtures";
import { RunRail } from "./RunRail";

describe("RunRail", () => {
  it("renders a station per node and the decision stamp", () => {
    render(<RunRail traces={FIXTURE_TRACES} decision={FIXTURE_DECISION} />);
    for (const node of ["orchestrator", "inventory", "carrier", "exception", "synthesis"]) {
      expect(screen.getByText(new RegExp(node, "i"))).toBeInTheDocument();
    }
    expect(screen.getByText(/HOLD/)).toBeInTheDocument();
  });

  it("shows pending stations and no stamp when the run is only partially traced", () => {
    render(<RunRail traces={FIXTURE_TRACES.slice(0, 2)} decision={null} />);
    expect(screen.getByText("orchestrator").closest(".station")).toHaveClass("station--done");
    expect(screen.getByText("inventory").closest(".station")).toHaveClass("station--done");
    expect(screen.getByText("carrier").closest(".station")).toHaveClass("station--active");
    expect(screen.getByText("synthesis").closest(".station")).toHaveClass("station--pending");
    expect(screen.queryByText(/HOLD/)).not.toBeInTheDocument();
  });
});
