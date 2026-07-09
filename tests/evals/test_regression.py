from pathlib import Path

import pytest

from evals.dataset import CASES
from evals.results import check_regression, load_report
from evals.run import run_comparison
from logistics_agents.data import seed

BASELINE_DIR = Path(__file__).resolve().parents[1] / "evals" / "baseline"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "llm"


def _baseline_models():
    if not BASELINE_DIR.exists():
        return []
    return [p.stem for p in BASELINE_DIR.glob("*.json")]


@pytest.mark.skipif(
    not _baseline_models(),
    reason="no committed eval baseline yet — record one with `python -m evals.run --mode live`",
)
def test_replay_matches_baseline_no_regression(postgres_conn, tmp_path):
    seed.load_seed(postgres_conn)
    for model in _baseline_models():
        baseline = load_report(BASELINE_DIR / f"{model}.json")
        reports = run_comparison(
            models=[model], cases=CASES, conn=postgres_conn, out_dir=tmp_path,
            mode="replay", fixtures_dir=FIXTURES_DIR, judge_llm=None,
        )
        regressions = check_regression(reports[0], baseline)
        assert regressions == [], f"{model}: {regressions}"
