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
