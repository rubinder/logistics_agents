# logistics_agents

**A multi-agent logistics decisioning system — built to demonstrate agent quality as an engineering discipline, not prompt tinkering.**

🔗 **Live demo:** https://dh95veq0vfppo.cloudfront.net — watch a shipment flow through the agent pipeline node-by-node to a structured decision, and compare model quality.

An inbound shipment notification is decomposed by an orchestrator agent, routed to three specialist agents (inventory reconciliation, carrier tracking, exception detection), and synthesized into a structured **accept / hold / reroute / escalate** decision. Wrapped around that pipeline is the real deliverable: a **labeled eval dataset, a hybrid grader (deterministic + LLM-as-judge), a regression suite that runs on every commit, and a model-comparison harness** — the machinery to prove the agents are good and catch the moment they regress.

## Why this exists

Most agent demos wire up an LLM and hope. This project treats agent output the way you'd treat any other critical code path: **measured, tested, and defended on every commit.** The logistics domain is a concrete, believable place to demonstrate that discipline.

## Architecture

```
Kafka (Redpanda)                    ┌──────────────┐
 shipment.notifications ──────────▶ │ Orchestrator │  decomposes the task
                                    └──────┬───────┘
                            deterministic routing (fixed DAG)
                     ┌─────────────┬───────┴───────┐
                     ▼             ▼               ▼
              ┌───────────┐ ┌───────────┐  ┌──────────────┐
              │ Inventory │ │  Carrier  │  │  Exception   │  specialist agents
              └─────┬─────┘ └─────┬─────┘  └──────┬───────┘
                    │  Postgres   │ carrier events │
                    └─────────────┴────────────────┘
                                  ▼
                          ┌──────────────┐
                          │  Synthesis   │ → structured Decision
                          └──────────────┘
                                  │  every node traced (cost/latency/tokens)
                                  ▼
                Decision + per-node trace  →  Postgres  →  API  →  Dashboard

   Eval harness:  dataset → deterministic graders + LLM judge → composite
                  score → regression-on-commit + Opus/Sonnet/Haiku comparison
```

## The eval story (the differentiator)

- **Labeled dataset** of shipment scenarios with expected outcomes (`evals/dataset.py`).
- **Deterministic graders** — decision-label match, exception-set precision/recall/**F1**, action coverage — the most rigorously unit-tested code in the repo, because a grader bug silently invalidates every score.
- **LLM-as-judge** with a version-pinned rubric that scores *reasoning faithfulness* (and is never shown the gold answer).
- **Composite score** blending the two, with a **regression suite** that runs in replay mode on every commit — free and deterministic (a record/replay fixture cache means CI never calls a paid API).
- **Model comparison** — run the whole dataset across Opus / Sonnet / Haiku and score quality vs. cost vs. latency.

## Engineering highlights

- **Deterministic, key-free CI.** A record/replay `Transport` cache makes every test hermetic; the full suite runs without an API key. Live model runs are a separate, opt-in step.
- **Safe public exposure.** The FastAPI service guards the public trigger with a budget ledger (hard monthly cap) + per-IP/global rate limits, fail-closed spend accounting, and a cheap default model — so a visitor can't run up an unbounded bill. The Anthropic key stays server-side in SSM.
- **Observability.** Every agent call is traced (input, output, cost, latency, tokens) and persisted; the dashboard replays a run node-by-node.
- **Real infra.** Postgres + Kafka (dockerized), a typed pydantic domain, testcontainers integration tests, and a one-command AWS deploy (Terraform: S3+CloudFront + EC2, same-origin proxy — no CORS).

## Tech stack

Python 3.12 · pydantic v2 · FastAPI · psycopg 3 · confluent-kafka / Redpanda · PostgreSQL · Anthropic SDK · pytest + testcontainers · Vite + React + TypeScript · Vitest · Terraform · AWS (S3, CloudFront, EC2, SSM) · GitHub Actions · uv · ruff

## Run it locally

```bash
# Backend: infra + tests (needs Docker for testcontainers)
docker compose up -d postgres redpanda
uv sync --extra dev
uv run pytest

# The full deploy stack (API + Postgres) locally:
docker compose -f docker-compose.deploy.yml up -d --build
curl localhost:80/health

# Dashboard (renders standalone from bundled sample data)
cd dashboard && npm install && npm run dev

# Live model comparison (spends API budget)
ANTHROPIC_API_KEY=sk-ant-... uv run python -m evals.run --mode live \
  --models claude-opus-4-8,claude-sonnet-5,claude-haiku-4-5
```

## Deploy to AWS

One-command provision (S3+CloudFront dashboard + EC2 API, key in SSM) — see [`infra/README.md`](infra/README.md) for the runbook, cost, and teardown.

## Project layout

| Path | What |
|---|---|
| `src/logistics_agents/domain/` | pydantic domain models + enums |
| `src/logistics_agents/data/` | Postgres schema, repository, seed, Kafka wrappers |
| `src/logistics_agents/llm/` | Anthropic wrapper + record/replay cache |
| `src/logistics_agents/agents/` | the five agents |
| `src/logistics_agents/orchestration/` | the fixed-DAG runner |
| `src/logistics_agents/tracing/` | per-node trace capture |
| `src/logistics_agents/api/` | FastAPI service (budget/rate guards, SSE) |
| `evals/` | dataset, graders, runner, model-comparison entrypoint |
| `dashboard/` | Vite + React + TS control-room dashboard |
| `infra/` | Terraform AWS deploy |
| `docs/superpowers/` | the spec and per-milestone implementation plans |

Built in eight reviewed milestones (see `docs/superpowers/plans/` and PRs #1–#8).
