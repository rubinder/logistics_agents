from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
    QuantityDiscrepancy,
)
from logistics_agents.domain.enums import ExceptionType
from logistics_agents.domain.models import ExceptionRecord


def test_inventory_finding_round_trips():
    f = InventoryFinding(
        po_matched=True,
        discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
        capacity_ok=True,
        reasoning="short by 10",
    )
    assert InventoryFinding.model_validate_json(f.model_dump_json()) == f


def test_carrier_finding_optional_eta_and_tz_enforced():
    ok = CarrierFinding(status="in_transit", eta=None, delayed=True, reasoning="late")
    assert ok.eta is None
    with pytest.raises(ValidationError):
        CarrierFinding(
            status="in_transit",
            eta=datetime(2026, 7, 5),  # naive — rejected by AwareDatetime
            delayed=False,
            reasoning="x",
        )


def test_exception_finding_holds_typed_exceptions():
    f = ExceptionFinding(
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="9 vs 10")],
        reasoning="mismatch",
    )
    assert f.exceptions[0].type is ExceptionType.QUANTITY_MISMATCH


def test_orchestration_plan_fields():
    p = OrchestrationPlan(subtasks=["inventory", "carrier", "exception"], reasoning="decompose")
    assert len(p.subtasks) == 3


def test_scripted_transport_returns_mapped_value(scripted_transport):
    from logistics_agents.llm.client import LLMClient

    plan = OrchestrationPlan(subtasks=["x"], reasoning="y")
    transport, calls = scripted_transport({OrchestrationPlan: plan})
    client = LLMClient(transport)
    result = client.complete_structured(
        model="claude-haiku-4-5", system="s", user="u", output_type=OrchestrationPlan
    )
    assert result.value == plan
    assert calls[0].model == "claude-haiku-4-5"
