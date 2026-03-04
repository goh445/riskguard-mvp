"""Tests for forex network risk analysis endpoint."""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

import config
import main


def _reload_client(monkeypatch) -> TestClient:
    monkeypatch.delenv("RISKGUARD_API_KEY", raising=False)
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1000")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    importlib.reload(config)
    refreshed_main = importlib.reload(main)
    return TestClient(refreshed_main.app)


def test_analyze_forex_risk_returns_hidden_links(monkeypatch) -> None:
    client = _reload_client(monkeypatch)
    payload = {
        "base_currency": "MYR",
        "quote_currency": "EUR",
        "observed_volatility": 0.012,
        "spread_bps": 14,
        "timestamp": "2026-03-01T12:34:56+08:00",
        "metadata": {"news_sentiment": -0.1, "macro_stress": 0.4},
    }

    response = client.post("/analyze-forex-risk", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) == {"score", "status", "flags", "reasons", "hidden_links", "debug"}
    assert isinstance(body["hidden_links"], list)
    assert body["status"] in {"Low", "Medium", "High"}


def test_analyze_forex_risk_high_stress_case(monkeypatch) -> None:
    client = _reload_client(monkeypatch)
    payload = {
        "base_currency": "USD",
        "quote_currency": "JPY",
        "observed_volatility": 0.03,
        "spread_bps": 30,
        "timestamp": "2026-03-01T12:34:56+08:00",
        "metadata": {"news_sentiment": -0.8, "macro_stress": 0.9},
    }

    response = client.post("/analyze-forex-risk", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["score"] >= 70
    assert body["status"] == "High"


def test_analyze_forex_risk_requires_timezone(monkeypatch) -> None:
    client = _reload_client(monkeypatch)
    payload = {
        "base_currency": "USD",
        "quote_currency": "EUR",
        "observed_volatility": 0.01,
        "spread_bps": 10,
        "timestamp": "2026-03-01T12:34:56",
        "metadata": {},
    }

    response = client.post("/analyze-forex-risk", json=payload)
    assert response.status_code == 422


def test_analyze_forex_risk_auto_market_enrichment(monkeypatch) -> None:
    client = _reload_client(monkeypatch)

    class StubMarketData:
        @staticmethod
        def fetch_snapshot(base: str, quote: str) -> dict[str, object]:
            return {
                "observed_volatility": 0.02,
                "spread_bps": 25.0,
                "sample_size": 30,
                "last_rate": 4.47,
                "source": "stub",
            }

    monkeypatch.setattr(main, "forex_market_data", StubMarketData())

    payload = {
        "base_currency": "USD",
        "quote_currency": "MYR",
        "timestamp": "2026-03-01T12:34:56+08:00",
        "metadata": {"news_sentiment": -0.3, "macro_stress": 0.7},
    }

    response = client.post("/analyze-forex-risk", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["debug"]["observed_volatility"] == 0.02
    assert body["debug"]["spread_bps"] == 25.0

