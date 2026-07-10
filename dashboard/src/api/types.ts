// Types mirroring the M6 API JSON shapes exactly (snake_case field names).
// See: src/logistics_agents/domain/models.py, domain/enums.py, evals/runner.py

export type DecisionLabel = "ACCEPT" | "HOLD" | "REROUTE" | "ESCALATE";

export type ExceptionType =
  | "QUANTITY_MISMATCH"
  | "LATE_DELIVERY"
  | "UNKNOWN_PO"
  | "OVERCAPACITY"
  | "MISSING_DOCS"
  | "DAMAGED";

export interface ExceptionRecord {
  type: ExceptionType;
  detail: string;
}

export interface Decision {
  label: DecisionLabel;
  exceptions: ExceptionRecord[];
  recommended_actions: string[];
  confidence: number;
  reasoning: string;
}

export interface TraceRecord {
  run_id: string;
  node: string;
  input_json: string;
  output_json: string;
  latency_ms: number;
  tokens: number;
  cost_usd: number;
  model: string;
  created_at: string;
}

export interface BudgetStatus {
  cap_usd: number;
  spent_usd: number;
  remaining_usd: number;
}

// Mirrors evals/graders/composite.py::CaseScore
export interface CaseScore {
  label_correct: boolean;
  exception_precision: number;
  exception_recall: number;
  exception_f1: number;
  action_coverage: number;
  judge_score: number | null;
  composite: number;
}

// Mirrors evals/runner.py::CaseResult
export interface CaseResult {
  case_id: string;
  model: string;
  label: string;
  score: CaseScore;
}

// Mirrors evals/runner.py::EvalReport
export interface EvalReport {
  model: string;
  results: CaseResult[];
  label_accuracy: number;
  mean_f1: number;
  mean_action_coverage: number;
  mean_judge: number | null;
  mean_composite: number;
  rubric_version: string;
  dataset_version: string;
  timestamp: string | null;
  git_sha: string | null;
}

// GET /runs response shape.
export interface RunListResponse {
  run_ids: string[];
}

// GET /scenarios response shape.
export interface ScenarioListResponse {
  scenarios: string[];
}

// POST /runs response shape.
export interface TriggerResult {
  run_id: string;
  decision: Decision;
  cost_usd: number;
}

// Dashboard-only convenience shape (not a direct API response) used to render
// a runs list without a round trip per run for id/label/cost/timestamp.
export interface RunSummary {
  run_id: string;
  label: DecisionLabel;
  cost_usd: number;
  created_at: string;
}
