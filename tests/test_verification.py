"""Unit tests for deterministic protocol verification."""

from app.evidence.models import Evidence, Observation
from app.protocols.models import Protocol, Requirement, RequirementType
from app.verification.models import RequirementOutcome, VerificationDecision
from app.verification.service import verify, verify_payload


def numeric_requirement(requirement_id: str = "length") -> Requirement:
    return Requirement(
        id=requirement_id,
        description="Length must be within tolerance.",
        requirement_type=RequirementType.NUMERIC_RANGE,
        minimum=9.5,
        maximum=10.5,
    )


def test_fully_valid_evidence_passes() -> None:
    protocol = Protocol(
        id="protocol-1",
        requirements=[
            numeric_requirement(),
            Requirement(
                id="run-time",
                description="Run must complete for at least one minute.",
                requirement_type=RequirementType.DURATION_COMPLETENESS,
                minimum_duration_seconds=60,
            ),
            Requirement(
                id="photo-required",
                description="A final photograph is required.",
                requirement_type=RequirementType.REQUIRED_EVIDENCE,
                required_evidence_id="final-photo",
            ),
        ],
    )
    evidence = [
        Evidence(id="measurements", observations=[Observation(requirement_id="length", numeric_value=10.0)]),
        Evidence(
            id="test-run",
            observations=[Observation(requirement_id="run-time", duration_seconds=65, complete=True)],
        ),
        Evidence(id="final-photo"),
    ]

    result = verify(protocol, evidence)

    assert result.decision is VerificationDecision.PASS
    assert [item.outcome for item in result.requirement_results] == [RequirementOutcome.PASS] * 3


def test_missing_required_evidence_blocks_verification() -> None:
    protocol = Protocol(
        id="protocol-1",
        requirements=[
            Requirement(
                id="photo-required",
                description="A final photograph is required.",
                requirement_type=RequirementType.REQUIRED_EVIDENCE,
                required_evidence_id="final-photo",
            )
        ],
    )

    result = verify(protocol, [Evidence(id="other-evidence")])

    assert result.decision is VerificationDecision.BLOCKED
    assert result.requirement_results[0].reason_code == "required_evidence_missing"


def test_incomplete_duration_evidence_is_insufficient() -> None:
    protocol = Protocol(
        id="protocol-1",
        requirements=[
            Requirement(
                id="run-time",
                description="Run must complete for at least one minute.",
                requirement_type=RequirementType.DURATION_COMPLETENESS,
                minimum_duration_seconds=60,
            )
        ],
    )
    evidence = [
        Evidence(
            id="test-run",
            observations=[Observation(requirement_id="run-time", duration_seconds=65, complete=False)],
        )
    ]

    result = verify(protocol, evidence)

    assert result.decision is VerificationDecision.INSUFFICIENT
    assert result.requirement_results[0].reason_code == "activity_incomplete"


def test_out_of_range_value_is_not_pass() -> None:
    protocol = Protocol(id="protocol-1", requirements=[numeric_requirement()])
    evidence = [Evidence(id="measurements", observations=[Observation(requirement_id="length", numeric_value=11.0)])]

    result = verify(protocol, evidence)

    assert result.decision is VerificationDecision.INSUFFICIENT
    assert result.requirement_results[0].outcome is RequirementOutcome.FAILED


def test_mixed_mandatory_outcomes_aggregate_to_insufficient() -> None:
    protocol = Protocol(id="protocol-1", requirements=[numeric_requirement("length"), numeric_requirement("width")])
    evidence = [
        Evidence(
            id="measurements",
            observations=[
                Observation(requirement_id="length", numeric_value=10.0),
                Observation(requirement_id="width", numeric_value=11.0),
            ],
        )
    ]

    result = verify(protocol, evidence)

    assert result.decision is VerificationDecision.INSUFFICIENT
    assert [item.outcome for item in result.requirement_results] == [
        RequirementOutcome.PASS,
        RequirementOutcome.FAILED,
    ]


def test_malformed_input_is_blocked() -> None:
    result = verify_payload(
        {"id": "protocol-1", "requirements": "not-a-list"},
        [],
    )

    assert result.decision is VerificationDecision.BLOCKED
    assert result.requirement_results[0].reason_code == "malformed_input"
