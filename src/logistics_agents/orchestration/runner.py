from logistics_agents.agents import carrier, exception, inventory, orchestrator, synthesis
from logistics_agents.data import repository
from logistics_agents.domain.models import Decision, ShipmentNotification
from logistics_agents.llm.client import LLMClient
from logistics_agents.tracing.tracer import Tracer


def run_pipeline(
    asn: ShipmentNotification,
    conn,
    llm: LLMClient,
    model: str,
    run_id: str,
    tracer: Tracer,
) -> Decision:
    plan = orchestrator.plan(asn, llm, model)
    tracer.record("orchestrator", asn, plan.value, plan.meta)

    inv = inventory.assess(asn, conn, llm, model)
    tracer.record("inventory", asn, inv.value, inv.meta)

    car = carrier.assess(asn, conn, llm, model)
    tracer.record("carrier", asn, car.value, car.meta)

    po = repository.get_purchase_order(conn, asn.po_id) if asn.po_id else None
    exc = exception.detect(asn, po, inv.value, car.value, llm, model)
    tracer.record("exception", asn, exc.value, exc.meta)

    decision = synthesis.decide(asn, inv.value, car.value, exc.value, llm, model)
    tracer.record("synthesis", asn, decision.value, decision.meta)

    repository.insert_decision(conn, run_id, asn.shipment_id, decision.value)
    return decision.value
