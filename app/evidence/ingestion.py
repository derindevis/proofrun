"""Deterministic parsing and normalization of local JSON evidence files."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

from pydantic import ValidationError

from app.evidence.models import Evidence


class EvidenceIngestionError(ValueError):
    """Raised when JSON evidence cannot be safely normalized."""


def ingest_evidence_data(data: Mapping[str, Any], *, source_id: str | None = None) -> Evidence:
    """Validate JSON-compatible data into the canonical evidence representation."""
    if not isinstance(data, Mapping):
        raise EvidenceIngestionError("evidence data must be a JSON object")

    try:
        evidence = Evidence.model_validate(data)
    except ValidationError as exc:
        raise EvidenceIngestionError("evidence data does not match the canonical schema") from exc

    resolved_source_id = evidence.source_id or source_id
    if not resolved_source_id:
        raise EvidenceIngestionError("evidence source_id is required")
    if evidence.source_id:
        return evidence
    return evidence.model_copy(update={"source_id": resolved_source_id})


def ingest_evidence_file(path: str | Path) -> Evidence:
    """Read one local JSON evidence file and normalize it into canonical evidence."""
    file_path = Path(path)
    try:
        with file_path.open(encoding="utf-8") as evidence_file:
            data = json.load(evidence_file, parse_constant=_reject_nonstandard_json_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EvidenceIngestionError("invalid JSON evidence file") from exc

    return ingest_evidence_data(data, source_id=str(file_path))


def _reject_nonstandard_json_constant(value: str) -> NoReturn:
    raise ValueError(f"invalid JSON constant: {value}")
