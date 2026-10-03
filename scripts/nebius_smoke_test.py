"""Execute exactly one minimal real Nebius request when configured."""

import json
import time
from dataclasses import asdict

from app.core.config import get_settings
from app.providers.nebius import NebiusProvider, NebiusProviderError


def main() -> int:
    settings = get_settings()
    started_at = time.perf_counter()
    model = settings.nebius_model or "not configured"
    if not settings.nebius_api_key or not settings.nebius_model:
        _report("failure", model, None, None, time.perf_counter() - started_at)
        return 1

    try:
        generation = NebiusProvider(settings).generate_text("Reply with exactly: ProofRun smoke test.")
    except NebiusProviderError as error:
        _report_failure(model, error, time.perf_counter() - started_at)
        return 1

    usage = asdict(generation.usage) if generation.usage else None
    _report("success", generation.model, generation.text, usage, time.perf_counter() - started_at)
    return 0


def _report(status: str, model: str, text: str | None, usage: dict[str, int | None] | None, elapsed: float) -> None:
    print(f"status: {status}")
    print(f"model: {model}")
    print(f"text: {text if text is not None else 'unavailable'}")
    print(f"token_usage: {json.dumps(usage) if usage is not None else 'unavailable'}")
    print(f"elapsed_seconds: {elapsed:.3f}")


def _report_failure(model: str, error: NebiusProviderError, elapsed: float) -> None:
    print("status: failure")
    print(f"model: {model}")
    print(f"category: {error.category}")
    if error.status_code is not None:
        print(f"status_code: {error.status_code}")
    if error.provider_code:
        print(f"provider_code: {error.provider_code}")
    print(f"message: {error}")
    if error.request_id:
        print(f"request_id: {error.request_id}")
    print(f"elapsed_seconds: {elapsed:.3f}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
