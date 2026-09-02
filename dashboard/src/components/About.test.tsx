import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AboutBlurb, AboutExtended } from "./About";

describe("AboutBlurb", () => {
  it("names the pipeline and the four decision labels", () => {
    render(<AboutBlurb />);
    const text = screen.getByRole("note").textContent ?? "";
    for (const term of ["orchestrator", "accept", "hold", "reroute", "escalate"]) {
      expect(text.toLowerCase()).toContain(term);
    }
  });

  it("points the reader at the Log tab for the reasoning", () => {
    render(<AboutBlurb />);
    expect(screen.getByRole("note")).toHaveTextContent(/log/i);
  });
});

describe("AboutExtended", () => {
  function headings(): string[] {
    return screen.getAllByRole("heading").map((h) => h.textContent ?? "");
  }

  it("covers why, flow, evaluation, comparison and the public guards", () => {
    render(<AboutExtended />);
    const joined = headings().join(" ").toLowerCase();
    for (const topic of ["why", "flow", "evaluat", "compar", "public"]) {
      expect(joined).toContain(topic);
    }
  });

  it("describes the end-to-end flow through to this dashboard", () => {
    render(<AboutExtended />);
    const text = document.body.textContent?.toLowerCase() ?? "";
    for (const stage of ["kafka", "postgres", "synthesis", "dashboard"]) {
      expect(text).toContain(stage);
    }
  });

  it("says plainly that the public demo serves bundled sample data", () => {
    render(<AboutExtended />);
    expect(document.body.textContent).toMatch(/sample data/i);
  });

  it("carries no hardcoded metrics, which rot as soon as the eval is re-run", () => {
    render(<AboutExtended />);
    const text = document.body.textContent ?? "";
    // The Eval Board on the same page renders real scores from data; prose
    // that repeats them silently goes stale the next time the eval runs.
    expect(text).not.toMatch(/\d+\.\d+/);
    expect(text).not.toContain("%");
  });
});
