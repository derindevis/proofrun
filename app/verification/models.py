"""Structured deterministic verification output models."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.evidence.models import Evidence
from app.protocols.models import Protocol


class VerificationDecision(StrEnum):
    PASS = "PASS"
    INSUFFICIENT = "INSUFFICIENT"
    BLOCKED = "BLOCKED"


class RequirementOutcome(StrEnum):
    PASS = "PASS"
    FAILED = "FAILED"
    INSUFFICIENT = "INSUFFICIENT"
    BLOCKED = "BLOCKED"


class RequirementVerification(BaseModel):
    """A deterministic reason for one requirement's outcome."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    outcome: RequirementOutcome
    reason_code: str
    message: str
    evidence_ids: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """The aggregate result and requirement-level audit trail."""

    model_config = ConfigDict(extra="forbid")

    decision: VerificationDecision
    requirement_results: list[RequirementVerification] = Field(default_factory=list)


class VerificationRequest(BaseModel):
    """HTTP contract for a deterministic protocol verification request."""

    model_config = ConfigDict(extra="forbid")

    protocol: Protocol
    evidence: list[Evidence]


class VerificationResponse(VerificationResult):
    """HTTP contract for a deterministic protocol verification response."""
