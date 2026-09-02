from datetime import datetime, timezone

from logistics_agents.data import repository
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import (
    Decision,
    ExceptionRecord,
    InventoryState,
    LineItem,
    PurchaseOrder,
)


def test_purchase_order_round_trip(postgres_conn):
    po = PurchaseOrder(
        po_id="PO-1",
        supplier="Acme",
        expected_items=[LineItem(sku="A1", quantity=10)],
        expected_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        destination_dc="DC-EAST",
    )
    repository.upsert_purchase_order(postgres_conn, po)
    assert repository.get_purchase_order(postgres_conn, "PO-1") == po


def test_get_missing_purchase_order_returns_none(postgres_conn):
    assert repository.get_purchase_order(postgres_conn, "NOPE") is None


def test_inventory_round_trip(postgres_conn):
    inv = InventoryState(sku="A1", dc_id="DC-EAST", on_hand=30, reserved=5, capacity=100)
    repository.upsert_inventory(postgres_conn, inv)
    fetched = repository.get_inventory(postgres_conn, "A1", "DC-EAST")
    assert fetched.on_hand == 30
    assert fetched.available_capacity == 70


def test_decision_round_trip(postgres_conn):
    decision = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="9 vs 10")],
        recommended_actions=["notify supplier"],
        confidence=0.8,
        reasoning="short by one",
    )
    repository.insert_decision(postgres_conn, "RUN-1", "SH-1", decision)
    assert repository.get_decision(postgres_conn, "RUN-1") == decision


def test_decision_isolation_allows_reused_run_id(postgres_conn):
    # RUN-1 is also used by test_decision_round_trip. Writing it again replaces
    # the row rather than raising, so re-running an eval over the same run_ids is
    # idempotent. Note this no longer doubles as proof that the fixture clears
    # committed rows between tests -- the upsert would mask a leak.
    decision = Decision(
        label=DecisionLabel.ACCEPT,
        exceptions=[],
        recommended_actions=[],
        confidence=1.0,
        reasoning="clean",
    )
    repository.insert_decision(postgres_conn, "RUN-1", "SH-2", decision)
    assert repository.get_decision(postgres_conn, "RUN-1") == decision


def test_insert_trace_is_idempotent(postgres_conn):
    """Re-recording an eval writes the same (run_id, node) keys again.

    Without an upsert the second run dies on runs_pkey partway through, leaving
    the database holding a torn mix of two runs.
    """
    from logistics_agents.domain.models import TraceRecord

    def _trace(latency: int) -> TraceRecord:
        return TraceRecord(
            run_id="RUN-T", node="synthesis", input_json="{}", output_json="{}",
            latency_ms=latency, tokens=10, cost_usd=0.001, model="claude-haiku-4-5",
            created_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
        )

    repository.insert_trace(postgres_conn, _trace(100))
    repository.insert_trace(postgres_conn, _trace(250))

    with postgres_conn.cursor() as cur:
        cur.execute("SELECT latency_ms FROM runs WHERE run_id = %s AND node = %s",
                    ("RUN-T", "synthesis"))
        rows = cur.fetchall()
    assert rows == [(250,)], "second write must replace the first, not duplicate or fail"
