from logistics_agents.data import repository


def test_budget_endpoint_reflects_spend(api_client, postgres_conn):
    before = api_client.get("/budget").json()
    assert before["cap_usd"] == 1.0  # test settings cap
    assert before["spent_usd"] == 0.0
    assert before["remaining_usd"] == 1.0

    repository.insert_budget_entry(postgres_conn, "R1", 0.25, "scheduled")
    after = api_client.get("/budget").json()
    assert after["spent_usd"] == 0.25
    assert after["remaining_usd"] == 0.75
