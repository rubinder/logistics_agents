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
  FIXTURE_TRIGGER_RESULT,
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

/**
 * Thrown by `Api.triggerRun` when a live POST /runs rejects (e.g. 402 budget
 * exhausted, 429 rate limited, 400 unknown scenario). `message` is the API's
 * `detail` string, suitable for direct display in the UI.
 */
export class TriggerError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "TriggerError";
    this.status = status;
  }
}

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

  /**
   * Per-run reads (this and `getDecision`) intentionally do NOT use
   * `withFallback`: on a live backend, a transient error here must surface
   * as an error, not silently swap in another run's fixture trace/decision
   * while the UI still claims "Live". Fixtures are only served in explicit
   * fixtures mode (VITE_USE_FIXTURES=1).
   */
  async getTrace(runId: string): Promise<TraceRecord[]> {
    if (import.meta.env.VITE_USE_FIXTURES === "1") {
      this.usingFixtures = true;
      return FIXTURE_TRACES;
    }
    const result = await this.getJson<TraceRecord[]>(`/runs/${runId}/trace`);
    this.usingFixtures = false;
    return result;
  }

  /**
   * Returns `null` on a 404 (a legitimate "no decision persisted yet" for a
   * still-running or not-yet-decided run). Any other error (non-OK, non-404
   * response, or network failure) throws rather than falling back to a
   * fixture decision.
   */
  async getDecision(runId: string): Promise<Decision | null> {
    if (import.meta.env.VITE_USE_FIXTURES === "1") {
      this.usingFixtures = true;
      return FIXTURE_DECISION;
    }
    const response = await fetch(`${this.baseUrl}/runs/${runId}/decision`);
    if (response.status === 404) {
      this.usingFixtures = false;
      return null;
    }
    if (!response.ok) {
      throw new Error(`request to /runs/${runId}/decision failed: ${response.status}`);
    }
    this.usingFixtures = false;
    return (await response.json()) as Decision;
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

  /**
   * POST /runs is a mutating, budget-gated dispatch: unlike the read
   * endpoints, it must NOT silently fall back to fixture "success" when a
   * live backend rejects it (402 budget exhausted, 429 rate limited, ...).
   * Only in explicit fixtures mode (VITE_USE_FIXTURES=1) does it return
   * fixture data; otherwise real errors propagate as `TriggerError` so the
   * UI can show the rejection instead of dispatching a fabricated run id.
   */
  async triggerRun(scenarioId: string): Promise<TriggerResult> {
    if (import.meta.env.VITE_USE_FIXTURES === "1") {
      this.usingFixtures = true;
      return FIXTURE_TRIGGER_RESULT;
    }
    const response = await fetch(`${this.baseUrl}/runs`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
    if (!response.ok) {
      let detail = `Dispatch failed (${response.status})`;
      try {
        const body = await response.json();
        if (body && typeof body.detail === "string") detail = body.detail;
      } catch {
        /* keep the default message */
      }
      throw new TriggerError(response.status, detail);
    }
    this.usingFixtures = false;
    return (await response.json()) as TriggerResult;
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
