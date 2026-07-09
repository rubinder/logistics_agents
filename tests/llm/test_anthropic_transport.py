import os
import types as _types

import pytest
from pydantic import BaseModel

from logistics_agents.llm.anthropic_transport import AnthropicTransport
from logistics_agents.llm.types import LLMRequest, RawResponse


class Sentiment(BaseModel):
    label: str
    score: float


def test_transport_maps_parse_response_to_raw_response():
    """Unit test with a stub SDK client — no network, no key. Verifies the
    transport calls messages.parse correctly and maps the result."""
    captured = {}

    def fake_parse(**kwargs):
        captured.update(kwargs)
        usage = _types.SimpleNamespace(input_tokens=123, output_tokens=45)
        parsed = Sentiment(label="neutral", score=0.5)
        return _types.SimpleNamespace(parsed_output=parsed, usage=usage)

    stub_client = _types.SimpleNamespace(
        messages=_types.SimpleNamespace(parse=fake_parse)
    )
    transport = AnthropicTransport(client=stub_client, max_tokens=256)
    req = LLMRequest(model="claude-haiku-4-5", system="sys", user="hi", output_type=Sentiment)

    raw = transport(req)

    assert isinstance(raw, RawResponse)
    assert raw.input_tokens == 123
    assert raw.output_tokens == 45
    assert raw.model == "claude-haiku-4-5"
    assert Sentiment.model_validate_json(raw.output_json) == Sentiment(label="neutral", score=0.5)
    # Verify the SDK was driven correctly.
    assert captured["model"] == "claude-haiku-4-5"
    assert captured["max_tokens"] == 256
    assert captured["system"] == "sys"
    assert captured["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["output_format"] is Sentiment


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live Anthropic call requires ANTHROPIC_API_KEY",
)
def test_live_call_returns_validated_model():
    transport = AnthropicTransport(max_tokens=256)
    req = LLMRequest(
        model="claude-haiku-4-5",
        system="You classify sentiment. Respond only via the structured schema.",
        user="I love this product!",
        output_type=Sentiment,
    )
    raw = transport(req)
    value = Sentiment.model_validate_json(raw.output_json)
    assert value.label
    assert raw.input_tokens > 0
