from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import (
    LineItem,
    PurchaseOrder,
    ShipmentNotification,
)


def test_enum_values():
    assert ExceptionType.QUANTITY_MISMATCH == "QUANTITY_MISMATCH"
    assert DecisionLabel.ACCEPT == "ACCEPT"
    assert set(DecisionLabel) == {
        DecisionLabel.ACCEPT,
        DecisionLabel.HOLD,
        DecisionLabel.REROUTE,
        DecisionLabel.ESCALATE,
    }


def test_line_item_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        LineItem(sku="A1", quantity=-1)


def test_purchase_order_round_trips_through_json():
    po = PurchaseOrder(
        po_id="PO-1",
        supplier="Acme",
        expected_items=[LineItem(sku="A1", quantity=10)],
        expected_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        destination_dc="DC-EAST",
    )
    restored = PurchaseOrder.model_validate_json(po.model_dump_json())
    assert restored == po


def test_shipment_notification_allows_unknown_po():
    asn = ShipmentNotification(
        shipment_id="SH-1",
        po_id=None,
        carrier="UPS",
        tracking_number="1Z999",
        reported_items=[LineItem(sku="A1", quantity=9)],
        reported_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
        docs_present=True,
        damaged=False,
    )
    assert asn.po_id is None
    assert asn.reported_items[0].quantity == 9


def test_purchase_order_rejects_naive_datetime():
    with pytest.raises(ValidationError):
        PurchaseOrder(
            po_id="PO-1",
            supplier="Acme",
            expected_items=[LineItem(sku="A1", quantity=10)],
            expected_date=datetime(2026, 7, 1),  # naive — no tzinfo
            destination_dc="DC-EAST",
        )


def test_shipment_notification_rejects_naive_datetime():
    with pytest.raises(ValidationError):
        ShipmentNotification(
            shipment_id="SH-1",
            po_id=None,
            carrier="UPS",
            tracking_number="1Z999",
            reported_items=[LineItem(sku="A1", quantity=9)],
            reported_date=datetime(2026, 7, 2),  # naive — no tzinfo
            docs_present=True,
            damaged=False,
        )
