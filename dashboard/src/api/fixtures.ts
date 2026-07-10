// Bundled fixture data so the dashboard renders standalone before the M6 API
// is reachable, and so client tests are deterministic without network access.

import type {
  BudgetStatus,
  CaseResult,
  Decision,
  EvalReport,
  RunSummary,
  ScenarioListResponse,
  TraceRecord,
  TriggerResult,
} from "./types";

export const FIXTURE_RUN_ID = "trigger-quantity-mismatch-a1b2c3d4e5f6";

const T0 = "2026-07-08T14:02:00Z";

export const FIXTURE_TRACES: TraceRecord[] = [
  {
    run_id: FIXTURE_RUN_ID,
    node: "orchestrator",
    input_json: JSON.stringify({
      po_id: "PO-10432",
      shipment_id: "SHP-88213",
    }),
    output_json: JSON.stringify({
      plan: ["inventory", "carrier", "exception", "synthesis"],
    }),
    latency_ms: 420,
    tokens: 612,
    cost_usd: 0.0092,
    model: "claude-sonnet-5",
    created_at: T0,
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "inventory",
    input_json: JSON.stringify({
      sku: "SKU-2291",
      dc_id: "DC-EAST-1",
      expected_quantity: 480,
      reported_quantity: 410,
    }),
    output_json: JSON.stringify({
      on_hand: 1220,
      reserved: 300,
      capacity: 2000,
      available_capacity: 780,
      quantity_gap: 70,
    }),
    latency_ms: 310,
    tokens: 498,
    cost_usd: 0.0071,
    model: "claude-sonnet-5",
    created_at: "2026-07-08T14:02:01Z",
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "carrier",
    input_json: JSON.stringify({
      tracking_number: "1Z999AA10123456784",
    }),
    output_json: JSON.stringify({
      status: "delivered",
      eta: null,
      delayed: false,
    }),
    latency_ms: 265,
    tokens: 341,
    cost_usd: 0.0048,
    model: "claude-sonnet-5",
    created_at: "2026-07-08T14:02:02Z",
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "exception",
    input_json: JSON.stringify({
      expected_quantity: 480,
      reported_quantity: 410,
      quantity_gap: 70,
    }),
    output_json: JSON.stringify({
      exceptions: [
        { type: "QUANTITY_MISMATCH", detail: "Reported 410 units vs 480 expected (70 short)." },
      ],
    }),
    latency_ms: 388,
    tokens: 574,
    cost_usd: 0.0083,
    model: "claude-sonnet-5",
    created_at: "2026-07-08T14:02:03Z",
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "synthesis",
    input_json: JSON.stringify({
      exceptions: [{ type: "QUANTITY_MISMATCH", detail: "Reported 410 units vs 480 expected (70 short)." }],
      carrier_status: "delivered",
    }),
    output_json: JSON.stringify({
      label: "HOLD",
      confidence: 0.82,
    }),
    latency_ms: 455,
    tokens: 703,
    cost_usd: 0.0106,
    model: "claude-sonnet-5",
    created_at: "2026-07-08T14:02:04Z",
  },
];

export const FIXTURE_DECISION: Decision = {
  label: "HOLD",
  exceptions: [
    {
      type: "QUANTITY_MISMATCH",
      detail: "Reported 410 units vs 480 expected (70 short) for SKU-2291 at DC-EAST-1.",
    },
  ],
  recommended_actions: [
    "Hold shipment SHP-88213 pending supplier confirmation of short-ship.",
    "Request corrected packing list from supplier for PO-10432.",
    "Notify DC-EAST-1 inventory lead of the 70-unit shortfall.",
  ],
  confidence: 0.82,
  reasoning:
    "Carrier delivered on time and documentation is present, but reported quantity " +
    "(410) falls short of the expected quantity (480) by 70 units. This exceeds the " +
    "quantity-mismatch tolerance, so the shipment is held pending supplier confirmation " +
    "rather than accepted outright.",
};

export const FIXTURE_BUDGET: BudgetStatus = {
  cap_usd: 20,
  spent_usd: 3.2,
  remaining_usd: 16.8,
};

export const FIXTURE_SCENARIOS: ScenarioListResponse = {
  scenarios: ["clean", "quantity-mismatch"],
};

// POST /runs fixture result, used only in explicit fixtures mode
// (VITE_USE_FIXTURES=1) - live dispatch calls never fall back to this.
export const FIXTURE_TRIGGER_RESULT: TriggerResult = {
  run_id: FIXTURE_RUN_ID,
  decision: FIXTURE_DECISION,
  cost_usd: 0.036,
};

function caseResult(model: string, caseId: string, label: string, composite: number): CaseResult {
  return {
    case_id: caseId,
    model,
    label,
    score: {
      label_correct: label !== "ACCEPT" || caseId !== "quantity-mismatch-01",
      exception_precision: composite > 0.8 ? 1.0 : 0.75,
      exception_recall: composite > 0.8 ? 1.0 : 0.7,
      exception_f1: composite > 0.8 ? 1.0 : 0.72,
      action_coverage: composite > 0.8 ? 1.0 : 0.67,
      judge_score: composite > 0.8 ? 5 : composite > 0.6 ? 4 : 3,
      composite,
    },
  };
}

export const FIXTURE_EVAL_REPORTS: EvalReport[] = [
  {
    model: "claude-opus-4-8",
    results: [
      caseResult("claude-opus-4-8", "clean-01", "ACCEPT", 0.96),
      caseResult("claude-opus-4-8", "quantity-mismatch-01", "HOLD", 0.93),
    ],
    label_accuracy: 1.0,
    mean_f1: 0.97,
    mean_action_coverage: 0.95,
    mean_judge: 4.8,
    mean_composite: 0.945,
    rubric_version: "v1",
    dataset_version: "v1",
    timestamp: "2026-07-08T12:00:00Z",
    git_sha: "a1b2c3d",
  },
  {
    model: "claude-sonnet-5",
    results: [
      caseResult("claude-sonnet-5", "clean-01", "ACCEPT", 0.91),
      caseResult("claude-sonnet-5", "quantity-mismatch-01", "HOLD", 0.85),
    ],
    label_accuracy: 1.0,
    mean_f1: 0.9,
    mean_action_coverage: 0.88,
    mean_judge: 4.3,
    mean_composite: 0.88,
    rubric_version: "v1",
    dataset_version: "v1",
    timestamp: "2026-07-08T12:05:00Z",
    git_sha: "a1b2c3d",
  },
  {
    model: "claude-haiku-4-5",
    results: [
      caseResult("claude-haiku-4-5", "clean-01", "ACCEPT", 0.78),
      caseResult("claude-haiku-4-5", "quantity-mismatch-01", "ACCEPT", 0.52),
    ],
    label_accuracy: 0.5,
    mean_f1: 0.68,
    mean_action_coverage: 0.7,
    mean_judge: 3.4,
    mean_composite: 0.65,
    rubric_version: "v1",
    dataset_version: "v1",
    timestamp: "2026-07-08T12:10:00Z",
    git_sha: "a1b2c3d",
  },
];

export const FIXTURE_RUN_SUMMARIES: RunSummary[] = [
  {
    run_id: FIXTURE_RUN_ID,
    label: "HOLD",
    cost_usd: FIXTURE_TRACES.reduce((sum, t) => sum + t.cost_usd, 0),
    created_at: T0,
  },
];
