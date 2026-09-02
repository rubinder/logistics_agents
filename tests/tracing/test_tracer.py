from datetime import datetime, timezone

from logistics_agents.agents.contracts import OrchestrationPlan
from logistics_agents.llm.types import CallMeta
from logistics_agents.tracing.tracer import Tracer

FIXED = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def _meta():
    return CallMeta(model="claude-sonnet-5", input_tokens=100, output_tokens=40, cost_usd=0.0015, latency_ms=250)


def test_record_builds_trace_with_summed_tokens():
    tracer = Tracer(run_id="RUN-T", clock=lambda: FIXED)
    inp = OrchestrationPlan(subtasks=["a"], reasoning="in")
    out = OrchestrationPlan(subtasks=["b"], reasoning="out")
    tr = tracer.record("orchestrator", inp, out, _meta())
    assert tr.run_id == "RUN-T"
    assert tr.node == "orchestrator"
    assert tr.tokens == 140  # 100 + 40
    assert tr.cost_usd == 0.0015
    assert tr.created_at == FIXED
    assert '"reasoning":"out"' in tr.output_json.replace(" ", "")
    assert len(tracer.records) == 1


def test_record_persists_when_conn_present(postgres_conn):

    tracer = Tracer(run_id="RUN-P", conn=postgres_conn, clock=lambda: FIXED)
    plan = OrchestrationPlan(subtasks=["a"], reasoning="x")
    tracer.record("orchestrator", plan, plan, _meta())
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT node, tokens FROM runs WHERE run_id = %s", ("RUN-P",))
        assert cur.fetchone() == ("orchestrator", 140)


def test_record_serializes_dict_input_with_models():
    from logistics_agents.agents.contracts import CarrierFinding

    tracer = Tracer(run_id="RUN-D", clock=lambda: FIXED)
    car = CarrierFinding(status="delayed", eta=None, delayed=True, reasoning="late")
    out = OrchestrationPlan(subtasks=["x"], reasoning="o")
    tr = tracer.record("exception", {"carrier_finding": car}, out, _meta())
    assert "delayed" in tr.input_json
    assert "carrier_finding" in tr.input_json
