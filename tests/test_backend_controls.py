"""Tests for backend production controls: auth and rate limit."""

from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

import config
import main


def _reload_app() -> TestClient:
    importlib.reload(config)
    refreshed_main = importlib.reload(main)
    return TestClient(refreshed_main.app)


def _payload() -> dict[str, object]:
    return {
        "user_id": "user_auth",
        "amount": 100.0,
        "city": "Kuala Lumpur",
        "timestamp": "2026-03-01T12:34:56+08:00",
        "metadata": {},
    }


def test_api_key_required_when_configured(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RISKGUARD_API_KEY", "secret-key")
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit_auth.db"))
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "100")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    client = _reload_app()

    unauthorized = client.post("/analyze-transaction", json=_payload())
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/analyze-transaction",
        json=_payload(),
        headers={"X-API-Key": "secret-key"},
    )
    assert authorized.status_code == 200


def test_rate_limit_enforced(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RISKGUARD_API_KEY", raising=False)
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit_rate.db"))
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    client = _reload_app()
    first = client.post("/analyze-transaction", json=_payload())
    second = client.post("/analyze-transaction", json=_payload())
    third = client.post("/analyze-transaction", json=_payload())

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
