import { useEffect, useRef } from "react";

import "./RunLog.css";

import type { Decision } from "../api/types";
import type { LogEntry } from "../hooks/useRunLog";

export interface RunLogProps {
  entries: LogEntry[];
}

/** How close to the bottom still counts as "following the feed", in px. */
const STICK_THRESHOLD_PX = 32;

interface ParsedOutput {
  /** The node's prose, when its output carried a `reasoning` field. */
  reasoning: string | null;
  /** Everything else, rendered as compact key lines. */
  fields: [string, string][];
  /** Set when the output could not be parsed as JSON — shown verbatim instead. */
  raw: string | null;
}

function parseOutput(outputJson: string): ParsedOutput {
  let parsed: unknown;
  try {
    parsed = JSON.parse(outputJson);
  } catch {
    // Never blank the feed on an unexpected payload — show what arrived.
    return { reasoning: null, fields: [], raw: outputJson };
  }

  if (parsed === null || typeof parsed !== "object") {
    return { reasoning: null, fields: [], raw: String(parsed) };
  }

  let reasoning: string | null = null;
  const fields: [string, string][] = [];
  for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
    if (key === "reasoning" && typeof value === "string") {
      reasoning = value;
      continue;
    }
    fields.push([key, typeof value === "string" ? value : JSON.stringify(value)]);
  }
  return { reasoning, fields, raw: null };
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

function DecisionBlock({ decision }: { decision: Decision }) {
  return (
    <div className="run-log-decision">
      <div className="run-log-decision-head">
        <span className={`run-log-label run-log-label--${decision.label.toLowerCase()}`}>
          {decision.label}
        </span>
        <span className="run-log-meta">confidence {decision.confidence.toFixed(2)}</span>
      </div>
      <p className="run-log-prose">{decision.reasoning}</p>
      {decision.exceptions.length > 0 && (
        <ul className="run-log-list">
          {decision.exceptions.map((exception) => (
            <li key={exception.type}>
              <span className="run-log-key">{exception.type}</span> {exception.detail}
            </li>
          ))}
        </ul>
      )}
      {decision.recommended_actions.length > 0 && (
        <ul className="run-log-list">
          {decision.recommended_actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * The append-only session feed: every node of every run visited, newest
 * last, as readable prose rather than the Trace tab's truncated JSON grid.
 *
 * Scroll stays pinned to the bottom only while the reader is already there,
 * so a run streaming in never yanks them away from something they scrolled
 * back to read.
 */
export function RunLog({ entries }: RunLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  useEffect(() => {
    const node = scrollRef.current;
    if (node && stickToBottom.current) {
      node.scrollTop = node.scrollHeight;
    }
  }, [entries]);

  function handleScroll() {
    const node = scrollRef.current;
    if (!node) return;
    const distance = node.scrollHeight - node.scrollTop - node.clientHeight;
    stickToBottom.current = distance <= STICK_THRESHOLD_PX;
  }

  if (entries.length === 0) {
    return (
      <div className="run-log run-log--empty panel">
        <p>Nothing has streamed yet — select or trigger a run to start the log.</p>
      </div>
    );
  }

  return (
    <div className="run-log panel" ref={scrollRef} onScroll={handleScroll}>
      {entries.map((entry, index) => {
        const startsRun = index === 0 || entries[index - 1].runId !== entry.runId;
        return (
          <div className="run-log-entry" key={entry.key}>
            {startsRun && <div className="run-log-run-head mono">{entry.runId}</div>}
            {entry.kind === "decision" && entry.decision ? (
              <DecisionBlock decision={entry.decision} />
            ) : (
              entry.trace && <TraceBlock entry={entry} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function TraceBlock({ entry }: { entry: LogEntry }) {
  const trace = entry.trace!;
  const { reasoning, fields, raw } = parseOutput(trace.output_json);
  return (
    <div className="run-log-trace">
      <div className="run-log-node mono">
        <span className="run-log-node-name">[{trace.node}]</span>
        <span className="run-log-meta">
          {trace.tokens} tok · {formatUsd(trace.cost_usd)} · {trace.latency_ms}ms
        </span>
      </div>
      {reasoning && <p className="run-log-prose">{reasoning}</p>}
      {fields.length > 0 && (
        <dl className="run-log-fields mono">
          {fields.map(([key, value]) => (
            <div className="run-log-field" key={key}>
              <dt className="run-log-key">{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {raw !== null && <pre className="run-log-raw mono">{raw}</pre>}
    </div>
  );
}
