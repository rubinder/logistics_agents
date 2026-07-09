import pytest
from pydantic import BaseModel

from logistics_agents.llm.types import RawResponse


@pytest.fixture
def scripted_transport():
    """Factory: scripted_transport({OutputType: canned_value, ...}) -> (transport, calls).
    The transport returns the canned value for the request's output_type, echoing the model."""

    def _factory(mapping: dict[type, BaseModel], input_tokens: int = 10, output_tokens: int = 5):
        calls = []

        def transport(request):
            calls.append(request)
            if request.output_type not in mapping:
                raise AssertionError(f"no scripted value for {request.output_type!r}")
            value = mapping[request.output_type]
            return RawResponse(
                output_json=value.model_dump_json(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=request.model,
            )

        return transport, calls

    return _factory
