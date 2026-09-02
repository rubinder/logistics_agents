import type { ReactNode } from "react";

import "./Shell.css";

import type { BudgetStatus } from "../api/types";
import { BudgetMeter } from "./BudgetMeter";

export interface ShellProps {
  budget: BudgetStatus;
  /** True whenever the data on screen is bundled fixtures rather than a live API. */
  usingFixtures?: boolean;
  children: ReactNode;
}

/**
 * App shell: a masthead (product name, live/sample-data status, budget
 * gauge) over a main content region. The visual foundation every dashboard
 * view is rendered inside.
 */
export function Shell({ budget, usingFixtures = false, children }: ShellProps) {
  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-brand">
          <span className="shell-brand-mark" aria-hidden="true" />
          <span className="shell-brand-name">Logistics Agents</span>
        </div>
        <div className="shell-status">
          <span
            className={`status-chip ${usingFixtures ? "status-chip--sample" : "status-chip--live"}`}
          >
            {usingFixtures ? "Sample Data" : "Live"}
          </span>
          <BudgetMeter {...budget} />
        </div>
      </header>
      <main className="shell-main">{children}</main>
    </div>
  );
}
