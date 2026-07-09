import json

from logistics_agents.agents.contracts import CarrierFinding
from logistics_agents.data import repository
from logistics_agents.domain.models import ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are a carrier-tracking specialist for a logistics decisioning system. "
    "Given an inbound shipment notification and the latest carrier tracking event, "
    "summarize the shipment's transit status, ETA, and whether it is delayed. "
    "If no tracking data exists, report status 'unknown'. Respond only via the structured schema."
)


def assess(asn: ShipmentNotification, conn, llm: LLMClient, model: str) -> StructuredResult:
    status = repository.get_latest_carrier_event(conn, asn.tracking_number)
    context = {
        "shipment_notification": asn.model_dump(mode="json"),
        "carrier_status": status.model_dump(mode="json") if status is not None else None,
        "tracking_number": asn.tracking_number,
    }
    user = json.dumps(context, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=CarrierFinding
    )
