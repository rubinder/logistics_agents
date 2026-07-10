// Typed client for the M6 API, with bundled-fixture fallback so the
// dashboard renders standalone before the backend is up (or in tests, where
// there is no network) and can be forced into fixture mode via
// VITE_USE_FIXTURES=1.

import {
  FIXTURE_BUDGET,
  FIXTURE_DECISION,
  FIXTURE_EVAL_REPORTS,
  FIXTURE_RUN_ID,
  FIXTURE_SCENARIOS,
  FIXTURE_TRACES,
} from "./fixtures";
import type {
  BudgetStatus,
  Decision,
  EvalReport,
  RunListResponse,
  ScenarioListResponse,
  TraceRecord,
  TriggerResult,
} from "./types";

export class Api {
  private readonly baseUrl: string;

  /** Set to true whenever the most recent call returned fixture data. */
  usingFixtures = false;

  constructor(baseUrl: string = import.meta.env.VITE_API_BASE ?? "") {
    this.baseUrl = baseUrl;
  }

  /**
   * Runs `fetcher`, returning its result. Falls back to `fixture` when
   * VITE_USE_FIXTURES is "1" (without attempting the fetch) or when
   * `fetcher` throws (network error, non-OK response, bad JSON, etc).
   */
  private async withFallback<T>(fetcher: () => Promise<T>, fixture: T): Promise<T> {
    if (import.meta.env.VITE_USE_FIXTURES === "1") {
      this.usingFixtures = true;
      return fixture;
    }
    try {
      const result = await fetcher();
      this.usingFixtures = false;
      return result;
    } catch {
      this.usingFixtures = true;
      return fixture;
    }
  }

  private async getJson<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`);
    if (!response.ok) {
      throw new Error(`request to ${path} failed: ${response.status}`);
    }
    return (await response.json()) as T;
  }

  listRuns(): Promise<RunListResponse> {
    return this.withFallback(() => this.getJson<RunListResponse>("/runs"), {
      run_ids: [FIXTURE_RUN_ID],
    });
  }

  getTrace(runId: string): Promise<TraceRecord[]> {
    return this.withFallback(
      () => this.getJson<TraceRecord[]>(`/runs/${runId}/trace`),
      FIXTURE_TRACES,
    );
  }

  getDecision(runId: string): Promise<Decision> {
    return this.withFallback(
      () => this.getJson<Decision>(`/runs/${runId}/decision`),
      FIXTURE_DECISION,
    );
  }

  getBudget(): Promise<BudgetStatus> {
    return this.withFallback(() => this.getJson<BudgetStatus>("/budget"), FIXTURE_BUDGET);
  }

  getScenarios(): Promise<ScenarioListResponse> {
    return this.withFallback(
      () => this.getJson<ScenarioListResponse>("/scenarios"),
      FIXTURE_SCENARIOS,
    );
  }

  triggerRun(scenarioId: string): Promise<TriggerResult> {
    const fixture: TriggerResult = {
      run_id: FIXTURE_RUN_ID,
      decision: FIXTURE_DECISION,
      cost_usd: FIXTURE_BUDGET.spent_usd,
    };
    return this.withFallback(async () => {
      const response = await fetch(`${this.baseUrl}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_id: scenarioId }),
      });
      if (!response.ok) {
        throw new Error(`trigger run failed: ${response.status}`);
      }
      return (await response.json()) as TriggerResult;
    }, fixture);
  }

  /**
   * There is no GET /eval endpoint yet on the M6 API - eval reports are only
   * available as fixtures until that endpoint exists, so this always
   * resolves to fixture data (still routed through withFallback so
   * `usingFixtures` reflects it consistently).
   */
  getEvalReports(): Promise<EvalReport[]> {
    return this.withFallback(
      () => Promise.reject(new Error("no eval endpoint available")),
      FIXTURE_EVAL_REPORTS,
    );
  }
}
