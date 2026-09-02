import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TriggerError, type Api } from "../api/client";
import type { BudgetStatus } from "../api/types";
import { TriggerPanel } from "./TriggerPanel";

const HEALTHY_BUDGET: BudgetStatus = { cap_usd: 20, spent_usd: 3.2, remaining_usd: 16.8 };
const EXHAUSTED_BUDGET: BudgetStatus = { cap_usd: 20, spent_usd: 20, remaining_usd: 0 };

describe("TriggerPanel", () => {
  it("shows the API's rejection detail inline and does not call onTriggered when dispatch is rejected", async () => {
    const user = userEvent.setup();
    const api = {
      triggerRun: vi.fn().mockRejectedValue(new TriggerError(402, "budget exhausted")),
    } as unknown as Api;
    const onTriggered = vi.fn();

    render(
      <TriggerPanel
        api={api}
        scenarios={["quantity-mismatch"]}
        budget={HEALTHY_BUDGET}
        onTriggered={onTriggered}
      />,
    );

    await user.selectOptions(screen.getByLabelText(/scenario/i), "quantity-mismatch");
    await user.click(screen.getByRole("button", { name: /dispatch run/i }));

    expect(await screen.findByText("budget exhausted")).toBeInTheDocument();
    expect(onTriggered).not.toHaveBeenCalled();
  });

  it("disables the dispatch button when the budget is exhausted", () => {
    const api = { triggerRun: vi.fn() } as unknown as Api;
    render(
      <TriggerPanel
        api={api}
        scenarios={["quantity-mismatch"]}
        budget={EXHAUSTED_BUDGET}
        onTriggered={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /dispatch run/i })).toBeDisabled();
  });
});
