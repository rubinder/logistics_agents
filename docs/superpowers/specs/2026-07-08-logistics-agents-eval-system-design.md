# Multi-Agent Logistics Decisioning System with Eval Infrastructure — Design

**Date:** 2026-07-08
**Status:** Approved (design)
**Author:** Rob Randhawa

## 1. Purpose & framing

A portfolio-grade system that demonstrates **agent quality as an engineering discipline**, not prompt tinkering. A multi-agent pipeline ingests an inbound shipment notification, decomposes the task across specialist agents, and synthesizes a structured decision. Wrapped around it is the real deliverable: a **labeled eval dataset, a composite grader, a regression suite that runs on every commit, model-comparison runs, and a public dashboard** that tracks quality over time and lets viewers watch runs execute live.

The multi-agent system is the vehicle; the eval + observability infrastructure is the differentiator.

### Success criteria

- A run turns a shipment notification into a validated structured `Decision`.
- Every node (orchestrator, 3 specialists, synthesis) is independently gradable.
- A regression suite runs deterministically and free on every commit (replay mode) and fails on quality regressions.
- Model-comparison runs produce quality/latency/cost metrics across Opus / Sonnet / Haiku.
- A publicly deployed dashboard visualizes the DAG live, replays past runs, and shows quality-over-time — safely, with no uncapped API-cost exposure.

## 2. Stack decisions (settled)

| Decision | Choice |
|---|---|
| Core language | Python |
| Dashboard | TypeScript / React (Vite) |
| Agent execution | Real Anthropic API calls + record/replay fixture cache |
| Data infra | Postgres + Kafka (Redpanda), dockerized |
| Orchestration | Fixed DAG, LLM-backed nodes (agentic decompose + synthesize, deterministic routing) |
| Grading | Hybrid: deterministic checks + LLM-as-judge, composite score |
| Public access | Watch-only + scheduled demo runs + small allowance of rate-limited visitor-triggered runs, one hard budget cap |
| Flow UI | Live-stream active runs (SSE) + replay stored traces |
| Cloud | Cost-conscious AWS: S3+CloudFront (dashboard), single small EC2 via docker-compose (API+runner+Redpanda+Postgres), Redpanda instead of MSK |

## 3. System architecture

```
Kafka topic: shipment.notifications  (inbound ASN messages)
                     │
                     ▼
        ┌─────────────────────────┐
        │   Orchestrator agent     │  LLM: ASN → decomposition/plan
        └─────────────────────────┘
             │ (deterministic routing to fixed specialist set)
   ┌─────────┼───────────────┐
   ▼         ▼               ▼
┌─────────┐ ┌────────┐  ┌──────────────┐
│Inventory│ │Carrier │  │  Exception   │  LLM agents w/ narrow tools
│ agent   │ │ agent  │  │  agent       │
└─────────┘ └────────┘  └──────────────┘
   │ Postgres   │ mock carrier   │ (reasons over PO + peer outputs)
   └────────────┴───────────────┘
                     ▼
        ┌─────────────────────────┐
        │   Synthesis agent        │  LLM → structured Decision
        └─────────────────────────┘
                     ▼
   Decision {label, exceptions[], actions[], confidence, reasoning}
                     │
                     ▼  persisted to Postgres `decisions` + trace store
```

Each node emits a **trace record** (input, output, latency, tokens, cost, model). Traces power the dashboard, the eval runner, and debugging.

## 4. Components & boundaries

| Unit | Responsibility | Depends on |
|---|---|---|
| `agents/orchestrator` | Read ASN, produce decomposition/plan | `llm/`, `domain/` |
| `agents/inventory` | Reconcile ASN vs PO + capacity via Postgres | `data/`, `llm/` |
| `agents/carrier` | ETA / delay / in-transit via mock carrier API | `data/`, `llm/` |
| `agents/exception` | Detect typed exceptions over peer outputs + PO | `llm/`, `domain/` |
| `agents/synthesis` | Merge into final `Decision` | `llm/`, `domain/` |
| `llm/` | Anthropic client wrapper, record/replay cache, structured-output enforcement | Anthropic SDK |
| `domain/` | Pydantic models & enums (single schema source of truth) | — |
| `data/` | Postgres access, Kafka consumer/producer, seed loader | Postgres, Redpanda |
| `orchestration/` | Fixed DAG runner; emits trace events | `agents/`, `tracing/` |
| `tracing/` | Structured per-run trace capture + persistence | Postgres |
| `evals/` | Dataset, graders, runner (replay + live modes), results | `orchestration/`, `data/` |
| `api/` (FastAPI) | Trace/eval reads, SSE live stream, rate-limited trigger, budget ledger | `orchestration/`, `data/` |
| `dashboard/` | React viewer: run visualizer, eval views, trigger panel | `api/` |

**Boundary test:** each specialist can be understood and graded without reading the others' internals; agents communicate only through typed pydantic contracts.

## 5. Domain model

**Postgres tables:** `purchase_orders`, `inventory`, `shipments`, `carrier_events`, `decisions`, `runs` (traces), `budget_ledger`.

**Pydantic models:** `ShipmentNotification` (ASN), `PurchaseOrder`, `InventoryState`, `CarrierStatus`, `ExceptionRecord`, `Decision`, `TraceRecord`.

**Exception taxonomy (typed enum):** `QUANTITY_MISMATCH`, `LATE_DELIVERY`, `UNKNOWN_PO`, `OVERCAPACITY`, `MISSING_DOCS`, `DAMAGED`.

**Decision labels:** `ACCEPT | HOLD | REROUTE | ESCALATE`.

**`Decision` shape:** `{ label, exceptions: ExceptionRecord[], recommended_actions: string[], confidence: float, reasoning: string }`. Emitted via Anthropic tool-use / structured output, validated by pydantic.

## 6. LLM wrapper & record/replay

- Thin wrapper around the Anthropic SDK enforcing structured output against pydantic schemas.
- **Record/replay cache** keyed on `(model, prompt hash, tool schema hash)`:
  - **live mode** → real call, records response to `fixtures/`.
  - **replay mode** → returns cached response; a cache miss is a hard failure (keeps CI honest).
- Captures tokens/cost/latency per call for tracing and model comparison.

## 7. Eval infrastructure (the star)

- **Dataset** — `evals/dataset/`, ~30–40 labeled cases: happy path, one per exception type, multi-exception, and ambiguous edge cases. Each case = `{ seed DB state + ASN input, expected Decision }`.
- **Graders (composite per case):**
  - *Deterministic:* decision-label match; exception-set **precision / recall / F1**; required-action coverage.
  - *LLM-judge:* reasoning rubric (evidence-faithfulness, actionability, no hallucinated facts), 1–5, judge prompt **version-pinned**.
  - *Node-level:* each specialist graded independently so a regression localizes to a node.
  - Composite weighted score per case + aggregate report.
- **Regression suite** — pytest in **replay mode** on every commit; asserts scores stay at/above a committed baseline within tolerance.
- **Model-comparison runs** — **live mode**, full dataset across Opus / Sonnet / Haiku → JSON results artifacts feeding the dashboard. Manual + nightly.
- **Grader tests are the most rigorous unit tests in the repo** — a grader bug silently invalidates every score.

## 8. API service & run control (FastAPI)

- **Endpoints:** list/detail traces; eval results; **SSE live-run stream**; `POST /runs` (rate-limited trigger from a fixed demo-scenario set); budget/quota status.
- **Budget ledger** (Postgres): every live run debits it; hard-stop when the monthly cap is hit.
- **Rate limiter:** per-IP + global daily quota for the trigger button; scheduled runs and visitor runs share one cap.
- **Scheduler** (EventBridge or in-container cron): generates demo runs at reduced frequency.
- Anthropic key **server-side only** (SSM Parameter Store); triggered runs default to a cheap model.

## 9. Dashboard (React viewer)

- **Run visualizer:** DAG renders live — nodes light up per agent with status, I/O, latency/cost, per-node + final scores. Live via SSE; any stored run replayable step-by-step.
- **Eval views:** quality-over-time (per commit & per model), per-model comparison, per-case drilldown, judge-vs-deterministic breakdown, latency/cost.
- **Trigger panel:** pick a demo scenario → run (quota-gated); budget/quota meter disables the button when exhausted.
- Read-only, static build.

## 10. CI/CD (GitHub Actions)

- **Every commit:** lint + typecheck + **pytest regression in replay mode** + dashboard build.
- **Nightly:** live model-comparison eval → results artifact committed/uploaded.
- **Deploy:** dashboard → S3+CloudFront; API/runner image → EC2.

## 11. AWS deployment (cost-conscious)

- **Dashboard** → S3 + CloudFront.
- **API + agent runner + Redpanda + Postgres** → single small EC2 via docker-compose (mirrors local dev; RDS an easy later swap).
- **Redpanda** single-node (Kafka-API compatible) instead of MSK.
- **IaC:** Terraform (S3, CloudFront, EC2, security groups, SSM Parameter Store). Secrets never in git.
- **Cost safety:** server-side key only; budget ledger hard-stop; triggered runs limited to demo scenarios + cheap model.

## 12. Testing strategy

TDD throughout. Priority order:
1. **Graders** (most rigorous — correctness of the whole eval hinges on them).
2. Domain models + structured-output validation.
3. Record/replay cache.
4. One full-pipeline integration test in replay mode.
5. API budget/rate-limit enforcement tests.

## 13. Scope / YAGNI guardrails

- Exactly 3 specialists; ~30–40 eval cases.
- Mock carrier API backed by `carrier_events` — no real carrier integrations.
- No auth, no multi-tenant, no live prod write-back beyond the demo.
- One Kafka topic, single consumer.
- Dashboard read-only; public deploy is a showcase over the same eval infra exercised locally + in CI.

## 14. Project layout

```
logistics_agents/
  docker-compose.yml
  pyproject.toml
  src/logistics_agents/
    agents/        # orchestrator, inventory, carrier, exception, synthesis
    llm/           # client wrapper, record_replay, structured output
    domain/        # pydantic models, enums
    data/          # db access, kafka, seed
    orchestration/ # DAG runner
    tracing/       # trace capture + persistence
    api/           # FastAPI app, SSE, budget, rate-limit
  evals/
    dataset/       # cases + seeds
    graders/       # deterministic, judge, composite
    runner.py      # replay + live modes
    results/       # artifacts
  dashboard/       # Vite + React + TS
  infra/           # Terraform
  fixtures/        # recorded LLM responses
  tests/
  .github/workflows/  # ci.yml, nightly-eval.yml
```

## 15. Implementation milestones

1. Domain models + Postgres/Kafka schema + docker-compose + seed loader.
2. LLM wrapper + record/replay + structured output.
3. Five agents + DAG runner + tracing.
4. Eval dataset + graders + runner (replay & live).
5. CI regression suite (replay mode).
6. FastAPI service: tracing reads, SSE, budget ledger, rate limiter, scheduler.
7. Dashboard: run visualizer + eval views + trigger panel.
8. AWS/Terraform deploy + deploy workflows.

Each milestone gets its own implementation-plan slice, built and reviewed in stages.
