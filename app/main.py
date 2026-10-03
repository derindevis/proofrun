"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the ProofRun API application."""
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.include_router(api_v1_router, prefix="/api/v1")

    @application.get("/", tags=["health"])
    def root_health() -> dict[str, str]:
        """Report availability of the ProofRun service."""
        return {"status": "ok", "service": "proofrun"}

    return application


app = create_app()
