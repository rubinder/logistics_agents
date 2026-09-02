// Bundled fixture data so the dashboard renders standalone before the M6 API
// is reachable, and so client tests are deterministic without network access.
//
// Generated from a real recorded run, not written by hand: the traces below are
// the actual model calls for the "quantity-mismatch" scenario (identical to the
// eval case of the same name), and the eval reports are the committed baselines
// in evals/baseline/. Regenerate them whenever the baseline is re-recorded, or
// this page starts advertising a system that no longer exists.

import type {
  BudgetStatus,
  Decision,
  EvalReport,
  RunSummary,
  ScenarioListResponse,
  TraceRecord,
  TriggerResult,
} from "./types";

export const FIXTURE_RUN_ID = "trigger-quantity-mismatch-a1b2c3d4e5f6";

export const FIXTURE_TRACES: TraceRecord[] = [
  {
    run_id: FIXTURE_RUN_ID,
    node: "orchestrator",
    input_json: "{\"shipment_id\":\"SH-QTY\",\"po_id\":\"PO-1001\",\"carrier\":\"UPS\",\"tracking_number\":\"1Z-1001\",\"reported_items\":[{\"sku\":\"SKU-A\",\"quantity\":80}],\"reported_date\":\"2026-07-05T00:00:00Z\",\"docs_present\":true,\"damaged\":false}",
    output_json: "{\"subtasks\":[\"Retrieve PO-1001 details (expected SKUs, quantities, ship dates) and compare against reported_items for SH-QTY to identify quantity variances (e.g., SKU-A reported 80 units vs PO-expected quantity)\",\"Verify carrier tracking status for UPS tracking number 1Z-1001: confirm current transit status, last scan location/timestamp, and estimated/actual delivery date relative to reported_date 2026-07-05\",\"Validate shipment documentation completeness and accuracy (docs_present=true) including packing list, BOL, and ASN alignment with reported_items and PO-1001 line items\",\"Run exception detection across quantity mismatch, damage flag (damaged=false), missing/incomplete docs, carrier delay or routing anomalies, and duplicate/conflicting shipment records for SH-QTY\",\"Perform inventory reconciliation at destination facility: check on-hand/in-transit inventory for SKU-A against open demand/allocations tied to PO-1001 to assess impact of the reported 80-unit quantity\",\"Synthesize findings from PO comparison, carrier tracking, documentation check, exception detection, and inventory reconciliation into a consolidated risk/exception summary for SH-QTY\",\"Generate final accept/hold/reroute/escalate recommendation for SH-QTY with supporting rationale and confidence level based on synthesized findings\"],\"reasoning\":\"The inbound shipment SH-QTY reports only a single SKU-A line with quantity 80 against PO-1001, with no other PO context provided, so the first priority is to pull the actual PO-1001 expected quantities to detect potential under/over-shipment (the 'QTY' naming hints at a quantity-focused exception). Parallel to that, carrier tracking must be validated independently since UPS tracking data determines transit legitimacy and timing risk. Documentation validation is included because docs_present=true needs corroboration against the shipment content, not just a boolean flag. A dedicated exception detection subtask aggregates signals (quantity variance, damage=false, tracking anomalies, doc issues) to flag any risk conditions requiring hold/reroute/escalate. Inventory reconciliation checks the downstream impact of accepting the shipment as-is against current stock and open orders for SKU-A. Finally, a synthesis and decision subtask consolidates all specialist outputs into the accept/hold/reroute/escalate recommendation, ensuring traceability of the decision back to each specialist finding.\"}",
    latency_ms: 12252,
    tokens: 1544,
    cost_usd: 0.016656,
    model: "claude-sonnet-5",
    created_at: "2026-09-02T18:07:02.712302Z",
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "inventory",
    input_json: "{\"shipment_id\":\"SH-QTY\",\"po_id\":\"PO-1001\",\"carrier\":\"UPS\",\"tracking_number\":\"1Z-1001\",\"reported_items\":[{\"sku\":\"SKU-A\",\"quantity\":80}],\"reported_date\":\"2026-07-05T00:00:00Z\",\"docs_present\":true,\"damaged\":false}",
    output_json: "{\"po_matched\":false,\"discrepancies\":[{\"sku\":\"SKU-A\",\"expected\":100,\"reported\":80}],\"capacity_ok\":true,\"reasoning\":\"PO-1001 expected 100 units of SKU-A but shipment notification reported only 80 units, resulting in a quantity discrepancy of 20 units, so the PO does not fully match. The destination DC-EAST has 160 units of available capacity for SKU-A, which comfortably accommodates the reported 80 units, so capacity is sufficient.\"}",
    latency_ms: 2803,
    tokens: 1278,
    cost_usd: 0.006498,
    model: "claude-sonnet-5",
    created_at: "2026-09-02T18:07:05.523568Z",
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "carrier",
    input_json: "{\"shipment_id\":\"SH-QTY\",\"po_id\":\"PO-1001\",\"carrier\":\"UPS\",\"tracking_number\":\"1Z-1001\",\"reported_items\":[{\"sku\":\"SKU-A\",\"quantity\":80}],\"reported_date\":\"2026-07-05T00:00:00Z\",\"docs_present\":true,\"damaged\":false}",
    output_json: "{\"status\":\"in_transit\",\"eta\":\"2026-07-05T00:00:00Z\",\"delayed\":false,\"reasoning\":\"Carrier tracking for 1Z-1001 (UPS) shows shipment SH-QTY is currently in transit with an ETA of 2026-07-05T00:00:00Z, matching the reported shipment date. The carrier has not flagged any delay for this shipment, so it is expected to arrive on schedule.\"}",
    latency_ms: 2159,
    tokens: 867,
    cost_usd: 0.004365,
    model: "claude-sonnet-5",
    created_at: "2026-09-02T18:07:07.687600Z",
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "exception",
    input_json: "{\"purchase_order\": {\"po_id\": \"PO-1001\", \"supplier\": \"Acme Components\", \"expected_items\": [{\"sku\": \"SKU-A\", \"quantity\": 100}], \"expected_date\": \"2026-07-05T00:00:00Z\", \"destination_dc\": \"DC-EAST\"}, \"inventory_finding\": {\"po_matched\": false, \"discrepancies\": [{\"sku\": \"SKU-A\", \"expected\": 100, \"reported\": 80}], \"capacity_ok\": true, \"reasoning\": \"PO-1001 expected 100 units of SKU-A but shipment notification reported only 80 units, resulting in a quantity discrepancy of 20 units, so the PO does not fully match. The destination DC-EAST has 160 units of available capacity for SKU-A, which comfortably accommodates the reported 80 units, so capacity is sufficient.\"}, \"carrier_finding\": {\"status\": \"in_transit\", \"eta\": \"2026-07-05T00:00:00Z\", \"delayed\": false, \"reasoning\": \"Carrier tracking for 1Z-1001 (UPS) shows shipment SH-QTY is currently in transit with an ETA of 2026-07-05T00:00:00Z, matching the reported shipment date. The carrier has not flagged any delay for this shipment, so it is expected to arrive on schedule.\"}}",
    output_json: "{\"exceptions\":[{\"type\":\"QUANTITY_MISMATCH\",\"detail\":\"PO-1001 expected 100 units of SKU-A but shipment SH-QTY reported only 80 units, a shortfall of 20 units.\"}],\"reasoning\":\"The inventory finding confirms a discrepancy between expected (100) and reported (80) quantities for SKU-A, triggering a QUANTITY_MISMATCH exception. Capacity is sufficient (capacity_ok true), so no OVERCAPACITY exception applies. The carrier finding shows the shipment is in transit with an ETA matching the expected date and no delay flagged, so no LATE_DELIVERY exception. Documentation is present and the shipment is not marked damaged, so MISSING_DOCS and DAMAGED do not apply. The PO ID is known and matches a valid PO record, so UNKNOWN_PO does not apply.\"}",
    latency_ms: 4234,
    tokens: 1671,
    cost_usd: 0.008673,
    model: "claude-sonnet-5",
    created_at: "2026-09-02T18:07:11.927947Z",
  },
  {
    run_id: FIXTURE_RUN_ID,
    node: "synthesis",
    input_json: "{\"inventory_finding\": {\"po_matched\": false, \"discrepancies\": [{\"sku\": \"SKU-A\", \"expected\": 100, \"reported\": 80}], \"capacity_ok\": true, \"reasoning\": \"PO-1001 expected 100 units of SKU-A but shipment notification reported only 80 units, resulting in a quantity discrepancy of 20 units, so the PO does not fully match. The destination DC-EAST has 160 units of available capacity for SKU-A, which comfortably accommodates the reported 80 units, so capacity is sufficient.\"}, \"carrier_finding\": {\"status\": \"in_transit\", \"eta\": \"2026-07-05T00:00:00Z\", \"delayed\": false, \"reasoning\": \"Carrier tracking for 1Z-1001 (UPS) shows shipment SH-QTY is currently in transit with an ETA of 2026-07-05T00:00:00Z, matching the reported shipment date. The carrier has not flagged any delay for this shipment, so it is expected to arrive on schedule.\"}, \"exception_finding\": {\"exceptions\": [{\"type\": \"QUANTITY_MISMATCH\", \"detail\": \"PO-1001 expected 100 units of SKU-A but shipment SH-QTY reported only 80 units, a shortfall of 20 units.\"}], \"reasoning\": \"The inventory finding confirms a discrepancy between expected (100) and reported (80) quantities for SKU-A, triggering a QUANTITY_MISMATCH exception. Capacity is sufficient (capacity_ok true), so no OVERCAPACITY exception applies. The carrier finding shows the shipment is in transit with an ETA matching the expected date and no delay flagged, so no LATE_DELIVERY exception. Documentation is present and the shipment is not marked damaged, so MISSING_DOCS and DAMAGED do not apply. The PO ID is known and matches a valid PO record, so UNKNOWN_PO does not apply.\"}}",
    output_json: "{\"label\":\"HOLD\",\"exceptions\":[{\"type\":\"QUANTITY_MISMATCH\",\"detail\":\"PO-1001 expected 100 units of SKU-A but shipment SH-QTY reported only 80 units, a shortfall of 20 units.\"}],\"recommended_actions\":[\"Hold shipment SH-QTY at DC-EAST pending review\",\"Contact supplier to confirm reason for 20-unit shortfall on SKU-A\",\"Verify if remaining 20 units will be shipped separately or if PO quantity should be adjusted\",\"Update inventory records once discrepancy is resolved\"],\"confidence\":0.9,\"reasoning\":\"The shipment is on time, documentation is present, and the shipment is undamaged, with sufficient destination capacity. However, a confirmed QUANTITY_MISMATCH exists between the expected PO quantity (100) and the reported quantity (80) for SKU-A. Per policy, a quantity mismatch is a recoverable discrepancy requiring review before acceptance, so the shipment should be placed on HOLD rather than accepted, rerouted, or escalated.\"}",
    latency_ms: 4748,
    tokens: 2376,
    cost_usd: 0.011568,
    model: "claude-sonnet-5",
    created_at: "2026-09-02T18:07:16.680330Z",
  },
];

export const FIXTURE_DECISION: Decision = {
  label: "HOLD",
  exceptions: [
    { type: "QUANTITY_MISMATCH", detail: "PO-1001 expected 100 units of SKU-A but shipment SH-QTY reported only 80 units, a shortfall of 20 units." },
  ],
  recommended_actions: [
    "Hold shipment SH-QTY at DC-EAST pending review",
    "Contact supplier to confirm reason for 20-unit shortfall on SKU-A",
    "Verify if remaining 20 units will be shipped separately or if PO quantity should be adjusted",
    "Update inventory records once discrepancy is resolved",
  ],
  confidence: 0.9,
  reasoning: "The shipment is on time, documentation is present, and the shipment is undamaged, with sufficient destination capacity. However, a confirmed QUANTITY_MISMATCH exists between the expected PO quantity (100) and the reported quantity (80) for SKU-A. Per policy, a quantity mismatch is a recoverable discrepancy requiring review before acceptance, so the shipment should be placed on HOLD rather than accepted, rerouted, or escalated.",
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
  cost_usd: 0.04776,
};

// The committed baselines from evals/baseline/, verbatim.
export const FIXTURE_EVAL_REPORTS: EvalReport[] = [
  {
    model: "claude-sonnet-5",
    results: [
      {
        case_id: "clean-accept",
        model: "claude-sonnet-5",
        label: "ACCEPT",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "quantity-mismatch",
        model: "claude-sonnet-5",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "late-delivery",
        model: "claude-sonnet-5",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "unknown-po",
        model: "claude-sonnet-5",
        label: "ESCALATE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 5,
          composite: 1.0,
        },
      },
      {
        case_id: "missing-docs",
        model: "claude-sonnet-5",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 3,
          composite: 0.92,
        },
      },
      {
        case_id: "damaged",
        model: "claude-sonnet-5",
        label: "REROUTE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 5,
          composite: 1.0,
        },
      },
      {
        case_id: "overcapacity",
        model: "claude-sonnet-5",
        label: "REROUTE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
    ],
    label_accuracy: 1.0,
    mean_f1: 1.0,
    mean_action_coverage: 1.0,
    mean_judge: 4.1429,
    mean_composite: 0.9657,
    rubric_version: "judge-v1",
    dataset_version: "dataset-v2",
    timestamp: "2026-09-02T18:10:12.483458+00:00",
    git_sha: "2b1a0859bb25da5bc4d7013b6801cb2ed451bd38",
  },
  {
    model: "claude-opus-4-8",
    results: [
      {
        case_id: "clean-accept",
        model: "claude-opus-4-8",
        label: "ACCEPT",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 5,
          composite: 1.0,
        },
      },
      {
        case_id: "quantity-mismatch",
        model: "claude-opus-4-8",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "late-delivery",
        model: "claude-opus-4-8",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 5,
          composite: 1.0,
        },
      },
      {
        case_id: "unknown-po",
        model: "claude-opus-4-8",
        label: "ESCALATE",
        score: {
          label_correct: true,
          exception_precision: 0.5,
          exception_recall: 1.0,
          exception_f1: 0.6667,
          action_coverage: 1.0,
          judge_score: 3,
          composite: 0.82,
        },
      },
      {
        case_id: "missing-docs",
        model: "claude-opus-4-8",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 5,
          composite: 1.0,
        },
      },
      {
        case_id: "damaged",
        model: "claude-opus-4-8",
        label: "REROUTE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "overcapacity",
        model: "claude-opus-4-8",
        label: "REROUTE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
    ],
    label_accuracy: 1.0,
    mean_f1: 0.9524,
    mean_action_coverage: 1.0,
    mean_judge: 4.2857,
    mean_composite: 0.9571,
    rubric_version: "judge-v1",
    dataset_version: "dataset-v2",
    timestamp: "2026-09-02T18:06:24.311928+00:00",
    git_sha: "2b1a0859bb25da5bc4d7013b6801cb2ed451bd38",
  },
  {
    model: "claude-haiku-4-5",
    results: [
      {
        case_id: "clean-accept",
        model: "claude-haiku-4-5",
        label: "ACCEPT",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "quantity-mismatch",
        model: "claude-haiku-4-5",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "late-delivery",
        model: "claude-haiku-4-5",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 2,
          composite: 0.88,
        },
      },
      {
        case_id: "unknown-po",
        model: "claude-haiku-4-5",
        label: "ESCALATE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 5,
          composite: 1.0,
        },
      },
      {
        case_id: "missing-docs",
        model: "claude-haiku-4-5",
        label: "HOLD",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "damaged",
        model: "claude-haiku-4-5",
        label: "REROUTE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
      {
        case_id: "overcapacity",
        model: "claude-haiku-4-5",
        label: "REROUTE",
        score: {
          label_correct: true,
          exception_precision: 1.0,
          exception_recall: 1.0,
          exception_f1: 1.0,
          action_coverage: 1.0,
          judge_score: 4,
          composite: 0.96,
        },
      },
    ],
    label_accuracy: 1.0,
    mean_f1: 1.0,
    mean_action_coverage: 1.0,
    mean_judge: 3.8571,
    mean_composite: 0.9543,
    rubric_version: "judge-v1",
    dataset_version: "dataset-v2",
    timestamp: "2026-09-02T18:12:23.325202+00:00",
    git_sha: "2b1a0859bb25da5bc4d7013b6801cb2ed451bd38",
  },
];

export const FIXTURE_RUN_SUMMARIES: RunSummary[] = [
  {
    run_id: FIXTURE_RUN_ID,
    label: FIXTURE_DECISION.label,
    cost_usd: FIXTURE_TRACES.reduce((sum, t) => sum + t.cost_usd, 0),
    created_at: FIXTURE_TRACES[0].created_at,
  },
];
