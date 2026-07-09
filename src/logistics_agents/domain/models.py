from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field


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
