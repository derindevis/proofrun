"""Unit tests for the isolated Nebius provider; no network calls are made."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.providers.nebius import NebiusConfigurationError, NebiusProvider, NebiusProviderError


def configured_settings(**overrides: str | None) -> Settings:
    values: dict[str, str | None] = {
        "nebius_api_key": "unit-test-key",
        "nebius_base_url": "https://api.tokenfactory.us-central1.nebius.com/v1/",
        "nebius_model": "nvidia/nvidia-nemotron-3-nano-30b-a3b",
    }
    values.update(overrides)
    return Settings(**values)


def test_provider_rejects_missing_configuration_before_client_creation() -> None:
    factory = Mock()
    provider = NebiusProvider(configured_settings(nebius_api_key=None), client_factory=factory)

    with pytest.raises(NebiusConfigurationError, match="configuration is incomplete"):
        provider.generate_text("test")

    factory.assert_not_called()


def test_provider_generates_text_with_a_mocked_client() -> None:
    completions = Mock()
    completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ProofRun smoke test."))],
        usage=SimpleNamespace(prompt_tokens=4, completion_tokens=5, total_tokens=9),
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    factory = Mock(return_value=client)
    provider = NebiusProvider(configured_settings(), client_factory=factory)

    result = provider.generate_text("Reply with exactly: ProofRun smoke test.")

    assert result.text == "ProofRun smoke test."
    assert result.usage and result.usage.total_tokens == 9
    factory.assert_called_once()
    completions.create.assert_called_once_with(
        model="nvidia/nvidia-nemotron-3-nano-30b-a3b",
        messages=[{"role": "user", "content": "Reply with exactly: ProofRun smoke test."}],
    )


def test_provider_wraps_api_failures_without_exposing_details() -> None:
    completions = Mock()
    completions.create.side_effect = RuntimeError("provider failure detail")
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = NebiusProvider(configured_settings(), client_factory=Mock(return_value=client))

    with pytest.raises(NebiusProviderError, match="Nebius generation failed") as error:
        provider.generate_text("test")

    assert "provider failure detail" not in str(error.value)


class FakeProviderApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int | None = None,
        code: str | None = None,
        error_type: str | None = None,
        message: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.type = error_type
        self.message = message
        self.request_id = request_id


def provider_with_failure(error: Exception) -> NebiusProvider:
    completions = Mock()
    completions.create.side_effect = error
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return NebiusProvider(configured_settings(), client_factory=Mock(return_value=client))


def test_provider_preserves_safe_http_error_metadata() -> None:
    provider = provider_with_failure(
        FakeProviderApiError(
            status_code=429,
            code="rate_limit_exceeded",
            message="Request limit reached",
            request_id="req_safe_123",
        )
    )

    with pytest.raises(NebiusProviderError) as captured:
        provider.generate_text("test")

    error = captured.value
    assert error.category == "rate_limit_or_credits"
    assert error.status_code == 429
    assert error.provider_code == "rate_limit_exceeded"
    assert error.request_id == "req_safe_123"
    assert str(error) == "Request limit reached"


def test_provider_classifies_and_redacts_authentication_failures() -> None:
    provider = provider_with_failure(
        FakeProviderApiError(
            status_code=401,
            error_type="authentication_error",
            message="Authorization: Bearer sk-sensitive-test-value",
        )
    )

    with pytest.raises(NebiusProviderError) as captured:
        provider.generate_text("test")

    error = captured.value
    assert error.category == "authentication"
    assert error.status_code == 401
    assert error.provider_code == "authentication_error"
    assert "sk-sensitive-test-value" not in str(error)
    assert "[REDACTED]" in str(error)


def test_provider_uses_generic_diagnostics_for_unstructured_exceptions() -> None:
    provider = provider_with_failure(RuntimeError("unstructured provider failure"))

    with pytest.raises(NebiusProviderError) as captured:
        provider.generate_text("test")

    error = captured.value
    assert error.category == "provider_error"
    assert error.exception_type == "RuntimeError"
    assert error.status_code is None
    assert str(error) == "Nebius generation failed"
