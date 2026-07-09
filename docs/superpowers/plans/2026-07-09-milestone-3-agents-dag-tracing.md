# Milestone 3: Agents + DAG Runner + Tracing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the multi-agent pipeline — an orchestrator that decomposes an inbound shipment notification, three specialist agents (inventory, carrier, exception) that produce typed findings, and a synthesis agent that emits the final structured `Decision` — wired by a fixed-DAG runner that records a per-node trace.

**Architecture:** Each agent is a pure function `(asn, [peer findings], conn, llm, model) -> StructuredResult`. It fetches any DB context deterministically (via the repository), builds a prompt, and calls `LLMClient.complete_structured` to get a validated pydantic finding plus cost/latency metadata. Routing is a deterministic DAG: orchestrator → inventory + carrier → exception (reasons over both peer findings) → synthesis → `Decision`. A `Tracer` captures one `TraceRecord` per node and persists it to the `runs` table. Tests inject a **scripted transport** (canned structured output keyed by requested `output_type`), so the whole pipeline runs deterministically against testcontainers Postgres with no API key.

**Tech Stack:** Python 3.12, pydantic v2, psycopg 3, pytest + testcontainers. Builds on M1 (domain, repository, seed, testcontainers `postgres_conn` fixture) and M2 (`LLMClient`, `Transport`, `RawResponse`).

## Global Constraints

- Python floor **3.12**; all agent I/O shapes are pydantic v2 models under `src/logistics_agents/agents/contracts.py`.
- Agents never call the Anthropic SDK directly — they call `LLMClient.complete_structured(model, system, user, output_type, max_tokens=...)`.
- Every integration test uses testcontainers and the existing `postgres_conn` fixture; no test requires `ANTHROPIC_API_KEY` (use a scripted fake transport).
- Timestamps are timezone-aware UTC (`AwareDatetime`); the `Tracer` takes an injectable `clock` so tests are deterministic.
- The exception model is `ExceptionRecord`; the decision model is `Decision` (both from `logistics_agents.domain.models`).
- Commit after every task with a `feat:`/`chore:`/`test:` prefix.

---

### Task 1: Agent contracts

**Files:**
- Create: `src/logistics_agents/agents/__init__.py`
- Create: `src/logistics_agents/agents/contracts.py`
- Create: `tests/agents/__init__.py`
- Create: `tests/agents/test_contracts.py`

**Interfaces:**
- Consumes: `domain.models.ExceptionRecord` (M1).
- Produces:
  - `contracts.QuantityDiscrepancy(sku: str, expected: int, reported: int)`
  - `contracts.InventoryFinding(po_matched: bool, discrepancies: list[QuantityDiscrepancy], capacity_ok: bool, reasoning: str)`
  - `contracts.CarrierFinding(status: str, eta: AwareDatetime | None, delayed: bool, reasoning: str)`
  - `contracts.ExceptionFinding(exceptions: list[ExceptionRecord], reasoning: str)`
  - `contracts.OrchestrationPlan(subtasks: list[str], reasoning: str)`

- [ ] **Step 1: Write the failing test**

`tests/agents/__init__.py`: (empty file)

`tests/agents/test_contracts.py`:
```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
    QuantityDiscrepancy,
)
from logistics_agents.domain.enums import ExceptionType
from logistics_agents.domain.models import ExceptionRecord


def test_inventory_finding_round_trips():
    f = InventoryFinding(
        po_matched=True,
        discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
        capacity_ok=True,
        reasoning="short by 10",
    )
    assert InventoryFinding.model_validate_json(f.model_dump_json()) == f


def test_carrier_finding_optional_eta_and_tz_enforced():
    ok = CarrierFinding(status="in_transit", eta=None, delayed=True, reasoning="late")
    assert ok.eta is None
    with pytest.raises(ValidationError):
        CarrierFinding(
            status="in_transit",
            eta=datetime(2026, 7, 5),  # naive — rejected by AwareDatetime
            delayed=False,
            reasoning="x",
        )


def test_exception_finding_holds_typed_exceptions():
    f = ExceptionFinding(
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="9 vs 10")],
        reasoning="mismatch",
    )
    assert f.exceptions[0].type is ExceptionType.QUANTITY_MISMATCH


def test_orchestration_plan_fields():
    p = OrchestrationPlan(subtasks=["inventory", "carrier", "exception"], reasoning="decompose")
    assert len(p.subtasks) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/test_contracts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.agents'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/agents/__init__.py`: (empty file)

`src/logistics_agents/agents/contracts.py`:
```python
from pydantic import AwareDatetime, BaseModel

from logistics_agents.domain.models import ExceptionRecord


class QuantityDiscrepancy(BaseModel):
    sku: str
    expected: int
    reported: int


class InventoryFinding(BaseModel):
    po_matched: bool
    discrepancies: list[QuantityDiscrepancy]
    capacity_ok: bool
    reasoning: str


class CarrierFinding(BaseModel):
    status: str
    eta: AwareDatetime | None
    delayed: bool
    reasoning: str


class ExceptionFinding(BaseModel):
    exceptions: list[ExceptionRecord]
    reasoning: str


class OrchestrationPlan(BaseModel):
    subtasks: list[str]
    reasoning: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agents/test_contracts.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/agents/__init__.py src/logistics_agents/agents/contracts.py tests/agents
git commit -m "feat: add agent I/O contracts for findings and orchestration plan"
```

---

### Task 2: Repository + seed additions (carrier events, traces)

**Files:**
- Modify: `src/logistics_agents/data/repository.py`
- Modify: `src/logistics_agents/data/seed_data.py`
- Modify: `src/logistics_agents/data/seed.py`
- Create: `tests/data/test_repository_m3.py`

**Interfaces:**
- Consumes: `domain.models.CarrierStatus`, `domain.models.TraceRecord`; `postgres_conn` fixture.
- Produces:
  - `repository.insert_carrier_event(conn, tracking_number, event_type, status, eta, delayed, event_time) -> None`
  - `repository.get_latest_carrier_event(conn, tracking_number) -> CarrierStatus | None` — most recent by `event_time`.
  - `repository.insert_trace(conn, trace: TraceRecord) -> None` — writes to `runs` (PK `(run_id, node)`).
  - `seed_data.SEED_CARRIER_EVENTS: list[dict]` and `seed.load_seed` also loads them.

- [ ] **Step 1: Write the failing test**

`tests/data/test_repository_m3.py`:
```python
from datetime import datetime, timezone

from logistics_agents.data import repository, seed
from logistics_agents.domain.models import TraceRecord


def test_carrier_event_latest_wins(postgres_conn):
    tn = "1Z-TEST"
    repository.insert_carrier_event(
        postgres_conn, tn, "picked_up", "in_transit",
        datetime(2026, 7, 8, tzinfo=timezone.utc), False,
        datetime(2026, 7, 4, tzinfo=timezone.utc),
    )
    repository.insert_carrier_event(
        postgres_conn, tn, "delayed", "delayed",
        datetime(2026, 7, 10, tzinfo=timezone.utc), True,
        datetime(2026, 7, 6, tzinfo=timezone.utc),
    )
    status = repository.get_latest_carrier_event(postgres_conn, tn)
    assert status.status == "delayed"
    assert status.delayed is True


def test_get_latest_carrier_event_missing_returns_none(postgres_conn):
    assert repository.get_latest_carrier_event(postgres_conn, "NOPE") is None


def test_insert_trace_round_trip(postgres_conn):
    tr = TraceRecord(
        run_id="RUN-9", node="inventory", input_json="{}", output_json="{}",
        latency_ms=12, tokens=30, cost_usd=0.001, model="claude-sonnet-5",
        created_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    repository.insert_trace(postgres_conn, tr)
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT node, tokens, model FROM runs WHERE run_id = %s", ("RUN-9",))
        row = cur.fetchone()
    assert row == ("inventory", 30, "claude-sonnet-5")


def test_seed_loads_carrier_events(postgres_conn):
    seed.load_seed(postgres_conn)
    from logistics_agents.data.seed_data import SEED_CARRIER_EVENTS
    tn = SEED_CARRIER_EVENTS[0]["tracking_number"]
    assert repository.get_latest_carrier_event(postgres_conn, tn) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_repository_m3.py -v`
Expected: FAIL — `AttributeError: module 'logistics_agents.data.repository' has no attribute 'insert_carrier_event'`.

- [ ] **Step 3: Write the implementation**

Append to `src/logistics_agents/data/repository.py`:
```python
from logistics_agents.domain.models import CarrierStatus, TraceRecord


def insert_carrier_event(
    conn, tracking_number, event_type, status, eta, delayed, event_time
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO carrier_events (tracking_number, event_type, status, eta, delayed, event_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (tracking_number, event_type, status, eta, delayed, event_time),
        )
    conn.commit()


def get_latest_carrier_event(conn, tracking_number: str) -> CarrierStatus | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tracking_number, status, eta, delayed FROM carrier_events "
            "WHERE tracking_number = %s ORDER BY event_time DESC LIMIT 1",
            (tracking_number,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return CarrierStatus(tracking_number=row[0], status=row[1], eta=row[2], delayed=row[3])


def insert_trace(conn, trace: TraceRecord) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO runs
                (run_id, node, input_json, output_json, latency_ms, tokens, cost_usd, model, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                trace.run_id, trace.node, trace.input_json, trace.output_json,
                trace.latency_ms, trace.tokens, trace.cost_usd, trace.model, trace.created_at,
            ),
        )
    conn.commit()
```
Note: put the `from logistics_agents.domain.models import ...` line at the top of the file with the existing imports; the existing top import is `from logistics_agents.domain.models import (Decision, InventoryState, LineItem, PurchaseOrder)` — extend it to also import `CarrierStatus` and `TraceRecord`.

Append to `src/logistics_agents/data/seed_data.py`:
```python
SEED_CARRIER_EVENTS: list[dict] = [
    {
        "tracking_number": "1Z-1001",
        "event_type": "in_transit",
        "status": "in_transit",
        "eta": datetime(2026, 7, 5, tzinfo=timezone.utc),
        "delayed": False,
        "event_time": datetime(2026, 7, 4, tzinfo=timezone.utc),
    },
    {
        "tracking_number": "1Z-1002",
        "event_type": "delayed",
        "status": "delayed",
        "eta": datetime(2026, 7, 9, tzinfo=timezone.utc),
        "delayed": True,
        "event_time": datetime(2026, 7, 6, tzinfo=timezone.utc),
    },
]
```

Modify `src/logistics_agents/data/seed.py` `load_seed` to also insert carrier events:
```python
from logistics_agents.data.seed_data import (
    SEED_CARRIER_EVENTS,
    SEED_INVENTORY,
    SEED_PURCHASE_ORDERS,
)


def load_seed(conn) -> None:
    for po in SEED_PURCHASE_ORDERS:
        repository.upsert_purchase_order(conn, po)
    for inv in SEED_INVENTORY:
        repository.upsert_inventory(conn, inv)
    for ev in SEED_CARRIER_EVENTS:
        repository.insert_carrier_event(
            conn, ev["tracking_number"], ev["event_type"], ev["status"],
            ev["eta"], ev["delayed"], ev["event_time"],
        )
```
Note: carrier-event inserts are not idempotent (append-only log), so seed idempotency for carrier events is not asserted; the existing `test_seed_is_idempotent` only checks POs/inventory, which remain upserts — do not change that test.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_repository_m3.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the data suite to check for regressions**

Run: `uv run pytest tests/data -v`
Expected: PASS (M1 data tests + these).

- [ ] **Step 6: Commit**

```bash
git add src/logistics_agents/data/repository.py src/logistics_agents/data/seed_data.py src/logistics_agents/data/seed.py tests/data/test_repository_m3.py
git commit -m "feat: add carrier-event and trace repository functions plus carrier seed data"
```

---

### Task 3: Test helper — scripted transport fixture

**Files:**
- Create: `tests/agents/conftest.py`

**Interfaces:**
- Consumes: `llm.types.RawResponse` (M2).
- Produces (pytest fixtures, reused by Tasks 4–8):
  - `scripted_transport` — factory: given a `dict[type, BaseModel]` mapping an `output_type` to the canned value it should return, produces a `Transport` that echoes the requested model and returns the mapped value serialized. Also records every request in a returned `calls` list.

- [ ] **Step 1: Write the fixture and a self-test**

`tests/agents/conftest.py`:
```python
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
```

Add a self-test to `tests/agents/test_contracts.py` (append):
```python
def test_scripted_transport_returns_mapped_value(scripted_transport):
    from logistics_agents.llm.client import LLMClient

    plan = OrchestrationPlan(subtasks=["x"], reasoning="y")
    transport, calls = scripted_transport({OrchestrationPlan: plan})
    client = LLMClient(transport)
    result = client.complete_structured(
        model="claude-haiku-4-5", system="s", user="u", output_type=OrchestrationPlan
    )
    assert result.value == plan
    assert calls[0].model == "claude-haiku-4-5"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/agents/test_contracts.py::test_scripted_transport_returns_mapped_value -v`
Expected: FAIL — fixture `scripted_transport` not found (until conftest.py is created).

Note: create `tests/agents/conftest.py` (Step 1 already writes it); if the file is written the fixture resolves. If you wrote the test before the conftest, the RED is "fixture not found"; after writing conftest it passes.

- [ ] **Step 3: Run to verify it passes**

Run: `uv run pytest tests/agents/test_contracts.py -v`
Expected: PASS (all contract tests + the scripted-transport self-test).

- [ ] **Step 4: Commit**

```bash
git add tests/agents/conftest.py tests/agents/test_contracts.py
git commit -m "test: add scripted transport fixture for deterministic agent tests"
```

---

### Task 4: Inventory agent

**Files:**
- Create: `src/logistics_agents/agents/inventory.py`
- Create: `tests/agents/test_inventory.py`

**Interfaces:**
- Consumes: `contracts.InventoryFinding`; `data.repository`; `llm.client.LLMClient`; `domain.models.ShipmentNotification`.
- Produces: `inventory.assess(asn: ShipmentNotification, conn, llm: LLMClient, model: str) -> StructuredResult` (value is `InventoryFinding`). It loads the PO and the inventory rows for each reported SKU at the ASN's inferred DC, includes them in the prompt, and returns the LLM's `InventoryFinding`.

- [ ] **Step 1: Write the failing test**

`tests/agents/test_inventory.py`:
```python
from datetime import datetime, timezone

from logistics_agents.agents import inventory
from logistics_agents.agents.contracts import InventoryFinding, QuantityDiscrepancy
from logistics_agents.data import repository, seed
from logistics_agents.domain.models import LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient


def _asn():
    return ShipmentNotification(
        shipment_id="SH-1",
        po_id="PO-1001",
        carrier="UPS",
        tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=90)],
        reported_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        docs_present=True,
        damaged=False,
    )


def test_inventory_agent_includes_po_context_and_returns_finding(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)
    finding = InventoryFinding(
        po_matched=True,
        discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
        capacity_ok=True,
        reasoning="short by 10",
    )
    transport, calls = scripted_transport({InventoryFinding: finding})
    llm = LLMClient(transport)

    result = inventory.assess(_asn(), postgres_conn, llm, model="claude-sonnet-5")

    assert result.value == finding
    assert result.meta.model == "claude-sonnet-5"
    # The prompt must carry the PO's expected quantity (100) and the reported quantity (90).
    prompt = calls[0].user
    assert "PO-1001" in prompt
    assert "100" in prompt and "90" in prompt
    assert calls[0].output_type is InventoryFinding
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/test_inventory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.agents.inventory'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/agents/inventory.py`:
```python
import json

from logistics_agents.agents.contracts import InventoryFinding
from logistics_agents.data import repository
from logistics_agents.domain.models import ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are an inventory reconciliation specialist for a logistics decisioning system. "
    "Given an inbound shipment notification, its purchase order, and current inventory, "
    "determine whether the PO matched, list per-SKU quantity discrepancies, and judge "
    "whether the destination DC has capacity. Respond only via the structured schema."
)


def _build_user_prompt(asn: ShipmentNotification, po_dict, inventory_rows) -> str:
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "purchase_order": po_dict,
        "inventory": inventory_rows,
    }
    return json.dumps(context, indent=2, default=str)


def assess(asn: ShipmentNotification, conn, llm: LLMClient, model: str) -> StructuredResult:
    po = repository.get_purchase_order(conn, asn.po_id) if asn.po_id else None
    po_dict = po.model_dump(mode="json") if po is not None else None

    dc_id = po.destination_dc if po is not None else None
    inventory_rows = []
    if dc_id is not None:
        for item in asn.reported_items:
            inv = repository.get_inventory(conn, item.sku, dc_id)
            if inv is not None:
                inventory_rows.append(inv.model_dump(mode="json"))

    user = _build_user_prompt(asn, po_dict, inventory_rows)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=InventoryFinding
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agents/test_inventory.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/agents/inventory.py tests/agents/test_inventory.py
git commit -m "feat: add inventory reconciliation agent"
```

---

### Task 5: Carrier agent

**Files:**
- Create: `src/logistics_agents/agents/carrier.py`
- Create: `tests/agents/test_carrier.py`

**Interfaces:**
- Consumes: `contracts.CarrierFinding`; `data.repository.get_latest_carrier_event`; `LLMClient`.
- Produces: `carrier.assess(asn, conn, llm, model) -> StructuredResult` (value is `CarrierFinding`). Looks up the latest carrier event for the ASN's tracking number, includes it in the prompt, returns the LLM's `CarrierFinding`.

- [ ] **Step 1: Write the failing test**

`tests/agents/test_carrier.py`:
```python
from datetime import datetime, timezone

from logistics_agents.agents import carrier
from logistics_agents.agents.contracts import CarrierFinding
from logistics_agents.data import seed
from logistics_agents.domain.models import LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient


def _asn(tracking_number="1Z-1002"):
    return ShipmentNotification(
        shipment_id="SH-2",
        po_id="PO-1002",
        carrier="FedEx",
        tracking_number=tracking_number,
        reported_items=[LineItem(sku="SKU-B", quantity=50)],
        reported_date=datetime(2026, 7, 6, tzinfo=timezone.utc),
        docs_present=True,
        damaged=False,
    )


def test_carrier_agent_includes_tracking_status_and_returns_finding(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)  # seeds 1Z-1002 as delayed
    finding = CarrierFinding(status="delayed", eta=None, delayed=True, reasoning="carrier reported delay")
    transport, calls = scripted_transport({CarrierFinding: finding})
    llm = LLMClient(transport)

    result = carrier.assess(_asn(), postgres_conn, llm, model="claude-haiku-4-5")

    assert result.value == finding
    prompt = calls[0].user
    assert "1Z-1002" in prompt
    assert "delayed" in prompt  # the looked-up carrier status appears in the prompt
    assert calls[0].output_type is CarrierFinding


def test_carrier_agent_handles_unknown_tracking(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)
    finding = CarrierFinding(status="unknown", eta=None, delayed=False, reasoning="no tracking data")
    transport, calls = scripted_transport({CarrierFinding: finding})
    llm = LLMClient(transport)

    result = carrier.assess(_asn(tracking_number="1Z-NONE"), postgres_conn, llm, model="claude-haiku-4-5")
    assert result.value.status == "unknown"
    assert "1Z-NONE" in calls[0].user
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/test_carrier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.agents.carrier'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/agents/carrier.py`:
```python
import json

from logistics_agents.agents.contracts import CarrierFinding
from logistics_agents.data import repository
from logistics_agents.domain.models import ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are a carrier-tracking specialist for a logistics decisioning system. "
    "Given an inbound shipment notification and the latest carrier tracking event, "
    "summarize the shipment's transit status, ETA, and whether it is delayed. "
    "If no tracking data exists, report status 'unknown'. Respond only via the structured schema."
)


def assess(asn: ShipmentNotification, conn, llm: LLMClient, model: str) -> StructuredResult:
    status = repository.get_latest_carrier_event(conn, asn.tracking_number)
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "carrier_status": status.model_dump(mode="json") if status is not None else None,
        "tracking_number": asn.tracking_number,
    }
    user = json.dumps(context, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=CarrierFinding
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agents/test_carrier.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/agents/carrier.py tests/agents/test_carrier.py
git commit -m "feat: add carrier tracking agent"
```

---

### Task 6: Exception + orchestrator + synthesis agents

**Files:**
- Create: `src/logistics_agents/agents/exception.py`
- Create: `src/logistics_agents/agents/orchestrator.py`
- Create: `src/logistics_agents/agents/synthesis.py`
- Create: `tests/agents/test_reasoning_agents.py`

**Interfaces:**
- Consumes: `contracts.*`; `domain.models.{Decision, PurchaseOrder, ShipmentNotification}`; `LLMClient`.
- Produces:
  - `exception.detect(asn, po, inventory_finding, carrier_finding, llm, model) -> StructuredResult` (value `ExceptionFinding`).
  - `orchestrator.plan(asn, llm, model) -> StructuredResult` (value `OrchestrationPlan`).
  - `synthesis.decide(asn, inventory_finding, carrier_finding, exception_finding, llm, model) -> StructuredResult` (value `Decision`).

These agents call no database — they reason over the passed-in objects.

- [ ] **Step 1: Write the failing test**

`tests/agents/test_reasoning_agents.py`:
```python
from datetime import datetime, timezone

from logistics_agents.agents import exception, orchestrator, synthesis
from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
    QuantityDiscrepancy,
)
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord, LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient


def _asn():
    return ShipmentNotification(
        shipment_id="SH-3", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=90)],
        reported_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        docs_present=True, damaged=False,
    )


INV = InventoryFinding(
    po_matched=True,
    discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
    capacity_ok=True, reasoning="short",
)
CAR = CarrierFinding(status="delayed", eta=None, delayed=True, reasoning="late")


def test_orchestrator_returns_plan(scripted_transport):
    plan = OrchestrationPlan(subtasks=["inventory", "carrier", "exception"], reasoning="decompose")
    transport, calls = scripted_transport({OrchestrationPlan: plan})
    result = orchestrator.plan(_asn(), LLMClient(transport), model="claude-opus-4-8")
    assert result.value == plan
    assert "SH-3" in calls[0].user


def test_exception_agent_reasons_over_peer_findings(scripted_transport):
    finding = ExceptionFinding(
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="90 vs 100")],
        reasoning="qty + delay",
    )
    transport, calls = scripted_transport({ExceptionFinding: finding})
    result = exception.detect(_asn(), None, INV, CAR, LLMClient(transport), model="claude-sonnet-5")
    assert result.value == finding
    # Peer findings must be present in the prompt.
    assert "delayed" in calls[0].user
    assert "SKU-A" in calls[0].user


def test_synthesis_returns_decision(scripted_transport):
    decision = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="90 vs 100")],
        recommended_actions=["notify supplier"], confidence=0.8, reasoning="hold for review",
    )
    exc = ExceptionFinding(exceptions=decision.exceptions, reasoning="x")
    transport, calls = scripted_transport({Decision: decision})
    result = synthesis.decide(_asn(), INV, CAR, exc, LLMClient(transport), model="claude-opus-4-8")
    assert result.value == decision
    assert calls[0].output_type is Decision
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/test_reasoning_agents.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.agents.exception'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/agents/orchestrator.py`:
```python
import json

from logistics_agents.agents.contracts import OrchestrationPlan
from logistics_agents.domain.models import ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are the orchestrator of a logistics decisioning system. Given an inbound shipment "
    "notification, decompose the work into the specialist subtasks needed to reach an "
    "accept/hold/reroute/escalate decision (inventory reconciliation, carrier tracking, "
    "exception detection). Respond only via the structured schema."
)


def plan(asn: ShipmentNotification, llm: LLMClient, model: str) -> StructuredResult:
    user = json.dumps({"shipment_notification": asn.model_dump(mode="json")}, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=OrchestrationPlan
    )
```

`src/logistics_agents/agents/exception.py`:
```python
import json

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
)
from logistics_agents.domain.models import PurchaseOrder, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are an exception-detection specialist for a logistics decisioning system. Given the "
    "shipment notification, its purchase order, and the inventory and carrier findings, detect "
    "typed exceptions (QUANTITY_MISMATCH, LATE_DELIVERY, UNKNOWN_PO, OVERCAPACITY, MISSING_DOCS, "
    "DAMAGED). Respond only via the structured schema."
)


def detect(
    asn: ShipmentNotification,
    po: PurchaseOrder | None,
    inventory_finding: InventoryFinding,
    carrier_finding: CarrierFinding,
    llm: LLMClient,
    model: str,
) -> StructuredResult:
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "purchase_order": po.model_dump(mode="json") if po is not None else None,
        "inventory_finding": inventory_finding.model_dump(mode="json"),
        "carrier_finding": carrier_finding.model_dump(mode="json"),
    }
    user = json.dumps(context, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=ExceptionFinding
    )
```

`src/logistics_agents/agents/synthesis.py`:
```python
import json

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
)
from logistics_agents.domain.models import Decision, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are the synthesis agent for a logistics decisioning system. Given the shipment "
    "notification and the inventory, carrier, and exception findings, produce the final "
    "structured decision: label (ACCEPT/HOLD/REROUTE/ESCALATE), the confirmed exceptions, "
    "recommended actions, a confidence in [0,1], and reasoning. Respond only via the schema."
)


def decide(
    asn: ShipmentNotification,
    inventory_finding: InventoryFinding,
    carrier_finding: CarrierFinding,
    exception_finding: ExceptionFinding,
    llm: LLMClient,
    model: str,
) -> StructuredResult:
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "inventory_finding": inventory_finding.model_dump(mode="json"),
        "carrier_finding": carrier_finding.model_dump(mode="json"),
        "exception_finding": exception_finding.model_dump(mode="json"),
    }
    user = json.dumps(context, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=Decision
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agents/test_reasoning_agents.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/agents/exception.py src/logistics_agents/agents/orchestrator.py src/logistics_agents/agents/synthesis.py tests/agents/test_reasoning_agents.py
git commit -m "feat: add orchestrator, exception, and synthesis agents"
```

---

### Task 7: Tracing

**Files:**
- Create: `src/logistics_agents/tracing/__init__.py`
- Create: `src/logistics_agents/tracing/tracer.py`
- Create: `tests/tracing/__init__.py`
- Create: `tests/tracing/test_tracer.py`

**Interfaces:**
- Consumes: `domain.models.TraceRecord`; `data.repository.insert_trace`; `llm.types.CallMeta`.
- Produces:
  - `tracer.Tracer(run_id: str, conn=None, clock=<utc-now callable>)` with:
    - `record(node: str, input_obj, output_obj, meta: CallMeta) -> TraceRecord` — serializes input/output pydantic models to JSON, builds a `TraceRecord` (tokens = `meta.input_tokens + meta.output_tokens`), appends to `self.records`, and if `conn` is set, persists via `repository.insert_trace`.

- [ ] **Step 1: Write the failing test**

`tests/tracing/__init__.py`: (empty file)

`tests/tracing/test_tracer.py`:
```python
from datetime import datetime, timezone

from logistics_agents.agents.contracts import OrchestrationPlan
from logistics_agents.domain.models import ShipmentNotification, LineItem
from logistics_agents.llm.types import CallMeta
from logistics_agents.tracing.tracer import Tracer

FIXED = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def _meta():
    return CallMeta(model="claude-sonnet-5", input_tokens=100, output_tokens=40, cost_usd=0.0015, latency_ms=250)


def test_record_builds_trace_with_summed_tokens():
    tracer = Tracer(run_id="RUN-T", clock=lambda: FIXED)
    inp = OrchestrationPlan(subtasks=["a"], reasoning="in")
    out = OrchestrationPlan(subtasks=["b"], reasoning="out")
    tr = tracer.record("orchestrator", inp, out, _meta())
    assert tr.run_id == "RUN-T"
    assert tr.node == "orchestrator"
    assert tr.tokens == 140  # 100 + 40
    assert tr.cost_usd == 0.0015
    assert tr.created_at == FIXED
    assert '"reasoning":"out"' in tr.output_json.replace(" ", "")
    assert len(tracer.records) == 1


def test_record_persists_when_conn_present(postgres_conn):
    from logistics_agents.data import repository

    tracer = Tracer(run_id="RUN-P", conn=postgres_conn, clock=lambda: FIXED)
    plan = OrchestrationPlan(subtasks=["a"], reasoning="x")
    tracer.record("orchestrator", plan, plan, _meta())
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT node, tokens FROM runs WHERE run_id = %s", ("RUN-P",))
        assert cur.fetchone() == ("orchestrator", 140)
```

Note: `tests/tracing/test_tracer.py` uses the `postgres_conn` fixture from `tests/data/conftest.py`. Move that fixture so it is visible to `tests/tracing/`: relocate the `postgres_container` and `postgres_conn` fixtures from `tests/data/conftest.py` into a top-level `tests/conftest.py` (pytest makes fixtures in `tests/conftest.py` available to all subpackages). Delete them from `tests/data/conftest.py` after moving. Run `uv run pytest tests/data -v` afterward to confirm the data tests still resolve the fixtures.

- [ ] **Step 2: Move the shared fixture, then run the test to verify it fails**

Relocate `postgres_container` + `postgres_conn` (and their imports: `psycopg`, `pytest`, `PostgresContainer`, `apply_schema`) from `tests/data/conftest.py` to a new `tests/conftest.py`. Then run:
Run: `uv run pytest tests/tracing/test_tracer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.tracing'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/tracing/__init__.py`: (empty file)

`src/logistics_agents/tracing/tracer.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/tracing/test_tracer.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the data suite to confirm the fixture move didn't break M1 tests**

Run: `uv run pytest tests/data -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/logistics_agents/tracing tests/tracing tests/conftest.py tests/data/conftest.py
git commit -m "feat: add per-node Tracer and relocate shared postgres fixture to tests/conftest.py"
```

---

### Task 8: Fixed-DAG pipeline runner

**Files:**
- Create: `src/logistics_agents/orchestration/__init__.py`
- Create: `src/logistics_agents/orchestration/runner.py`
- Create: `tests/orchestration/__init__.py`
- Create: `tests/orchestration/test_runner.py`

**Interfaces:**
- Consumes: all five agents (Tasks 4–6); `tracing.Tracer` (Task 7); `data.repository.{get_purchase_order, insert_decision}`.
- Produces:
  - `runner.run_pipeline(asn, conn, llm, model, run_id, tracer) -> Decision` — runs orchestrator → inventory → carrier → exception → synthesis, records a trace at each node, persists the final decision via `repository.insert_decision`, and returns the `Decision`.

- [ ] **Step 1: Write the failing test**

`tests/orchestration/__init__.py`: (empty file)

`tests/orchestration/test_runner.py`:
```python
from datetime import datetime, timezone

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
    QuantityDiscrepancy,
)
from logistics_agents.data import repository, seed
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord, LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.orchestration import runner
from logistics_agents.tracing.tracer import Tracer

FIXED = datetime(2026, 7, 9, tzinfo=timezone.utc)


def _asn():
    return ShipmentNotification(
        shipment_id="SH-99", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=90)],
        reported_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        docs_present=True, damaged=False,
    )


def _full_script():
    decision = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="90 vs 100")],
        recommended_actions=["notify supplier"], confidence=0.8, reasoning="hold",
    )
    return {
        OrchestrationPlan: OrchestrationPlan(subtasks=["inventory", "carrier", "exception"], reasoning="d"),
        InventoryFinding: InventoryFinding(
            po_matched=True,
            discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
            capacity_ok=True, reasoning="short",
        ),
        CarrierFinding: CarrierFinding(status="in_transit", eta=None, delayed=False, reasoning="ok"),
        ExceptionFinding: ExceptionFinding(exceptions=decision.exceptions, reasoning="qty"),
        Decision: decision,
    }, decision


def test_pipeline_returns_decision_persists_it_and_traces_five_nodes(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)
    script, expected = _full_script()
    transport, calls = scripted_transport(script)
    llm = LLMClient(transport)
    tracer = Tracer(run_id="RUN-99", conn=postgres_conn, clock=lambda: FIXED)

    result = runner.run_pipeline(
        _asn(), postgres_conn, llm, model="claude-opus-4-8", run_id="RUN-99", tracer=tracer
    )

    # Returns and persists the synthesized decision.
    assert result == expected
    assert repository.get_decision(postgres_conn, "RUN-99") == expected

    # One trace per node, in DAG order.
    nodes = [tr.node for tr in tracer.records]
    assert nodes == ["orchestrator", "inventory", "carrier", "exception", "synthesis"]

    # All five agents ran against the requested model, and traces were persisted.
    assert all(c.model == "claude-opus-4-8" for c in calls)
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM runs WHERE run_id = %s", ("RUN-99",))
        assert cur.fetchone()[0] == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/orchestration/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.orchestration'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/orchestration/__init__.py`: (empty file)

`src/logistics_agents/orchestration/runner.py`:
```python
from logistics_agents.agents import carrier, exception, inventory, orchestrator, synthesis
from logistics_agents.data import repository
from logistics_agents.domain.models import Decision, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.tracing.tracer import Tracer


def run_pipeline(
    asn: ShipmentNotification,
    conn,
    llm: LLMClient,
    model: str,
    run_id: str,
    tracer: Tracer,
) -> Decision:
    plan = orchestrator.plan(asn, llm, model)
    tracer.record("orchestrator", asn, plan.value, plan.meta)

    inv = inventory.assess(asn, conn, llm, model)
    tracer.record("inventory", asn, inv.value, inv.meta)

    car = carrier.assess(asn, conn, llm, model)
    tracer.record("carrier", asn, car.value, car.meta)

    po = repository.get_purchase_order(conn, asn.po_id) if asn.po_id else None
    exc = exception.detect(asn, po, inv.value, car.value, llm, model)
    tracer.record("exception", asn, exc.value, exc.meta)

    decision = synthesis.decide(asn, inv.value, car.value, exc.value, llm, model)
    tracer.record("synthesis", asn, decision.value, decision.meta)

    repository.insert_decision(conn, run_id, asn.shipment_id, decision.value)
    return decision.value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/orchestration/test_runner.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Run the full milestone suite**

Run: `uv run pytest -v`
Expected: PASS — all M1 + M2 + M3 tests (M2 live test skipped).

- [ ] **Step 6: Commit**

```bash
git add src/logistics_agents/orchestration tests/orchestration
git commit -m "feat: add fixed-DAG pipeline runner wiring all five agents with tracing"
```

---

## Self-Review

**Spec coverage (Milestone 3 scope = spec §3 architecture, §4 agents, milestone 15.3):**
- Orchestrator agent that decomposes (§3/§4): Task 6 (`orchestrator.plan` → `OrchestrationPlan`). ✅
- Three specialists — inventory reconciliation, carrier tracking, exception detection (§4): Tasks 4, 5, 6. ✅
- Synthesis agent → structured `Decision` (§3): Task 6 (`synthesis.decide`). ✅
- Fixed DAG, deterministic routing, LLM-backed nodes (§3): Task 8 runner; routing is hard-coded, each node calls `LLMClient`. ✅
- Every node emits a trace record persisted to `runs` (§3 tracing): Task 7 `Tracer` + Task 2 `insert_trace`; wired in Task 8. ✅
- Decision persisted to `decisions` (§3): Task 8 calls `repository.insert_decision`. ✅
- Carrier data via mock backed by `carrier_events` (§8): Task 2 `get_latest_carrier_event` + seed. ✅
- Deterministic, key-free tests (Global Constraint): scripted transport (Task 3) + testcontainers throughout. ✅

Out of scope (correctly deferred): eval dataset/graders (M4), CI (M5), FastAPI/SSE/budget (M6), dashboard (M7), Terraform (M8). Real-model runs and fixture recording are an M4 concern — M3 proves the wiring with scripted outputs. Effort/adaptive-thinking knobs remain unused here (the runner passes only `model` + default `max_tokens`); wiring them is a natural M4 refinement once model-comparison runs need deeper reasoning, and they will automatically enter the cache key (M2's generic `request_key`).

**Placeholder scan:** No TBD/TODO. Every code step is complete. Prompts are real system strings, not placeholders.

**Type consistency:** Agent functions all return `StructuredResult` (M2) with `value` typed to their contract. The runner (Task 8) reads `.value`/`.meta` on each, matching. `Tracer.record(node, input_obj, output_obj, meta)` (Task 7) is called with exactly those args in Task 8. `insert_trace(conn, trace)` (Task 2) matches `Tracer`'s call. `get_latest_carrier_event` returns `CarrierStatus | None`, consumed by the carrier agent (Task 5). The shared `postgres_conn` fixture relocation (Task 7) keeps every DB-backed test resolving the same fixture.
