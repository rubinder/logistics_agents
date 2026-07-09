from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord
from logistics_agents.llm.client import LLMClient
from evals.dataset import CASES
from evals.graders.judge import JudgeScore, judge_reasoning


def _decision():
    return Decision(
        label=DecisionLabel.HOLD,
        exceptions=[ExceptionRecord(type=ExceptionType.QUANTITY_MISMATCH, detail="80 vs 100")],
        recommended_actions=["notify supplier"],
        confidence=0.8,
        reasoning="Short by 20 units against PO-1001; holding for supplier confirmation.",
    )


def test_judge_returns_score(scripted_transport):
    case = next(c for c in CASES if c.case_id == "quantity-mismatch")
    canned = JudgeScore(score=4, rationale="reasoning cites the PO and the shortfall")
    transport, calls = scripted_transport({JudgeScore: canned})
    result = judge_reasoning(case, _decision(), LLMClient(transport), model="claude-opus-4-8")
    assert result.value == canned
    # The judged decision's reasoning must appear in the judge prompt.
    assert "supplier confirmation" in calls[0].user
    assert calls[0].output_type is JudgeScore


def test_judge_score_bounds():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        JudgeScore(score=6, rationale="too high")
