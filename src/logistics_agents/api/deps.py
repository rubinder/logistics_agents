import os

import psycopg
from pydantic import BaseModel

from logistics_agents.llm.client import LLMClient


class Settings(BaseModel):
    budget_cap_usd: float = 20.0
    per_ip_daily: int = 5
    global_daily: int = 50


def get_settings() -> Settings:
    return Settings()


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
