from pathlib import Path

import pytest

from evals.dataset import CASES
from evals.results import check_regression, load_report
from evals.run import DEFAULT_JUDGE_MODEL, build_client, run_comparison
from logistics_agents.data import seed

BASELINE_DIR = Path(__file__).resolve().parents[2] / "evals" / "baseline"
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "llm"


def _baseline_models():
    if not BASELINE_DIR.exists():
        return []
    return [p.stem for p in BASELINE_DIR.glob("*.json")]


@pytest.mark.skipif(
    not _baseline_models(),
    reason=(
        "no committed eval baseline yet — record a live run "
        "(`python -m evals.run --mode live`), then copy the produced "
        "evals/results/<model>.json to evals/baseline/<model>.json and commit it"
    ),
)
def test_replay_matches_baseline_no_regression(postgres_conn, tmp_path):
    seed.load_seed(postgres_conn)
    for model in _baseline_models():
        baseline = load_report(BASELINE_DIR / f"{model}.json")
        # Score on the same basis the baseline was recorded with. The judge runs
        # from the fixture cache, so it stays free and deterministic in CI; grading
        # without it would renormalize the composite and flag a phantom regression.
        reports = run_comparison(
            models=[model], cases=CASES, conn=postgres_conn, out_dir=tmp_path,
            mode="replay", fixtures_dir=FIXTURES_DIR,
            judge_llm=build_client("replay", FIXTURES_DIR),
            judge_model=DEFAULT_JUDGE_MODEL,
        )
        regressions = check_regression(reports[0], baseline)
        assert regressions == [], f"{model}: {regressions}"
