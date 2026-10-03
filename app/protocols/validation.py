"""Deterministic validation and normalization for canonical test protocols."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

from pydantic import ValidationError

from app.protocols.models import Protocol


class ProtocolValidationError(ValueError):
    """Raised when protocol input cannot conform to the canonical contract."""


def normalize_protocol_data(data: Mapping[str, Any]) -> Protocol:
    """Validate JSON-compatible protocol data into the canonical Protocol model."""
    if not isinstance(data, Mapping):
        raise ProtocolValidationError("protocol data must be a JSON object")
    try:
        return Protocol.model_validate(data)
    except ValidationError as exc:
        raise ProtocolValidationError("protocol data does not match the canonical schema") from exc


def normalize_protocol_file(path: str | Path) -> Protocol:
    """Read and validate one local JSON protocol file."""
    file_path = Path(path)
    try:
        with file_path.open(encoding="utf-8") as protocol_file:
            data = json.load(protocol_file, parse_constant=_reject_nonstandard_json_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProtocolValidationError("invalid JSON protocol file") from exc

    return normalize_protocol_data(data)


def _reject_nonstandard_json_constant(value: str) -> NoReturn:
    raise ValueError(f"invalid JSON constant: {value}")
