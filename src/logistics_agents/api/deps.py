import os

import psycopg
from pydantic import BaseModel

from logistics_agents.llm.client import LLMClient


class Settings(BaseModel):
    budget_cap_usd: float = 20.0
    per_ip_daily: int = 5
    global_daily: int = 50
    trigger_model: str = "claude-haiku-4-5"


def get_settings() -> Settings:
    defaults = Settings()
    return Settings(
        budget_cap_usd=float(os.environ.get("LOGISTICS_BUDGET_CAP_USD", defaults.budget_cap_usd)),
        per_ip_daily=int(os.environ.get("LOGISTICS_PER_IP_DAILY", defaults.per_ip_daily)),
        global_daily=int(os.environ.get("LOGISTICS_GLOBAL_DAILY", defaults.global_daily)),
        trigger_model=os.environ.get("LOGISTICS_TRIGGER_MODEL", defaults.trigger_model),
    )


def get_conn():
    dsn = os.environ.get(
        "LOGISTICS_DATABASE_URL", "postgresql://logistics:logistics@localhost:5432/logistics"
    )
    conn = psycopg.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()


def get_llm() -> LLMClient:  # pragma: no cover - overridden in tests; live wiring in run/deploy
    from logistics_agents.llm.anthropic_transport import AnthropicTransport

    return LLMClient(AnthropicTransport())
