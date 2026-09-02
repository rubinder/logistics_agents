# USD per 1,000,000 tokens: (input_per_mtok, output_per_mtok).
# Rates as published by Anthropic. Sonnet 5 is $2/$10: an earlier note here assumed
# that was introductory pricing reverting to $3/$15 after 2026-08-31, which it did not.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model for pricing: {model!r}")
    input_rate, output_rate = MODEL_PRICING[model]
    return input_tokens / 1_000_000 * input_rate + output_tokens / 1_000_000 * output_rate
