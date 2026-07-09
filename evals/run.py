import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from logistics_agents.data import seed
from logistics_agents.data.apply_schema import apply_schema
from logistics_agents.llm.anthropic_transport import AnthropicTransport
from logistics_agents.llm.cache import RecordReplayCache
from logistics_agents.llm.client import LLMClient
from evals.dataset import CASES
from evals.results import write_report
from evals.runner import EvalReport, run_eval

DEFAULT_DSN = "postgresql://logistics:logistics@localhost:5432/logistics"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def build_client(mode: str, fixtures_dir: Path) -> LLMClient:
    cache = RecordReplayCache(AnthropicTransport(), mode=mode, fixtures_dir=Path(fixtures_dir))
    return LLMClient(cache)


def run_comparison(
    models,
    cases,
    conn,
    out_dir,
    mode: str = "replay",
    fixtures_dir: Path | None = None,
    judge_llm: LLMClient | None = None,
    judge_model: str | None = None,
    client_factory=None,
) -> list[EvalReport]:
    fixtures_dir = Path(fixtures_dir) if fixtures_dir is not None else Path("fixtures/llm")
    factory = client_factory or (lambda model: build_client(mode, fixtures_dir))
    reports: list[EvalReport] = []
    for model in models:
        llm = factory(model)
        report = run_eval(
            cases, conn, llm, model=model,
            judge_llm=judge_llm, judge_model=judge_model, persist_traces=True,
        )
        report = report.model_copy(update={"timestamp": _now_iso(), "git_sha": _git_sha()})
        write_report(report, Path(out_dir))
        reports.append(report)
    return reports


def _summary(reports: list[EvalReport]) -> str:
    lines = [f"{'model':24} {'label_acc':>10} {'mean_f1':>8} {'judge':>6} {'composite':>10}"]
    for r in reports:
        judge = f"{r.mean_judge:.2f}" if r.mean_judge is not None else "  -  "
        lines.append(
            f"{r.model:24} {r.label_accuracy:>10.2f} {r.mean_f1:>8.2f} {judge:>6} {r.mean_composite:>10.3f}"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the logistics-agents model comparison eval.")
    parser.add_argument("--models", default="claude-opus-4-8,claude-sonnet-5,claude-haiku-4-5")
    parser.add_argument("--mode", default="live", choices=["live", "replay"])
    parser.add_argument("--out", default="evals/results")
    parser.add_argument("--fixtures", default="fixtures/llm")
    parser.add_argument("--judge-model", default="claude-opus-4-8")
    args = parser.parse_args(argv)

    dsn = os.environ.get("LOGISTICS_DATABASE_URL", DEFAULT_DSN)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    with psycopg.connect(dsn) as conn:
        apply_schema(conn)
        seed.load_seed(conn)
        judge_llm = build_client(args.mode, Path(args.fixtures))
        reports = run_comparison(
            models, CASES, conn, out_dir=args.out, mode=args.mode,
            fixtures_dir=Path(args.fixtures), judge_llm=judge_llm, judge_model=args.judge_model,
        )
    print(_summary(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
