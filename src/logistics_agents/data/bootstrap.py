import os

import psycopg

from logistics_agents.data import repository, seed
from logistics_agents.data.apply_schema import apply_schema


def bootstrap(conn) -> None:
    """Apply the schema (idempotent) and seed the demo data if the DB is empty."""
    apply_schema(conn)
    # Seed only when there is no carrier-event data yet, so container restarts
    # don't duplicate the append-only carrier_events rows.
    if repository.count_carrier_events(conn) == 0:
        seed.load_seed(conn)


def main() -> None:
    dsn = os.environ.get(
        "LOGISTICS_DATABASE_URL", "postgresql://logistics:logistics@localhost:5432/logistics"
    )
    with psycopg.connect(dsn) as conn:
        bootstrap(conn)


if __name__ == "__main__":
    main()
