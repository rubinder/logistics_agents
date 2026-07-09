import json

import pytest
from pydantic import BaseModel

from logistics_agents.llm.types import LLMRequest, RawResponse


class Sentiment(BaseModel):
    label: str
    score: float


@pytest.fixture
def sentiment_type():
    return Sentiment


@pytest.fixture
def make_request(sentiment_type):
    def _make(model="claude-haiku-4-5", system="sys", user="hello"):
        return LLMRequest(model=model, system=system, user=user, output_type=sentiment_type)

    return _make


@pytest.fixture
def fake_transport_factory(sentiment_type):
    """Returns (transport, calls) where transport yields a canned RawResponse and
    records every request it received in `calls`."""

    def _factory(label="positive", score=0.9, input_tokens=100, output_tokens=20):
        calls = []

        def transport(request):
            calls.append(request)
            payload = sentiment_type(label=label, score=score)
            return RawResponse(
                output_json=payload.model_dump_json(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=request.model,
            )

        return transport, calls

    return _factory
