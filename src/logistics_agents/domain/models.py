from datetime import datetime

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    sku: str
    quantity: int = Field(ge=0)


class PurchaseOrder(BaseModel):
    po_id: str
    supplier: str
    expected_items: list[LineItem]
    expected_date: datetime
    destination_dc: str


class ShipmentNotification(BaseModel):
    shipment_id: str
    po_id: str | None
    carrier: str
    tracking_number: str
    reported_items: list[LineItem]
    reported_date: datetime
    docs_present: bool
    damaged: bool
