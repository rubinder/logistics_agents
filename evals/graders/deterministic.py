from pydantic import BaseModel

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import ExceptionRecord


class PRF(BaseModel):
    precision: float
    recall: float
    f1: float


def label_match(expected: DecisionLabel, actual: DecisionLabel) -> bool:
    return expected == actual


def exception_prf(expected: list[ExceptionType], actual: list[ExceptionRecord]) -> PRF:
    expected_set = set(expected)
    actual_set = {e.type for e in actual}
    if not expected_set and not actual_set:
        return PRF(precision=1.0, recall=1.0, f1=1.0)
    tp = len(expected_set & actual_set)
    fp = len(actual_set - expected_set)
    fn = len(expected_set - actual_set)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PRF(precision=precision, recall=recall, f1=f1)


def action_coverage(required: list[str], actual_actions: list[str]) -> float:
    if not required:
        return 1.0
    haystack = " ".join(actual_actions).lower()
    hits = sum(1 for kw in required if kw.lower() in haystack)
    return hits / len(required)
