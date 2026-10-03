"""Health-check endpoint for the versioned API."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def api_health() -> dict[str, str]:
    """Report the availability of API version 1."""
    return {"status": "ok", "service": "proofrun-api", "api_version": "v1"}
