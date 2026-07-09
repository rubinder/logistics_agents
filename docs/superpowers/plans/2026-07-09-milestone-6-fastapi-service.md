# Milestone 6: FastAPI Service — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A FastAPI service that exposes the multi-agent system safely to the public dashboard: read endpoints for runs/traces/decisions, a budget/quota status view, a rate-limited + budget-guarded trigger endpoint that runs the pipeline on a fixed demo-scenario set, and an SSE endpoint that streams a run's traces for the visualizer. The Anthropic key stays server-side; public spend is bounded by a budget ledger + per-IP/global rate limits.

**Architecture:** The service is a thin HTTP layer over the existing repository + `run_pipeline`. A single `budget_ledger` table is the source of truth for both **cost** (sum of `cost_usd` → monthly budget) and **rate** (count of `trigger:<ip>` entries → per-IP/global daily quota). `create_app()` builds the FastAPI app; a `get_conn` / `get_llm` / `get_settings` dependency trio makes everything injectable, so tests use FastAPI's `dependency_overrides` with the testcontainers connection and a scripted transport — **no API key, deterministic**. `POST /runs` checks rate + budget *before* running, then runs the pipeline, records spend, and returns the decision. SSE replays a completed run's persisted traces (live-during-execution streaming is an M7 enhancement).

**Tech Stack:** Python 3.12, FastAPI + Starlette, pydantic v2, psycopg 3, pytest + FastAPI TestClient (httpx) + testcontainers. Builds on M1–M4.

## Global Constraints

- Python floor **3.12**. The Anthropic key is server-side only; it never appears in a response or in client-supplied data.
- Every test is key-free and deterministic: `dependency_overrides` inject the testcontainers `postgres_conn` and a scripted-transport `LLMClient`.
- The `budget_ledger` table (M1 schema) is the single ledger: `source` is `scheduled` or `trigger:<client_ip>`; cost drives the monthly budget, entry-counts drive rate limits.
- All new code must pass `ruff check` (config from M5) and keep the suite green.
- Commit after every task with a `feat:`/`chore:`/`test:` prefix.

---

### Task 1: Budget-ledger repository functions

**Files:**
- Modify: `src/logistics_agents/data/repository.py`
- Create: `tests/data/test_budget_repository.py`

**Interfaces:**
- Consumes: `postgres_conn` fixture.
- Produces (all on `repository`):
  - `insert_budget_entry(conn, run_id: str, cost_usd: float, source: str) -> None` — appends to `budget_ledger`.
  - `total_spend_usd(conn, since: datetime | None = None) -> float` — `SUM(cost_usd)` over `budget_ledger`, optionally `WHERE created_at >= since`. Returns 0.0 when empty.
  - `count_entries(conn, source: str | None = None, source_prefix: str | None = None, since: datetime | None = None) -> int` — counts rows, optionally filtered by exact `source`, a `source LIKE prefix || '%'`, and/or `created_at >= since`.

- [ ] **Step 1: Write the failing test**

`tests/data/test_budget_repository.py`:
```python
from datetime import datetime, timedelta, timezone

from logistics_agents.data import repository


def test_total_spend_sums_costs(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.01, "scheduled")
    repository.insert_budget_entry(postgres_conn, "R2", 0.02, "trigger:1.2.3.4")
    assert repository.total_spend_usd(postgres_conn) == 0.03


def test_total_spend_empty_is_zero(postgres_conn):
    assert repository.total_spend_usd(postgres_conn) == 0.0


def test_count_entries_by_source_and_prefix(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.01, "trigger:1.1.1.1")
    repository.insert_budget_entry(postgres_conn, "R2", 0.01, "trigger:1.1.1.1")
    repository.insert_budget_entry(postgres_conn, "R3", 0.01, "trigger:2.2.2.2")
    repository.insert_budget_entry(postgres_conn, "R4", 0.01, "scheduled")
    assert repository.count_entries(postgres_conn, source="trigger:1.1.1.1") == 2
    assert repository.count_entries(postgres_conn, source_prefix="trigger:") == 3
    assert repository.count_entries(postgres_conn) == 4


def test_count_entries_since(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.01, "scheduled")
    future = datetime.now(timezone.utc) + timedelta(days=1)
    assert repository.count_entries(postgres_conn, since=future) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_budget_repository.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'insert_budget_entry'`.

- [ ] **Step 3: Write the implementation**

Append to `src/logistics_agents/data/repository.py`:
```python
from datetime import datetime


def insert_budget_entry(conn, run_id: str, cost_usd: float, source: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO budget_ledger (run_id, cost_usd, source) VALUES (%s, %s, %s)",
            (run_id, cost_usd, source),
        )
    conn.commit()


def total_spend_usd(conn, since: datetime | None = None) -> float:
    clause, params = ("WHERE created_at >= %s", (since,)) if since is not None else ("", ())
    with conn.cursor() as cur:
        cur.execute(f"SELECT COALESCE(SUM(cost_usd), 0) FROM budget_ledger {clause}", params)
        return float(cur.fetchone()[0])


def count_entries(
    conn,
    source: str | None = None,
    source_prefix: str | None = None,
    since: datetime | None = None,
) -> int:
    conditions = []
    params: list = []
    if source is not None:
        conditions.append("source = %s")
        params.append(source)
    if source_prefix is not None:
        conditions.append("source LIKE %s")
        params.append(source_prefix + "%")
    if since is not None:
        conditions.append("created_at >= %s")
        params.append(since)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM budget_ledger {where}", params)
        return int(cur.fetchone()[0])
```
Note: `datetime` is already imported at the top of `repository.py` (from M3); do not add a duplicate import — verify and reuse the existing one.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_budget_repository.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/data/repository.py tests/data/test_budget_repository.py
git commit -m "feat: add budget-ledger repository functions (spend sum, entry counts)"
```

---

### Task 2: Budget policy + rate limiter

**Files:**
- Create: `src/logistics_agents/api/__init__.py`
- Create: `src/logistics_agents/api/guards.py`
- Create: `tests/api/__init__.py`
- Create: `tests/api/test_guards.py`

**Interfaces:**
- Consumes: `repository` (Task 1).
- Produces:
  - `guards.BudgetStatus(cap_usd: float, spent_usd: float, remaining_usd: float)` (pydantic).
  - `guards.budget_status(conn, cap_usd: float, clock=<utc-now>) -> BudgetStatus` — spend is summed since the start of the current UTC month.
  - `guards.budget_allows(conn, cap_usd: float, clock=<utc-now>) -> bool` — `remaining_usd > 0`.
  - `guards.rate_allows(conn, client_ip: str, per_ip_daily: int, global_daily: int, clock=<utc-now>) -> bool` — counts `trigger:<ip>` and `trigger:` entries in the last 24h; True iff both under their caps.

- [ ] **Step 1: Write the failing test**

`tests/api/__init__.py`: (empty file)

`tests/api/test_guards.py`:
```python
from datetime import datetime, timezone

from logistics_agents.api import guards
from logistics_agents.data import repository

CLOCK = lambda: datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def test_budget_status_and_allows(postgres_conn):
    repository.insert_budget_entry(postgres_conn, "R1", 0.40, "scheduled")
    status = guards.budget_status(postgres_conn, cap_usd=1.0, clock=CLOCK)
    assert status.spent_usd == 0.40
    assert status.remaining_usd == 0.60
    assert guards.budget_allows(postgres_conn, cap_usd=1.0, clock=CLOCK) is True
    assert guards.budget_allows(postgres_conn, cap_usd=0.40, clock=CLOCK) is False


def test_rate_allows_per_ip_and_global(postgres_conn):
    ip = "9.9.9.9"
    # Under both caps initially.
    assert guards.rate_allows(postgres_conn, ip, per_ip_daily=2, global_daily=5, clock=CLOCK) is True
    repository.insert_budget_entry(postgres_conn, "R1", 0.0, f"trigger:{ip}")
    repository.insert_budget_entry(postgres_conn, "R2", 0.0, f"trigger:{ip}")
    # Per-IP cap (2) now reached.
    assert guards.rate_allows(postgres_conn, ip, per_ip_daily=2, global_daily=5, clock=CLOCK) is False
    # A different IP still allowed under the global cap.
    assert guards.rate_allows(postgres_conn, "8.8.8.8", per_ip_daily=2, global_daily=5, clock=CLOCK) is True


def test_rate_global_cap(postgres_conn):
    for i in range(3):
        repository.insert_budget_entry(postgres_conn, f"R{i}", 0.0, f"trigger:1.1.1.{i}")
    # global cap of 3 reached regardless of per-ip
    assert guards.rate_allows(postgres_conn, "5.5.5.5", per_ip_daily=10, global_daily=3, clock=CLOCK) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_guards.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.api'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/api/__init__.py`: (empty file)

`src/logistics_agents/api/guards.py`:
```python
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from logistics_agents.data import repository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class BudgetStatus(BaseModel):
    cap_usd: float
    spent_usd: float
    remaining_usd: float


def budget_status(conn, cap_usd: float, clock=_utc_now) -> BudgetStatus:
    spent = repository.total_spend_usd(conn, since=_month_start(clock()))
    return BudgetStatus(cap_usd=cap_usd, spent_usd=spent, remaining_usd=cap_usd - spent)


def budget_allows(conn, cap_usd: float, clock=_utc_now) -> bool:
    return budget_status(conn, cap_usd, clock).remaining_usd > 0


def rate_allows(
    conn, client_ip: str, per_ip_daily: int, global_daily: int, clock=_utc_now
) -> bool:
    since = clock() - timedelta(days=1)
    per_ip = repository.count_entries(conn, source=f"trigger:{client_ip}", since=since)
    total = repository.count_entries(conn, source_prefix="trigger:", since=since)
    return per_ip < per_ip_daily and total < global_daily
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_guards.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/api/__init__.py src/logistics_agents/api/guards.py tests/api
git commit -m "feat: add budget policy and per-ip/global rate limiter over the ledger"
```

---

### Task 3: FastAPI app skeleton + dependencies

**Files:**
- Create: `src/logistics_agents/api/deps.py`
- Create: `src/logistics_agents/api/app.py`
- Create: `tests/api/conftest.py`
- Create: `tests/api/test_health.py`
- Modify: `pyproject.toml` (add `fastapi`, `uvicorn`; dev `httpx`)

**Interfaces:**
- Produces:
  - `deps.Settings(budget_cap_usd, per_ip_daily, global_daily)` (pydantic; defaults for prod).
  - `deps.get_conn()`, `deps.get_llm()`, `deps.get_settings()` — FastAPI dependencies (prod implementations; overridden in tests).
  - `app.create_app() -> FastAPI` — an app with `GET /health`.
  - `tests/api/conftest.py` — a `client` fixture: builds the app, overrides `get_conn` → `postgres_conn`, `get_llm` → a scripted-transport `LLMClient`, `get_settings` → small test caps, returns a `TestClient`.

- [ ] **Step 1: Add dependencies**

Run: `uv add fastapi uvicorn` and `uv add --dev httpx`. (fastapi's `TestClient` needs `httpx`.)

- [ ] **Step 2: Write the failing test**

`tests/api/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient

from logistics_agents.api.app import create_app
from logistics_agents.api.deps import Settings, get_conn, get_llm, get_settings
from logistics_agents.llm.client import LLMClient


@pytest.fixture
def api_client(postgres_conn, scripted_transport):
    from logistics_agents.agents.contracts import (
        CarrierFinding, ExceptionFinding, InventoryFinding, OrchestrationPlan,
    )
    from logistics_agents.domain.enums import DecisionLabel
    from logistics_agents.domain.models import Decision

    script = {
        OrchestrationPlan: OrchestrationPlan(subtasks=["x"], reasoning="d"),
        InventoryFinding: InventoryFinding(po_matched=True, discrepancies=[], capacity_ok=True, reasoning="i"),
        CarrierFinding: CarrierFinding(status="in_transit", eta=None, delayed=False, reasoning="c"),
        ExceptionFinding: ExceptionFinding(exceptions=[], reasoning="e"),
        Decision: Decision(label=DecisionLabel.ACCEPT, exceptions=[], recommended_actions=[], confidence=0.9, reasoning="r"),
    }
    transport, _ = scripted_transport(script)

    app = create_app()
    app.dependency_overrides[get_conn] = lambda: postgres_conn
    app.dependency_overrides[get_llm] = lambda: LLMClient(transport)
    app.dependency_overrides[get_settings] = lambda: Settings(
        budget_cap_usd=1.0, per_ip_daily=2, global_daily=5
    )
    return TestClient(app)
```

`tests/api/test_health.py`:
```python
def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/api/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.api.app'`.

- [ ] **Step 4: Write the implementation**

`src/logistics_agents/api/deps.py`:
```python
import os

import psycopg
from pydantic import BaseModel

from logistics_agents.llm.client import LLMClient


class Settings(BaseModel):
    budget_cap_usd: float = 20.0
    per_ip_daily: int = 5
    global_daily: int = 50


def get_settings() -> Settings:
    return Settings()


def get_conn():
    dsn = os.environ.get(
        "LOGISTICS_DATABASE_URL", "postgresql://logistics:logistics@localhost:5432/logistics"
    )
    conn = psycopg.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()


def get_llm() -> LLMClient:  # pragma: no cover - overridden in tests; live wiring in run/deploy
    from logistics_agents.llm.anthropic_transport import AnthropicTransport

    return LLMClient(AnthropicTransport())
```

`src/logistics_agents/api/app.py`:
```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="logistics-agents API")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    from logistics_agents.api.routes import register_routes

    register_routes(app)
    return app
```

Create a stub `src/logistics_agents/api/routes.py` so the import resolves (later tasks fill it):
```python
from fastapi import FastAPI


def register_routes(app: FastAPI) -> None:
    # routes are added in later tasks
    return None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/api/test_health.py -v`
Expected: PASS (1 test).

- [ ] **Step 6: Commit**

```bash
git add src/logistics_agents/api/deps.py src/logistics_agents/api/app.py src/logistics_agents/api/routes.py tests/api/conftest.py tests/api/test_health.py pyproject.toml
git commit -m "feat: add FastAPI app skeleton with injectable conn/llm/settings dependencies"
```

---

### Task 4: Read endpoints (runs, trace, decision)

**Files:**
- Modify: `src/logistics_agents/api/routes.py`
- Modify: `src/logistics_agents/data/repository.py`
- Create: `tests/api/test_read_endpoints.py`

**Interfaces:**
- Consumes: `repository`, `deps.get_conn`.
- Produces:
  - `repository.list_run_ids(conn) -> list[str]` — distinct `run_id` from `runs`, newest-first by max(created_at).
  - `repository.get_traces(conn, run_id) -> list[TraceRecord]` — ordered by `created_at`.
  - Routes: `GET /runs` → `{"run_ids": [...]}`; `GET /runs/{run_id}/trace` → list of trace dicts; `GET /runs/{run_id}/decision` → the decision dict (404 if absent).

- [ ] **Step 1: Write the failing test**

`tests/api/test_read_endpoints.py`:
```python
from datetime import datetime, timezone

from logistics_agents.data import repository
from logistics_agents.domain.enums import DecisionLabel
from logistics_agents.domain.models import Decision, TraceRecord


def _seed_run(conn, run_id):
    tr = TraceRecord(
        run_id=run_id, node="orchestrator", input_json="{}", output_json="{}",
        latency_ms=10, tokens=5, cost_usd=0.001, model="claude-sonnet-5",
        created_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    repository.insert_trace(conn, tr)
    repository.insert_decision(
        conn, run_id, "SH-1",
        Decision(label=DecisionLabel.ACCEPT, exceptions=[], recommended_actions=[], confidence=1.0, reasoning="ok"),
    )


def test_list_runs_and_trace_and_decision(api_client, postgres_conn):
    _seed_run(postgres_conn, "RUN-A")

    runs = api_client.get("/runs").json()
    assert "RUN-A" in runs["run_ids"]

    trace = api_client.get("/runs/RUN-A/trace").json()
    assert len(trace) == 1
    assert trace[0]["node"] == "orchestrator"

    decision = api_client.get("/runs/RUN-A/decision").json()
    assert decision["label"] == "ACCEPT"


def test_missing_decision_is_404(api_client):
    assert api_client.get("/runs/NOPE/decision").status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_read_endpoints.py -v`
Expected: FAIL — 404 for `/runs` (route not registered yet) or `AttributeError` for `list_run_ids`.

- [ ] **Step 3: Write the implementation**

Append to `src/logistics_agents/data/repository.py`:
```python
from logistics_agents.domain.models import TraceRecord  # ensure imported at top (reuse existing)


def list_run_ids(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT run_id, MAX(created_at) AS ts FROM runs GROUP BY run_id ORDER BY ts DESC")
        return [row[0] for row in cur.fetchall()]


def get_traces(conn, run_id: str) -> list[TraceRecord]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT run_id, node, input_json, output_json, latency_ms, tokens, cost_usd, model, created_at "
            "FROM runs WHERE run_id = %s ORDER BY created_at",
            (run_id,),
        )
        rows = cur.fetchall()
    return [
        TraceRecord(
            run_id=r[0], node=r[1], input_json=r[2], output_json=r[3], latency_ms=r[4],
            tokens=r[5], cost_usd=r[6], model=r[7], created_at=r[8],
        )
        for r in rows
    ]
```
(Reuse the existing top-of-file `TraceRecord` import from M3 — do not duplicate.)

Replace `src/logistics_agents/api/routes.py`:
```python
from fastapi import Depends, FastAPI, HTTPException

from logistics_agents.api.deps import get_conn
from logistics_agents.data import repository


def register_routes(app: FastAPI) -> None:
    @app.get("/runs")
    def list_runs(conn=Depends(get_conn)):
        return {"run_ids": repository.list_run_ids(conn)}

    @app.get("/runs/{run_id}/trace")
    def run_trace(run_id: str, conn=Depends(get_conn)):
        return [t.model_dump(mode="json") for t in repository.get_traces(conn, run_id)]

    @app.get("/runs/{run_id}/decision")
    def run_decision(run_id: str, conn=Depends(get_conn)):
        decision = repository.get_decision(conn, run_id)
        if decision is None:
            raise HTTPException(status_code=404, detail="decision not found")
        return decision.model_dump(mode="json")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_read_endpoints.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/api/routes.py src/logistics_agents/data/repository.py tests/api/test_read_endpoints.py
git commit -m "feat: add read endpoints for runs, traces, and decisions"
```

---

### Task 5: Budget status endpoint

**Files:**
- Modify: `src/logistics_agents/api/routes.py`
- Create: `tests/api/test_budget_endpoint.py`

**Interfaces:**
- Consumes: `guards.budget_status`, `deps.{get_conn, get_settings}`.
- Produces: `GET /budget` → `BudgetStatus` dict (`cap_usd`, `spent_usd`, `remaining_usd`).

- [ ] **Step 1: Write the failing test**

`tests/api/test_budget_endpoint.py`:
```python
from logistics_agents.data import repository


def test_budget_endpoint_reflects_spend(api_client, postgres_conn):
    before = api_client.get("/budget").json()
    assert before["cap_usd"] == 1.0  # test settings cap
    assert before["spent_usd"] == 0.0
    assert before["remaining_usd"] == 1.0

    repository.insert_budget_entry(postgres_conn, "R1", 0.25, "scheduled")
    after = api_client.get("/budget").json()
    assert after["spent_usd"] == 0.25
    assert after["remaining_usd"] == 0.75
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_budget_endpoint.py -v`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Write the implementation**

Add to `register_routes` in `src/logistics_agents/api/routes.py` (add imports for `get_settings` and `guards`):
```python
    from logistics_agents.api.deps import get_settings
    from logistics_agents.api import guards

    @app.get("/budget")
    def budget(conn=Depends(get_conn), settings=Depends(get_settings)):
        return guards.budget_status(conn, settings.budget_cap_usd).model_dump()
```
(Place the imports at the top of `routes.py` alongside the existing ones rather than inside the function if you prefer; keep it ruff-clean.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_budget_endpoint.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/api/routes.py tests/api/test_budget_endpoint.py
git commit -m "feat: add budget status endpoint"
```

---

### Task 6: Rate-limited + budget-guarded trigger endpoint

**Files:**
- Create: `src/logistics_agents/api/scenarios.py`
- Modify: `src/logistics_agents/api/routes.py`
- Create: `tests/api/test_trigger.py`

**Interfaces:**
- Consumes: `scenarios.SCENARIOS`, `run_pipeline`, `Tracer`, `guards`, `repository.insert_budget_entry`, `deps.{get_conn, get_llm, get_settings}`.
- Produces:
  - `scenarios.SCENARIOS: dict[str, ShipmentNotification]` — a few demo scenarios (e.g. `clean`, `quantity-mismatch`) using seeded entities.
  - `POST /runs` — body `{"scenario_id": "..."}`. Rejects unknown scenario (400), rate-limit exceeded (429), or budget exhausted (402). Otherwise: generates a unique `run_id` from the scenario + a counter derived from the ledger, runs `run_pipeline` (persisting traces), records the run's total cost to `budget_ledger` with `source=f"trigger:{client_ip}"`, and returns `{"run_id", "decision", "cost_usd"}`.
  - `GET /scenarios` → `{"scenarios": [ids]}`.

- [ ] **Step 1: Write the failing test**

`tests/api/test_trigger.py`:
```python
from logistics_agents.data import repository


def test_trigger_runs_pipeline_and_records_spend(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)

    r = api_client.post("/runs", json={"scenario_id": "clean"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["label"] in {"ACCEPT", "HOLD", "REROUTE", "ESCALATE"}
    run_id = body["run_id"]

    # Traces + decision were persisted, and spend recorded under a trigger: source.
    assert repository.get_decision(postgres_conn, run_id) is not None
    assert repository.count_entries(postgres_conn, source_prefix="trigger:") == 1


def test_trigger_unknown_scenario_400(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)
    assert api_client.post("/runs", json={"scenario_id": "nope"}).status_code == 400


def test_trigger_rate_limited_429(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)
    # test settings: per_ip_daily=2 → third trigger from the same client is blocked
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 200
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 200
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 429


def test_trigger_budget_exhausted_402(api_client, postgres_conn):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)
    # Exhaust the $1.0 test cap directly, then a trigger is rejected.
    repository.insert_budget_entry(postgres_conn, "PRIOR", 1.0, "scheduled")
    assert api_client.post("/runs", json={"scenario_id": "clean"}).status_code == 402
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_trigger.py -v`
Expected: FAIL — 404/405 (route not registered) or `ModuleNotFoundError` for `scenarios`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/api/scenarios.py`:
```python
from datetime import datetime, timezone

from logistics_agents.domain.models import LineItem, ShipmentNotification

_ON_TIME = datetime(2026, 7, 5, tzinfo=timezone.utc)

SCENARIOS: dict[str, ShipmentNotification] = {
    "clean": ShipmentNotification(
        shipment_id="DEMO-CLEAN", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=100)], reported_date=_ON_TIME,
        docs_present=True, damaged=False,
    ),
    "quantity-mismatch": ShipmentNotification(
        shipment_id="DEMO-QTY", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=80)], reported_date=_ON_TIME,
        docs_present=True, damaged=False,
    ),
}
```

Add to `register_routes` in `routes.py` (import `Request`, `get_llm`, `Tracer`, `run_pipeline`, `scenarios`):
```python
    from fastapi import Request
    from logistics_agents.api.deps import get_llm
    from logistics_agents.api.scenarios import SCENARIOS
    from logistics_agents.orchestration.runner import run_pipeline
    from logistics_agents.tracing.tracer import Tracer

    @app.get("/scenarios")
    def scenarios_list():
        return {"scenarios": sorted(SCENARIOS)}

    @app.post("/runs")
    def trigger_run(
        request: Request,
        payload: dict,
        conn=Depends(get_conn),
        llm=Depends(get_llm),
        settings=Depends(get_settings),
    ):
        scenario_id = payload.get("scenario_id")
        if scenario_id not in SCENARIOS:
            raise HTTPException(status_code=400, detail="unknown scenario_id")

        client_ip = request.client.host if request.client else "unknown"
        if not guards.rate_allows(conn, client_ip, settings.per_ip_daily, settings.global_daily):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        if not guards.budget_allows(conn, settings.budget_cap_usd):
            raise HTTPException(status_code=402, detail="budget exhausted")

        asn = SCENARIOS[scenario_id]
        seq = repository.count_entries(conn, source_prefix="trigger:")
        run_id = f"trigger-{scenario_id}-{seq}"
        tracer = Tracer(run_id=run_id, conn=conn)
        decision = run_pipeline(asn, conn, llm, model="claude-opus-4-8", run_id=run_id, tracer=tracer)

        cost = sum(t.cost_usd for t in tracer.records)
        repository.insert_budget_entry(conn, run_id, cost, f"trigger:{client_ip}")
        return {"run_id": run_id, "decision": decision.model_dump(mode="json"), "cost_usd": cost}
```
Note: keep the `model="claude-opus-4-8"` here — in a live deployment the trigger defaults to a cheap model; that is a config concern for M8. For M6 the scripted transport makes the model label irrelevant to test outcomes.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_trigger.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/api/scenarios.py src/logistics_agents/api/routes.py tests/api/test_trigger.py
git commit -m "feat: add rate-limited, budget-guarded run-trigger endpoint with demo scenarios"
```

---

### Task 7: SSE run-trace stream

**Files:**
- Modify: `src/logistics_agents/api/routes.py`
- Create: `tests/api/test_stream.py`

**Interfaces:**
- Consumes: `repository.get_traces`, `deps.get_conn`.
- Produces: `GET /runs/{run_id}/stream` — a `text/event-stream` that emits one SSE frame per persisted trace (`event: <node>\ndata: <trace-json>\n\n`), then a terminal `event: done` frame. (Replays a completed run's traces for the visualizer; live-during-execution streaming is an M7 enhancement.)

- [ ] **Step 1: Write the failing test**

`tests/api/test_stream.py`:
```python
from datetime import datetime, timezone

from logistics_agents.data import repository
from logistics_agents.domain.models import TraceRecord


def _seed_traces(conn, run_id, nodes):
    for i, node in enumerate(nodes):
        repository.insert_trace(conn, TraceRecord(
            run_id=run_id, node=node, input_json="{}", output_json='{"ok": true}',
            latency_ms=i, tokens=1, cost_usd=0.0, model="claude-sonnet-5",
            created_at=datetime(2026, 7, 9, 12, i, tzinfo=timezone.utc),
        ))


def test_stream_emits_a_frame_per_node_then_done(api_client, postgres_conn):
    _seed_traces(postgres_conn, "RUN-S", ["orchestrator", "inventory", "synthesis"])
    with api_client.stream("GET", "/runs/RUN-S/stream") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(chunk for chunk in r.iter_text())
    assert "event: orchestrator" in body
    assert "event: inventory" in body
    assert "event: synthesis" in body
    assert "event: done" in body
    # Trace payload is present.
    assert '"ok": true' in body or '"ok":true' in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_stream.py -v`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Write the implementation**

Add to `register_routes` in `routes.py` (import `StreamingResponse`):
```python
    from fastapi.responses import StreamingResponse

    @app.get("/runs/{run_id}/stream")
    def run_stream(run_id: str, conn=Depends(get_conn)):
        traces = repository.get_traces(conn, run_id)

        def event_gen():
            for t in traces:
                yield f"event: {t.node}\ndata: {t.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_stream.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Run the full milestone suite + lint**

Run: `uv run ruff check .` → PASS.
Run: `uv run pytest -q` → PASS (all M1–M6 tests; live/scaffold tests skip).

- [ ] **Step 6: Commit**

```bash
git add src/logistics_agents/api/routes.py tests/api/test_stream.py
git commit -m "feat: add SSE run-trace stream endpoint for the visualizer"
```

---

## Self-Review

**Spec coverage (Milestone 6 scope = spec §8 API service & run control, milestone 15.6):**
- Endpoints: list/detail traces, decisions (§8): Task 4. ✅
- SSE run stream (§8): Task 7 (replay; live-during-execution deferred to M7). ✅
- `POST /runs` rate-limited trigger from a fixed demo-scenario set (§8): Task 6. ✅
- Budget/quota status (§8): Task 5. ✅
- Budget ledger — every triggered run debits it; hard-stop at cap (§8): Tasks 1, 2, 6 (`insert_budget_entry` + `budget_allows` → 402). ✅
- Rate limiter — per-IP + global daily (§8): Task 2 + Task 6 (429). ✅
- Anthropic key server-side only (§8): `get_llm` builds the client server-side; never in a response; tests never need a key. ✅
- Key-free deterministic tests (Global Constraint): `dependency_overrides` + scripted transport + testcontainers throughout. ✅

Out of scope (correctly deferred): the **scheduler** (EventBridge/cron generating demo runs) is deployment infra — it lands in M8's Terraform (or as a nightly workflow); the endpoint + ledger it drives exist here. **Live-during-execution SSE** (nodes stream as they run, not replayed) is deferred to M7 where the dashboard consumes it — M6 ships the replay feed the visualizer needs. The `POST /runs` model defaults to `claude-opus-4-8`; wiring a cheap default + record/replay for the public deploy is an M8 config concern.

**Placeholder scan:** No TBD/TODO. The `get_llm` `# pragma: no cover` marks the live-only branch (unit tests override it) — a coverage marker, not a placeholder. The initial `routes.py` stub in Task 3 is immediately filled in Task 4 (documented as such).

**Type consistency:** `Settings`/`get_conn`/`get_llm`/`get_settings` (Task 3) are the exact dependencies overridden in `tests/api/conftest.py` and used by every route (Tasks 4–7). `guards.budget_status`/`budget_allows`/`rate_allows` (Task 2) are called with matching signatures in Tasks 5–6. `repository.insert_budget_entry`/`count_entries`/`total_spend_usd` (Task 1) back the guards. `run_pipeline(asn, conn, llm, model, run_id, tracer)` (M3) and `Tracer(run_id, conn)` (M3) are called with their exact signatures in Task 6. `repository.get_traces` (Task 4) feeds the SSE stream (Task 7).
