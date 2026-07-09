from datetime import datetime, timezone

from logistics_agents.domain.models import InventoryState, LineItem, PurchaseOrder

SEED_PURCHASE_ORDERS: list[PurchaseOrder] = [
    PurchaseOrder(
        po_id="PO-1001",
        supplier="Acme Components",
        expected_items=[LineItem(sku="SKU-A", quantity=100)],
        expected_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        destination_dc="DC-EAST",
    ),
    PurchaseOrder(
        po_id="PO-1002",
        supplier="Globex Parts",
        expected_items=[LineItem(sku="SKU-B", quantity=50), LineItem(sku="SKU-C", quantity=25)],
        expected_date=datetime(2026, 7, 6, tzinfo=timezone.utc),
        destination_dc="DC-WEST",
    ),
]

SEED_INVENTORY: list[InventoryState] = [
    InventoryState(sku="SKU-A", dc_id="DC-EAST", on_hand=40, reserved=10, capacity=200),
    InventoryState(sku="SKU-B", dc_id="DC-WEST", on_hand=180, reserved=5, capacity=200),
    InventoryState(sku="SKU-C", dc_id="DC-WEST", on_hand=20, reserved=0, capacity=100),
]

SEED_CARRIER_EVENTS: list[dict] = [
    {
        "tracking_number": "1Z-1001",
        "event_type": "in_transit",
        "status": "in_transit",
        "eta": datetime(2026, 7, 5, tzinfo=timezone.utc),
        "delayed": False,
        "event_time": datetime(2026, 7, 4, tzinfo=timezone.utc),
    },
    {
        "tracking_number": "1Z-1002",
        "event_type": "delayed",
        "status": "delayed",
        "eta": datetime(2026, 7, 9, tzinfo=timezone.utc),
        "delayed": True,
        "event_time": datetime(2026, 7, 6, tzinfo=timezone.utc),
    },
]
