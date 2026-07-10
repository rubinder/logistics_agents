import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="logistics-agents API")

    cors_origins = os.environ.get("LOGISTICS_CORS_ORIGINS")
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin.strip() for origin in cors_origins.split(",")],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    from logistics_agents.api.routes import register_routes

    register_routes(app)
    return app
