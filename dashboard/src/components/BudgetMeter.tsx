import "./BudgetMeter.css";

import type { BudgetStatus } from "../api/types";

/** Below this fraction of the cap remaining, the gauge shifts to the HOLD tint. */
const LOW_HEADROOM_RATIO = 0.25;

type Tone = "accept" | "hold" | "escalate";

function formatUsd(value: number): string {
  return value.toFixed(2);
}

function toneFor(cap_usd: number, remaining_usd: number): Tone {
  if (remaining_usd <= 0) {
    return "escalate";
  }
  const remainingRatio = cap_usd > 0 ? remaining_usd / cap_usd : 0;
  if (remainingRatio < LOW_HEADROOM_RATIO) {
    return "hold";
  }
  return "accept";
}

/**
 * A labelled fuel-gauge bar for the run budget: fill width tracks spent/cap,
 * tinted by how much headroom is left (healthy / low / exhausted).
 */
export function BudgetMeter({ cap_usd, spent_usd, remaining_usd }: BudgetStatus) {
  const cap = cap_usd > 0 ? cap_usd : 1;
  const fillRatio = Math.min(Math.max(spent_usd / cap, 0), 1);
  const tone = toneFor(cap_usd, remaining_usd);

  return (
    <div className="budget-meter" role="group" aria-label="Run budget">
      <div className="budget-meter-row">
        <span className="budget-meter-title">Budget</span>
        <span className={`mono budget-meter-figures budget-meter-figures--${tone}`}>
          ${formatUsd(spent_usd)} / ${formatUsd(cap_usd)}
          <span className="budget-meter-remaining">&nbsp;&middot; ${formatUsd(remaining_usd)} left</span>
        </span>
      </div>
      <div
        className="budget-meter-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={cap_usd}
        aria-valuenow={spent_usd}
        aria-label="Budget spent"
      >
        <div
          className={`budget-meter-fill budget-meter-fill--${tone}`}
          style={{ width: `${fillRatio * 100}%` }}
        />
      </div>
    </div>
  );
}
