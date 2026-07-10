import { useEffect, useState } from "react";

import type { Api } from "../api/client";
import type { Decision, TraceRecord } from "../api/types";

/** Delay between revealing successive traces — tuned for a legible "watch it think" cadence. */
const REPLAY_INTERVAL_MS = 350;

export interface UseRunStreamResult {
  /** Traces revealed so far (one-by-one, unless reduced motion is set). */
  traces: TraceRecord[];
  /** The run's decision, populated once the trace replay has fully drained. */
  decision: Decision | null;
  /** True once both the trace replay and the decision fetch have completed. */
  done: boolean;
}

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Fetches the persisted trace for `runId` and replays it into state one
 * record at a time on a short interval, so `RunRail`'s stations light up in
 * sequence rather than all appearing at once — the run's signature
 * "watch it think" animation over the already-completed run.
 *
 * Once the replay drains (or immediately, under `prefers-reduced-motion`,
 * where every trace is revealed at once) the run's decision is fetched.
 */
export function useRunStream(runId: string | null, api: Api): UseRunStreamResult {
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | undefined;

    setTraces([]);
    setDecision(null);
    setDone(false);

    if (!runId) {
      return undefined;
    }

    async function finish(allTraces: TraceRecord[]) {
      const decisionResult = await api.getDecision(runId as string);
      if (cancelled) return;
      setDecision(decisionResult);
      setDone(true);
      void allTraces;
    }

    api.getTrace(runId).then((allTraces) => {
      if (cancelled) return;

      if (allTraces.length === 0 || prefersReducedMotion()) {
        setTraces(allTraces);
        void finish(allTraces);
        return;
      }

      let index = 0;
      timer = setInterval(() => {
        index += 1;
        setTraces(allTraces.slice(0, index));
        if (index >= allTraces.length) {
          if (timer) {
            clearInterval(timer);
            timer = undefined;
          }
          void finish(allTraces);
        }
      }, REPLAY_INTERVAL_MS);
    });

    return () => {
      cancelled = true;
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [runId, api]);

  return { traces, decision, done };
}
