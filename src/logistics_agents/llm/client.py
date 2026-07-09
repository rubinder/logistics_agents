import time

from pydantic import BaseModel

from logistics_agents.llm.pricing import cost_usd
from logistics_agents.llm.types import CallMeta, LLMRequest, StructuredResult, Transport


class LLMClient:
    def __init__(self, transport: Transport):
        self._transport = transport

    def complete_structured(
        self,
        model: str,
        system: str,
        user: str,
        output_type: type[BaseModel],
    ) -> StructuredResult:
        request = LLMRequest(model=model, system=system, user=user, output_type=output_type)

        start = time.perf_counter()
        raw = self._transport(request)
        latency_ms = int((time.perf_counter() - start) * 1000)

        value = output_type.model_validate_json(raw.output_json)
        meta = CallMeta(
            model=raw.model,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            cost_usd=cost_usd(raw.model, raw.input_tokens, raw.output_tokens),
            latency_ms=latency_ms,
        )
        return StructuredResult(value=value, meta=meta)
