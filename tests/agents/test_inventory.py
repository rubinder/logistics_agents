from datetime import datetime, timezone

from logistics_agents.agents import inventory
from logistics_agents.agents.contracts import InventoryFinding, QuantityDiscrepancy
from logistics_agents.data import seed
from logistics_agents.domain.models import LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient


def _asn():
    return ShipmentNotification(
        shipment_id="SH-1",
        po_id="PO-1001",
        carrier="UPS",
        tracking_number="1Z-1001",
        reported_items=[LineItem(sku="SKU-A", quantity=90)],
        reported_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        docs_present=True,
        damaged=False,
    )


def test_inventory_agent_includes_po_context_and_returns_finding(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)
    finding = InventoryFinding(
        po_matched=True,
        discrepancies=[QuantityDiscrepancy(sku="SKU-A", expected=100, reported=90)],
        capacity_ok=True,
        reasoning="short by 10",
    )
    transport, calls = scripted_transport({InventoryFinding: finding})
    llm = LLMClient(transport)

    result = inventory.assess(_asn(), postgres_conn, llm, model="claude-sonnet-5")

    assert result.value == finding
    assert result.meta.model == "claude-sonnet-5"
    # The prompt must carry the PO's expected quantity (100) and the reported quantity (90).
    prompt = calls[0].user
    assert "PO-1001" in prompt
    assert "100" in prompt and "90" in prompt
    assert calls[0].output_type is InventoryFinding
