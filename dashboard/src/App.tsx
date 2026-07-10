import { useCallback, useEffect, useRef, useState } from "react";

import "./App.css";

import { Api } from "./api/client";
import { FIXTURE_BUDGET } from "./api/fixtures";
import type { BudgetStatus } from "./api/types";
import { RunsBoard } from "./components/RunsBoard";
import { RunView } from "./components/RunView";
import { Shell } from "./components/Shell";
import { TriggerPanel } from "./components/TriggerPanel";

export default function App() {
  // A single Api instance for the app's lifetime, so its `usingFixtures`
  // bookkeeping and any in-flight requests stay consistent across renders.
  const apiRef = useRef<Api>();
  if (!apiRef.current) {
    apiRef.current = new Api();
  }
  const api = apiRef.current;

  const [budget, setBudget] = useState<BudgetStatus>(FIXTURE_BUDGET);
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [runIds, setRunIds] = useState<string[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [usingFixtures, setUsingFixtures] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [budgetStatus, scenarioList, runList] = await Promise.all([
        api.getBudget(),
        api.getScenarios(),
        api.listRuns(),
      ]);
      if (cancelled) return;
      setBudget(budgetStatus);
      setScenarios(scenarioList.scenarios);
      setRunIds(runList.run_ids);
      setUsingFixtures(api.usingFixtures);
      setSelectedRunId((current) => current ?? runList.run_ids[0] ?? null);
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [api]);

  const handleTriggered = useCallback(
    async (runId: string) => {
      const [runList, budgetStatus] = await Promise.all([api.listRuns(), api.getBudget()]);
      setRunIds(runList.run_ids);
      setBudget(budgetStatus);
      setUsingFixtures(api.usingFixtures);
      setSelectedRunId(runId);
    },
    [api],
  );

  return (
    <Shell budget={budget} usingFixtures={usingFixtures}>
      <h1>Logistics Agents</h1>
      <div className="app-layout">
        <aside className="app-layout-side">
          <RunsBoard runIds={runIds} selectedRunId={selectedRunId} onSelect={setSelectedRunId} />
          <TriggerPanel api={api} scenarios={scenarios} budget={budget} onTriggered={handleTriggered} />
        </aside>
        <section className="app-layout-main">
          <RunView runId={selectedRunId} api={api} />
        </section>
      </div>
    </Shell>
  );
}
