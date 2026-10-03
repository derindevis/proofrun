# ProofRun

ProofRun is an evidence-gated AI quality assurance application for testing physical prototypes. This repository currently contains only the backend foundation: configuration and health endpoints. No AI agent, database, frontend, or product workflows are implemented yet.

## Architecture

```
app/
  api/v1/endpoints/   # Versioned HTTP endpoints
  core/               # Configuration and shared cross-cutting concerns
  protocols/          # Future: protocol extraction
  evidence/           # Future: evidence ingestion
  verification/       # Future: deterministic verification
  orchestration/      # Future: agent orchestration
  reporting/          # Future: reporting
  evaluation/         # Future: evaluation
tests/                # Automated API tests
```

The future module directories are intentionally empty architectural boundaries; no workflows have been implemented in them.

## Configuration

Copy `.env.example` to `.env` and replace only the placeholders for integrations you enable. `.env` is ignored by Git, and no credentials are hardcoded.

Settings use the `PROOFRUN_` prefix. For example, `PROOFRUN_DEBUG=true` enables debug mode. Nebius Token Factory and LangSmith values are placeholders for future integration work and are not used by the initial foundation.

## Nebius provider smoke test

The isolated Nebius provider reads `PROOFRUN_NEBIUS_API_KEY`, `PROOFRUN_NEBIUS_BASE_URL`, and `PROOFRUN_NEBIUS_MODEL` through application settings. It is not connected to protocol extraction or verification.

After installation and configuration, make one real minimal request with:

```powershell
python -m scripts.nebius_smoke_test
```

The script reports only request status, model, returned text, token usage when supplied, and elapsed time.

## Setup

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` for the current terminal, then activate again.

### macOS, Linux, and general Python environments

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

## Run

From the repository root, with the virtual environment active:

```powershell
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/> for the root health endpoint, or <http://127.0.0.1:8000/api/v1/health> for the versioned API health endpoint. Interactive API documentation is available at <http://127.0.0.1:8000/docs>.

## Test

```powershell
python -m pytest
```

The tests use FastAPI's `TestClient` and cover both health endpoints.
