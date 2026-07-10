import type { DecisionLabel } from "../api/types";

/** Fixed agent DAG order the routing-manifest rail renders stations in. */
export const NODE_ORDER = ["orchestrator", "inventory", "carrier", "exception", "synthesis"] as const;

export type NodeName = (typeof NODE_ORDER)[number];

const SIGNAL_VAR: Record<DecisionLabel, string> = {
  ACCEPT: "var(--accept)",
  HOLD: "var(--hold)",
  REROUTE: "var(--reroute)",
  ESCALATE: "var(--escalate)",
};

/** The signal CSS var (as a `var(--x)` string) for a decision label. */
export function labelColor(label: DecisionLabel): string {
  return SIGNAL_VAR[label];
}
