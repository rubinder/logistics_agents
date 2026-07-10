import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FIXTURE_EVAL_REPORTS } from "../api/fixtures";
import { EvalBoard } from "./EvalBoard";

describe("EvalBoard", () => {
  it("renders each model id and its mean composite value", () => {
    render(<EvalBoard reports={FIXTURE_EVAL_REPORTS} />);

    for (const report of FIXTURE_EVAL_REPORTS) {
      expect(screen.getByText(report.model)).toBeInTheDocument();
      expect(screen.getByText(report.mean_composite.toFixed(3))).toBeInTheDocument();
    }
  });

  it("orders models by mean_composite descending regardless of input order", () => {
    // Feed the reports in reverse so this test actually exercises the sort
    // rather than happening to match a fixture that's already descending.
    const shuffled = [...FIXTURE_EVAL_REPORTS].reverse();
    render(<EvalBoard reports={shuffled} />);

    const expectedOrder = [...FIXTURE_EVAL_REPORTS]
      .sort((a, b) => b.mean_composite - a.mean_composite)
      .map((report) => report.model);

    const renderedOrder = screen.getAllByTestId("eval-model").map((el) => el.textContent);
    expect(renderedOrder).toEqual(expectedOrder);
  });
});
