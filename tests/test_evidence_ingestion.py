"""Tests for deterministic local JSON evidence ingestion."""

from pathlib import Path

import pytest

from app.evidence.ingestion import EvidenceIngestionError, ingest_evidence_data, ingest_evidence_file
from app.protocols.models import Protocol, Requirement, RequirementType
from app.verification.models import VerificationDecision
from app.verification.service import verify

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "evidence"


def test_ingests_and_normalizes_valid_evidence_deterministically() -> None:
    first = ingest_evidence_file(FIXTURE_DIR / "valid.json")
    second = ingest_evidence_file(FIXTURE_DIR / "valid.json")

    assert first.model_dump() == second.model_dump()
    assert first.id == "measurement-001"
    assert first.source_id == "fixture://valid.json"
    assert first.observations[0].requirement_id == "length"
    assert first.observations[0].raw_value == "10.0 mm"


def test_ingestion_preserves_incomplete_evidence() -> None:
    evidence = ingest_evidence_file(FIXTURE_DIR / "incomplete.json")

    assert evidence.source_id == "fixture://incomplete.json"
    assert evidence.observations[0].complete is False
    assert evidence.observations[0].raw_value == "test stopped before completion"


def test_ingestion_rejects_malformed_evidence() -> None:
    with pytest.raises(EvidenceIngestionError, match="canonical schema"):
        ingest_evidence_file(FIXTURE_DIR / "malformed.json")


def test_ingestion_requires_a_traceable_source() -> None:
    with pytest.raises(EvidenceIngestionError, match="source_id"):
        ingest_evidence_data({"id": "measurement-001", "observations": []})


def test_normalized_json_evidence_integrates_with_verifier() -> None:
    evidence = ingest_evidence_file(FIXTURE_DIR / "valid.json")
    protocol = Protocol(
        id="protocol-1",
        requirements=[
            Requirement(
                id="length",
                description="Length must be within tolerance.",
                requirement_type=RequirementType.NUMERIC_RANGE,
                minimum=9.5,
                maximum=10.5,
            )
        ],
    )

    result = verify(protocol, [evidence])

    assert result.decision is VerificationDecision.PASS
    assert result.requirement_results[0].evidence_ids == ["measurement-001"]
