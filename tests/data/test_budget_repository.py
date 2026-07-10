from datetime import datetime, timedelta, timezone

from logistics_agents.data import repository


def test_total_spend_sums_costs(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.01, "scheduled")
    repository.insert_budget_entry(postgres_conn, "R2", 0.02, "trigger:1.2.3.4")
    assert repository.total_spend_usd(postgres_conn) == 0.03


def test_total_spend_empty_is_zero(postgres_conn):
    assert repository.total_spend_usd(postgres_conn) == 0.0


def test_count_entries_by_source_and_prefix(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.01, "trigger:1.1.1.1")
    repository.insert_budget_entry(postgres_conn, "R2", 0.01, "trigger:1.1.1.1")
    repository.insert_budget_entry(postgres_conn, "R3", 0.01, "trigger:2.2.2.2")
    repository.insert_budget_entry(postgres_conn, "R4", 0.01, "scheduled")
    assert repository.count_entries(postgres_conn, source="trigger:1.1.1.1") == 2
    assert repository.count_entries(postgres_conn, source_prefix="trigger:") == 3
    assert repository.count_entries(postgres_conn) == 4


def test_count_entries_since(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.01, "scheduled")
    future = datetime.now(timezone.utc) + timedelta(days=1)
    assert repository.count_entries(postgres_conn, since=future) == 0
