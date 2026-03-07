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


def test_news_sources_crud_endpoints(monkeypatch) -> None:
    client = TestClient(app)

    class StubAuditStore:
        sources = [{"url": "https://feeds.example.com/a", "enabled": True, "created_at": "x", "updated_at": "x"}]

        @classmethod
        def list_news_sources(cls, enabled_only: bool = False):
            if enabled_only:
                return [row for row in cls.sources if row["enabled"]]
            return list(cls.sources)

        @classmethod
        def upsert_news_source(cls, url: str, enabled: bool):
            cls.sources = [row for row in cls.sources if row["url"] != url]
            cls.sources.append({"url": url, "enabled": enabled, "created_at": "x", "updated_at": "x"})

        @classmethod
        def delete_news_source(cls, url: str):
            before = len(cls.sources)
            cls.sources = [row for row in cls.sources if row["url"] != url]
            return before - len(cls.sources)

    class StubNewsIntelligence:
        active = ["https://feeds.example.com/a"]

        @classmethod
        def get_feed_sources(cls):
            return list(cls.active)

        @classmethod
        def set_feed_sources(cls, sources):
            cls.active = list(sources)

    monkeypatch.setattr("main.audit_store", StubAuditStore)
    monkeypatch.setattr("main.news_intelligence", StubNewsIntelligence)

    listed = client.get("/ops/news-sources")
    assert listed.status_code == 200
    assert "sources" in listed.json()

    upserted = client.post("/ops/news-sources", json={"url": "https://feeds.example.com/b", "enabled": True})
    assert upserted.status_code == 200
    assert upserted.json()["updated"] is True

    deleted = client.request("DELETE", "/ops/news-sources", params={"url": "https://feeds.example.com/b"})
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] in {0, 1}


def test_cooperative_risk_endpoints(monkeypatch) -> None:
    client = TestClient(app)

    class StubAuditStore:
        @staticmethod
        def insert_cooperative_signal(**kwargs):
            return 101

        @staticmethod
        def cooperative_summary_last_30d():
            return {
                "window_days": 30,
                "total_shared_signals": 5,
                "avg_shared_score": 67.2,
                "high_risk_shared_count": 2,
                "top_pairs": [{"pair": "USD/MYR", "signal_count": 2, "avg_score": 70.0}],
                "category_distribution": [{"category": "FOREX", "count": 4}],
            }

    monkeypatch.setattr("main.audit_store", StubAuditStore)

    share_resp = client.post(
        "/ops/cooperative-risk/share",
        json={
            "pair": "USD/MYR",
            "category": "FOREX",
            "score": 71,
            "status": "HIGH",
            "flags": ["volatility_spike"],
        },
    )
    assert share_resp.status_code == 200
    assert share_resp.json()["shared"] is True

    summary_resp = client.get("/ops/cooperative-risk/summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["window_days"] == 30


def test_subscription_endpoints(monkeypatch) -> None:
    client = TestClient(app)

    class StubAuditStore:
        @staticmethod
        def create_webhook_subscription(**kwargs):
            return 7

        @staticmethod
        def list_webhook_subscriptions(enabled_only: bool = False):
            return [
                {
                    "id": 7,
                    "url": "https://example.com/webhook",
                    "events": ["risk.forex.analyzed"],
                    "secret": None,
                    "enabled": True,
                    "description": "stub",
                    "created_at": "x",
                    "updated_at": "x",
                }
            ]

        @staticmethod
        def delete_webhook_subscription(subscription_id: int):
            return 1 if subscription_id == 7 else 0

        @staticmethod
        def log_webhook_delivery(**kwargs):
            return 1

    monkeypatch.setattr("main.audit_store", StubAuditStore)

    created = client.post(
        "/api/v1/subscriptions",
        json={
            "url": "https://example.com/webhook",
            "events": ["risk.forex.analyzed"],
            "enabled": True,
        },
    )
    assert created.status_code == 200
    assert created.json()["saved"] is True

    listed = client.get("/api/v1/subscriptions")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    deleted = client.request("DELETE", "/api/v1/subscriptions/7")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
