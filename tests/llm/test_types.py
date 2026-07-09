from logistics_agents.llm.types import CallMeta, RawResponse


def test_raw_response_round_trips():
    r = RawResponse(output_json='{"label": "x", "score": 1.0}', input_tokens=5, output_tokens=3, model="claude-haiku-4-5")
    assert RawResponse.model_validate_json(r.model_dump_json()) == r


def test_request_fingerprint_stable_and_type_sensitive(make_request):
    a = make_request()
    b = make_request()
    assert a.schema_fingerprint() == b.schema_fingerprint()
    assert "Sentiment" in a.schema_fingerprint()

    from pydantic import BaseModel

    class Other(BaseModel):
        text: str

    from logistics_agents.llm.types import LLMRequest

    other = LLMRequest(model=a.model, system=a.system, user=a.user, output_type=Other)
    assert other.schema_fingerprint() != a.schema_fingerprint()


def test_call_meta_fields():
    m = CallMeta(model="claude-opus-4-8", input_tokens=10, output_tokens=5, cost_usd=0.0, latency_ms=42)
    assert m.latency_ms == 42
