from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="logistics-agents API")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    from logistics_agents.api.routes import register_routes

    register_routes(app)
    return app
