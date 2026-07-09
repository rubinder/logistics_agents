import json
from datetime import datetime

import psycopg

from logistics_agents.domain.models import (
    CarrierStatus,
    Decision,
    ExceptionRecord,
    InventoryState,
    LineItem,
    PurchaseOrder,
    TraceRecord,
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
        exceptions=[ExceptionRecord(**e) for e in row[1]],
        recommended_actions=row[2],
        confidence=row[3],
        reasoning=row[4],
    )


def insert_carrier_event(
    conn: psycopg.Connection, tracking_number, event_type, status, eta, delayed, event_time
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO carrier_events (tracking_number, event_type, status, eta, delayed, event_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (tracking_number, event_type, status, eta, delayed, event_time),
        )
    conn.commit()


def get_latest_carrier_event(conn: psycopg.Connection, tracking_number: str) -> CarrierStatus | None:
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


def insert_trace(conn: psycopg.Connection, trace: TraceRecord) -> None:
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
