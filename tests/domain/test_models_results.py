from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import (
    CarrierStatus,
    Decision,
    ExceptionRecord,
    InventoryState,
    TraceRecord,
)


def test_inventory_available_capacity():
    inv = InventoryState(sku="A1", dc_id="DC-EAST", on_hand=30, reserved=5, capacity=100)
    assert inv.available_capacity == 70


def test_decision_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        Decision(
            label=DecisionLabel.ACCEPT,
            exceptions=[],
            recommended_actions=[],
            confidence=1.5,
            reasoning="x",
        )


def test_decision_with_exceptions_round_trips():
    d = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="9 vs 10")],
        recommended_actions=["notify supplier"],
        confidence=0.8,
        reasoning="short by one unit",
    )
    restored = Decision.model_validate_json(d.model_dump_json())
    assert restored == d
    assert restored.exceptions[0].type is ExceptionType.QUANTITY_MISMATCH


def test_carrier_status_optional_eta():
    cs = CarrierStatus(tracking_number="1Z999", status="in_transit", eta=None, delayed=True)
    assert cs.eta is None


def test_trace_record_fields():
    tr = TraceRecord(
        run_id="RUN-1",
        node="inventory",
        input_json="{}",
        output_json="{}",
        latency_ms=120,
        tokens=350,
        cost_usd=0.0021,
        model="claude-sonnet-5",
        created_at=datetime(2026, 7, 8, tzinfo=timezone.utc),
    )
    assert tr.node == "inventory"
    assert tr.tokens == 350
