"""Tests for deterministic canonical protocol validation and normalization."""

from pathlib import Path

import pytest

from app.evidence.ingestion import ingest_evidence_file
from app.protocols.models import RequirementType
from app.protocols.validation import ProtocolValidationError, normalize_protocol_data, normalize_protocol_file
from app.verification.models import VerificationDecision
from app.verification.service import verify

FIXTURE_DIR = Path(__file__).parent / "fixtures"
PROTOCOL_DIR = FIXTURE_DIR / "protocols"
EVIDENCE_DIR = FIXTURE_DIR / "evidence"


def test_normalizes_valid_protocol_deterministically() -> None:
    first = normalize_protocol_file(PROTOCOL_DIR / "valid.json")
    second = normalize_protocol_file(PROTOCOL_DIR / "valid.json")

    assert first.model_dump() == second.model_dump()
    assert first.id == "length-check"
    assert first.requirements[0].mandatory is True


def test_normalizes_all_supported_requirement_types() -> None:
    protocol = normalize_protocol_file(PROTOCOL_DIR / "multiple_types.json")

    assert [requirement.requirement_type for requirement in protocol.requirements] == [
        RequirementType.NUMERIC_RANGE,
        RequirementType.DURATION_COMPLETENESS,
        RequirementType.REQUIRED_EVIDENCE,
    ]
    assert protocol.requirements[2].mandatory is False


def test_rejects_invalid_protocol_fixture() -> None:
    with pytest.raises(ProtocolValidationError, match="canonical schema"):
        normalize_protocol_file(PROTOCOL_DIR / "invalid.json")


def test_rejects_unsupported_requirement_types() -> None:
    with pytest.raises(ProtocolValidationError, match="canonical schema"):
        normalize_protocol_data(
            {
                "id": "protocol-1",
                "requirements": [
                    {
                        "id": "unknown",
                        "description": "Unsupported rule.",
                        "requirement_type": "text_match",
                    }
                ],
            }
        )


def test_rejects_missing_type_specific_fields() -> None:
    with pytest.raises(ProtocolValidationError, match="canonical schema"):
        normalize_protocol_data(
            {
                "id": "protocol-1",
                "requirements": [
                    {
                        "id": "length",
                        "description": "Range with no bounds.",
                        "requirement_type": "numeric_range",
                    }
                ],
            }
        )


def test_normalized_protocol_and_evidence_integrate_with_verifier() -> None:
    protocol = normalize_protocol_file(PROTOCOL_DIR / "valid.json")
    evidence = ingest_evidence_file(EVIDENCE_DIR / "valid.json")

    result = verify(protocol, [evidence])

    assert result.decision is VerificationDecision.PASS
    assert result.requirement_results[0].requirement_id == "length"
