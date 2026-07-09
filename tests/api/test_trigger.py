from logistics_agents.data import repository


def test_trigger_runs_pipeline_and_records_spend(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)

    r = api_client.post("/runs", json={"scenario_id": "clean"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["label"] in {"ACCEPT", "HOLD", "REROUTE", "ESCALATE"}
    run_id = body["run_id"]

    # Traces + decision were persisted, and spend recorded under a trigger: source.
    assert repository.get_decision(postgres_conn, run_id) is not None
    assert repository.count_entries(postgres_conn, source_prefix="trigger:") == 1


def test_trigger_unknown_scenario_400(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)
    assert api_client.post("/runs", json={"scenario_id": "nope"}).status_code == 400


def test_trigger_rate_limited_429(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)
    # test settings: per_ip_daily=2 → third trigger from the same client is blocked
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 200
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 200
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 429


def test_trigger_budget_exhausted_402(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)
    # Exhaust the $1.0 test cap directly, then a trigger is rejected.
    repository.insert_budget_entry(postgres_conn, "PRIOR", 1.0, "scheduled")
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 402


def test_trigger_records_spend_even_when_pipeline_raises(postgres_conn):
    from fastapi.testclient import TestClient

    from logistics_agents.agents.contracts import (
        CarrierFinding,
        InventoryFinding,
        OrchestrationPlan,
    )
    from logistics_agents.api.app import create_app
    from logistics_agents.api.deps import Settings, get_conn, get_llm, get_settings
    from logistics_agents.data import repository, seed
    from logistics_agents.llm.client import LLMClient
    from logistics_agents.llm.types import RawResponse

    seed.load_seed(postgres_conn)

    # Transport that succeeds for the first two nodes (recording cost) then raises at carrier.
    ok = {
        OrchestrationPlan: OrchestrationPlan(subtasks=["x"], reasoning="d"),
        InventoryFinding: InventoryFinding(po_matched=True, discrepancies=[], capacity_ok=True, reasoning="i"),
    }

    def raising_transport(request):
        if request.output_type is CarrierFinding:
            raise RuntimeError("boom")
        value = ok[request.output_type]
        return RawResponse(
            output_json=value.model_dump_json(), input_tokens=10, output_tokens=5, model=request.model
        )

    app = create_app()
    app.dependency_overrides[get_conn] = lambda: postgres_conn
    app.dependency_overrides[get_llm] = lambda: LLMClient(raising_transport)
    app.dependency_overrides[get_settings] = lambda: Settings(
        budget_cap_usd=1.0, per_ip_daily=5, global_daily=50
    )
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/runs", json={"scenario_id": "clean"})
    assert r.status_code == 500
    # Spend from the orchestrator + inventory nodes was still debited to the ledger.
    assert repository.count_entries(postgres_conn, source_prefix="trigger:") == 1
    assert repository.total_spend_usd(postgres_conn) > 0
