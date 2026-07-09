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
