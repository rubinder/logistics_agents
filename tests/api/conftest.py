import pytest
from fastapi.testclient import TestClient

from logistics_agents.api.app import create_app
from logistics_agents.api.deps import Settings, get_conn, get_llm, get_settings
from logistics_agents.llm.client import LLMClient


@pytest.fixture
def api_client(postgres_conn, scripted_transport):
    from logistics_agents.agents.contracts import (
        CarrierFinding,
        ExceptionFinding,
        InventoryFinding,
        OrchestrationPlan,
    )
    from logistics_agents.domain.enums import DecisionLabel
    from logistics_agents.domain.models import Decision

    script = {
        OrchestrationPlan: OrchestrationPlan(subtasks=["x"], reasoning="d"),
        InventoryFinding: InventoryFinding(po_matched=True, discrepancies=[], capacity_ok=True, reasoning="i"),
        CarrierFinding: CarrierFinding(status="in_transit", eta=None, delayed=False, reasoning="c"),
        ExceptionFinding: ExceptionFinding(exceptions=[], reasoning="e"),
        Decision: Decision(label=DecisionLabel.ACCEPT, exceptions=[], recommended_actions=[], confidence=0.9, reasoning="r"),
    }
    transport, _ = scripted_transport(script)

    app = create_app()
    app.dependency_overrides[get_conn] = lambda: postgres_conn
    app.dependency_overrides[get_llm] = lambda: LLMClient(transport)
    app.dependency_overrides[get_settings] = lambda: Settings(
        budget_cap_usd=1.0, per_ip_daily=2, global_daily=5
    )
    return TestClient(app)
