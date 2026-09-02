import json

from logistics_agents.agents.contracts import InventoryFinding
from logistics_agents.data import repository
from logistics_agents.domain.models import ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are an inventory reconciliation specialist for a logistics decisioning system. "
    "Given an inbound shipment notification, its purchase order, and current inventory, "
    "determine whether the PO matched, list per-SKU quantity discrepancies, and judge "
    "whether the destination DC has capacity. Respond only via the structured schema."
)


def _build_user_prompt(asn: ShipmentNotification, po_dict, inventory_rows) -> str:
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "purchase_order": po_dict,
        "inventory": inventory_rows,
    }
    return json.dumps(context, indent=2, default=str)


def assess(asn: ShipmentNotification, conn, llm: LLMClient, model: str) -> StructuredResult:
    po = repository.get_purchase_order(conn, asn.po_id) if asn.po_id else None
    po_dict = po.model_dump(mode="json") if po is not None else None

    dc_id = po.destination_dc if po is not None else None
    inventory_rows = []
    if dc_id is not None:
        for item in asn.reported_items:
            inv = repository.get_inventory(conn, item.sku, dc_id)
            if inv is not None:
                inventory_rows.append(inv.model_dump(mode="json"))

    user = _build_user_prompt(asn, po_dict, inventory_rows)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=InventoryFinding
    )
