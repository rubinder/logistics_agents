from datetime import datetime, timezone

from pydantic import BaseModel

from logistics_agents.data import repository
from logistics_agents.domain.models import TraceRecord
from logistics_agents.llm.types import CallMeta


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tracer:
    def __init__(self, run_id: str, conn=None, clock=_utc_now):
        self.run_id = run_id
        self._conn = conn
        self._clock = clock
        self.records: list[TraceRecord] = []

    def record(self, node: str, input_obj: BaseModel, output_obj: BaseModel, meta: CallMeta) -> TraceRecord:
        trace = TraceRecord(
            run_id=self.run_id,
            node=node,
            input_json=input_obj.model_dump_json(),
            output_json=output_obj.model_dump_json(),
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
