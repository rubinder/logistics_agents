from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field, computed_field

from logistics_agents.domain.enums import DecisionLabel, ExceptionType


class LineItem(BaseModel):
    sku: str
    quantity: int = Field(ge=0)


class PurchaseOrder(BaseModel):
    po_id: str
    supplier: str
    expected_items: list[LineItem]
    expected_date: AwareDatetime
    destination_dc: str


class ShipmentNotification(BaseModel):
    shipment_id: str
    po_id: str | None
    carrier: str
    tracking_number: str
    reported_items: list[LineItem]
    reported_date: AwareDatetime
    docs_present: bool
    damaged: bool


class InventoryState(BaseModel):
    sku: str
    dc_id: str
    on_hand: int = Field(ge=0)
    reserved: int = Field(ge=0)
    capacity: int = Field(ge=0)

    @computed_field
    @property
    def available_capacity(self) -> int:
        return self.capacity - self.on_hand


class CarrierStatus(BaseModel):
    tracking_number: str
    status: str
    eta: AwareDatetime | None
    delayed: bool


class Exception(BaseModel):
    type: ExceptionType
    detail: str


class Decision(BaseModel):
    label: DecisionLabel
    exceptions: list[Exception]
    recommended_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class TraceRecord(BaseModel):
    run_id: str
    node: str
    input_json: str
    output_json: str
    latency_ms: int = Field(ge=0)
    tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    model: str
    created_at: AwareDatetime
