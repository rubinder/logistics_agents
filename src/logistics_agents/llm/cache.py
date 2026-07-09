import dataclasses
import hashlib
from pathlib import Path

from logistics_agents.llm.types import LLMRequest, RawResponse, Transport


class CacheMissError(Exception):
    pass


def request_key(request: LLMRequest) -> str:
    parts = []
    for field in dataclasses.fields(request):
        if field.name == "output_type":
            parts.append(f"output_type={request.schema_fingerprint()}")
        else:
            parts.append(f"{field.name}={getattr(request, field.name)!r}")
    canonical = "\x00".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RecordReplayCache:
    def __init__(self, transport: Transport, mode: str, fixtures_dir: Path):
        if mode not in ("live", "replay"):
            raise ValueError(f"mode must be 'live' or 'replay', got {mode!r}")
        self._transport = transport
        self._mode = mode
        self._fixtures_dir = Path(fixtures_dir)

    def _path(self, request: LLMRequest) -> Path:
        return self._fixtures_dir / f"{request_key(request)}.json"

    def __call__(self, request: LLMRequest) -> RawResponse:
        path = self._path(request)
        if self._mode == "replay":
            if not path.exists():
                raise CacheMissError(
                    f"No fixture for request key {request_key(request)} at {path}"
                )
            return RawResponse.model_validate_json(path.read_text(encoding="utf-8"))

        # live: call through, record, return
        response = self._transport(request)
        self._fixtures_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(response.model_dump_json(), encoding="utf-8")
        return response
