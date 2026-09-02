from pathlib import Path

from evals.runner import EvalReport


def write_report(report: EvalReport, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report.model}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_report(path: Path) -> EvalReport:
    return EvalReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def check_regression(report: EvalReport, baseline: EvalReport, tolerance: float = 0.0) -> list[str]:
    messages: list[str] = []
    # A score is only comparable to a baseline recorded from the same dataset and
    # rubric. Without this, editing the dataset and forgetting to re-record leaves
    # the gate silently grading new cases against stale expectations.
    for field in ("dataset_version", "rubric_version"):
        current, prior = getattr(report, field), getattr(baseline, field)
        if current != prior:
            messages.append(
                f"{field} mismatch: report is {current!r} but baseline is {prior!r} "
                f"— re-record the baseline"
            )
    if report.mean_composite < baseline.mean_composite - tolerance:
        messages.append(
            f"mean_composite regressed: {report.mean_composite:.3f} < "
            f"{baseline.mean_composite:.3f} (baseline)"
        )
    baseline_by_case = {r.case_id: r.score.composite for r in baseline.results}
    for r in report.results:
        prior = baseline_by_case.get(r.case_id)
        if prior is not None and r.score.composite < prior - tolerance:
            messages.append(
                f"case {r.case_id} composite regressed: {r.score.composite:.3f} < {prior:.3f}"
            )
    return messages
