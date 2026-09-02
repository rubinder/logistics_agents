import "./RunRail.css";

import type { CSSProperties } from "react";

import type { Decision, TraceRecord } from "../api/types";
import { DecisionStamp } from "./DecisionStamp";
import { labelColor, NODE_ORDER } from "./signal";
import { Station, type StationStatus } from "./Station";

export interface RunRailProps {
  traces: TraceRecord[];
  decision: Decision | null;
}

/**
 * The signature "watch it think" visualization: the fixed agent DAG as a
 * horizontal routing-manifest rail — a shipment passing through terminal
 * stations (orchestrator -> inventory -> carrier -> exception -> synthesis).
 *
 * Driven entirely off `traces`: a node with a matching trace is "done" and
 * shows its metrics; the next unreached node is "active" while the run is
 * still in flight; everything after that is "pending". Works identically
 * whether `traces` arrives complete or is fed in one-by-one over SSE.
 * Terminates in the DecisionStamp once `decision` is present.
 */
export function RunRail({ traces, decision }: RunRailProps) {
  const traceByNode = new Map(traces.map((trace) => [trace.node, trace]));
  const runInFlight = decision === null;
  let activeAssigned = false;

  const stations = NODE_ORDER.map((node) => {
    const trace = traceByNode.get(node);
    let status: StationStatus;
    if (trace) {
      status = "done";
    } else if (runInFlight && !activeAssigned) {
      status = "active";
      activeAssigned = true;
    } else {
      status = "pending";
    }
    return { node, trace, status };
  });

  const signalColor = decision ? labelColor(decision.label) : "var(--cyan)";

  return (
    <div className="run-rail">
      <ol className="run-rail-track">
        {stations.map((station, index) => (
          <li key={station.node} className="run-rail-item">
            <Station
              name={station.node}
              status={station.status}
              trace={station.trace}
              signalColor={signalColor}
            />
            {index < stations.length - 1 && (
              <span
                className={`run-rail-connector ${station.status === "done" ? "run-rail-connector--done" : ""}`}
                style={{ "--connector-signal": signalColor } as CSSProperties}
                aria-hidden="true"
              />
            )}
          </li>
        ))}
      </ol>
      {decision && (
        <div className="run-rail-terminus">
          <DecisionStamp decision={decision} />
        </div>
      )}
    </div>
  );
}
