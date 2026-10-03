"""Pure deterministic verification of structured protocols and evidence."""

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from app.evidence.models import Evidence, Observation
from app.protocols.models import Protocol, Requirement, RequirementType
from app.verification.models import (
    RequirementOutcome,
    RequirementVerification,
    VerificationDecision,
    VerificationResult,
)


def verify(protocol: Protocol, evidence: Sequence[Evidence]) -> VerificationResult:
    """Verify typed inputs without I/O, network calls, or non-deterministic behavior."""
    evidence_items = list(evidence)
    duplicate_evidence_ids = _duplicates(item.id for item in evidence_items)
    if duplicate_evidence_ids:
        return _blocked_input("duplicate_evidence_ids")

    results = [_verify_requirement(requirement, evidence_items) for requirement in protocol.requirements]
    return VerificationResult(
        decision=_aggregate(protocol, results),
        requirement_results=results,
    )


def verify_payload(protocol_data: Mapping[str, Any], evidence_data: Sequence[Mapping[str, Any]]) -> VerificationResult:
    """Validate raw structured input, returning BLOCKED instead of raising on malformed input."""
    try:
        protocol = Protocol.model_validate(protocol_data)
        evidence = [Evidence.model_validate(item) for item in evidence_data]
    except (ValidationError, TypeError):
        return _blocked_input("malformed_input")
    return verify(protocol, evidence)


def _verify_requirement(requirement: Requirement, evidence: Sequence[Evidence]) -> RequirementVerification:
    if requirement.requirement_type is RequirementType.REQUIRED_EVIDENCE:
        if any(item.id == requirement.required_evidence_id for item in evidence):
            return _result(
                requirement.id,
                RequirementOutcome.PASS,
                "evidence_present",
                [requirement.required_evidence_id],
            )
        return _result(requirement.id, RequirementOutcome.BLOCKED, "required_evidence_missing")

    matches = [
        (item.id, observation)
        for item in evidence
        for observation in item.observations
        if observation.requirement_id == requirement.id
    ]
    # A mandatory measurement/completion observation is required to safely evaluate its rule.
    if not matches:
        return _result(requirement.id, RequirementOutcome.BLOCKED, "required_observation_missing")

    evidence_ids = _unique_evidence_ids(matches)
    observations = [observation for _, observation in matches]
    if requirement.requirement_type is RequirementType.NUMERIC_RANGE:
        return _verify_numeric(requirement, observations, evidence_ids)
    return _verify_duration(requirement, observations, evidence_ids)


def _verify_numeric(
    requirement: Requirement,
    observations: Sequence[Observation],
    evidence_ids: list[str],
) -> RequirementVerification:
    values = {observation.numeric_value for observation in observations}
    if None in values:
        return _result(requirement.id, RequirementOutcome.INSUFFICIENT, "numeric_value_missing", evidence_ids)
    if len(values) != 1:
        return _result(requirement.id, RequirementOutcome.INSUFFICIENT, "numeric_values_ambiguous", evidence_ids)

    value = values.pop()
    assert value is not None
    if (requirement.minimum is not None and value < requirement.minimum) or (
        requirement.maximum is not None and value > requirement.maximum
    ):
        return _result(requirement.id, RequirementOutcome.FAILED, "numeric_value_out_of_range", evidence_ids)
    return _result(requirement.id, RequirementOutcome.PASS, "numeric_value_in_range", evidence_ids)


def _verify_duration(
    requirement: Requirement,
    observations: Sequence[Observation],
    evidence_ids: list[str],
) -> RequirementVerification:
    values = {(observation.duration_seconds, observation.complete) for observation in observations}
    if len(values) != 1:
        return _result(requirement.id, RequirementOutcome.INSUFFICIENT, "duration_observations_ambiguous", evidence_ids)

    duration, complete = values.pop()
    if duration is None or complete is None:
        return _result(requirement.id, RequirementOutcome.INSUFFICIENT, "duration_or_completeness_missing", evidence_ids)
    if not complete:
        return _result(requirement.id, RequirementOutcome.INSUFFICIENT, "activity_incomplete", evidence_ids)
    assert requirement.minimum_duration_seconds is not None
    if duration < requirement.minimum_duration_seconds:
        return _result(requirement.id, RequirementOutcome.FAILED, "duration_too_short", evidence_ids)
    return _result(requirement.id, RequirementOutcome.PASS, "duration_and_completeness_satisfied", evidence_ids)


def _aggregate(protocol: Protocol, results: Sequence[RequirementVerification]) -> VerificationDecision:
    mandatory_results = [
        result for requirement, result in zip(protocol.requirements, results, strict=True) if requirement.mandatory
    ]
    if any(result.outcome is RequirementOutcome.BLOCKED for result in mandatory_results):
        return VerificationDecision.BLOCKED
    if any(result.outcome is not RequirementOutcome.PASS for result in mandatory_results):
        return VerificationDecision.INSUFFICIENT
    return VerificationDecision.PASS


def _blocked_input(reason_code: str) -> VerificationResult:
    return VerificationResult(
        decision=VerificationDecision.BLOCKED,
        requirement_results=[
            RequirementVerification(
                requirement_id="__input__",
                outcome=RequirementOutcome.BLOCKED,
                reason_code=reason_code,
                message=reason_code.replace("_", " "),
            )
        ],
    )


def _result(
    requirement_id: str,
    outcome: RequirementOutcome,
    reason_code: str,
    evidence_ids: list[str] | None = None,
) -> RequirementVerification:
    return RequirementVerification(
        requirement_id=requirement_id,
        outcome=outcome,
        reason_code=reason_code,
        message=reason_code.replace("_", " "),
        evidence_ids=evidence_ids or [],
    )


def _duplicates(values: Sequence[str] | Any) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _unique_evidence_ids(matches: Sequence[tuple[str, Observation]]) -> list[str]:
    return list(dict.fromkeys(evidence_id for evidence_id, _ in matches))
