"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from reefcommand.api.routes import health, observations, plan, resources, sites


def create_app() -> FastAPI:
    """Build the application with all routers mounted."""
    application = FastAPI(
        title="ReefCommand",
        version="0.1.0",
        summary=(
            "Decision support that turns environmental monitoring, field observations, "
            "scientific intervention guidance, and limited conservation resources into "
            "continuously updated reef-response plans."
        ),
    )
    application.include_router(health.router)
    application.include_router(sites.router)
    application.include_router(observations.router)
    application.include_router(plan.router)
    application.include_router(resources.router)
    return application


app = create_app()
