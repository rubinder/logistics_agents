import json

from logistics_agents.agents.contracts import OrchestrationPlan
from logistics_agents.domain.models import ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult

SYSTEM = (
    "You are the orchestrator of a logistics decisioning system. Given an inbound shipment "
    "notification, decompose the work into the specialist subtasks needed to reach an "
    "accept/hold/reroute/escalate decision (inventory reconciliation, carrier tracking, "
    "exception detection). Respond only via the structured schema."
)


def plan(asn: ShipmentNotification, llm: LLMClient, model: str) -> StructuredResult:
    user = json.dumps({"shipment_notification": asn.model_dump(mode="json")}, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=SYSTEM, user=user, output_type=OrchestrationPlan
    )
