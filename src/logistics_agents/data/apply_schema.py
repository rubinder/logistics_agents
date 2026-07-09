from importlib import resources

import psycopg


def _schema_sql() -> str:
    return resources.files("logistics_agents.data").joinpath("schema.sql").read_text()


def apply_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(_schema_sql())
    conn.commit()
