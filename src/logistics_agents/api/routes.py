from fastapi import Depends, FastAPI, HTTPException

from logistics_agents.api import guards
from logistics_agents.api.deps import get_conn, get_settings
from logistics_agents.data import repository


def register_routes(app: FastAPI) -> None:
    @app.get("/budget")
    def budget(conn=Depends(get_conn), settings=Depends(get_settings)):
        return guards.budget_status(conn, settings.budget_cap_usd).model_dump()

    @app.get("/runs")
    def list_runs(conn=Depends(get_conn)):
        return {"run_ids": repository.list_run_ids(conn)}

    @app.get("/runs/{run_id}/trace")
    def run_trace(run_id: str, conn=Depends(get_conn)):
        return [t.model_dump(mode="json") for t in repository.get_traces(conn, run_id)]

    @app.get("/runs/{run_id}/decision")
    def run_decision(run_id: str, conn=Depends(get_conn)):
        decision = repository.get_decision(conn, run_id)
        if decision is None:
            raise HTTPException(status_code=404, detail="decision not found")
        return decision.model_dump(mode="json")

    from fastapi import Request

    from logistics_agents.api.deps import get_llm
    from logistics_agents.api.scenarios import SCENARIOS
    from logistics_agents.orchestration.runner import run_pipeline
    from logistics_agents.tracing.tracer import Tracer

    @app.get("/scenarios")
    def scenarios_list():
        return {"scenarios": sorted(SCENARIOS)}

    @app.post("/runs")
    def trigger_run(
        request: Request,
        payload: dict,
        conn=Depends(get_conn),
        llm=Depends(get_llm),
        settings=Depends(get_settings),
    ):
        scenario_id = payload.get("scenario_id")
        if scenario_id not in SCENARIOS:
            raise HTTPException(status_code=400, detail="unknown scenario_id")

        client_ip = request.client.host if request.client else "unknown"
        if not guards.rate_allows(conn, client_ip, settings.per_ip_daily, settings.global_daily):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        if not guards.budget_allows(conn, settings.budget_cap_usd):
            raise HTTPException(status_code=402, detail="budget exhausted")

        asn = SCENARIOS[scenario_id]
        seq = repository.count_entries(conn, source_prefix="trigger:")
        run_id = f"trigger-{scenario_id}-{seq}"
        tracer = Tracer(run_id=run_id, conn=conn)
        decision = run_pipeline(asn, conn, llm, model="claude-opus-4-8", run_id=run_id, tracer=tracer)

        cost = sum(t.cost_usd for t in tracer.records)
        repository.insert_budget_entry(conn, run_id, cost, f"trigger:{client_ip}")
        return {"run_id": run_id, "decision": decision.model_dump(mode="json"), "cost_usd": cost}
