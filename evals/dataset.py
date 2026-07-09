from datetime import datetime, timezone

from pydantic import BaseModel

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import LineItem, ShipmentNotification


class ExpectedOutcome(BaseModel):
    label: DecisionLabel
    exception_types: list[ExceptionType]
    required_actions: list[str]


class EvalCase(BaseModel):
    case_id: str
    asn: ShipmentNotification
    expected: ExpectedOutcome


def _asn(shipment_id, po_id, tracking, items, reported_date, docs_present=True, damaged=False):
    return ShipmentNotification(
        shipment_id=shipment_id,
        po_id=po_id,
        carrier="UPS",
        tracking_number=tracking,
        reported_items=[LineItem(sku=s, quantity=q) for s, q in items],
        reported_date=reported_date,
        docs_present=docs_present,
        damaged=damaged,
    )


_ON_TIME = datetime(2026, 7, 5, tzinfo=timezone.utc)
_LATE = datetime(2026, 7, 20, tzinfo=timezone.utc)

CASES: list[EvalCase] = [
    EvalCase(
        case_id="clean-accept",
        asn=_asn("SH-CLEAN", "PO-1001", "1Z-1001", [("SKU-A", 100)], _ON_TIME),
        expected=ExpectedOutcome(label=DecisionLabel.ACCEPT, exception_types=[], required_actions=[]),
    ),
    EvalCase(
        case_id="quantity-mismatch",
        asn=_asn("SH-QTY", "PO-1001", "1Z-1001", [("SKU-A", 80)], _ON_TIME),
        expected=ExpectedOutcome(
            label=DecisionLabel.HOLD,
            exception_types=[ExceptionType.QUANTITY_MISMATCH],
            required_actions=["supplier"],
        ),
    ),
    EvalCase(
        case_id="late-delivery",
        asn=_asn("SH-LATE", "PO-1001", "1Z-1002", [("SKU-A", 100)], _LATE),
        expected=ExpectedOutcome(
            label=DecisionLabel.HOLD,
            exception_types=[ExceptionType.LATE_DELIVERY],
            required_actions=[],
        ),
    ),
    EvalCase(
        case_id="unknown-po",
        asn=_asn("SH-NOPO", None, "1Z-1001", [("SKU-A", 50)], _ON_TIME),
        expected=ExpectedOutcome(
            label=DecisionLabel.ESCALATE,
            exception_types=[ExceptionType.UNKNOWN_PO],
            required_actions=[],
        ),
    ),
    EvalCase(
        case_id="missing-docs",
        asn=_asn("SH-DOCS", "PO-1002", "1Z-1002", [("SKU-B", 50)], _ON_TIME, docs_present=False),
        expected=ExpectedOutcome(
            label=DecisionLabel.HOLD,
            exception_types=[ExceptionType.MISSING_DOCS],
            required_actions=[],
        ),
    ),
    EvalCase(
        case_id="damaged",
        asn=_asn("SH-DMG", "PO-1002", "1Z-1002", [("SKU-B", 50)], _ON_TIME, damaged=True),
        expected=ExpectedOutcome(
            label=DecisionLabel.REROUTE,
            exception_types=[ExceptionType.DAMAGED],
            required_actions=[],
        ),
    ),
]
