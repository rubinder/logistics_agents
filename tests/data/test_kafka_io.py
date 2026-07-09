from datetime import datetime, timezone

import pytest
from testcontainers.kafka import RedpandaContainer

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
