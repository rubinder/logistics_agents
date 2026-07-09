import pytest

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import ExceptionRecord
from evals.graders.deterministic import action_coverage, exception_prf, label_match


def _exc(t):
    return ExceptionRecord(type=t, detail="x")


def test_label_match():
    assert label_match(DecisionLabel.HOLD, DecisionLabel.HOLD) is True
    assert label_match(DecisionLabel.HOLD, DecisionLabel.ACCEPT) is False


def test_exception_prf_perfect():
    prf = exception_prf([ExceptionType.QUANTITY_MISMATCH], [_exc(ExceptionType.QUANTITY_MISMATCH)])
    assert (prf.precision, prf.recall, prf.f1) == (1.0, 1.0, 1.0)


def test_exception_prf_both_empty_is_one():
    prf = exception_prf([], [])
    assert (prf.precision, prf.recall, prf.f1) == (1.0, 1.0, 1.0)


def test_exception_prf_false_positive_and_negative():
    # expected {QTY, LATE}; actual {QTY, DAMAGED}: tp=1, fp=1, fn=1
    prf = exception_prf(
        [ExceptionType.QUANTITY_MISMATCH, ExceptionType.LATE_DELIVERY],
        [_exc(ExceptionType.QUANTITY_MISMATCH), _exc(ExceptionType.DAMAGED)],
    )
    assert prf.precision == pytest.approx(0.5)
    assert prf.recall == pytest.approx(0.5)
    assert prf.f1 == pytest.approx(0.5)


def test_exception_prf_missed_all():
    prf = exception_prf([ExceptionType.QUANTITY_MISMATCH], [])
    assert prf.recall == 0.0
    assert prf.f1 == 0.0


def test_exception_prf_dedupes_actual():
    # two actual records of the same type count once
    prf = exception_prf(
        [ExceptionType.QUANTITY_MISMATCH],
        [_exc(ExceptionType.QUANTITY_MISMATCH), _exc(ExceptionType.QUANTITY_MISMATCH)],
    )
    assert (prf.precision, prf.recall, prf.f1) == (1.0, 1.0, 1.0)


def test_action_coverage():
    assert action_coverage([], []) == 1.0
    assert action_coverage(["supplier"], ["Notify the supplier of the shortage"]) == 1.0
    assert action_coverage(["supplier", "reroute"], ["notify supplier"]) == pytest.approx(0.5)
    assert action_coverage(["supplier"], []) == 0.0
