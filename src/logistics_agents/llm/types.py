import json
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class LLMRequest:
    model: str
    system: str
    user: str
    output_type: type[BaseModel]
    max_tokens: int = 4096

    def schema_fingerprint(self) -> str:
        schema = json.dumps(self.output_type.model_json_schema(), sort_keys=True)
        return f"{self.output_type.__name__}:{schema}"


class RawResponse(BaseModel):
    output_json: str
    input_tokens: int
    output_tokens: int
    model: str
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class CallMeta(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class StructuredResult:
    value: BaseModel
    meta: CallMeta


class Transport(Protocol):
    def __call__(self, request: LLMRequest) -> RawResponse: ...
