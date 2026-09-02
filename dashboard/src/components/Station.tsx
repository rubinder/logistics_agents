import "./Station.css";

import type { CSSProperties } from "react";

import type { TraceRecord } from "../api/types";

export type StationStatus = "pending" | "active" | "done";

export interface StationProps {
  /** Agent/node name, e.g. "orchestrator". */
  name: string;
  status: StationStatus;
  /** The trace for this node, once its call has completed. */
  trace?: TraceRecord;
  /** CSS color (a `var(--x)` string) used for the "done" arrival pulse and border. */
  signalColor: string;
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

/**
 * One terminal stop on the routing-manifest rail: the agent name, its
 * pending/active/done status, and — once its trace has arrived — the
 * cost/latency/token readout in mono, stamped like a manifest scan.
 */
export function Station({ name, status, trace, signalColor }: StationProps) {
  const style = { "--station-signal": signalColor } as CSSProperties;

  return (
    <div className={`station station--${status}`} style={style}>
      <span className="station-dot" aria-hidden="true" />
      <div className="station-body">
        <span className="station-name">{name}</span>
        <span className={`station-status station-status--${status}`}>{status}</span>
        <div className="station-metrics mono" aria-live="off">
          {trace ? (
            <>
              <span className="station-metric">{formatUsd(trace.cost_usd)}</span>
              <span className="station-metric">{trace.latency_ms}ms</span>
              <span className="station-metric">{trace.tokens}tok</span>
            </>
          ) : (
            <span className="station-metric station-metric--empty">&mdash;</span>
          )}
        </div>
      </div>
    </div>
  );
}
