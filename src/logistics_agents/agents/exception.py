import json

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
)
from logistics_agents.domain.models import PurchaseOrder, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are an exception-detection specialist for a logistics decisioning system. Given the "
    "shipment notification, its purchase order, and the inventory and carrier findings, detect "
    "typed exceptions (QUANTITY_MISMATCH, LATE_DELIVERY, UNKNOWN_PO, OVERCAPACITY, MISSING_DOCS, "
    "DAMAGED). Respond only via the structured schema."
)


def detect(
    asn: ShipmentNotification,
    po: PurchaseOrder | None,
    inventory_finding: InventoryFinding,
    carrier_finding: CarrierFinding,
    llm: LLMClient,
    model: str,
) -> StructuredResult:
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "purchase_order": po.model_dump(mode="json") if po is not None else None,
        "inventory_finding": inventory_finding.model_dump(mode="json"),
        "carrier_finding": carrier_finding.model_dump(mode="json"),
    }
    user = json.dumps(context, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=ExceptionFinding
    )
