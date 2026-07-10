import os

from logistics_agents.api.deps import get_settings


def test_get_settings_honors_env_override():
    os.environ["LOGISTICS_BUDGET_CAP_USD"] = "3.5"
    try:
        settings = get_settings()
        assert settings.budget_cap_usd == 3.5
    finally:
        del os.environ["LOGISTICS_BUDGET_CAP_USD"]
