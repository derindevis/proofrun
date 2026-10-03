"""API contract tests for deterministic verification."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def numeric_requirement(requirement_id: str = "length") -> dict[str, object]:
    return {
        "id": requirement_id,
        "description": "Length must be within tolerance.",
        "requirement_type": "numeric_range",
        "minimum": 9.5,
        "maximum": 10.5,
    }


def payload(requirements: list[dict[str, object]], evidence: list[dict[str, object]]) -> dict[str, object]:
    return {"protocol": {"id": "protocol-1", "requirements": requirements}, "evidence": evidence}


def test_verify_api_returns_pass_and_is_deterministic() -> None:
    request_body = payload(
        [numeric_requirement()],
        [{"id": "measurement-1", "observations": [{"requirement_id": "length", "numeric_value": 10.0}]}],
    )

    first_response = client.post("/api/v1/verify", json=request_body)
    second_response = client.post("/api/v1/verify", json=request_body)

    assert first_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert first_response.json() == {
        "decision": "PASS",
        "requirement_results": [
            {
                "requirement_id": "length",
                "outcome": "PASS",
                "reason_code": "numeric_value_in_range",
                "message": "numeric value in range",
                "evidence_ids": ["measurement-1"],
            }
        ],
    }


def test_verify_api_blocks_when_required_evidence_is_missing() -> None:
    response = client.post(
        "/api/v1/verify",
        json=payload(
            [
                {
                    "id": "photo-required",
                    "description": "A final photograph is required.",
                    "requirement_type": "required_evidence",
                    "required_evidence_id": "final-photo",
                }
            ],
            [],
        ),
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "BLOCKED"
    assert response.json()["requirement_results"][0]["reason_code"] == "required_evidence_missing"


def test_verify_api_returns_insufficient_for_ambiguous_evidence() -> None:
    response = client.post(
        "/api/v1/verify",
        json=payload(
            [numeric_requirement()],
            [
                {
                    "id": "measurement-1",
                    "observations": [
                        {"requirement_id": "length", "numeric_value": 9.8},
                        {"requirement_id": "length", "numeric_value": 10.2},
                    ],
                }
            ],
        ),
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "INSUFFICIENT"
    assert response.json()["requirement_results"][0]["reason_code"] == "numeric_values_ambiguous"


def test_verify_api_returns_non_pass_for_out_of_range_evidence() -> None:
    response = client.post(
        "/api/v1/verify",
        json=payload(
            [numeric_requirement()],
            [{"id": "measurement-1", "observations": [{"requirement_id": "length", "numeric_value": 11.0}]}],
        ),
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "INSUFFICIENT"
    assert response.json()["requirement_results"][0]["outcome"] == "FAILED"


def test_verify_api_aggregates_mixed_requirements() -> None:
    response = client.post(
        "/api/v1/verify",
        json=payload(
            [numeric_requirement("length"), numeric_requirement("width")],
            [
                {
                    "id": "measurement-1",
                    "observations": [
                        {"requirement_id": "length", "numeric_value": 10.0},
                        {"requirement_id": "width", "numeric_value": 11.0},
                    ],
                }
            ],
        ),
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "INSUFFICIENT"
    assert [item["outcome"] for item in response.json()["requirement_results"]] == ["PASS", "FAILED"]


def test_verify_api_rejects_malformed_request() -> None:
    response = client.post("/api/v1/verify", json={"protocol": {"id": "protocol-1"}, "evidence": []})

    assert response.status_code == 422
