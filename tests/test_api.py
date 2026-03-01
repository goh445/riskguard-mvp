"""Integration tests for FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_transaction_response_schema() -> None:
    client = TestClient(app)
    payload = {
        "user_id": "user_001",
        "amount": 100.0,
        "city": "Kuala Lumpur",
        "timestamp": "2026-03-01T12:34:56+08:00",
        "metadata": {"channel": "mobile"},
    }

    response = client.post("/analyze-transaction", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"score", "status", "flags", "reasons", "debug"}
    assert isinstance(body["score"], int)
    assert body["status"] in {"Low", "Medium", "High"}
    assert isinstance(body["flags"], list)
    assert isinstance(body["reasons"], list)
    assert isinstance(body["debug"], dict)
