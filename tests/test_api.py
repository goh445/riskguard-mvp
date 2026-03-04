"""Integration tests for FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers


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


def test_ops_summary_endpoint_shape() -> None:
    client = TestClient(app)
    response = client.get("/ops/summary")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"window_hours", "total_analyzed", "avg_score", "high_risk_count"}


def test_analyze_transaction_rejects_non_malaysia_timezone() -> None:
    client = TestClient(app)
    payload = {
        "user_id": "user_001",
        "amount": 100.0,
        "city": "Kuala Lumpur",
        "timestamp": "2026-03-01T12:34:56+00:00",
        "metadata": {},
    }

    response = client.post("/analyze-transaction", json=payload)
    assert response.status_code == 422


def test_ops_top_risk_pairs_endpoint_shape(monkeypatch) -> None:
    client = TestClient(app)

    class StubScanner:
        @staticmethod
        def top_risk_pairs(limit: int, force_refresh: bool) -> dict[str, object]:
            return {
                "scan_date": "2026-03-04",
                "pair_count": 2,
                "latest_update_utc": "2026-03-04T10:00:00+00:00",
                "rankings": [
                    {
                        "pair": "USD/MYR",
                        "score": 79,
                        "status": "High",
                        "flags": ["volatility_spike"],
                        "reasons": ["test reason"],
                        "hidden_links": ["MYR -> USD"],
                        "debug": {},
                        "updated_at": "2026-03-04T10:00:00+00:00",
                    },
                    {
                        "pair": "EUR/USD",
                        "score": 52,
                        "status": "Medium",
                        "flags": ["hub_exposure"],
                        "reasons": ["test reason"],
                        "hidden_links": [],
                        "debug": {},
                        "updated_at": "2026-03-04T10:00:00+00:00",
                    },
                ],
            }

    monkeypatch.setattr("main.forex_pair_scanner", StubScanner())

    response = client.get("/ops/top-risk-pairs?limit=2")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"scan_date", "pair_count", "latest_update_utc", "rankings"}
    assert isinstance(body["rankings"], list)
    assert body["pair_count"] == 2
