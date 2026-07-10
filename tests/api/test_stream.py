from datetime import datetime, timezone

from logistics_agents.data import repository
from logistics_agents.domain.models import TraceRecord


def _seed_traces(conn, run_id, nodes):
    for i, node in enumerate(nodes):
        repository.insert_trace(conn, TraceRecord(
            run_id=run_id, node=node, input_json="{}", output_json='{"ok": true}',
            latency_ms=i, tokens=1, cost_usd=0.0, model="claude-sonnet-5",
            created_at=datetime(2026, 7, 9, 12, i, tzinfo=timezone.utc),
        ))


def test_stream_emits_a_frame_per_node_then_done(api_client, postgres_conn):
    _seed_traces(postgres_conn, "RUN-S", ["orchestrator", "inventory", "synthesis"])
    with api_client.stream("GET", "/runs/RUN-S/stream") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(chunk for chunk in r.iter_text())
    assert "event: orchestrator" in body
    assert "event: inventory" in body
    assert "event: synthesis" in body
    assert "event: done" in body
    # Trace payload is present.
    assert "ok" in body and "true" in body
