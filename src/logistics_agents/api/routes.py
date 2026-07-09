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
