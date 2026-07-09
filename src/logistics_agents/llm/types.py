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

    def schema_fingerprint(self) -> str:
        schema = json.dumps(self.output_type.model_json_schema(), sort_keys=True)
        return f"{self.output_type.__name__}:{schema}"


class RawResponse(BaseModel):
    output_json: str
    input_tokens: int
    output_tokens: int
    model: str


class CallMeta(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


@dataclass
class StructuredResult:
    value: BaseModel
    meta: CallMeta


class Transport(Protocol):
    def __call__(self, request: LLMRequest) -> RawResponse: ...
