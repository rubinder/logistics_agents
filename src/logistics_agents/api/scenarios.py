from datetime import datetime, timezone

from logistics_agents.domain.models import LineItem, ShipmentNotification

_ON_TIME = datetime(2026, 7, 5, tzinfo=timezone.utc)

SCENARIOS: dict[str, ShipmentNotification] = {
    "clean": ShipmentNotification(
        shipment_id="DEMO-CLEAN", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=100)], reported_date=_ON_TIME,
        docs_present=True, damaged=False,
    ),
    "quantity-mismatch": ShipmentNotification(
        shipment_id="DEMO-QTY", po_id="PO-1001", carrier="UPS", tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=80)], reported_date=_ON_TIME,
        docs_present=True, damaged=False,
    ),
}
