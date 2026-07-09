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
