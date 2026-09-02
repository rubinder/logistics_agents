import { useCallback, useEffect, useRef, useState } from "react";

import "./App.css";

import { Api } from "./api/client";
import { FIXTURE_BUDGET, FIXTURE_EVAL_REPORTS } from "./api/fixtures";
import type { BudgetStatus, EvalReport } from "./api/types";
import { AboutBlurb, AboutExtended } from "./components/About";
import { EvalBoard } from "./components/EvalBoard";
import { RunLog } from "./components/RunLog";
import { RunsBoard } from "./components/RunsBoard";
import { RunView } from "./components/RunView";
import { Shell } from "./components/Shell";
import { TriggerPanel } from "./components/TriggerPanel";
import { useRunLog } from "./hooks/useRunLog";
import { useRunStream } from "./hooks/useRunStream";

type MainTab = "trace" | "log" | "about";

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
  const [evalReports, setEvalReports] = useState<EvalReport[]>(FIXTURE_EVAL_REPORTS);
  const [tab, setTab] = useState<MainTab>("trace");

  // Owned here, not in RunView, so both tabs render one replay rather than
  // opening two subscriptions that fetch twice and animate out of step.
  const { traces, decision, error } = useRunStream(selectedRunId, api);
  // Above the tab switch, so the feed keeps filling while Trace is on screen.
  const logEntries = useRunLog(traces, decision);

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

      // Fetched separately from the above: getEvalReports() always falls
      // back to fixture data (there is no live eval endpoint yet), and
      // `api.usingFixtures` is a single shared flag, so folding this into
      // the Promise.all above would permanently flip the live/sample-data
      // badge to "Sample Data" even when the other endpoints are live.
      const evalReportList = await api.getEvalReports();
      if (cancelled) return;
      setEvalReports(evalReportList);
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
          <div className="app-tabs" role="tablist" aria-label="Run views">
            <button
              type="button"
              role="tab"
              id="tab-trace"
              aria-selected={tab === "trace"}
              aria-controls="panel-trace"
              className={`app-tab ${tab === "trace" ? "app-tab--active" : ""}`}
              onClick={() => setTab("trace")}
            >
              Trace
            </button>
            <button
              type="button"
              role="tab"
              id="tab-log"
              aria-selected={tab === "log"}
              aria-controls="panel-log"
              className={`app-tab ${tab === "log" ? "app-tab--active" : ""}`}
              onClick={() => setTab("log")}
            >
              Log
              {logEntries.length > 0 && <span className="app-tab-count">{logEntries.length}</span>}
            </button>
            <button
              type="button"
              role="tab"
              id="tab-about"
              aria-selected={tab === "about"}
              aria-controls="panel-about"
              className={`app-tab ${tab === "about" ? "app-tab--active" : ""}`}
              onClick={() => setTab("about")}
            >
              About Extended
            </button>
          </div>
          {tab === "trace" && (
            <div role="tabpanel" id="panel-trace" aria-labelledby="tab-trace">
              <AboutBlurb />
              <RunView
                runId={selectedRunId}
                traces={traces}
                decision={decision}
                error={error}
              />
            </div>
          )}
          {tab === "log" && (
            <div role="tabpanel" id="panel-log" aria-labelledby="tab-log">
              <RunLog entries={logEntries} />
            </div>
          )}
          {tab === "about" && (
            <div role="tabpanel" id="panel-about" aria-labelledby="tab-about">
              <AboutExtended />
            </div>
          )}
        </section>
      </div>
      <section className="app-eval-section">
        <EvalBoard reports={evalReports} />
      </section>
    </Shell>
  );
}
