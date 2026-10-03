"""Structured test protocol models used by deterministic verification."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequirementType(StrEnum):
    """Requirement checks supported by the initial verifier."""

    NUMERIC_RANGE = "numeric_range"
    DURATION_COMPLETENESS = "duration_completeness"
    REQUIRED_EVIDENCE = "required_evidence"


class Requirement(BaseModel):
    """A single, explicitly verifiable protocol requirement."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    requirement_type: RequirementType
    mandatory: bool = True
    minimum: float | None = None
    maximum: float | None = None
    minimum_duration_seconds: float | None = Field(default=None, ge=0)
    required_evidence_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_check_parameters(self) -> "Requirement":
        if self.requirement_type is RequirementType.NUMERIC_RANGE:
            if self.minimum is None and self.maximum is None:
                raise ValueError("numeric_range requires a minimum or maximum")
            if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
                raise ValueError("minimum must not exceed maximum")
        elif self.requirement_type is RequirementType.DURATION_COMPLETENESS:
            if self.minimum_duration_seconds is None:
                raise ValueError("duration_completeness requires minimum_duration_seconds")
        elif self.requirement_type is RequirementType.REQUIRED_EVIDENCE:
            if self.required_evidence_id is None:
                raise ValueError("required_evidence requires required_evidence_id")
        return self


class Protocol(BaseModel):
    """An ordered set of requirements for a single test protocol."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    requirements: list[Requirement] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_requirement_ids(self) -> "Protocol":
        ids = [requirement.id for requirement in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("requirement ids must be unique")
        return self
