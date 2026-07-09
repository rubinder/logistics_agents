from datetime import datetime, timezone

from logistics_agents.agents import exception, orchestrator, synthesis
from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
    QuantityDiscrepancy,
)
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord, LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient


def _asn():
    return ShipmentNotification(
        shipment_id="SH-3", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=90)],
        reported_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        docs_present=True, damaged=False,
    )


INV = InventoryFinding(
    po_matched=True,
    discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
    capacity_ok=True, reasoning="short",
)
CAR = CarrierFinding(status="delayed", eta=None, delayed=True, reasoning="late")


def test_orchestrator_returns_plan(scripted_transport):
    plan = OrchestrationPlan(subtasks=["inventory", "carrier", "exception"], reasoning="decompose")
    transport, calls = scripted_transport({OrchestrationPlan: plan})
    result = orchestrator.plan(_asn(), LLMClient(transport), model="claude-opus-4-8")
    assert result.value == plan
    assert "SH-3" in calls[0].user


def test_exception_agent_reasons_over_peer_findings(scripted_transport):
    finding = ExceptionFinding(
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="90 vs 100")],
        reasoning="qty + delay",
    )
    transport, calls = scripted_transport({ExceptionFinding: finding})
    result = exception.detect(_asn(), None, INV, CAR, LLMClient(transport), model="claude-sonnet-5")
    assert result.value == finding
    # Peer findings must be present in the prompt.
    assert "delayed" in calls[0].user
    assert "SKU-A" in calls[0].user


def test_synthesis_returns_decision(scripted_transport):
    decision = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="90 vs 100")],
        recommended_actions=["notify supplier"], confidence=0.8, reasoning="hold for review",
    )
    exc = ExceptionFinding(exceptions=decision.exceptions, reasoning="x")
    transport, calls = scripted_transport({Decision: decision})
    result = synthesis.decide(_asn(), INV, CAR, exc, LLMClient(transport), model="claude-opus-4-8")
    assert result.value == decision
    assert calls[0].output_type is Decision
