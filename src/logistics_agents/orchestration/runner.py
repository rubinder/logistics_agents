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
    """Run the fixed agent DAG (orchestrator → inventory → carrier → exception →
    synthesis) and return the synthesized Decision.

    Non-transactional: each trace and the final decision are committed
    independently, and an error raised by any agent propagates — leaving the
    already-committed traces with no decision row. Callers running a dataset
    must wrap each case and supply a unique run_id per run; reusing a run_id
    raises IntegrityError on the runs/decisions primary keys.
    """
    plan = orchestrator.plan(asn, llm, model)
    tracer.record("orchestrator", asn, plan.value, plan.meta)

    inv = inventory.assess(asn, conn, llm, model)
    tracer.record("inventory", asn, inv.value, inv.meta)

    car = carrier.assess(asn, conn, llm, model)
    tracer.record("carrier", asn, car.value, car.meta)

    po = repository.get_purchase_order(conn, asn.po_id) if asn.po_id else None
    exc = exception.detect(asn, po, inv.value, car.value, llm, model)
    tracer.record(
        "exception",
        {
            "purchase_order": po.model_dump(mode="json") if po is not None else None,
            "inventory_finding": inv.value,
            "carrier_finding": car.value,
        },
        exc.value,
        exc.meta,
    )

    decision = synthesis.decide(asn, inv.value, car.value, exc.value, llm, model)
    tracer.record(
        "synthesis",
        {
            "inventory_finding": inv.value,
            "carrier_finding": car.value,
            "exception_finding": exc.value,
        },
        decision.value,
        decision.meta,
    )

    repository.insert_decision(conn, run_id, asn.shipment_id, decision.value)
    return decision.value
