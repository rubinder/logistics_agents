# USD per 1,000,000 tokens: (input_per_mtok, output_per_mtok).
# Sonnet 5 has intro pricing ($2/$10 through 2026-08-31); we use standard rates.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model for pricing: {model!r}")
    input_rate, output_rate = MODEL_PRICING[model]
    return input_tokens / 1_000_000 * input_rate + output_tokens / 1_000_000 * output_rate
