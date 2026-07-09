from pydantic import BaseModel

from logistics_agents.llm.client import LLMClient
from logistics_agents.tracing.tracer import Tracer
from evals.dataset import EvalCase
from evals.graders import composite
from evals.graders.composite import CaseScore
from evals.graders.judge import judge_reasoning
from logistics_agents.orchestration.runner import run_pipeline


class CaseResult(BaseModel):
    case_id: str
    model: str
    label: str
    score: CaseScore


class EvalReport(BaseModel):
    model: str
    results: list[CaseResult]
    label_accuracy: float
    mean_f1: float
    mean_action_coverage: float
    mean_judge: float | None
    mean_composite: float


def run_eval(
    cases: list[EvalCase],
    conn,
    llm: LLMClient,
    model: str,
    judge_llm: LLMClient | None = None,
    judge_model: str | None = None,
    persist_traces: bool = False,
) -> EvalReport:
    results: list[CaseResult] = []
    for case in cases:
        tracer = Tracer(run_id=f"{model}:{case.case_id}", conn=conn if persist_traces else None)
        decision = run_pipeline(
            case.asn, conn, llm, model=model, run_id=f"{model}:{case.case_id}", tracer=tracer
        )
        judge = None
        if judge_llm is not None:
            judge = judge_reasoning(case, decision, judge_llm, judge_model or model).value
        score = composite.grade(case.expected, decision, judge)
        results.append(CaseResult(case_id=case.case_id, model=model, label=decision.label.value, score=score))

    n = len(results) or 1
    judged = [r.score.judge_score for r in results if r.score.judge_score is not None]
    return EvalReport(
        model=model,
        results=results,
        label_accuracy=sum(1 for r in results if r.score.label_correct) / n,
        mean_f1=sum(r.score.exception_f1 for r in results) / n,
        mean_action_coverage=sum(r.score.action_coverage for r in results) / n,
        mean_judge=(sum(judged) / len(judged)) if judged else None,
        mean_composite=sum(r.score.composite for r in results) / n,
    )
