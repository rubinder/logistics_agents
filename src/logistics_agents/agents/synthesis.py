import json

from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
)
from logistics_agents.domain.models import Decision, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are the synthesis agent for a logistics decisioning system. Given the shipment "
    "notification and the inventory, carrier, and exception findings, produce the final "
    "structured decision: a label, the confirmed exceptions, recommended actions, a "
    "confidence in [0,1], and reasoning.\n\n"
    "Apply this decision policy when choosing the label:\n"
    "- ACCEPT: no exceptions — the shipment matches its purchase order, arrived on time, "
    "has documentation, and is undamaged.\n"
    "- HOLD: a recoverable discrepancy needs review before acceptance — a quantity "
    "mismatch, a late delivery, or missing documentation.\n"
    "- REROUTE: the goods have a physical problem requiring redirection — a damaged shipment.\n"
    "- ESCALATE: the shipment cannot be reconciled automatically and needs a human — an "
    "unknown or unmatched purchase order, or multiple conflicting critical exceptions.\n\n"
    "Respond only via the structured schema."
)


def decide(
    asn: ShipmentNotification,
    inventory_finding: InventoryFinding,
    carrier_finding: CarrierFinding,
    exception_finding: ExceptionFinding,
    llm: LLMClient,
    model: str,
) -> StructuredResult:
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "inventory_finding": inventory_finding.model_dump(mode="json"),
        "carrier_finding": carrier_finding.model_dump(mode="json"),
        "exception_finding": exception_finding.model_dump(mode="json"),
    }
    user = json.dumps(context, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=Decision
    )
