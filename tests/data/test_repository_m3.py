from datetime import datetime, timezone

from logistics_agents.data import repository, seed
from logistics_agents.domain.models import TraceRecord


def test_carrier_event_latest_wins(postgres_conn):
    tn = "1Z-TEST"
    repository.insert_carrier_event(
        postgres_conn, tn, "picked_up", "in_transit",
        datetime(2026, 7, 8, tzinfo=timezone.utc), False,
        datetime(2026, 7, 4, tzinfo=timezone.utc),
    )
    repository.insert_carrier_event(
        postgres_conn, tn, "delayed", "delayed",
        datetime(2026, 7, 10, tzinfo=timezone.utc), True,
        datetime(2026, 7, 6, tzinfo=timezone.utc),
    )
    status = repository.get_latest_carrier_event(postgres_conn, tn)
    assert status.status == "delayed"
    assert status.delayed is True


def test_get_latest_carrier_event_missing_returns_none(postgres_conn):
    assert repository.get_latest_carrier_event(postgres_conn, "NOPE") is None


def test_insert_trace_round_trip(postgres_conn):
    tr = TraceRecord(
        run_id="RUN-9", node="inventory", input_json="{}", output_json="{}",
        latency_ms=12, tokens=30, cost_usd=0.001, model="claude-sonnet-5",
        created_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    repository.insert_trace(postgres_conn, tr)
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT node, tokens, model FROM runs WHERE run_id = %s", ("RUN-9",))
        row = cur.fetchone()
    assert row == ("inventory", 30, "claude-sonnet-5")


def test_seed_loads_carrier_events(postgres_conn):
    seed.load_seed(postgres_conn)
    from logistics_agents.data.seed_data import SEED_CARRIER_EVENTS
    tn = SEED_CARRIER_EVENTS[0]["tracking_number"]
    assert repository.get_latest_carrier_event(postgres_conn, tn) is not None
