from datetime import datetime, timezone

from logistics_agents.api import guards
from logistics_agents.data import repository


def CLOCK():
    return datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def test_budget_status_and_allows(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.40, "scheduled")
    status = guards.budget_status(postgres_conn, cap_usd=1.0, clock=CLOCK)
    assert status.spent_usd == 0.40
    assert status.remaining_usd == 0.60
    assert guards.budget_allows(postgres_conn, cap_usd=1.0, clock=CLOCK) is True
    assert guards.budget_allows(postgres_conn, cap_usd=0.40, clock=CLOCK) is False


def test_rate_allows_per_ip_and_global(postgres_conn):
    ip = "9.9.9.9"
    # Under both caps initially.
    assert guards.rate_allows(postgres_conn, ip, per_ip_daily=2, global_daily=5, clock=CLOCK) is True
    repository.insert_budget_entry(postgres_conn, "R1", 0.0, f"trigger:{ip}")
    repository.insert_budget_entry(postgres_conn, "R2", 0.0, f"trigger:{ip}")
    # Per-IP cap (2) now reached.
    assert guards.rate_allows(postgres_conn, ip, per_ip_daily=2, global_daily=5, clock=CLOCK) is False
    # A different IP still allowed under the global cap.
    assert guards.rate_allows(postgres_conn, "8.8.8.8", per_ip_daily=2, global_daily=5, clock=CLOCK) is True


def test_rate_global_cap(postgres_conn):
    for i in range(3):
        repository.insert_budget_entry(postgres_conn, f"R{i}", 0.0, f"trigger:1.1.1.{i}")
    # global cap of 3 reached regardless of per-ip
    assert guards.rate_allows(postgres_conn, "5.5.5.5", per_ip_daily=10, global_daily=3, clock=CLOCK) is False
