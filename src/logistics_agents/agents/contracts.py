from pydantic import AwareDatetime, BaseModel

from logistics_agents.domain.models import ExceptionRecord


class QuantityDiscrepancy(BaseModel):
    sku: str
    expected: int
    reported: int


class InventoryFinding(BaseModel):
    po_matched: bool
    discrepancies: list[QuantityDiscrepancy]
    capacity_ok: bool
    reasoning: str


class CarrierFinding(BaseModel):
    status: str
    eta: AwareDatetime | None
    delayed: bool
    reasoning: str


class ExceptionFinding(BaseModel):
    exceptions: list[ExceptionRecord]
    reasoning: str


class OrchestrationPlan(BaseModel):
    subtasks: list[str]
    reasoning: str
