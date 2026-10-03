"""Versioned deterministic verification endpoint."""

from fastapi import APIRouter

from app.verification.models import VerificationRequest, VerificationResponse
from app.verification.service import verify

router = APIRouter(tags=["verification"])


@router.post("/verify", response_model=VerificationResponse)
def verify_protocol(request: VerificationRequest) -> VerificationResponse:
    """Verify structured protocol evidence using the pure deterministic verifier."""
    result = verify(request.protocol, request.evidence)
    return VerificationResponse.model_validate(result.model_dump())
