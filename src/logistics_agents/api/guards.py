from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from logistics_agents.data import repository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class BudgetStatus(BaseModel):
    cap_usd: float
    spent_usd: float
    remaining_usd: float


def budget_status(conn, cap_usd: float, clock=_utc_now) -> BudgetStatus:
    spent = repository.total_spend_usd(conn, since=_month_start(clock()))
    return BudgetStatus(cap_usd=cap_usd, spent_usd=spent, remaining_usd=cap_usd - spent)


def budget_allows(conn, cap_usd: float, clock=_utc_now) -> bool:
    return budget_status(conn, cap_usd, clock).remaining_usd > 0


def rate_allows(
    conn, client_ip: str, per_ip_daily: int, global_daily: int, clock=_utc_now
) -> bool:
    since = clock() - timedelta(days=1)
    per_ip = repository.count_entries(conn, source=f"trigger:{client_ip}", since=since)
    total = repository.count_entries(conn, source_prefix="trigger:", since=since)
    return per_ip < per_ip_daily and total < global_daily
