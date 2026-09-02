from evals.dataset import CASES
from evals.graders.judge import JudgeScore
from evals.runner import run_eval
from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
)
from logistics_agents.domain.models import Decision, ExceptionRecord
from logistics_agents.llm.client import LLMClient


def _pipeline_script_for(label, exc_types, actions):
    decision = Decision(
        label=label,
        exceptions=[ExceptionRecord(type=t, detail="x") for t in exc_types],
        recommended_actions=actions, confidence=0.9, reasoning="r",
    )
    return {
        OrchestrationPlan: OrchestrationPlan(subtasks=["x"], reasoning="d"),
        InventoryFinding: InventoryFinding(po_matched=True, discrepancies=[], capacity_ok=True, reasoning="i"),
        CarrierFinding: CarrierFinding(status="in_transit", eta=None, delayed=False, reasoning="c"),
        ExceptionFinding: ExceptionFinding(exceptions=decision.exceptions, reasoning="e"),
        Decision: decision,
    }


def test_run_eval_scores_every_case_and_aggregates(postgres_conn, scripted_transport):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)

    # Make the pipeline emit each case's EXPECTED decision, so every case scores perfectly
    # on the deterministic axes. One combined script keyed by output_type can't vary per
    # case, so drive the two cases we assert on individually.
    clean = next(c for c in CASES if c.case_id == "clean-accept")
    script = _pipeline_script_for(clean.expected.label, clean.expected.exception_types, [])
    transport, _ = scripted_transport(script)
    llm = LLMClient(transport)

    report = run_eval([clean], postgres_conn, llm, model="claude-sonnet-5")

    assert report.model == "claude-sonnet-5"
    assert len(report.results) == 1
    assert report.results[0].case_id == "clean-accept"
    assert report.label_accuracy == 1.0
    assert report.mean_f1 == 1.0
    assert report.mean_judge is None  # no judge llm passed
    assert report.mean_composite == 1.0

    from evals.dataset import DATASET_VERSION
    from evals.graders.judge import RUBRIC_VERSION
    assert report.rubric_version == RUBRIC_VERSION
    assert report.dataset_version == DATASET_VERSION


def test_run_eval_with_judge_includes_judge_mean(postgres_conn, scripted_transport):
    from logistics_agents.data import seed
    seed.load_seed(postgres_conn)

    clean = next(c for c in CASES if c.case_id == "clean-accept")
    script = _pipeline_script_for(clean.expected.label, clean.expected.exception_types, [])
    pipeline_transport, _ = scripted_transport(script)
    judge_transport, _ = scripted_transport({JudgeScore: JudgeScore(score=4, rationale="ok")})

    report = run_eval(
        [clean], postgres_conn, LLMClient(pipeline_transport), model="claude-sonnet-5",
        judge_llm=LLMClient(judge_transport), judge_model="claude-opus-4-8",
    )
    assert report.mean_judge == 4.0
    assert report.results[0].score.judge_score == 4
