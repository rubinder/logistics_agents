# Milestone 2: LLM Wrapper + Record/Replay — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Anthropic LLM wrapper that returns validated pydantic structured outputs with token/cost/latency metadata, plus a record/replay fixture cache that makes agent runs deterministic and free in CI while still supporting real model-comparison runs.

**Architecture:** A thin, injectable `Transport` boundary isolates the real Anthropic SDK call from everything else. The real transport wraps `client.messages.parse(...)`; tests inject a fake transport, so all record/replay and cost logic is unit-tested with **no API key**. A `RecordReplayCache` wraps any transport: in `live` mode it calls through and writes a JSON fixture keyed on a hash of the request; in `replay` mode it reads the fixture and a cache miss is a hard failure. `LLMClient.complete_structured(...)` ties them together — it validates the transport's JSON into the caller's pydantic type, computes cost from a per-model pricing table, and measures latency.

**Tech Stack:** Python 3.12, `anthropic` SDK, pydantic v2, pytest. Builds on Milestone 1 (uv project, `logistics_agents` package).

## Global Constraints

- Python version floor: **3.12**.
- All model IDs come from this exact set: `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5`. Never append date suffixes.
- Pricing (USD per 1,000,000 tokens, input/output): opus-4-8 = 5.00 / 25.00; sonnet-5 = 3.00 / 15.00; haiku-4-5 = 1.00 / 5.00.
- Structured output uses `client.messages.parse(..., output_format=<PydanticModel>)` → `response.parsed_output`; usage via `response.usage.input_tokens` / `response.usage.output_tokens`.
- CI must run the full suite in **replay mode with committed fixtures and no `ANTHROPIC_API_KEY`**. Any test that needs a real API call must `pytest.mark.skipif` when credentials are absent.
- All cross-module data shapes are pydantic v2 models or frozen dataclasses — no bare dicts crossing module boundaries.
- Commit after every task with a `feat:`/`chore:`/`test:` prefixed message.

---

### Task 1: Pricing table + cost function

**Files:**
- Create: `src/logistics_agents/llm/__init__.py`
- Create: `src/logistics_agents/llm/pricing.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_pricing.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `pricing.MODEL_PRICING: dict[str, tuple[float, float]]` mapping model id → `(input_per_mtok, output_per_mtok)`.
  - `pricing.cost_usd(model: str, input_tokens: int, output_tokens: int) -> float` — raises `ValueError` for an unknown model.

- [ ] **Step 1: Write the failing test**

`tests/llm/__init__.py`: (empty file)

`tests/llm/test_pricing.py`:
```python
import pytest

from logistics_agents.llm.pricing import MODEL_PRICING, cost_usd


def test_all_three_models_priced():
    assert set(MODEL_PRICING) == {"claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5"}


def test_cost_opus():
    # 1000 in * $5/1M + 500 out * $25/1M = 0.005 + 0.0125
    assert cost_usd("claude-opus-4-8", 1000, 500) == pytest.approx(0.0175)


def test_cost_haiku_zero_tokens():
    assert cost_usd("claude-haiku-4-5", 0, 0) == 0.0


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        cost_usd("gpt-4", 100, 100)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/llm/test_pricing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.llm'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/llm/__init__.py`: (empty file)

`src/logistics_agents/llm/pricing.py`:
```python
# USD per 1,000,000 tokens: (input_per_mtok, output_per_mtok).
# Sonnet 5 has intro pricing ($2/$10 through 2026-08-31); we use standard rates.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model for pricing: {model!r}")
    input_rate, output_rate = MODEL_PRICING[model]
    return input_tokens / 1_000_000 * input_rate + output_tokens / 1_000_000 * output_rate
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/llm/test_pricing.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/llm/__init__.py src/logistics_agents/llm/pricing.py tests/llm
git commit -m "feat: add LLM model pricing table and cost function"
```

---

### Task 2: Core LLM types + Transport protocol

**Files:**
- Create: `src/logistics_agents/llm/types.py`
- Create: `tests/llm/conftest.py`
- Create: `tests/llm/test_types.py`

**Interfaces:**
- Consumes: pydantic.
- Produces:
  - `types.LLMRequest` — frozen dataclass: `model: str`, `system: str`, `user: str`, `output_type: type[BaseModel]`. Method `schema_fingerprint(self) -> str` returns `output_type.__name__ + canonical-json-of-model_json_schema`.
  - `types.RawResponse` — pydantic model: `output_json: str`, `input_tokens: int`, `output_tokens: int`, `model: str`.
  - `types.CallMeta` — pydantic model: `model: str`, `input_tokens: int`, `output_tokens: int`, `cost_usd: float`, `latency_ms: int`.
  - `types.StructuredResult` — generic-ish container (plain dataclass): `value: BaseModel`, `meta: CallMeta`.
  - `types.Transport` — `typing.Protocol` with `__call__(self, request: LLMRequest) -> RawResponse`.
- Also produces a shared pytest fixture `fake_transport_factory` in `tests/llm/conftest.py` (used by Tasks 3–4).

- [ ] **Step 1: Write the failing test**

`tests/llm/conftest.py`:
```python
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
```

`tests/llm/test_types.py`:
```python
from logistics_agents.llm.types import CallMeta, RawResponse


def test_raw_response_round_trips():
    r = RawResponse(output_json='{"label": "x", "score": 1.0}', input_tokens=5, output_tokens=3, model="claude-haiku-4-5")
    assert RawResponse.model_validate_json(r.model_dump_json()) == r


def test_request_fingerprint_stable_and_type_sensitive(make_request):
    a = make_request()
    b = make_request()
    assert a.schema_fingerprint() == b.schema_fingerprint()
    assert "Sentiment" in a.schema_fingerprint()


def test_call_meta_fields():
    m = CallMeta(model="claude-opus-4-8", input_tokens=10, output_tokens=5, cost_usd=0.0, latency_ms=42)
    assert m.latency_ms == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/llm/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.llm.types'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/llm/types.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/llm/test_types.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/llm/types.py tests/llm/conftest.py tests/llm/test_types.py
git commit -m "feat: add LLM request/response types and Transport protocol"
```

---

### Task 3: Record/replay cache

**Files:**
- Create: `src/logistics_agents/llm/cache.py`
- Create: `tests/llm/test_cache.py`

**Interfaces:**
- Consumes: `types.LLMRequest`, `types.RawResponse`, `types.Transport` (Task 2).
- Produces:
  - `cache.request_key(request: LLMRequest) -> str` — sha256 hex of `model | system | user | schema_fingerprint`.
  - `cache.RecordReplayCache(transport: Transport, mode: str, fixtures_dir: Path)` with `mode in {"live", "replay"}`.
    - `__call__(request) -> RawResponse`: in `live`, calls `transport`, writes `fixtures_dir/<key>.json` (the `RawResponse` JSON), returns it. In `replay`, reads the fixture; a missing fixture raises `CacheMissError`.
  - `cache.CacheMissError(Exception)`.

- [ ] **Step 1: Write the failing test**

`tests/llm/test_cache.py`:
```python
import pytest

from logistics_agents.llm.cache import CacheMissError, RecordReplayCache, request_key


def test_key_stable_and_input_sensitive(make_request):
    assert request_key(make_request()) == request_key(make_request())
    assert request_key(make_request(model="claude-opus-4-8")) != request_key(make_request(model="claude-haiku-4-5"))
    assert request_key(make_request(user="a")) != request_key(make_request(user="b"))


def test_live_records_then_replay_reads(make_request, fake_transport_factory, tmp_path):
    transport, calls = fake_transport_factory(label="positive")
    req = make_request()

    live = RecordReplayCache(transport, mode="live", fixtures_dir=tmp_path)
    recorded = live(req)
    assert len(calls) == 1
    assert (tmp_path / f"{request_key(req)}.json").exists()

    # A fresh transport that would explode if called proves replay does not call through.
    def exploding(_request):
        raise AssertionError("replay must not call the transport")

    replay = RecordReplayCache(exploding, mode="replay", fixtures_dir=tmp_path)
    replayed = replay(req)
    assert replayed == recorded


def test_replay_miss_raises(make_request, tmp_path):
    def unused(_request):
        raise AssertionError("should not be called")

    replay = RecordReplayCache(unused, mode="replay", fixtures_dir=tmp_path)
    with pytest.raises(CacheMissError):
        replay(make_request())


def test_invalid_mode_raises(make_request, fake_transport_factory, tmp_path):
    transport, _ = fake_transport_factory()
    with pytest.raises(ValueError):
        RecordReplayCache(transport, mode="bogus", fixtures_dir=tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/llm/test_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.llm.cache'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/llm/cache.py`:
```python
import hashlib
from pathlib import Path

from logistics_agents.llm.types import LLMRequest, RawResponse, Transport


class CacheMissError(Exception):
    pass


def request_key(request: LLMRequest) -> str:
    canonical = "\x00".join(
        [request.model, request.system, request.user, request.schema_fingerprint()]
    )
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
            return RawResponse.model_validate_json(path.read_text())

        # live: call through, record, return
        response = self._transport(request)
        self._fixtures_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(response.model_dump_json())
        return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/llm/test_cache.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/llm/cache.py tests/llm/test_cache.py
git commit -m "feat: add record/replay fixture cache for LLM calls"
```

---

### Task 4: LLMClient (structured completion with metadata)

**Files:**
- Create: `src/logistics_agents/llm/client.py`
- Create: `tests/llm/test_client.py`

**Interfaces:**
- Consumes: `types` (Task 2), `cache.RecordReplayCache` (Task 3), `pricing.cost_usd` (Task 1).
- Produces:
  - `client.LLMClient(transport_or_cache)` — accepts any callable `Transport` (the `RecordReplayCache` is one).
  - `client.LLMClient.complete_structured(model: str, system: str, user: str, output_type: type[BaseModel]) -> StructuredResult` — builds an `LLMRequest`, invokes the transport, validates `RawResponse.output_json` into `output_type`, computes `cost_usd`, measures wall-clock latency in ms, and returns `StructuredResult(value, meta)`.

- [ ] **Step 1: Write the failing test**

`tests/llm/test_client.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/llm/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.llm.client'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/llm/client.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/llm/test_client.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/llm/client.py tests/llm/test_client.py
git commit -m "feat: add LLMClient for structured completion with cost/latency metadata"
```

---

### Task 5: Real Anthropic transport (+ skippable live test)

**Files:**
- Create: `src/logistics_agents/llm/anthropic_transport.py`
- Create: `tests/llm/test_anthropic_transport.py`

**Interfaces:**
- Consumes: `types.LLMRequest`, `types.RawResponse` (Task 2); the `anthropic` SDK.
- Produces:
  - `anthropic_transport.AnthropicTransport(client=None, max_tokens=4096)` — a `Transport`. On `__call__(request)` it calls `client.messages.parse(model=..., max_tokens=..., system=request.system, messages=[{"role": "user", "content": request.user}], output_format=request.output_type)`, then returns `RawResponse(output_json=response.parsed_output.model_dump_json(), input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens, model=request.model)`. If `client` is None it lazily constructs `anthropic.Anthropic()`.

- [ ] **Step 1: Write the failing test**

`tests/llm/test_anthropic_transport.py`:
```python
import os
import types as _types

import pytest
from pydantic import BaseModel

from logistics_agents.llm.anthropic_transport import AnthropicTransport
from logistics_agents.llm.types import LLMRequest, RawResponse


class Sentiment(BaseModel):
    label: str
    score: float


def test_transport_maps_parse_response_to_raw_response():
    """Unit test with a stub SDK client — no network, no key. Verifies the
    transport calls messages.parse correctly and maps the result."""
    captured = {}

    def fake_parse(**kwargs):
        captured.update(kwargs)
        usage = _types.SimpleNamespace(input_tokens=123, output_tokens=45)
        parsed = Sentiment(label="neutral", score=0.5)
        return _types.SimpleNamespace(parsed_output=parsed, usage=usage)

    stub_client = _types.SimpleNamespace(
        messages=_types.SimpleNamespace(parse=fake_parse)
    )
    transport = AnthropicTransport(client=stub_client, max_tokens=256)
    req = LLMRequest(model="claude-haiku-4-5", system="sys", user="hi", output_type=Sentiment)

    raw = transport(req)

    assert isinstance(raw, RawResponse)
    assert raw.input_tokens == 123
    assert raw.output_tokens == 45
    assert raw.model == "claude-haiku-4-5"
    assert Sentiment.model_validate_json(raw.output_json) == Sentiment(label="neutral", score=0.5)
    # Verify the SDK was driven correctly.
    assert captured["model"] == "claude-haiku-4-5"
    assert captured["max_tokens"] == 256
    assert captured["system"] == "sys"
    assert captured["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["output_format"] is Sentiment


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live Anthropic call requires ANTHROPIC_API_KEY",
)
def test_live_call_returns_validated_model():
    transport = AnthropicTransport(max_tokens=256)
    req = LLMRequest(
        model="claude-haiku-4-5",
        system="You classify sentiment. Respond only via the structured schema.",
        user="I love this product!",
        output_type=Sentiment,
    )
    raw = transport(req)
    value = Sentiment.model_validate_json(raw.output_json)
    assert value.label
    assert raw.input_tokens > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/llm/test_anthropic_transport.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.llm.anthropic_transport'`. (The live test is skipped when `ANTHROPIC_API_KEY` is unset.)

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/llm/anthropic_transport.py`:
```python
from logistics_agents.llm.types import LLMRequest, RawResponse


class AnthropicTransport:
    """Transport that calls the real Anthropic Messages API via structured outputs."""

    def __init__(self, client=None, max_tokens: int = 4096):
        self._client = client
        self._max_tokens = max_tokens

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def __call__(self, request: LLMRequest) -> RawResponse:
        response = self._get_client().messages.parse(
            model=request.model,
            max_tokens=self._max_tokens,
            system=request.system,
            messages=[{"role": "user", "content": request.user}],
            output_format=request.output_type,
        )
        return RawResponse(
            output_json=response.parsed_output.model_dump_json(),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=request.model,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/llm/test_anthropic_transport.py -v`
Expected: PASS (1 passed, 1 skipped — the live test skips without a key).

- [ ] **Step 5: Run the full milestone suite**

Run: `uv run pytest -v`
Expected: PASS — all Milestone 1 + Milestone 2 tests (M2 live test skipped).

- [ ] **Step 6: Commit**

```bash
git add src/logistics_agents/llm/anthropic_transport.py tests/llm/test_anthropic_transport.py
git commit -m "feat: add real Anthropic transport using messages.parse structured outputs"
```

---

## Self-Review

**Spec coverage (Milestone 2 scope = spec §6 LLM wrapper & record/replay, milestone 15.2):**
- Anthropic client wrapper enforcing pydantic structured output (§6): Task 5 (`AnthropicTransport` via `messages.parse` + `output_format`) + Task 4 (`LLMClient` validates into `output_type`). ✅
- Record/replay cache keyed on model + prompt + schema, live records / replay hard-fails on miss (§6): Task 3. ✅
- Captures tokens/cost/latency (§6): Task 1 (cost) + Task 4 (`CallMeta` with tokens, cost, latency). ✅
- Model-comparison support across Opus/Sonnet/Haiku (§2): `model` is a per-call parameter (Task 4) and all three are priced (Task 1). ✅
- Deterministic, key-free CI (Global Constraint): every test except the Task 5 live test uses a fake/stub transport; the live test is `skipif` on `ANTHROPIC_API_KEY`. ✅

Out of Milestone 2 scope (correctly deferred): agents/DAG (M3), evals/graders (M4), CI wiring (M5). Effort/adaptive-thinking knobs on the transport are intentionally omitted here — add them in M3 if a specialist agent needs deeper reasoning; M2's transport keeps the minimal correct `messages.parse` shape.

**Placeholder scan:** No TBD/TODO. Every code step is complete. The lazy `import anthropic` inside `_get_client` is deliberate (keeps the module importable without the SDK configured, and keeps unit tests key-free), not a placeholder.

**Type consistency:** `LLMRequest`, `RawResponse`, `CallMeta`, `StructuredResult`, `Transport` defined in Task 2 are used with identical signatures in Tasks 3–5. `request_key`/`RecordReplayCache` (Task 3) match their use as a `Transport` in Task 4. `cost_usd` (Task 1) is called in Task 4 with `(model, input_tokens, output_tokens)`. The real transport (Task 5) returns the same `RawResponse` shape the fake transport (Task 2 conftest) returns, so `LLMClient` treats live and replay identically.
