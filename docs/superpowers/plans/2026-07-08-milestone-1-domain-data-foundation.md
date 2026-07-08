# Milestone 1: Domain + Data Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the typed domain models, dockerized Postgres + Redpanda infrastructure, database schema, repository layer, deterministic seed loader, and Kafka wrappers that every later milestone builds on.

**Architecture:** Pydantic v2 models are the single source of truth for all data shapes. Postgres holds logistics data (POs, inventory, shipments, carrier events) plus operational tables (decisions, runs, budget_ledger). A thin psycopg-3 repository layer reads/writes these. A seed loader populates deterministic fixtures used by both demos and (later) evals. Redpanda provides the Kafka-compatible `shipment.notifications` topic. Integration tests run against ephemeral containers via testcontainers, so they are hermetic and CI-friendly.

**Tech Stack:** Python 3.12, `uv` (package/venv manager), pydantic v2, psycopg 3, confluent-kafka, pytest, testcontainers-python, Postgres 16, Redpanda.

## Global Constraints

- Python version floor: **3.12**.
- All data shapes are **pydantic v2** models in `src/logistics_agents/domain/` — no bare dicts crossing module boundaries.
- Money/quantities that must be exact use `int` (whole units); no floats for counts.
- Timestamps are timezone-aware UTC (`datetime` with `tzinfo`).
- Every integration test uses **testcontainers** — no reliance on a developer's already-running services.
- Package/module root is `logistics_agents` under `src/` (src-layout).
- Commit after every task with a `feat:`/`chore:`/`test:` prefixed message.

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/logistics_agents/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `README.md`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: importable package `logistics_agents` with `__version__: str`; a working `uv run pytest` command.

- [ ] **Step 1: Write the failing test**

`tests/test_smoke.py`:
```python
import logistics_agents


def test_package_exposes_version():
    assert isinstance(logistics_agents.__version__, str)
    assert logistics_agents.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents'` (package not yet created).

- [ ] **Step 3: Create the project files**

`pyproject.toml`:
```toml
[project]
name = "logistics-agents"
version = "0.1.0"
description = "Multi-agent logistics decisioning system with eval infrastructure"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.6",
    "psycopg[binary]>=3.1",
    "confluent-kafka>=2.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "testcontainers[postgres]>=4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/logistics_agents"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`src/logistics_agents/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/__init__.py`: (empty file)

`README.md`:
```markdown
# logistics_agents

Multi-agent logistics decisioning system with eval infrastructure.

## Dev setup
```
uv sync --extra dev
uv run pytest
```
```

- [ ] **Step 4: Install deps and run the test**

Run: `uv sync --extra dev && uv run pytest tests/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/logistics_agents/__init__.py tests/__init__.py tests/test_smoke.py README.md
git commit -m "chore: scaffold project with uv, pydantic, psycopg, pytest"
```

---

### Task 2: Domain enums + PurchaseOrder + ShipmentNotification

**Files:**
- Create: `src/logistics_agents/domain/__init__.py`
- Create: `src/logistics_agents/domain/enums.py`
- Create: `src/logistics_agents/domain/models.py`
- Create: `tests/domain/__init__.py`
- Create: `tests/domain/test_models_core.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces:
  - `enums.ExceptionType` (StrEnum): `QUANTITY_MISMATCH, LATE_DELIVERY, UNKNOWN_PO, OVERCAPACITY, MISSING_DOCS, DAMAGED`.
  - `enums.DecisionLabel` (StrEnum): `ACCEPT, HOLD, REROUTE, ESCALATE`.
  - `models.LineItem(sku: str, quantity: int)`.
  - `models.PurchaseOrder(po_id: str, supplier: str, expected_items: list[LineItem], expected_date: datetime, destination_dc: str)`.
  - `models.ShipmentNotification(shipment_id: str, po_id: str | None, carrier: str, tracking_number: str, reported_items: list[LineItem], reported_date: datetime, docs_present: bool, damaged: bool)`.

- [ ] **Step 1: Write the failing test**

`tests/domain/test_models_core.py`:
```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import (
    LineItem,
    PurchaseOrder,
    ShipmentNotification,
)


def test_enum_values():
    assert ExceptionType.QUANTITY_MISMATCH == "QUANTITY_MISMATCH"
    assert DecisionLabel.ACCEPT == "ACCEPT"
    assert set(DecisionLabel) == {
        DecisionLabel.ACCEPT,
        DecisionLabel.HOLD,
        DecisionLabel.REROUTE,
        DecisionLabel.ESCALATE,
    }


def test_line_item_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        LineItem(sku="A1", quantity=-1)


def test_purchase_order_round_trips_through_json():
    po = PurchaseOrder(
        po_id="PO-1",
        supplier="Acme",
        expected_items=[LineItem(sku="A1", quantity=10)],
        expected_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        destination_dc="DC-EAST",
    )
    restored = PurchaseOrder.model_validate_json(po.model_dump_json())
    assert restored == po


def test_shipment_notification_allows_unknown_po():
    asn = ShipmentNotification(
        shipment_id="SH-1",
        po_id=None,
        carrier="UPS",
        tracking_number="1Z999",
        reported_items=[LineItem(sku="A1", quantity=9)],
        reported_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
        docs_present=True,
        damaged=False,
    )
    assert asn.po_id is None
    assert asn.reported_items[0].quantity == 9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_models_core.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.domain'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/domain/__init__.py`: (empty file)

`tests/domain/__init__.py`: (empty file)

`src/logistics_agents/domain/enums.py`:
```python
from enum import StrEnum


class ExceptionType(StrEnum):
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    LATE_DELIVERY = "LATE_DELIVERY"
    UNKNOWN_PO = "UNKNOWN_PO"
    OVERCAPACITY = "OVERCAPACITY"
    MISSING_DOCS = "MISSING_DOCS"
    DAMAGED = "DAMAGED"


class DecisionLabel(StrEnum):
    ACCEPT = "ACCEPT"
    HOLD = "HOLD"
    REROUTE = "REROUTE"
    ESCALATE = "ESCALATE"
```

`src/logistics_agents/domain/models.py`:
```python
from datetime import datetime

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    sku: str
    quantity: int = Field(ge=0)


class PurchaseOrder(BaseModel):
    po_id: str
    supplier: str
    expected_items: list[LineItem]
    expected_date: datetime
    destination_dc: str


class ShipmentNotification(BaseModel):
    shipment_id: str
    po_id: str | None
    carrier: str
    tracking_number: str
    reported_items: list[LineItem]
    reported_date: datetime
    docs_present: bool
    damaged: bool
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain/test_models_core.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/domain tests/domain
git commit -m "feat: add domain enums, LineItem, PurchaseOrder, ShipmentNotification"
```

---

### Task 3: Result models — InventoryState, CarrierStatus, Exception, Decision, TraceRecord

**Files:**
- Modify: `src/logistics_agents/domain/models.py`
- Create: `tests/domain/test_models_results.py`

**Interfaces:**
- Consumes: `enums.ExceptionType`, `enums.DecisionLabel`, `models.LineItem` (Task 2).
- Produces:
  - `models.InventoryState(sku: str, dc_id: str, on_hand: int, reserved: int, capacity: int)` with computed `available_capacity: int` property = `capacity - on_hand`.
  - `models.CarrierStatus(tracking_number: str, status: str, eta: datetime | None, delayed: bool)`.
  - `models.Exception(type: ExceptionType, detail: str)`.
  - `models.Decision(label: DecisionLabel, exceptions: list[Exception], recommended_actions: list[str], confidence: float in [0,1], reasoning: str)`.
  - `models.TraceRecord(run_id: str, node: str, input_json: str, output_json: str, latency_ms: int, tokens: int, cost_usd: float, model: str, created_at: datetime)`.

- [ ] **Step 1: Write the failing test**

`tests/domain/test_models_results.py`:
```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import (
    CarrierStatus,
    Decision,
    Exception,
    InventoryState,
    TraceRecord,
)


def test_inventory_available_capacity():
    inv = InventoryState(sku="A1", dc_id="DC-EAST", on_hand=30, reserved=5, capacity=100)
    assert inv.available_capacity == 70


def test_decision_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        Decision(
            label=DecisionLabel.ACCEPT,
            exceptions=[],
            recommended_actions=[],
            confidence=1.5,
            reasoning="x",
        )


def test_decision_with_exceptions_round_trips():
    d = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[Exception(type=ExceptionType.QUANTITY_MISMATCH, detail="9 vs 10")],
        recommended_actions=["notify supplier"],
        confidence=0.8,
        reasoning="short by one unit",
    )
    restored = Decision.model_validate_json(d.model_dump_json())
    assert restored == d
    assert restored.exceptions[0].type is ExceptionType.QUANTITY_MISMATCH


def test_carrier_status_optional_eta():
    cs = CarrierStatus(tracking_number="1Z999", status="in_transit", eta=None, delayed=True)
    assert cs.eta is None


def test_trace_record_fields():
    tr = TraceRecord(
        run_id="RUN-1",
        node="inventory",
        input_json="{}",
        output_json="{}",
        latency_ms=120,
        tokens=350,
        cost_usd=0.0021,
        model="claude-sonnet-5",
        created_at=datetime(2026, 7, 8, tzinfo=timezone.utc),
    )
    assert tr.node == "inventory"
    assert tr.tokens == 350
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_models_results.py -v`
Expected: FAIL — `ImportError: cannot import name 'InventoryState'`.

- [ ] **Step 3: Append the implementation**

Append to `src/logistics_agents/domain/models.py`:
```python
from pydantic import computed_field

from logistics_agents.domain.enums import DecisionLabel, ExceptionType


class InventoryState(BaseModel):
    sku: str
    dc_id: str
    on_hand: int = Field(ge=0)
    reserved: int = Field(ge=0)
    capacity: int = Field(ge=0)

    @computed_field
    @property
    def available_capacity(self) -> int:
        return self.capacity - self.on_hand


class CarrierStatus(BaseModel):
    tracking_number: str
    status: str
    eta: datetime | None
    delayed: bool


class Exception(BaseModel):
    type: ExceptionType
    detail: str


class Decision(BaseModel):
    label: DecisionLabel
    exceptions: list[Exception]
    recommended_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class TraceRecord(BaseModel):
    run_id: str
    node: str
    input_json: str
    output_json: str
    latency_ms: int = Field(ge=0)
    tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    model: str
    created_at: datetime
```

Note: move the `from pydantic import ...` and `from logistics_agents.domain.enums import ...` lines to the top of the file with the existing imports (do not leave mid-file imports). Final top-of-file imports should read:
```python
from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
```

- [ ] **Step 4: Run all domain tests to verify they pass**

Run: `uv run pytest tests/domain -v`
Expected: PASS (all Task 2 + Task 3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/domain/models.py tests/domain/test_models_results.py
git commit -m "feat: add InventoryState, CarrierStatus, Exception, Decision, TraceRecord models"
```

---

### Task 4: docker-compose + database schema

**Files:**
- Create: `docker-compose.yml`
- Create: `src/logistics_agents/data/__init__.py`
- Create: `src/logistics_agents/data/schema.sql`
- Create: `src/logistics_agents/data/apply_schema.py`
- Create: `tests/data/__init__.py`
- Create: `tests/data/conftest.py`
- Create: `tests/data/test_schema.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure SQL + a runner).
- Produces:
  - `apply_schema.apply_schema(conn) -> None` — executes `schema.sql` against an open psycopg connection.
  - A `postgres_conn` pytest fixture (in `tests/data/conftest.py`) yielding a psycopg connection to an ephemeral Postgres with the schema applied.
  - Tables: `purchase_orders`, `inventory`, `shipments`, `carrier_events`, `decisions`, `runs`, `budget_ledger`.

- [ ] **Step 1: Write the failing test**

`tests/data/__init__.py`: (empty file)

`tests/data/conftest.py`:
```python
import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from logistics_agents.data.apply_schema import apply_schema


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture
def postgres_conn(postgres_container):
    dsn = postgres_container.get_connection_url().replace("postgresql+psycopg2", "postgresql")
    with psycopg.connect(dsn) as conn:
        apply_schema(conn)
        yield conn
        conn.rollback()
```

`tests/data/test_schema.py`:
```python
EXPECTED_TABLES = {
    "purchase_orders",
    "inventory",
    "shipments",
    "carrier_events",
    "decisions",
    "runs",
    "budget_ledger",
}


def test_all_tables_created(postgres_conn):
    with postgres_conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = {row[0] for row in cur.fetchall()}
    assert EXPECTED_TABLES.issubset(tables)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logistics_agents.data'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/data/__init__.py`: (empty file)

`docker-compose.yml`:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: logistics
      POSTGRES_PASSWORD: logistics
      POSTGRES_DB: logistics
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redpanda:
    image: redpandadata/redpanda:v24.1.1
    command:
      - redpanda
      - start
      - --smp=1
      - --overprovisioned
      - --node-id=0
      - --kafka-addr=PLAINTEXT://0.0.0.0:9092
      - --advertise-kafka-addr=PLAINTEXT://localhost:9092
    ports:
      - "9092:9092"

volumes:
  pgdata:
```

`src/logistics_agents/data/schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id          TEXT PRIMARY KEY,
    supplier       TEXT NOT NULL,
    expected_items JSONB NOT NULL,
    expected_date  TIMESTAMPTZ NOT NULL,
    destination_dc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    sku      TEXT NOT NULL,
    dc_id    TEXT NOT NULL,
    on_hand  INTEGER NOT NULL,
    reserved INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    PRIMARY KEY (sku, dc_id)
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id     TEXT PRIMARY KEY,
    po_id           TEXT,
    carrier         TEXT NOT NULL,
    tracking_number TEXT NOT NULL,
    reported_items  JSONB NOT NULL,
    reported_date   TIMESTAMPTZ NOT NULL,
    docs_present    BOOLEAN NOT NULL,
    damaged         BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS carrier_events (
    tracking_number TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    status          TEXT NOT NULL,
    eta             TIMESTAMPTZ,
    delayed         BOOLEAN NOT NULL,
    event_time      TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    run_id             TEXT PRIMARY KEY,
    shipment_id        TEXT NOT NULL,
    label              TEXT NOT NULL,
    exceptions         JSONB NOT NULL,
    recommended_actions JSONB NOT NULL,
    confidence         DOUBLE PRECISION NOT NULL,
    reasoning          TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT NOT NULL,
    node        TEXT NOT NULL,
    input_json  TEXT NOT NULL,
    output_json TEXT NOT NULL,
    latency_ms  INTEGER NOT NULL,
    tokens      INTEGER NOT NULL,
    cost_usd    DOUBLE PRECISION NOT NULL,
    model       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (run_id, node)
);

CREATE TABLE IF NOT EXISTS budget_ledger (
    id         BIGSERIAL PRIMARY KEY,
    run_id     TEXT NOT NULL,
    cost_usd   DOUBLE PRECISION NOT NULL,
    source     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`src/logistics_agents/data/apply_schema.py`:
```python
from importlib import resources

import psycopg


def _schema_sql() -> str:
    return resources.files("logistics_agents.data").joinpath("schema.sql").read_text()


def apply_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(_schema_sql())
    conn.commit()
```

Add `schema.sql` to the wheel package data. Append to `pyproject.toml`:
```toml
[tool.hatch.build.targets.wheel.force-include]
"src/logistics_agents/data/schema.sql" = "logistics_agents/data/schema.sql"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_schema.py -v`
Expected: PASS (Docker must be running; testcontainers pulls `postgres:16-alpine`).

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml src/logistics_agents/data tests/data pyproject.toml
git commit -m "feat: add docker-compose and Postgres schema with apply_schema runner"
```

---

### Task 5: Repository layer

**Files:**
- Create: `src/logistics_agents/data/repository.py`
- Create: `tests/data/test_repository.py`

**Interfaces:**
- Consumes: domain models (Tasks 2–3); `postgres_conn` fixture (Task 4).
- Produces:
  - `repository.upsert_purchase_order(conn, po: PurchaseOrder) -> None`
  - `repository.get_purchase_order(conn, po_id: str) -> PurchaseOrder | None`
  - `repository.upsert_inventory(conn, inv: InventoryState) -> None`
  - `repository.get_inventory(conn, sku: str, dc_id: str) -> InventoryState | None`
  - `repository.insert_decision(conn, run_id: str, shipment_id: str, decision: Decision) -> None`
  - `repository.get_decision(conn, run_id: str) -> Decision | None`

- [ ] **Step 1: Write the failing test**

`tests/data/test_repository.py`:
```python
from datetime import datetime, timezone

from logistics_agents.data import repository
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import (
    Decision,
    Exception,
    InventoryState,
    LineItem,
    PurchaseOrder,
)


def test_purchase_order_round_trip(postgres_conn):
    po = PurchaseOrder(
        po_id="PO-1",
        supplier="Acme",
        expected_items=[LineItem(sku="A1", quantity=10)],
        expected_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        destination_dc="DC-EAST",
    )
    repository.upsert_purchase_order(postgres_conn, po)
    assert repository.get_purchase_order(postgres_conn, "PO-1") == po


def test_get_missing_purchase_order_returns_none(postgres_conn):
    assert repository.get_purchase_order(postgres_conn, "NOPE") is None


def test_inventory_round_trip(postgres_conn):
    inv = InventoryState(sku="A1", dc_id="DC-EAST", on_hand=30, reserved=5, capacity=100)
    repository.upsert_inventory(postgres_conn, inv)
    fetched = repository.get_inventory(postgres_conn, "A1", "DC-EAST")
    assert fetched.on_hand == 30
    assert fetched.available_capacity == 70


def test_decision_round_trip(postgres_conn):
    decision = Decision(
        label=DecisionLabel.HOLD,
        exceptions=[Exception(type=ExceptionType.QUANTITY_MISMATCH, detail="9 vs 10")],
        recommended_actions=["notify supplier"],
        confidence=0.8,
        reasoning="short by one",
    )
    repository.insert_decision(postgres_conn, "RUN-1", "SH-1", decision)
    assert repository.get_decision(postgres_conn, "RUN-1") == decision
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_repository.py -v`
Expected: FAIL — `ImportError: cannot import name 'repository'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/data/repository.py`:
```python
import json

import psycopg

from logistics_agents.domain.models import (
    Decision,
    InventoryState,
    LineItem,
    PurchaseOrder,
)


def upsert_purchase_order(conn: psycopg.Connection, po: PurchaseOrder) -> None:
    items = json.dumps([item.model_dump() for item in po.expected_items])
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO purchase_orders (po_id, supplier, expected_items, expected_date, destination_dc)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (po_id) DO UPDATE SET
                supplier = EXCLUDED.supplier,
                expected_items = EXCLUDED.expected_items,
                expected_date = EXCLUDED.expected_date,
                destination_dc = EXCLUDED.destination_dc
            """,
            (po.po_id, po.supplier, items, po.expected_date, po.destination_dc),
        )
    conn.commit()


def get_purchase_order(conn: psycopg.Connection, po_id: str) -> PurchaseOrder | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT po_id, supplier, expected_items, expected_date, destination_dc "
            "FROM purchase_orders WHERE po_id = %s",
            (po_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return PurchaseOrder(
        po_id=row[0],
        supplier=row[1],
        expected_items=[LineItem(**i) for i in row[2]],
        expected_date=row[3],
        destination_dc=row[4],
    )


def upsert_inventory(conn: psycopg.Connection, inv: InventoryState) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO inventory (sku, dc_id, on_hand, reserved, capacity)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (sku, dc_id) DO UPDATE SET
                on_hand = EXCLUDED.on_hand,
                reserved = EXCLUDED.reserved,
                capacity = EXCLUDED.capacity
            """,
            (inv.sku, inv.dc_id, inv.on_hand, inv.reserved, inv.capacity),
        )
    conn.commit()


def get_inventory(conn: psycopg.Connection, sku: str, dc_id: str) -> InventoryState | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sku, dc_id, on_hand, reserved, capacity FROM inventory "
            "WHERE sku = %s AND dc_id = %s",
            (sku, dc_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return InventoryState(
        sku=row[0], dc_id=row[1], on_hand=row[2], reserved=row[3], capacity=row[4]
    )


def insert_decision(
    conn: psycopg.Connection, run_id: str, shipment_id: str, decision: Decision
) -> None:
    exceptions = json.dumps([e.model_dump() for e in decision.exceptions])
    actions = json.dumps(decision.recommended_actions)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO decisions
                (run_id, shipment_id, label, exceptions, recommended_actions, confidence, reasoning)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id,
                shipment_id,
                decision.label.value,
                exceptions,
                actions,
                decision.confidence,
                decision.reasoning,
            ),
        )
    conn.commit()


def get_decision(conn: psycopg.Connection, run_id: str) -> Decision | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT label, exceptions, recommended_actions, confidence, reasoning "
            "FROM decisions WHERE run_id = %s",
            (run_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return Decision(
        label=row[0],
        exceptions=row[1],
        recommended_actions=row[2],
        confidence=row[3],
        reasoning=row[4],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_repository.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/data/repository.py tests/data/test_repository.py
git commit -m "feat: add repository layer for POs, inventory, and decisions"
```

---

### Task 6: Deterministic seed loader

**Files:**
- Create: `src/logistics_agents/data/seed.py`
- Create: `src/logistics_agents/data/seed_data.py`
- Create: `tests/data/test_seed.py`

**Interfaces:**
- Consumes: `repository` (Task 5); domain models.
- Produces:
  - `seed_data.SEED_PURCHASE_ORDERS: list[PurchaseOrder]`
  - `seed_data.SEED_INVENTORY: list[InventoryState]`
  - `seed.load_seed(conn) -> None` — idempotently upserts all seed data.

- [ ] **Step 1: Write the failing test**

`tests/data/test_seed.py`:
```python
from logistics_agents.data import repository, seed
from logistics_agents.data.seed_data import SEED_INVENTORY, SEED_PURCHASE_ORDERS


def test_seed_loads_all_purchase_orders(postgres_conn):
    seed.load_seed(postgres_conn)
    for po in SEED_PURCHASE_ORDERS:
        assert repository.get_purchase_order(postgres_conn, po.po_id) == po


def test_seed_is_idempotent(postgres_conn):
    seed.load_seed(postgres_conn)
    seed.load_seed(postgres_conn)  # second load must not error or duplicate
    first_inv = SEED_INVENTORY[0]
    fetched = repository.get_inventory(postgres_conn, first_inv.sku, first_inv.dc_id)
    assert fetched == first_inv
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_seed.py -v`
Expected: FAIL — `ImportError: cannot import name 'seed'`.

- [ ] **Step 3: Write the implementation**

`src/logistics_agents/data/seed_data.py`:
```python
from datetime import datetime, timezone

from logistics_agents.domain.models import InventoryState, LineItem, PurchaseOrder

SEED_PURCHASE_ORDERS: list[PurchaseOrder] = [
    PurchaseOrder(
        po_id="PO-1001",
        supplier="Acme Components",
        expected_items=[LineItem(sku="SKU-A", quantity=100)],
        expected_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        destination_dc="DC-EAST",
    ),
    PurchaseOrder(
        po_id="PO-1002",
        supplier="Globex Parts",
        expected_items=[LineItem(sku="SKU-B", quantity=50), LineItem(sku="SKU-C", quantity=25)],
        expected_date=datetime(2026, 7, 6, tzinfo=timezone.utc),
        destination_dc="DC-WEST",
    ),
]

SEED_INVENTORY: list[InventoryState] = [
    InventoryState(sku="SKU-A", dc_id="DC-EAST", on_hand=40, reserved=10, capacity=200),
    InventoryState(sku="SKU-B", dc_id="DC-WEST", on_hand=180, reserved=5, capacity=200),
    InventoryState(sku="SKU-C", dc_id="DC-WEST", on_hand=20, reserved=0, capacity=100),
]
```

`src/logistics_agents/data/seed.py`:
```python
import psycopg

from logistics_agents.data import repository
from logistics_agents.data.seed_data import SEED_INVENTORY, SEED_PURCHASE_ORDERS


def load_seed(conn: psycopg.Connection) -> None:
    for po in SEED_PURCHASE_ORDERS:
        repository.upsert_purchase_order(conn, po)
    for inv in SEED_INVENTORY:
        repository.upsert_inventory(conn, inv)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_seed.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/logistics_agents/data/seed.py src/logistics_agents/data/seed_data.py tests/data/test_seed.py
git commit -m "feat: add deterministic seed data and idempotent loader"
```

---

### Task 7: Kafka (Redpanda) producer/consumer wrappers

**Files:**
- Create: `src/logistics_agents/data/kafka_io.py`
- Create: `tests/data/test_kafka_io.py`

**Interfaces:**
- Consumes: `ShipmentNotification` (Task 2).
- Produces:
  - `kafka_io.SHIPMENT_TOPIC = "shipment.notifications"`
  - `kafka_io.publish_notification(bootstrap: str, asn: ShipmentNotification) -> None`
  - `kafka_io.consume_one(bootstrap: str, group_id: str, timeout_s: float = 10.0) -> ShipmentNotification | None`

- [ ] **Step 1: Write the failing test**

`tests/data/test_kafka_io.py`:
```python
from datetime import datetime, timezone

import pytest
from testcontainers.redpanda import RedpandaContainer

from logistics_agents.data import kafka_io
from logistics_agents.domain.models import LineItem, ShipmentNotification


@pytest.fixture(scope="module")
def redpanda_bootstrap():
    with RedpandaContainer("redpandadata/redpanda:v24.1.1") as rp:
        yield rp.get_bootstrap_server()


def test_publish_then_consume_round_trip(redpanda_bootstrap):
    asn = ShipmentNotification(
        shipment_id="SH-100",
        po_id="PO-1001",
        carrier="UPS",
        tracking_number="1Z-TEST",
        reported_items=[LineItem(sku="SKU-A", quantity=100)],
        reported_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        docs_present=True,
        damaged=False,
    )
    kafka_io.publish_notification(redpanda_bootstrap, asn)
    received = kafka_io.consume_one(redpanda_bootstrap, group_id="test-group", timeout_s=15.0)
    assert received == asn
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_kafka_io.py -v`
Expected: FAIL — `ImportError: cannot import name 'kafka_io'`.

- [ ] **Step 3: Add the testcontainers Redpanda extra**

Modify `pyproject.toml` dev extra to include redpanda support:
```toml
dev = [
    "pytest>=8.0",
    "testcontainers[postgres,redpanda]>=4.0",
]
```
Run: `uv sync --extra dev`

- [ ] **Step 4: Write the implementation**

`src/logistics_agents/data/kafka_io.py`:
```python
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from logistics_agents.domain.models import ShipmentNotification

SHIPMENT_TOPIC = "shipment.notifications"


def _ensure_topic(bootstrap: str) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap})
    existing = admin.list_topics(timeout=10).topics
    if SHIPMENT_TOPIC not in existing:
        futures = admin.create_topics([NewTopic(SHIPMENT_TOPIC, num_partitions=1, replication_factor=1)])
        for future in futures.values():
            try:
                future.result()
            except Exception:
                pass  # already exists / concurrent create


def publish_notification(bootstrap: str, asn: ShipmentNotification) -> None:
    _ensure_topic(bootstrap)
    producer = Producer({"bootstrap.servers": bootstrap})
    producer.produce(SHIPMENT_TOPIC, value=asn.model_dump_json().encode("utf-8"))
    producer.flush(10)


def consume_one(
    bootstrap: str, group_id: str, timeout_s: float = 10.0
) -> ShipmentNotification | None:
    _ensure_topic(bootstrap)
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([SHIPMENT_TOPIC])
    try:
        msg = consumer.poll(timeout_s)
        if msg is None or msg.error():
            return None
        return ShipmentNotification.model_validate_json(msg.value().decode("utf-8"))
    finally:
        consumer.close()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/data/test_kafka_io.py -v`
Expected: PASS (1 test; testcontainers pulls the Redpanda image).

- [ ] **Step 6: Run the full milestone test suite**

Run: `uv run pytest -v`
Expected: PASS — all tests from Tasks 1–7.

- [ ] **Step 7: Commit**

```bash
git add src/logistics_agents/data/kafka_io.py tests/data/test_kafka_io.py pyproject.toml
git commit -m "feat: add Kafka producer/consumer wrappers for shipment notifications"
```

---

## Self-Review

**Spec coverage (Milestone 1 scope = spec §5 domain, §14 layout, milestone 15.1):**
- Domain models (§5): `ShipmentNotification`, `PurchaseOrder`, `InventoryState`, `CarrierStatus`, `Exception`, `Decision`, `TraceRecord` — Tasks 2–3. ✅
- Exception taxonomy + decision labels (§5): Task 2 enums. ✅
- Postgres tables (§5): `purchase_orders, inventory, shipments, carrier_events, decisions, runs, budget_ledger` — Task 4. ✅
- Docker infra (§2, §11): docker-compose Postgres + Redpanda — Task 4. ✅
- Seed loader (milestone 15.1): Task 6. ✅
- Kafka topic + IO (§3): Task 7. ✅
- Repository layer (§4 `data/`): Task 5. ✅
- src-layout project structure (§14): Task 1. ✅

Out of Milestone 1 scope (deferred to later milestones, correctly not covered here): LLM wrapper/record-replay (M2), agents/DAG (M3), evals/graders (M4), CI (M5), FastAPI/budget/SSE (M6), dashboard (M7), Terraform (M8). Note: `shipments`/`carrier_events` tables are created now but their repository writers arrive with M3 agents — schema-first is intentional.

**Placeholder scan:** No TBD/TODO/"handle edge cases" placeholders; every code step contains complete code. The single `pass` in `_ensure_topic` is deliberate idempotency handling, not a placeholder.

**Type consistency:** `apply_schema(conn)` defined in Task 4, consumed identically in the Task 4 fixture. `repository.*` signatures defined in Task 5 match calls in Tasks 6 (`upsert_purchase_order`, `upsert_inventory`) and the tests. `ShipmentNotification` fields defined in Task 2 match the Task 7 producer/consumer usage. Enum `.value` used for DB writes, enum-coercion-from-str used on reads — consistent.
