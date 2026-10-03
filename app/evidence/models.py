"""Structured observation and evidence models for verification input."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class Observation(BaseModel):
    """A measurement or completion assertion associated with one requirement."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    requirement_id: str = Field(min_length=1)
    numeric_value: float | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    complete: bool | None = None
    raw_value: JsonValue | None = None


class Evidence(BaseModel):
    """A uniquely identified piece of structured test evidence."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    source_id: str | None = Field(default=None, min_length=1)
    observations: list[Observation] = Field(default_factory=list)
