"""Minimal OpenAI-compatible client for Nebius Token Factory."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
import re

from openai import OpenAI

from app.core.config import Settings, get_settings


class NebiusProviderError(RuntimeError):
    """Raised when Nebius client creation or generation fails."""

    def __init__(
        self,
        message: str = "Nebius provider failure",
        *,
        category: str = "provider_error",
        exception_type: str | None = None,
        status_code: int | None = None,
        provider_code: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.exception_type = exception_type
        self.status_code = status_code
        self.provider_code = provider_code
        self.request_id = request_id


class NebiusConfigurationError(NebiusProviderError):
    """Raised when required Nebius settings are missing or unusable."""

    def __init__(self, message: str = "Nebius provider configuration is incomplete") -> None:
        super().__init__(message, category="configuration", exception_type=self.__class__.__name__)


@dataclass(frozen=True)
class NebiusTokenUsage:
    """Token usage returned by Nebius when supplied by the compatible API."""

    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class NebiusGeneration:
    """Minimal text-generation output with optional token accounting."""

    model: str
    text: str
    usage: NebiusTokenUsage | None


class NebiusProvider:
    """Lazy, configuration-backed Nebius client with no application business logic."""

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[..., OpenAI] = OpenAI,
    ) -> None:
        self._settings = settings or get_settings()
        self._client_factory = client_factory
        self._client: OpenAI | None = None

    def generate_text(self, prompt: str) -> NebiusGeneration:
        """Make one non-streaming text-generation request through Nebius."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise NebiusProviderError("prompt must be a non-empty string")

        try:
            response = self._get_client().chat.completions.create(
                model=self._settings.nebius_model,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.choices[0].message.content
            if not text:
                raise ValueError("generation returned no text")
            return NebiusGeneration(
                model=self._settings.nebius_model,
                text=text,
                usage=_usage_from_response(response),
            )
        except NebiusProviderError:
            raise
        except Exception as error:
            raise _provider_failure(error, "Nebius generation failed") from None

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        api_key = self._settings.nebius_api_key
        base_url = self._settings.nebius_base_url
        model = self._settings.nebius_model
        if not api_key or not api_key.strip() or not base_url or not base_url.strip() or not model or not model.strip():
            raise NebiusConfigurationError("Nebius provider configuration is incomplete")
        try:
            self._client = self._client_factory(
                api_key=api_key,
                base_url=base_url,
                max_retries=0,
            )
        except Exception as error:
            raise _provider_failure(error, "Nebius client initialization failed") from None
        return self._client


def _usage_from_response(response: Any) -> NebiusTokenUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return NebiusTokenUsage(
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )


def _provider_failure(error: Exception, fallback_message: str) -> NebiusProviderError:
    """Extract only safe, scalar diagnostics from a provider exception."""
    status_code = _status_code(error)
    body = getattr(error, "body", None)
    nested_details = body.get("error", body) if isinstance(body, dict) else {}
    details = nested_details if isinstance(nested_details, dict) else {}
    provider_code = _safe_scalar(getattr(error, "code", None)) or _safe_scalar(details.get("code"))
    provider_code = provider_code or _safe_scalar(getattr(error, "type", None)) or _safe_scalar(details.get("type"))
    message = _safe_message(getattr(error, "message", None)) or _safe_message(details.get("message"))
    return NebiusProviderError(
        message or fallback_message,
        category=_category_for(error, status_code),
        exception_type=error.__class__.__name__,
        status_code=status_code,
        provider_code=provider_code,
        request_id=_safe_scalar(getattr(error, "request_id", None)),
    )


def _status_code(error: Exception) -> int | None:
    value = getattr(error, "status_code", None)
    return value if isinstance(value, int) and 100 <= value <= 599 else None


def _category_for(error: Exception, status_code: int | None) -> str:
    exception_type = error.__class__.__name__.lower()
    if status_code == 401 or "authentication" in exception_type:
        return "authentication"
    if status_code == 403 or "permission" in exception_type:
        return "permission"
    if status_code in {400, 422} or "badrequest" in exception_type:
        return "request_format"
    if status_code == 404:
        return "endpoint_or_model"
    if status_code in {408, 504} or "timeout" in exception_type:
        return "timeout"
    if "connection" in exception_type:
        return "network"
    if status_code == 429 or "ratelimit" in exception_type:
        return "rate_limit_or_credits"
    return "api_error" if status_code is not None else "provider_error"


def _safe_scalar(value: Any) -> str | None:
    if not isinstance(value, (str, int)):
        return None
    text = str(value).strip()
    return text if text and len(text) <= 200 else None


def _safe_message(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > 300:
        return None
    text = re.sub(r"(?i)\b(authorization|api[_ -]?key|token|cookie|set-cookie)\s*[:=]\s*[^\s,;]+", r"\1: [REDACTED]", text)
    text = re.sub(r"(?i)\bbearer\s+[^\s,;]+", "Bearer [REDACTED]", text)
    text = re.sub(r"\b(?:sk|nvapi|nvidia)[-_][A-Za-z0-9_-]{8,}\b", "[REDACTED]", text)
    return text
