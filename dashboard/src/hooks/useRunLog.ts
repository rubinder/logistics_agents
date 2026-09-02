import { useEffect, useRef, useState } from "react";

import type { Decision, TraceRecord } from "../api/types";

/** One line in the append-only feed: a revealed trace, or a run's final decision. */
export interface LogEntry {
  /** Stable identity, and the de-duplication key: `<run_id>:<node>`. */
  key: string;
  runId: string;
  kind: "trace" | "decision";
  trace?: TraceRecord;
  decision?: Decision;
}

const DECISION_NODE = "__decision__";

/**
 * Accumulates an append-only log across every run visited this session.
 *
 * `useRunStream` is per-run: it resets on selection and then reveals a
 * *growing prefix* of that run's traces on an interval. Appending only
 * unseen `<run_id>:<node>` keys turns that into a feed that grows one line
 * at a time in lockstep with the rail, survives switching runs, and stays
 * flat when a run already in the feed is replayed — a feed that regrew on
 * every click would be noise rather than history.
 *
 * Lives above the tab switch so the log keeps filling while the Trace tab
 * is on screen.
 */
export function useRunLog(traces: TraceRecord[], decision: Decision | null): LogEntry[] {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    const fresh: LogEntry[] = [];
    for (const trace of traces) {
      const key = `${trace.run_id}:${trace.node}`;
      if (seen.current.has(key)) continue;
      seen.current.add(key);
      fresh.push({ key, runId: trace.run_id, kind: "trace", trace });
    }
    if (fresh.length > 0) {
      setEntries((prev) => [...prev, ...fresh]);
    }
  }, [traces]);

  useEffect(() => {
    if (decision === null || traces.length === 0) return;
    // The decision is fetched only after the replay drains, so the last
    // revealed trace always belongs to the run the decision describes.
    const runId = traces[traces.length - 1].run_id;
    const key = `${runId}:${DECISION_NODE}`;
    if (seen.current.has(key)) return;
    seen.current.add(key);
    setEntries((prev) => [...prev, { key, runId, kind: "decision", decision }]);
  }, [decision, traces]);

  return entries;
}
