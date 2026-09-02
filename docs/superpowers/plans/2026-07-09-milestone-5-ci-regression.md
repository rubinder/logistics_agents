# Milestone 5: CI + Regression — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire continuous integration — lint + the deterministic (key-free, replay/scripted) test suite on every commit — plus a replay-mode eval-regression scaffold that activates once a baseline is committed, and a nightly workflow that runs the live model comparison. This makes "agent quality tracked on every commit" a real, enforced thing.

**Architecture:** The existing test suite is already the regression suite — every test is key-free (scripted transports) and deterministic, and the integration tests use testcontainers, which run on GitHub Actions' Docker-enabled `ubuntu-latest`. M5 adds: a ruff config + a one-pass lint sweep of accumulated nits; a `ci.yml` workflow (lint + full `pytest`); a replay-mode eval-regression test that compares a fresh `run_comparison(mode="replay")` against a committed baseline `EvalReport` (skipped until that baseline + its fixtures exist — recorded by the operator's live run); and a `nightly-eval.yml` workflow that runs the live comparison with the `ANTHROPIC_API_KEY` repo secret and uploads the results.

**Tech Stack:** Python 3.12, uv, ruff, pytest + testcontainers, GitHub Actions. Builds on M1–M4.

## Global Constraints

- Python floor **3.12**. CI runs on `ubuntu-latest` (Docker available for testcontainers).
- CI must be **key-free**: the on-commit workflow runs only the deterministic suite (live tests self-skip without `ANTHROPIC_API_KEY`).
- Ruff ruleset: `select = ["E", "F", "I"]`, `line-length = 100`.
- Workflow YAML is verified by running its exact commands locally and confirming green (no separate lint harness required).
- Commit after every task with a `chore:`/`ci:`/`test:` prefix.

---

### Task 1: Ruff config + lint sweep

**Files:**
- Modify: `pyproject.toml`
- Modify: (whatever files ruff flags — expected: a few test files with unused imports)

**Interfaces:**
- Consumes: nothing.
- Produces: a `[tool.ruff]` config and a clean `uv run ruff check .` (exit 0).

- [ ] **Step 1: Add ruff to the dev extra and configure it**

In `pyproject.toml`, add `"ruff>=0.6"` to the `[project.optional-dependencies].dev` list, and add:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I"]
```
Run `uv sync --extra dev`.

- [ ] **Step 2: Run ruff to see the failures (RED)**

Run: `uv run ruff check .`
Expected: FAIL — reports unused imports (e.g. `timezone` in `tests/agents/test_contracts.py`, unused imports in `tests/tracing/test_tracer.py` and `tests/evals/test_runner.py`) and possibly import-order (I) fixes.

- [ ] **Step 3: Auto-fix and hand-fix the remainder**

Run: `uv run ruff check . --fix`
Then run `uv run ruff check .` again. If anything remains that `--fix` can't resolve, fix it by hand. Do NOT change any behavior — these are import/formatting-only fixes. Do NOT delete an import that is actually used (verify each removal).

- [ ] **Step 4: Verify lint is clean AND tests still pass**

Run: `uv run ruff check .`
Expected: PASS (exit 0, "All checks passed!").
Run: `uv run pytest -q`
Expected: PASS — same counts as before (81 passed, 2 skipped), proving the lint sweep changed nothing behavioral.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: add ruff config and sweep unused imports across test files"
```

---

### Task 2: Replay-mode eval-regression scaffold

**Files:**
- Create: `evals/baseline/__init__.py`
- Create: `tests/evals/test_regression.py`

**Interfaces:**
- Consumes: `evals.run.run_comparison`, `evals.results.{load_report, check_regression}`, `evals.dataset.CASES`.
- Produces:
  - `tests/evals/test_regression.py` — a test that, when a committed baseline exists at `evals/baseline/<model>.json` AND replay fixtures exist, runs `run_comparison(mode="replay")` for that model over `CASES` and asserts `check_regression(current, baseline) == []`. When the baseline directory has no reports yet, the test **skips** with a clear reason (so CI is green before the operator records a baseline).

- [ ] **Step 1: Write the test**

`evals/baseline/__init__.py`: (empty file — marks the dir; baselines are committed here later as `<model>.json`)

`tests/evals/test_regression.py`:
```python
from pathlib import Path

import pytest

from logistics_agents.data import seed
from evals.dataset import CASES
from evals.results import check_regression, load_report
from evals.run import run_comparison

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
```
Note: this uses `judge_llm=None` so the replay regression is purely the deterministic pipeline against recorded fixtures (a judge-inclusive baseline would also need judge fixtures + a judge client; keep the regression deterministic).

- [ ] **Step 2: Run it to confirm it SKIPS cleanly (no baseline yet)**

Run: `uv run pytest tests/evals/test_regression.py -v`
Expected: 1 skipped (reason mentions recording a baseline). This is correct pre-baseline behavior.

- [ ] **Step 3: Commit**

```bash
git add evals/baseline/__init__.py tests/evals/test_regression.py
git commit -m "test: add replay-mode eval-regression scaffold (skips until a baseline is committed)"
```

---

### Task 3: CI workflow (lint + tests on every commit)

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `uv`, `ruff`, `pytest` (all wired in earlier tasks).
- Produces: a GitHub Actions workflow that, on push and PR, installs deps, runs `ruff check`, and runs the full key-free test suite (testcontainers works on the Docker-enabled runner).

- [ ] **Step 1: Write the workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check .

      - name: Test (deterministic, key-free; testcontainers uses the runner's Docker)
        run: uv run pytest -q
```

- [ ] **Step 2: Verify the workflow commands locally (this IS the test for YAML)**

Run the exact commands the workflow runs, locally, and confirm each is green:
Run: `uv run ruff check .`  → Expected: PASS.
Run: `uv run pytest -q`     → Expected: PASS (81 passed, 2 skipped — live tests skip; no `ANTHROPIC_API_KEY` in CI).
Confirm the YAML is well-formed (no tabs, valid structure) by reading it back.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run ruff and the deterministic test suite on every push and PR"
```

---

### Task 4: Nightly live model-comparison workflow

**Files:**
- Create: `.github/workflows/nightly-eval.yml`

**Interfaces:**
- Consumes: the `evals.run` CLI (M4); an `ANTHROPIC_API_KEY` GitHub Actions secret.
- Produces: a scheduled + manually-dispatchable workflow that runs the live model comparison and uploads the `evals/results/` artifacts. (It no-ops gracefully if the secret is absent.)

- [ ] **Step 1: Write the workflow**

`.github/workflows/nightly-eval.yml`:
```yaml
name: Nightly Eval

on:
  schedule:
    - cron: "0 6 * * *"   # 06:00 UTC daily
  workflow_dispatch:
    inputs:
      models:
        description: "Comma-separated model ids"
        default: "claude-opus-4-8,claude-sonnet-5,claude-haiku-4-5"

jobs:
  compare:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Start Postgres
        run: docker compose up -d postgres

      - name: Skip if no API key
        id: guard
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "run=false" >> "$GITHUB_OUTPUT"
            echo "No ANTHROPIC_API_KEY secret set — skipping live eval."
          else
            echo "run=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Run live model comparison
        if: steps.guard.outputs.run == 'true'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LOGISTICS_DATABASE_URL: postgresql://logistics:logistics@localhost:5432/logistics
        run: |
          uv run python -m evals.run --mode live \
            --models "${{ github.event.inputs.models || 'claude-opus-4-8,claude-sonnet-5,claude-haiku-4-5' }}"

      - name: Upload results
        if: steps.guard.outputs.run == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: evals/results/
```

- [ ] **Step 2: Verify the YAML and the referenced command shape**

Read the workflow back; confirm it is well-formed YAML. Confirm the invoked command matches the M4 CLI: `python -m evals.run --mode live --models ...` — cross-check against `evals/run.py`'s `argparse` flags (`--mode`, `--models`). Confirm `docker-compose.yml` has a `postgres` service on port 5432 with user/pass/db `logistics` (matches `LOGISTICS_DATABASE_URL`). Do NOT run the live eval locally (it needs a key + budget).

- [ ] **Step 3: Run the full suite once more to confirm nothing regressed**

Run: `uv run pytest -q`
Expected: PASS (81 passed, 2 skipped).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/nightly-eval.yml
git commit -m "ci: add nightly + manual live model-comparison workflow with results upload"
```

---

## Self-Review

**Spec coverage (Milestone 5 scope = spec §10 CI/CD, milestone 15.5):**
- Lint + regression on every commit (§10): Task 1 (ruff) + Task 3 (ci.yml runs ruff + the deterministic suite). ✅
- The deterministic suite IS the replay regression (§7/§10): every test is key-free/scripted; Task 3 runs it in CI. ✅
- Eval-regression vs. a committed baseline (§7): Task 2 scaffold — activates once the operator commits `evals/baseline/<model>.json` + fixtures. ✅
- Nightly live model-comparison → results artifact (§10, §2): Task 4 (nightly-eval.yml, uploads `evals/results/`). ✅

Out of scope (correctly deferred): the dashboard build step in CI is deferred to M7 (no dashboard exists yet — add a `build` job when it does). The actual baseline artifact is an operator step (needs `ANTHROPIC_API_KEY` + a live run); Task 2 is the scaffold that consumes it. FastAPI/dashboard/Terraform are M6–M8.

**Placeholder scan:** No TBD/TODO. Workflows are complete and runnable. The regression test's skip-until-baseline is intentional (documented reason), not a placeholder.

**Type consistency:** Task 2 calls `run_comparison(models=, cases=, conn=, out_dir=, mode=, fixtures_dir=, judge_llm=)` and `check_regression(report, baseline)` / `load_report(path)` with the exact M4 signatures. Task 4's CLI invocation matches `evals/run.py`'s argparse (`--mode`, `--models`). The `LOGISTICS_DATABASE_URL` matches `evals/run.py`'s `DEFAULT_DSN` and `docker-compose.yml`.
