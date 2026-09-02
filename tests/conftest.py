import psycopg
import pytest
from pydantic import BaseModel
from testcontainers.postgres import PostgresContainer

from logistics_agents.data.apply_schema import apply_schema
from logistics_agents.llm.types import RawResponse


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
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE purchase_orders, inventory, shipments, "
                "carrier_events, decisions, runs, budget_ledger RESTART IDENTITY CASCADE"
            )
        conn.commit()


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
