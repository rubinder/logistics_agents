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
