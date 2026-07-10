import "./RunView.css";

import type { Api } from "../api/client";
import { useRunStream } from "../hooks/useRunStream";
import { RunRail } from "./RunRail";

export interface RunViewProps {
  runId: string | null;
  api: Api;
}

const MAX_JSON_PREVIEW = 140;

function truncateJson(json: string): string {
  return json.length > MAX_JSON_PREVIEW ? `${json.slice(0, MAX_JSON_PREVIEW)}…` : json;
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

/**
 * The main run view: the `RunRail` "watch it think" visualizer over a
 * per-node trace detail table (model, cost, latency, tokens, and truncated
 * input/output JSON) in mono, driven by `useRunStream`'s replay of the
 * selected run.
 */
export function RunView({ runId, api }: RunViewProps) {
  const { traces, decision } = useRunStream(runId, api);

  if (!runId) {
    return (
      <div className="run-view run-view--empty panel">
        <p>Select a run from the board to watch it replay.</p>
      </div>
    );
  }

  return (
    <div className="run-view">
      <RunRail traces={traces} decision={decision} />
      <div className="run-view-table-wrap panel">
        <table className="run-view-table mono">
          <thead>
            <tr>
              <th>Node</th>
              <th>Model</th>
              <th>Cost</th>
              <th>Latency</th>
              <th>Tokens</th>
              <th>Input</th>
              <th>Output</th>
            </tr>
          </thead>
          <tbody>
            {traces.map((trace) => (
              <tr key={trace.node}>
                <td>{trace.node}</td>
                <td>{trace.model}</td>
                <td>{formatUsd(trace.cost_usd)}</td>
                <td>{trace.latency_ms}ms</td>
                <td>{trace.tokens}</td>
                <td className="run-view-json">{truncateJson(trace.input_json)}</td>
                <td className="run-view-json">{truncateJson(trace.output_json)}</td>
              </tr>
            ))}
            {traces.length === 0 && (
              <tr>
                <td colSpan={7} className="run-view-empty-row">
                  Waiting for the first trace&hellip;
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
