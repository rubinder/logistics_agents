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
