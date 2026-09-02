import { useEffect, useState } from "react";

import "./TriggerPanel.css";

import { TriggerError } from "../api/client";
import type { Api } from "../api/client";
import type { BudgetStatus } from "../api/types";

export interface TriggerPanelProps {
  api: Api;
  scenarios: string[];
  budget: BudgetStatus;
  /** Called with the newly triggered run's id once dispatch succeeds. */
  onTriggered: (runId: string) => void;
}

/** Turns a thrown error's message into operator-facing copy for rate/budget rejections. */
function friendlyMessage(message: string): string {
  if (/\b429\b/.test(message)) {
    return "Rate limit reached — wait a moment and try again.";
  }
  if (/\b402\b/.test(message)) {
    return "Budget exhausted — the run was rejected.";
  }
  return "Dispatch failed. Please try again.";
}

/**
 * The dispatch console: pick a scenario, fire a run. Disabled outright once
 * the budget meter reads exhausted; surfaces the API's rate/budget
 * rejections inline rather than failing silently.
 */
export function TriggerPanel({ api, scenarios, budget, onTriggered }: TriggerPanelProps) {
  const [scenarioId, setScenarioId] = useState(scenarios[0] ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scenarioId && scenarios.length > 0) {
      setScenarioId(scenarios[0]);
    }
  }, [scenarios, scenarioId]);

  const exhausted = budget.remaining_usd <= 0;

  async function handleDispatch() {
    if (!scenarioId || pending) return;
    setPending(true);
    setError(null);
    try {
      const result = await api.triggerRun(scenarioId);
      onTriggered(result.run_id);
    } catch (err) {
      if (err instanceof TriggerError) {
        // The API's own rejection detail (e.g. "budget exhausted",
        // "rate limit exceeded") is already operator-facing - surface it
        // directly rather than remapping it.
        setError(err.message);
      } else if (err instanceof Error) {
        setError(friendlyMessage(err.message));
      } else {
        setError("Dispatch failed. Please try again.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="trigger-panel panel">
      <div className="trigger-panel-header">
        <span className="trigger-panel-title">Trigger</span>
      </div>
      <label className="trigger-panel-label" htmlFor="trigger-panel-scenario">
        Scenario
      </label>
      <select
        id="trigger-panel-scenario"
        className="trigger-panel-select mono"
        value={scenarioId}
        onChange={(event) => setScenarioId(event.target.value)}
        disabled={scenarios.length === 0}
      >
        {scenarios.map((scenario) => (
          <option key={scenario} value={scenario}>
            {scenario}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="trigger-panel-button"
        onClick={handleDispatch}
        disabled={exhausted || pending || !scenarioId}
      >
        {pending ? "Dispatching…" : "Dispatch run"}
      </button>
      {exhausted && (
        <p className="trigger-panel-message trigger-panel-message--warning">
          Budget exhausted &mdash; dispatch disabled.
        </p>
      )}
      {error && <p className="trigger-panel-message trigger-panel-message--error">{error}</p>}
    </div>
  );
}
