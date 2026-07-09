import os

import pytest

from evals.run import build_client, run_comparison


def test_build_client_returns_llm_client(tmp_path):
    from logistics_agents.llm.client import LLMClient

    client = build_client(mode="replay", fixtures_dir=tmp_path)
    assert isinstance(client, LLMClient)


def test_run_comparison_scores_each_model_with_scripted_clients(postgres_conn, scripted_transport, tmp_path):
    # Inject scripted clients directly (bypass the Anthropic transport) to keep this key-free.
    from logistics_agents.agents.contracts import (
        CarrierFinding, ExceptionFinding, InventoryFinding, OrchestrationPlan,
    )
    from logistics_agents.domain.enums import DecisionLabel
    from logistics_agents.domain.models import Decision
    from logistics_agents.llm.client import LLMClient
    from logistics_agents.data import seed
    from evals.dataset import CASES

    seed.load_seed(postgres_conn)
    clean = next(c for c in CASES if c.case_id == "clean-accept")
    script = {
        OrchestrationPlan: OrchestrationPlan(subtasks=["x"], reasoning="d"),
        InventoryFinding: InventoryFinding(po_matched=True, discrepancies=[], capacity_ok=True, reasoning="i"),
        CarrierFinding: CarrierFinding(status="in_transit", eta=None, delayed=False, reasoning="c"),
        ExceptionFinding: ExceptionFinding(exceptions=[], reasoning="e"),
        Decision: Decision(label=DecisionLabel.ACCEPT, exceptions=[], recommended_actions=[], confidence=0.9, reasoning="r"),
    }
    transport, _ = scripted_transport(script)

    reports = run_comparison(
        models=["claude-sonnet-5", "claude-haiku-4-5"],
        cases=[clean],
        conn=postgres_conn,
        out_dir=tmp_path,
        client_factory=lambda model: LLMClient(transport),  # test hook
        judge_llm=None,
    )
    assert {r.model for r in reports} == {"claude-sonnet-5", "claude-haiku-4-5"}
    assert (tmp_path / "claude-sonnet-5.json").exists()
    assert all(r.label_accuracy == 1.0 for r in reports)


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="live comparison needs ANTHROPIC_API_KEY")
def test_live_smoke_single_case(postgres_conn):
    # Records fixtures + does one real call per node for one case on the cheapest model.
    from logistics_agents.data import seed
    from evals.dataset import CASES
    import tempfile

    seed.load_seed(postgres_conn)
    clean = next(c for c in CASES if c.case_id == "clean-accept")
    with tempfile.TemporaryDirectory() as d:
        reports = run_comparison(
            models=["claude-haiku-4-5"], cases=[clean], conn=postgres_conn,
            out_dir=d, mode="live", fixtures_dir=d, judge_llm=None,
        )
    assert reports[0].results[0].label in {"ACCEPT", "HOLD", "REROUTE", "ESCALATE"}
