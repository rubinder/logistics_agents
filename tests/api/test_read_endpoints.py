from datetime import datetime, timezone

from logistics_agents.data import repository
from logistics_agents.domain.enums import DecisionLabel
from logistics_agents.domain.models import Decision, TraceRecord


def _seed_run(conn, run_id):
    tr = TraceRecord(
        run_id=run_id, node="orchestrator", input_json="{}", output_json="{}",
        latency_ms=10, tokens=5, cost_usd=0.001, model="claude-sonnet-5",
        created_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    repository.insert_trace(conn, tr)
    repository.insert_decision(
        conn, run_id, "SH-1",
        Decision(label=DecisionLabel.ACCEPT, exceptions=[], recommended_actions=[], confidence=1.0, reasoning="ok"),
    )


def test_list_runs_and_trace_and_decision(api_client, postgres_conn):
    _seed_run(postgres_conn, "RUN-A")

    runs = api_client.get("/runs").json()
    assert "RUN-A" in runs["run_ids"]

    trace = api_client.get("/runs/RUN-A/trace").json()
    assert len(trace) == 1
    assert trace[0]["node"] == "orchestrator"

    decision = api_client.get("/runs/RUN-A/decision").json()
    assert decision["label"] == "ACCEPT"


def test_missing_decision_is_404(api_client):
    assert api_client.get("/runs/NOPE/decision").status_code == 404
