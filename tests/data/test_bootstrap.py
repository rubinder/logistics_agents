from logistics_agents.data import repository
from logistics_agents.data.bootstrap import bootstrap
from logistics_agents.data.seed_data import SEED_CARRIER_EVENTS, SEED_PURCHASE_ORDERS


def test_bootstrap_is_idempotent(postgres_conn):
    bootstrap(postgres_conn)
    bootstrap(postgres_conn)  # second call must not duplicate seed data

    assert repository.count_carrier_events(postgres_conn) == len(SEED_CARRIER_EVENTS)

    seeded_po = SEED_PURCHASE_ORDERS[0]
    assert repository.get_purchase_order(postgres_conn, seeded_po.po_id) == seeded_po
