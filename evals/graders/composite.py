from pydantic import BaseModel

from logistics_agents.domain.models import Decision
from evals.dataset import ExpectedOutcome
from evals.graders import deterministic
from evals.graders.judge import JudgeScore

_W_LABEL = 0.4
_W_F1 = 0.3
_W_ACTION = 0.1
_W_JUDGE = 0.2


class CaseScore(BaseModel):
    label_correct: bool
    exception_precision: float
    exception_recall: float
    exception_f1: float
    action_coverage: float
    judge_score: int | None
    composite: float


def grade(expected: ExpectedOutcome, decision: Decision, judge: JudgeScore | None) -> CaseScore:
    label_correct = deterministic.label_match(expected.label, decision.label)
    prf = deterministic.exception_prf(expected.exception_types, decision.exceptions)
    action = deterministic.action_coverage(expected.required_actions, decision.recommended_actions)

    label_component = _W_LABEL * (1.0 if label_correct else 0.0)
    f1_component = _W_F1 * prf.f1
    action_component = _W_ACTION * action

    if judge is not None:
        judge_component = _W_JUDGE * (judge.score / 5)
        composite = label_component + f1_component + action_component + judge_component
        judge_val = judge.score
    else:
        # Renormalize the deterministic weights to sum to 1.
        det_total = _W_LABEL + _W_F1 + _W_ACTION
        composite = (label_component + f1_component + action_component) / det_total
        judge_val = None

    return CaseScore(
        label_correct=label_correct,
        exception_precision=prf.precision,
        exception_recall=prf.recall,
        exception_f1=prf.f1,
        action_coverage=action,
        judge_score=judge_val,
        composite=composite,
    )
