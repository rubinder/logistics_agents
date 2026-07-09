import pytest

from evals.dataset import ExpectedOutcome
from evals.graders.composite import grade
from evals.graders.judge import JudgeScore
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord


def _decision(label, types, actions):
    return Decision(
        label=label,
        exceptions=[ExceptionRecord(type=t, detail="x") for t in types],
        recommended_actions=actions,
        confidence=0.9,
        reasoning="r",
    )


def _expected(label, types, actions):
    return ExpectedOutcome(label=label, exception_types=types, required_actions=actions)


def test_perfect_case_with_top_judge_is_one():
    exp = _expected(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["supplier"])
    dec = _decision(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["notify supplier"])
    score = grade(exp, dec, JudgeScore(score=5, rationale="great"))
    assert score.label_correct is True
    assert score.exception_f1 == 1.0
    assert score.action_coverage == 1.0
    assert score.judge_score == 5
    assert score.composite == pytest.approx(1.0)


def test_wrong_label_caps_composite_below_one():
    exp = _expected(DecisionLabel.HOLD, [], [])
    dec = _decision(DecisionLabel.ACCEPT, [], [])
    score = grade(exp, dec, JudgeScore(score=5, rationale="x"))
    assert score.label_correct is False
    # label weight (0.4) is lost; everything else perfect → 0.6
    assert score.composite == pytest.approx(0.6)


def test_composite_without_judge_renormalizes_to_one():
    exp = _expected(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["supplier"])
    dec = _decision(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["notify supplier"])
    score = grade(exp, dec, None)
    assert score.judge_score is None
    assert score.composite == pytest.approx(1.0)
