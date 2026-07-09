from datetime import datetime, timezone

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
    QuantityDiscrepancy,
)
from logistics_agents.data import repository, seed
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord, LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.orchestration import runner
from logistics_agents.tracing.tracer import Tracer

FIXED = datetime(2026, 7, 9, tzinfo=timezone.utc)


def _asn():
    return ShipmentNotification(
        shipment_id="SH-99", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=90)],
        reported_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        docs_present=True, damaged=False,
    )


def _full_script():
    decision = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="90 vs 100")],
        recommended_actions=["notify supplier"], confidence=0.8, reasoning="hold",
    )
    return {
        OrchestrationPlan: OrchestrationPlan(subtasks=["inventory", "carrier", "exception"], reasoning="d"),
        InventoryFinding: InventoryFinding(
            po_matched=True,
            discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
            capacity_ok=True, reasoning="short",
        ),
        CarrierFinding: CarrierFinding(status="in_transit", eta=None, delayed=False, reasoning="ok"),
        ExceptionFinding: ExceptionFinding(exceptions=decision.exceptions, reasoning="qty"),
        Decision: decision,
    }, decision


def test_pipeline_returns_decision_persists_it_and_traces_five_nodes(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)
    script, expected = _full_script()
    transport, calls = scripted_transport(script)
    llm = LLMClient(transport)
    tracer = Tracer(run_id="RUN-99", conn=postgres_conn, clock=lambda: FIXED)

    result = runner.run_pipeline(
        _asn(), postgres_conn, llm, model="claude-opus-4-8", run_id="RUN-99", tracer=tracer
    )

    # Returns and persists the synthesized decision.
    assert result == expected
    assert repository.get_decision(postgres_conn, "RUN-99") == expected

    # One trace per node, in DAG order.
    nodes = [tr.node for tr in tracer.records]
    assert nodes == ["orchestrator", "inventory", "carrier", "exception", "synthesis"]

    by_node = {tr.node: tr for tr in tracer.records}
    # Exception node's trace input reflects the peer findings it reasoned over.
    assert "SKU-A" in by_node["exception"].input_json        # inventory discrepancy
    assert "in_transit" in by_node["exception"].input_json   # carrier status
    # Synthesis node's trace input includes the exception finding.
    assert "QUANTITY_MISMATCH" in by_node["synthesis"].input_json

    # All five agents ran against the requested model, and traces were persisted.
    assert all(c.model == "claude-opus-4-8" for c in calls)
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM runs WHERE run_id = %s", ("RUN-99",))
        assert cur.fetchone()[0] == 5
