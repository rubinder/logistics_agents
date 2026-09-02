from evals.dataset import CASES, EvalCase, ExpectedOutcome
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import ShipmentNotification


def test_cases_are_well_formed_and_unique():
    assert len(CASES) >= 6
    ids = [c.case_id for c in CASES]
    assert len(ids) == len(set(ids)), "case_ids must be unique"
    for c in CASES:
        assert isinstance(c, EvalCase)
        assert isinstance(c.asn, ShipmentNotification)
        assert isinstance(c.expected, ExpectedOutcome)
        assert isinstance(c.expected.label, DecisionLabel)


def test_dataset_covers_key_exception_types():
    covered = {t for c in CASES for t in c.expected.exception_types}
    for required in (
        ExceptionType.QUANTITY_MISMATCH,
        ExceptionType.LATE_DELIVERY,
        ExceptionType.UNKNOWN_PO,
        ExceptionType.MISSING_DOCS,
        ExceptionType.DAMAGED,
        ExceptionType.OVERCAPACITY,
    ):
        assert required in covered, f"dataset missing a case for {required}"


def test_at_least_one_clean_accept():
    accepts = [c for c in CASES if c.expected.label is DecisionLabel.ACCEPT and not c.expected.exception_types]
    assert accepts, "dataset must include a clean ACCEPT case"


def test_non_late_cases_avoid_the_delayed_tracking_number():
    from logistics_agents.data.seed_data import SEED_CARRIER_EVENTS
    from logistics_agents.domain.enums import ExceptionType

    delayed_tns = {ev["tracking_number"] for ev in SEED_CARRIER_EVENTS if ev["delayed"]}
    for c in CASES:
        if ExceptionType.LATE_DELIVERY not in c.expected.exception_types:
            assert c.asn.tracking_number not in delayed_tns, (
                f"case {c.case_id} expects no LATE_DELIVERY but uses a seeded-delayed "
                f"tracking number {c.asn.tracking_number}"
            )


def test_non_overcapacity_cases_fit_destination_headroom():
    """A case must not smuggle in a second exception via the seed's capacity limits.

    The sibling guard above does this for delayed tracking numbers. This one covers
    capacity: a case whose line items overflow the destination DC carries an implicit
    OVERCAPACITY exception, which breaks the one-perturbation-per-case design and
    makes the case grade against an incomplete expected set.
    """
    from logistics_agents.data.seed_data import SEED_INVENTORY, SEED_PURCHASE_ORDERS

    pos = {p.po_id: p for p in SEED_PURCHASE_ORDERS}
    headroom = {(i.sku, i.dc_id): i.capacity - i.on_hand for i in SEED_INVENTORY}

    for c in CASES:
        if ExceptionType.OVERCAPACITY in c.expected.exception_types:
            continue
        po = pos.get(c.asn.po_id)
        if po is None:
            continue
        for item in c.asn.reported_items:
            room = headroom.get((item.sku, po.destination_dc))
            if room is None:
                continue
            assert item.quantity <= room, (
                f"case {c.case_id} expects no OVERCAPACITY but ships {item.quantity} "
                f"of {item.sku} into {po.destination_dc}, which has only {room} of "
                f"headroom"
            )
