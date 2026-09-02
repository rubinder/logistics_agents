import json
from datetime import datetime, timezone

from pydantic import BaseModel

from logistics_agents.data import repository
from logistics_agents.domain.models import TraceRecord
from logistics_agents.llm.types import CallMeta


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_json(obj) -> str:
    if isinstance(obj, BaseModel):
        return obj.model_dump_json()
    if isinstance(obj, dict):
        materialized = {
            k: (v.model_dump(mode="json") if isinstance(v, BaseModel) else v)
            for k, v in obj.items()
        }
        return json.dumps(materialized, default=str)
    return json.dumps(obj, default=str)


class Tracer:
    def __init__(self, run_id: str, conn=None, clock=_utc_now):
        self.run_id = run_id
        self._conn = conn
        self._clock = clock
        self.records: list[TraceRecord] = []

    def record(self, node: str, input_obj: object, output_obj: object, meta: CallMeta) -> TraceRecord:
        trace = TraceRecord(
            run_id=self.run_id,
            node=node,
            input_json=_to_json(input_obj),
            output_json=_to_json(output_obj),
            latency_ms=meta.latency_ms,
            tokens=meta.input_tokens + meta.output_tokens,
            cost_usd=meta.cost_usd,
            model=meta.model,
            created_at=self._clock(),
        )
        self.records.append(trace)
        if self._conn is not None:
            repository.insert_trace(self._conn, trace)
        return trace
