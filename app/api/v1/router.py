"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.verification import router as verification_router

router = APIRouter()
router.include_router(health_router)
router.include_router(verification_router)
