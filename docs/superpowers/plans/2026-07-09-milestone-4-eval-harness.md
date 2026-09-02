# Milestone 4: Eval Harness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the eval infrastructure that is the project's differentiator — a labeled dataset of expected outcomes, a hybrid grader (deterministic scorers + an LLM-as-judge), a composite per-case score, an eval runner that scores the whole pipeline across a dataset, a serializable results format for the dashboard, and a live entrypoint that runs a real Opus/Sonnet/Haiku comparison.

**Architecture:** A dataset is a list of `EvalCase`s, each pairing an input `ShipmentNotification` with an `ExpectedOutcome` (decision label + expected exception types + required action keywords). **Deterministic graders** are pure functions over the expected/actual pair — the most rigorously tested code in the repo, since a grader bug silently invalidates every score. The **LLM-judge** grader scores the decision's reasoning against a version-pinned rubric via `LLMClient.complete_structured` (so it runs key-free in tests with a scripted transport). A **composite** grader blends them per case. The **runner** executes `run_pipeline` per case (fresh `Tracer` + unique `run_id`), grades each, and aggregates into an `EvalReport`. A **live entrypoint** (`evals/run.py`) runs the runner across multiple models with a live transport, recording fixtures and writing results — the only part that needs an API key.

**Tech Stack:** Python 3.12, pydantic v2, psycopg 3, pytest + testcontainers. Builds on M1–M3 (`run_pipeline`, `Tracer`, `LLMClient`, `Transport`, domain models).

## Global Constraints

- Python floor **3.12**; eval data shapes are pydantic v2 models under `evals/`.
- Graders never call the Anthropic SDK directly; the LLM-judge uses `LLMClient.complete_structured`.
- Every test is key-free: deterministic graders use concrete inputs; the judge and runner use a scripted transport; live API calls live only in `evals/run.py`, exercised by a `skipif(no ANTHROPIC_API_KEY)` test.
- The runner gives each case a unique `run_id` (`run_pipeline` is non-transactional and requires it).
- Exception-set scoring is over `ExceptionType` values; the decision model is `Decision` (`domain.models`).
- Commit after every task with a `feat:`/`chore:`/`test:` prefix.

---

### Task 1: Dataset structures + a labeled case set

**Files:**
- Create: `evals/__init__.py`
- Create: `evals/dataset.py`
- Create: `tests/evals/__init__.py`
- Create: `tests/evals/test_dataset.py`

**Interfaces:**
- Consumes: `domain.models.ShipmentNotification`, `domain.enums.{DecisionLabel, ExceptionType}`.
- Produces:
  - `dataset.ExpectedOutcome(label: DecisionLabel, exception_types: list[ExceptionType], required_actions: list[str])`
  - `dataset.EvalCase(case_id: str, asn: ShipmentNotification, expected: ExpectedOutcome)`
  - `dataset.CASES: list[EvalCase]` — a labeled set (>= 6 cases) built against the M1 seed entities (PO-1001/PO-1002, SKU-A/B/C, tracking 1Z-1001/1Z-1002), covering: clean accept, quantity mismatch, late delivery, unknown PO, missing docs, damaged.

- [ ] **Step 1: Write the failing test**

`tests/evals/__init__.py`: (empty file)

`tests/evals/test_dataset.py`:
```python
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import ShipmentNotification
from evals.dataset import CASES, EvalCase, ExpectedOutcome


def test_cases_are_well_formed_and_unique():
    assert len(CASES) >= 6
    ids = [c.case_id for c in CASES]
    assert len(ids) == len(set(ids)), "case_ids must be unique"
    for c in CASES:
        assert isinstance(c, EvalCase)
        assert isinstance(c.asn, ShipmentNotification)
        assert isinstance(c.expected, ExpectedOutcome)
        assert isinstance(c.expected.label, DecisionLabel)


def test_dataset_covers_key_exception_types():
    covered = {t for c in CASES for t in c.expected.exception_types}
    for required in (
        ExceptionType.QUANTITY_MISMATCH,
        ExceptionType.LATE_DELIVERY,
        ExceptionType.UNKNOWN_PO,
        ExceptionType.MISSING_DOCS,
        ExceptionType.DAMAGED,
    ):
        assert required in covered, f"dataset missing a case for {required}"


def test_at_least_one_clean_accept():
    accepts = [c for c in CASES if c.expected.label is DecisionLabel.ACCEPT and not c.expected.exception_types]
    assert accepts, "dataset must include a clean ACCEPT case"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/evals/test_dataset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals'`.

- [ ] **Step 3: Write the implementation**

`evals/__init__.py`: (empty file)

`evals/dataset.py`:
```python
from datetime import datetime, timezone

from pydantic import BaseModel

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import LineItem, ShipmentNotification


class ExpectedOutcome(BaseModel):
    label: DecisionLabel
    exception_types: list[ExceptionType]
    required_actions: list[str]


class EvalCase(BaseModel):
    case_id: str
    asn: ShipmentNotification
    expected: ExpectedOutcome


def _asn(shipment_id, po_id, tracking, items, reported_date, docs_present=True, damaged=False):
    return ShipmentNotification(
        shipment_id=shipment_id,
        po_id=po_id,
        carrier="UPS",
        tracking_number=tracking,
        reported_items=[LineItem(sku=s, quantity=q) for s, q in items],
        reported_date=reported_date,
        docs_present=docs_present,
        damaged=damaged,
    )


_ON_TIME = datetime(2026, 7, 5, tzinfo=timezone.utc)
_LATE = datetime(2026, 7, 20, tzinfo=timezone.utc)

CASES: list[EvalCase] = [
    EvalCase(
        case_id="clean-accept",
        asn=_asn("SH-CLEAN", "PO-1001", "1Z-1001", [("SKU-A", 100)], _ON_TIME),
        expected=ExpectedOutcome(label=DecisionLabel.ACCEPT, exception_types=[], required_actions=[]),
    ),
    EvalCase(
        case_id="quantity-mismatch",
        asn=_asn("SH-QTY", "PO-1001", "1Z-1001", [("SKU-A", 80)], _ON_TIME),
        expected=ExpectedOutcome(
            label=DecisionLabel.HOLD,
            exception_types=[ExceptionType.QUANTITY_MISMATCH],
            required_actions=["supplier"],
        ),
    ),
    EvalCase(
        case_id="late-delivery",
        asn=_asn("SH-LATE", "PO-1001", "1Z-1002", [("SKU-A", 100)], _LATE),
        expected=ExpectedOutcome(
            label=DecisionLabel.HOLD,
            exception_types=[ExceptionType.LATE_DELIVERY],
            required_actions=[],
        ),
    ),
    EvalCase(
        case_id="unknown-po",
        asn=_asn("SH-NOPO", None, "1Z-1001", [("SKU-A", 50)], _ON_TIME),
        expected=ExpectedOutcome(
            label=DecisionLabel.ESCALATE,
            exception_types=[ExceptionType.UNKNOWN_PO],
            required_actions=[],
        ),
    ),
    EvalCase(
        case_id="missing-docs",
        asn=_asn("SH-DOCS", "PO-1002", "1Z-1002", [("SKU-B", 50)], _ON_TIME, docs_present=False),
        expected=ExpectedOutcome(
            label=DecisionLabel.HOLD,
            exception_types=[ExceptionType.MISSING_DOCS],
            required_actions=[],
        ),
    ),
    EvalCase(
        case_id="damaged",
        asn=_asn("SH-DMG", "PO-1002", "1Z-1002", [("SKU-B", 50)], _ON_TIME, damaged=True),
        expected=ExpectedOutcome(
            label=DecisionLabel.REROUTE,
            exception_types=[ExceptionType.DAMAGED],
            required_actions=[],
        ),
    ),
]
```
Note: `pyproject.toml` already sets `pythonpath = ["src"]`; add `.` so top-level `evals` is importable in tests. Change `pythonpath = ["src"]` to `pythonpath = ["src", "."]` in `[tool.pytest.ini_options]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/evals/test_dataset.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add evals/__init__.py evals/dataset.py tests/evals pyproject.toml
git commit -m "feat: add labeled eval dataset of shipment cases and expected outcomes"
```

---

### Task 2: Deterministic graders

**Files:**
- Create: `evals/graders/__init__.py`
- Create: `evals/graders/deterministic.py`
- Create: `tests/evals/test_deterministic_graders.py`

**Interfaces:**
- Consumes: `domain.models.{Decision, ExceptionRecord}`, `domain.enums.{DecisionLabel, ExceptionType}`.
- Produces:
  - `deterministic.PRF(precision: float, recall: float, f1: float)` (pydantic model).
  - `deterministic.label_match(expected: DecisionLabel, actual: DecisionLabel) -> bool`.
  - `deterministic.exception_prf(expected: list[ExceptionType], actual: list[ExceptionRecord]) -> PRF` — precision/recall/f1 over the *set* of exception types. Empty-expected + empty-actual → (1,1,1).
  - `deterministic.action_coverage(required: list[str], actual_actions: list[str]) -> float` — fraction of `required` keywords found (case-insensitive substring) across the joined `actual_actions`. Empty `required` → 1.0.

- [ ] **Step 1: Write the failing test**

`tests/evals/test_deterministic_graders.py`:
```python
import pytest

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import ExceptionRecord
from evals.graders.deterministic import action_coverage, exception_prf, label_match


def _exc(t):
    return ExceptionRecord(type=t, detail="x")


def test_label_match():
    assert label_match(DecisionLabel.HOLD, DecisionLabel.HOLD) is True
    assert label_match(DecisionLabel.HOLD, DecisionLabel.ACCEPT) is False


def test_exception_prf_perfect():
    prf = exception_prf([ExceptionType.QUANTITY_MISMATCH], [_exc(ExceptionType.QUANTITY_MISMATCH)])
    assert (prf.precision, prf.recall, prf.f1) == (1.0, 1.0, 1.0)


def test_exception_prf_both_empty_is_one():
    prf = exception_prf([], [])
    assert (prf.precision, prf.recall, prf.f1) == (1.0, 1.0, 1.0)


def test_exception_prf_false_positive_and_negative():
    # expected {QTY, LATE}; actual {QTY, DAMAGED}: tp=1, fp=1, fn=1
    prf = exception_prf(
        [ExceptionType.QUANTITY_MISMATCH, ExceptionType.LATE_DELIVERY],
        [_exc(ExceptionType.QUANTITY_MISMATCH), _exc(ExceptionType.DAMAGED)],
    )
    assert prf.precision == pytest.approx(0.5)
    assert prf.recall == pytest.approx(0.5)
    assert prf.f1 == pytest.approx(0.5)


def test_exception_prf_missed_all():
    prf = exception_prf([ExceptionType.QUANTITY_MISMATCH], [])
    assert prf.recall == 0.0
    assert prf.f1 == 0.0


def test_exception_prf_dedupes_actual():
    # two actual records of the same type count once
    prf = exception_prf(
        [ExceptionType.QUANTITY_MISMATCH],
        [_exc(ExceptionType.QUANTITY_MISMATCH), _exc(ExceptionType.QUANTITY_MISMATCH)],
    )
    assert (prf.precision, prf.recall, prf.f1) == (1.0, 1.0, 1.0)


def test_action_coverage():
    assert action_coverage([], []) == 1.0
    assert action_coverage(["supplier"], ["Notify the supplier of the shortage"]) == 1.0
    assert action_coverage(["supplier", "reroute"], ["notify supplier"]) == pytest.approx(0.5)
    assert action_coverage(["supplier"], []) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/evals/test_deterministic_graders.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals.graders'`.

- [ ] **Step 3: Write the implementation**

`evals/graders/__init__.py`: (empty file)

`evals/graders/deterministic.py`:
```python
from pydantic import BaseModel

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import ExceptionRecord


class PRF(BaseModel):
    precision: float
    recall: float
    f1: float


def label_match(expected: DecisionLabel, actual: DecisionLabel) -> bool:
    return expected == actual


def exception_prf(expected: list[ExceptionType], actual: list[ExceptionRecord]) -> PRF:
    expected_set = set(expected)
    actual_set = {e.type for e in actual}
    if not expected_set and not actual_set:
        return PRF(precision=1.0, recall=1.0, f1=1.0)
    tp = len(expected_set & actual_set)
    fp = len(actual_set - expected_set)
    fn = len(expected_set - actual_set)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PRF(precision=precision, recall=recall, f1=f1)


def action_coverage(required: list[str], actual_actions: list[str]) -> float:
    if not required:
        return 1.0
    haystack = " ".join(actual_actions).lower()
    hits = sum(1 for kw in required if kw.lower() in haystack)
    return hits / len(required)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/evals/test_deterministic_graders.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add evals/graders/__init__.py evals/graders/deterministic.py tests/evals/test_deterministic_graders.py
git commit -m "feat: add deterministic eval graders (label, exception PRF, action coverage)"
```

---

### Task 3: LLM-judge grader

**Files:**
- Create: `evals/graders/judge.py`
- Create: `tests/evals/test_judge.py`

**Interfaces:**
- Consumes: `domain.models.Decision`; `dataset.EvalCase`; `LLMClient`.
- Produces:
  - `judge.JudgeScore(score: int, rationale: str)` — pydantic, `score` in 1..5.
  - `judge.JUDGE_SYSTEM: str` — a version-pinned rubric constant (include a `RUBRIC_VERSION`).
  - `judge.judge_reasoning(case: EvalCase, decision: Decision, llm: LLMClient, model: str) -> StructuredResult` (value `JudgeScore`). Builds a prompt embedding the case's ASN + expected outcome + the produced decision, and calls `llm.complete_structured(..., output_type=JudgeScore)`.

- [ ] **Step 1: Write the failing test**

`tests/evals/test_judge.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/evals/test_judge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals.graders.judge'`.

- [ ] **Step 3: Write the implementation**

`evals/graders/judge.py`:
```python
import json

from pydantic import BaseModel, Field

from logistics_agents.domain.models import Decision
from logistics_agents.llm.client import LLMClient
from logistics_agents.llm.types import StructuredResult
from evals.dataset import EvalCase

RUBRIC_VERSION = "judge-v1"

JUDGE_SYSTEM = (
    "You are an expert logistics operations reviewer acting as an impartial grader "
    f"(rubric {RUBRIC_VERSION}). You are given a shipment notification, the expected "
    "outcome, and the decision an automated agent produced. Score the decision's "
    "REASONING quality from 1 (unusable) to 5 (excellent) on: whether it is faithful to "
    "the evidence, cites the relevant PO/inventory/carrier facts, avoids hallucinated "
    "claims, and justifies the chosen label and actions. Judge the reasoning, not just "
    "whether the label matched. Respond only via the structured schema."
)


class JudgeScore(BaseModel):
    score: int = Field(ge=1, le=5)
    rationale: str


def judge_reasoning(case: EvalCase, decision: Decision, llm: LLMClient, model: str) -> StructuredResult:
    context = {
        "shipment_notification": case.asn.model_dump(mode="json"),
        "expected_outcome": case.expected.model_dump(mode="json"),
        "agent_decision": decision.model_dump(mode="json"),
    }
    user = json.dumps(context, indent=2, default=str)
    return llm.complete_structured(
        model=model, system=JUDGE_SYSTEM, user=user, output_type=JudgeScore
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/evals/test_judge.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add evals/graders/judge.py tests/evals/test_judge.py
git commit -m "feat: add LLM-as-judge reasoning grader with version-pinned rubric"
```

---

### Task 4: Composite grader

**Files:**
- Create: `evals/graders/composite.py`
- Create: `tests/evals/test_composite.py`

**Interfaces:**
- Consumes: `dataset.ExpectedOutcome`; `domain.models.Decision`; `deterministic` (Task 2); `judge.JudgeScore` (Task 3).
- Produces:
  - `composite.CaseScore(label_correct: bool, exception_f1: float, exception_precision: float, exception_recall: float, action_coverage: float, judge_score: int | None, composite: float)`.
  - `composite.grade(expected: ExpectedOutcome, decision: Decision, judge: JudgeScore | None) -> CaseScore` — composite = `0.4*label + 0.3*f1 + 0.1*action + 0.2*(judge/5)` when a judge score is present; when `judge is None`, renormalize over the deterministic weights (`0.4/0.3/0.1` scaled to sum 1) so the composite stays in [0,1].

- [ ] **Step 1: Write the failing test**

`tests/evals/test_composite.py`:
```python
import pytest

from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord
from evals.dataset import ExpectedOutcome
from evals.graders.composite import grade
from evals.graders.judge import JudgeScore


def _decision(label, types, actions):
    return Decision(
        label=label,
        exceptions=[ExceptionRecord(type=t, detail="x") for t in types],
        recommended_actions=actions,
        confidence=0.9,
        reasoning="r",
    )


def _expected(label, types, actions):
    return ExpectedOutcome(label=label, exception_types=types, required_actions=actions)


def test_perfect_case_with_top_judge_is_one():
    exp = _expected(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["supplier"])
    dec = _decision(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["notify supplier"])
    score = grade(exp, dec, JudgeScore(score=5, rationale="great"))
    assert score.label_correct is True
    assert score.exception_f1 == 1.0
    assert score.action_coverage == 1.0
    assert score.judge_score == 5
    assert score.composite == pytest.approx(1.0)


def test_wrong_label_caps_composite_below_one():
    exp = _expected(DecisionLabel.HOLD, [], [])
    dec = _decision(DecisionLabel.ACCEPT, [], [])
    score = grade(exp, dec, JudgeScore(score=5, rationale="x"))
    assert score.label_correct is False
    # label weight (0.4) is lost; everything else perfect → 0.6
    assert score.composite == pytest.approx(0.6)


def test_composite_without_judge_renormalizes_to_one():
    exp = _expected(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["supplier"])
    dec = _decision(DecisionLabel.HOLD, [ExceptionType.QUANTITY_MISMATCH], ["notify supplier"])
    score = grade(exp, dec, None)
    assert score.judge_score is None
    assert score.composite == pytest.approx(1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/evals/test_composite.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals.graders.composite'`.

- [ ] **Step 3: Write the implementation**

`evals/graders/composite.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/evals/test_composite.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add evals/graders/composite.py tests/evals/test_composite.py
git commit -m "feat: add composite grader blending deterministic scores with LLM judge"
```

---

### Task 5: Eval runner

**Files:**
- Create: `evals/runner.py`
- Create: `tests/evals/test_runner.py`

**Interfaces:**
- Consumes: `dataset.EvalCase`; `orchestration.runner.run_pipeline`; `tracing.Tracer`; `graders.{judge, composite}`; `LLMClient`.
- Produces:
  - `runner.CaseResult(case_id: str, model: str, label: str, score: CaseScore)`.
  - `runner.EvalReport(model: str, results: list[CaseResult], label_accuracy: float, mean_f1: float, mean_action_coverage: float, mean_judge: float | None, mean_composite: float)`.
  - `runner.run_eval(cases, conn, llm, model, judge_llm=None, judge_model=None, persist_traces=False) -> EvalReport` — for each case: run `run_pipeline` (fresh `Tracer`, `run_id=f"{model}:{case_id}"`, `conn` passed only when `persist_traces`), grade deterministically, optionally judge (when `judge_llm` given), compose, collect. Aggregate the means.

- [ ] **Step 1: Write the failing test**

`tests/evals/test_runner.py`:
```python
from logistics_agents.agents.contracts import (
    CarrierFinding,
    ExceptionFinding,
    InventoryFinding,
    OrchestrationPlan,
    QuantityDiscrepancy,
)
from logistics_agents.domain.enums import DecisionLabel, ExceptionType
from logistics_agents.domain.models import Decision, ExceptionRecord
from logistics_agents.llm.client import LLMClient
from evals.dataset import CASES
from evals.graders.judge import JudgeScore
from evals.runner import run_eval


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/evals/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals.runner'`.

- [ ] **Step 3: Write the implementation**

`evals/runner.py`:
```python
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
```

Note: `run_pipeline` persists a `Decision` row via `insert_decision`. With `persist_traces=False` the `Tracer` won't write traces, but `run_pipeline` still calls `insert_decision(conn, run_id, ...)`. Since each case uses a unique `run_id` (`model:case_id`) and the test fixture truncates between tests, there is no PK collision within a single `run_eval` call across distinct cases. (Re-running the same case+model in one process on a persistent DB would collide — that's the documented unique-`run_id` contract.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/evals/test_runner.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add evals/runner.py tests/evals/test_runner.py
git commit -m "feat: add eval runner scoring the pipeline across a dataset into an EvalReport"
```

---

### Task 6: Results persistence + regression baseline

**Files:**
- Create: `evals/results.py`
- Create: `tests/evals/test_results.py`

**Interfaces:**
- Consumes: `runner.EvalReport`.
- Produces:
  - `results.write_report(report: EvalReport, out_dir: Path) -> Path` — writes `<out_dir>/<model>.json` (the `EvalReport` JSON), returns the path.
  - `results.load_report(path: Path) -> EvalReport`.
  - `results.check_regression(report: EvalReport, baseline: EvalReport, tolerance: float = 0.0) -> list[str]` — returns a list of human-readable regression messages where `report.mean_composite < baseline.mean_composite - tolerance` or any per-case composite drops below its baseline by more than `tolerance`; empty list means no regression.

- [ ] **Step 1: Write the failing test**

`tests/evals/test_results.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/evals/test_results.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals.results'`.

- [ ] **Step 3: Write the implementation**

`evals/results.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/evals/test_results.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add evals/results.py tests/evals/test_results.py
git commit -m "feat: add eval report persistence and regression-vs-baseline check"
```

---

### Task 7: Live entrypoint (model comparison)

**Files:**
- Create: `evals/run.py`
- Create: `tests/evals/test_run_entry.py`

**Interfaces:**
- Consumes: `dataset.CASES`; `runner.run_eval`; `results.write_report`; `llm.{client.LLMClient, cache.RecordReplayCache, anthropic_transport.AnthropicTransport}`.
- Produces:
  - `run.build_client(mode: str, fixtures_dir: Path) -> LLMClient` — wraps `AnthropicTransport` in a `RecordReplayCache` (`mode` `live`/`replay`) → `LLMClient`.
  - `run.run_comparison(models: list[str], cases, conn, mode, fixtures_dir, out_dir, judge_model) -> list[EvalReport]` — runs `run_eval` for each model (using the record/replay client for both pipeline and judge), writes each report.
  - `run.main(argv=None)` — argparse CLI: `--models a,b,c`, `--mode live|replay`, `--out`, `--fixtures`, `--judge-model`; connects to Postgres via `LOGISTICS_DATABASE_URL` (default the docker-compose DSN), seeds, runs the comparison, prints a summary table.

- [ ] **Step 1: Write the failing test**

`tests/evals/test_run_entry.py`:
```python
import os

import pytest

from evals.run import build_client, run_comparison


def test_build_client_returns_llm_client(tmp_path):
    from logistics_agents.llm.client import LLMClient

    client = build_client(mode="replay", fixtures_dir=tmp_path)
    assert isinstance(client, LLMClient)


def test_run_comparison_scores_each_model_with_scripted_clients(postgres_conn, scripted_transport, tmp_path):
    # Inject scripted clients directly (bypass the Anthropic transport) to keep this key-free.
    from logistics_agents.agents.contracts import (
        CarrierFinding, ExceptionFinding, InventoryFinding, OrchestrationPlan,
    )
    from logistics_agents.domain.enums import DecisionLabel
    from logistics_agents.domain.models import Decision
    from logistics_agents.llm.client import LLMClient
    from logistics_agents.data import seed
    from evals.dataset import CASES

    seed.load_seed(postgres_conn)
    clean = next(c for c in CASES if c.case_id == "clean-accept")
    script = {
        OrchestrationPlan: OrchestrationPlan(subtasks=["x"], reasoning="d"),
        InventoryFinding: InventoryFinding(po_matched=True, discrepancies=[], capacity_ok=True, reasoning="i"),
        CarrierFinding: CarrierFinding(status="in_transit", eta=None, delayed=False, reasoning="c"),
        ExceptionFinding: ExceptionFinding(exceptions=[], reasoning="e"),
        Decision: Decision(label=DecisionLabel.ACCEPT, exceptions=[], recommended_actions=[], confidence=0.9, reasoning="r"),
    }
    transport, _ = scripted_transport(script)

    reports = run_comparison(
        models=["claude-sonnet-5", "claude-haiku-4-5"],
        cases=[clean],
        conn=postgres_conn,
        out_dir=tmp_path,
        client_factory=lambda model: LLMClient(transport),  # test hook
        judge_llm=None,
    )
    assert {r.model for r in reports} == {"claude-sonnet-5", "claude-haiku-4-5"}
    assert (tmp_path / "claude-sonnet-5.json").exists()
    assert all(r.label_accuracy == 1.0 for r in reports)


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="live comparison needs ANTHROPIC_API_KEY")
def test_live_smoke_single_case(postgres_conn):
    # Records fixtures + does one real call per node for one case on the cheapest model.
    from logistics_agents.data import seed
    from evals.dataset import CASES
    import tempfile

    seed.load_seed(postgres_conn)
    clean = next(c for c in CASES if c.case_id == "clean-accept")
    with tempfile.TemporaryDirectory() as d:
        reports = run_comparison(
            models=["claude-haiku-4-5"], cases=[clean], conn=postgres_conn,
            out_dir=d, mode="live", fixtures_dir=d, judge_llm=None,
        )
    assert reports[0].results[0].label in {"ACCEPT", "HOLD", "REROUTE", "ESCALATE"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/evals/test_run_entry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals.run'`. (The live smoke test is skipped without a key.)

- [ ] **Step 3: Write the implementation**

`evals/run.py`:
```python
import argparse
import os
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/evals/test_run_entry.py -v`
Expected: PASS (2 passed, 1 skipped — the live smoke test skips without a key).

- [ ] **Step 5: Run the full milestone suite**

Run: `uv run pytest -v`
Expected: PASS — all M1–M4 tests (M2 + M4 live tests skipped).

- [ ] **Step 6: Commit**

```bash
git add evals/run.py tests/evals/test_run_entry.py
git commit -m "feat: add live model-comparison entrypoint with record/replay and results output"
```

---

## Self-Review

**Spec coverage (Milestone 4 scope = spec §7 eval infrastructure, milestone 15.4):**
- Labeled dataset with expected outputs (§7): Task 1 (`CASES` + `ExpectedOutcome`). ✅
- Deterministic scorers — label match, exception precision/recall/F1, action coverage (§7): Task 2, rigorously unit-tested (the graders get the most tests, per spec). ✅
- LLM-as-judge with version-pinned rubric (§7): Task 3 (`JUDGE_SYSTEM` + `RUBRIC_VERSION`). ✅
- Composite weighted score per case (§7): Task 4. ✅
- Runner over the dataset feeding results (§7): Task 5 (`run_eval` → `EvalReport`). ✅
- Regression vs. a committed baseline (§7): Task 6 (`check_regression`). ✅
- Model-comparison across Opus/Sonnet/Haiku in live mode → results artifacts (§7, §2): Task 7 (`run.py`, record/replay). ✅
- Key-free CI (Global Constraint): every test uses concrete inputs or a scripted transport; the two live tests are `skipif` on `ANTHROPIC_API_KEY`. ✅

Out of scope (correctly deferred): node-level per-specialist grading is deferred — it needs expected per-node findings (more labeling); M4 grades the final `Decision` + reasoning, which is the core. CI wiring of the replay regression suite is M5. Dashboard consumption of the `EvalReport` JSON is M7. The `evals.run` live entrypoint is built and unit-tested key-free, but recording real fixtures / running the true model comparison is an operator step (`ANTHROPIC_API_KEY` + `mode=live`).

**Placeholder scan:** No TBD/TODO. Every code step is complete. The `client_factory` test hook in `run_comparison` is a real dependency-injection seam (keeps the entrypoint test key-free), not a placeholder.

**Type consistency:** `EvalCase`/`ExpectedOutcome` (Task 1) consumed unchanged by graders (Tasks 3–4) and the runner (Task 5). `PRF`/`exception_prf`/`label_match`/`action_coverage` (Task 2) called with matching signatures in `composite.grade` (Task 4). `JudgeScore` (Task 3) is the judge `output_type` and a `grade` argument. `CaseScore` (Task 4) is nested in `CaseResult`/`EvalReport` (Task 5), which `results.py` (Task 6) and `run.py` (Task 7) serialize/consume. `run_eval` (Task 5) is called identically by `run_comparison` (Task 7). The runner passes a unique `run_id=f"{model}:{case_id}"` to `run_pipeline`, honoring M3's documented contract.
