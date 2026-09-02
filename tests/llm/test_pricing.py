import pytest

from logistics_agents.llm.pricing import MODEL_PRICING, cost_usd


def test_all_three_models_priced():
    assert set(MODEL_PRICING) == {"claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5"}


def test_cost_opus():
    # 1000 in * $5/1M + 500 out * $25/1M = 0.005 + 0.0125
    assert cost_usd("claude-opus-4-8", 1000, 500) == pytest.approx(0.0175)


def test_cost_haiku_zero_tokens():
    assert cost_usd("claude-haiku-4-5", 0, 0) == 0.0


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        cost_usd("gpt-4", 100, 100)
