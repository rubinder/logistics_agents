from logistics_agents.llm.client import LLMClient


def test_complete_structured_returns_validated_value_and_meta(fake_transport_factory, sentiment_type):
    transport, calls = fake_transport_factory(label="positive", score=0.9, input_tokens=1000, output_tokens=500)
    client = LLMClient(transport)

    result = client.complete_structured(
        model="claude-opus-4-8", system="sys", user="rate this", output_type=sentiment_type
    )

    assert isinstance(result.value, sentiment_type)
    assert result.value.label == "positive"
    assert result.value.score == 0.9
    assert result.meta.model == "claude-opus-4-8"
    assert result.meta.input_tokens == 1000
    assert result.meta.output_tokens == 500
    assert result.meta.cost_usd == 0.0175  # 1000*$5/1M + 500*$25/1M
    assert result.meta.latency_ms >= 0
    # The request forwarded to the transport used the requested model.
    assert calls[0].model == "claude-opus-4-8"


def test_complete_structured_forwards_prompt(fake_transport_factory, sentiment_type):
    transport, calls = fake_transport_factory()
    client = LLMClient(transport)
    client.complete_structured(
        model="claude-haiku-4-5", system="be terse", user="ping", output_type=sentiment_type
    )
    assert calls[0].system == "be terse"
    assert calls[0].user == "ping"
    assert calls[0].output_type is sentiment_type
