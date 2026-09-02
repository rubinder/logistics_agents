from datetime import datetime, timezone

from logistics_agents.agents import carrier
from logistics_agents.agents.contracts import CarrierFinding
from logistics_agents.data import seed
from logistics_agents.domain.models import LineItem, ShipmentNotification
from logistics_agents.llm.client import LLMClient


def _asn(tracking_number="1Z-1002"):
    return ShipmentNotification(
        shipment_id="SH-2",
        po_id="PO-1002",
        carrier="FedEx",
        tracking_number=tracking_number,
        reported_items=[LineItem(sku="SKU-B", quantity=50)],
        reported_date=datetime(2026, 7, 6, tzinfo=timezone.utc),
        docs_present=True,
        damaged=False,
    )


def test_carrier_agent_includes_tracking_status_and_returns_finding(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)  # seeds 1Z-1002 as delayed
    finding = CarrierFinding(status="delayed", eta=None, delayed=True, reasoning="carrier reported delay")
    transport, calls = scripted_transport({CarrierFinding: finding})
    llm = LLMClient(transport)

    result = carrier.assess(_asn(), postgres_conn, llm, model="claude-haiku-4-5")

    assert result.value == finding
    prompt = calls[0].user
    assert "1Z-1002" in prompt
    assert "delayed" in prompt  # the looked-up carrier status appears in the prompt
    assert calls[0].output_type is CarrierFinding


def test_carrier_agent_handles_unknown_tracking(postgres_conn, scripted_transport):
    seed.load_seed(postgres_conn)
    finding = CarrierFinding(status="unknown", eta=None, delayed=False, reasoning="no tracking data")
    transport, calls = scripted_transport({CarrierFinding: finding})
    llm = LLMClient(transport)

    result = carrier.assess(_asn(tracking_number="1Z-NONE"), postgres_conn, llm, model="claude-haiku-4-5")
    assert result.value.status == "unknown"
    assert "1Z-NONE" in calls[0].user
