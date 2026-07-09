import psycopg

from logistics_agents.data import repository
from logistics_agents.data.seed_data import SEED_INVENTORY, SEED_PURCHASE_ORDERS


def load_seed(conn: psycopg.Connection) -> None:
    for po in SEED_PURCHASE_ORDERS:
        repository.upsert_purchase_order(conn, po)
    for inv in SEED_INVENTORY:
        repository.upsert_inventory(conn, inv)
