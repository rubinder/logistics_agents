from evals.graders.composite import CaseScore
from evals.results import check_regression, load_report, write_report
from evals.runner import CaseResult, EvalReport


def _report(composite, case_composite):
    score = CaseScore(
        label_correct=True, exception_precision=1.0, exception_recall=1.0, exception_f1=1.0,
        action_coverage=1.0, judge_score=5, composite=case_composite,
    )
    return EvalReport(
        model="claude-sonnet-5",
        results=[CaseResult(case_id="c1", model="claude-sonnet-5", label="ACCEPT", score=score)],
        label_accuracy=1.0, mean_f1=1.0, mean_action_coverage=1.0, mean_judge=5.0,
        mean_composite=composite,
    )


def test_write_then_load_round_trips(tmp_path):
    report = _report(0.9, 0.9)
    path = write_report(report, tmp_path)
    assert path.name == "claude-sonnet-5.json"
    assert load_report(path) == report


def test_no_regression_returns_empty(tmp_path):
    baseline = _report(0.9, 0.9)
    current = _report(0.92, 0.92)
    assert check_regression(current, baseline) == []


def test_aggregate_regression_flagged():
    baseline = _report(0.9, 0.9)
    current = _report(0.7, 0.7)
    msgs = check_regression(current, baseline)
    assert any("mean_composite" in m for m in msgs)


def test_per_case_regression_flagged():
    baseline = _report(0.9, 0.9)
    current = _report(0.9, 0.5)  # aggregate same, one case dropped
    msgs = check_regression(current, baseline)
    assert any("c1" in m for m in msgs)
