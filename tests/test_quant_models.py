"""Tests for ES/EWMA quantitative risk enhancements."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from forex_market_data import ForexMarketDataClient
from models import TransactionRequest
from risk_engine import RiskEngine


def test_market_snapshot_contains_ewma_and_es() -> None:
    client = ForexMarketDataClient()
    series = [100.0, 99.5, 100.2, 98.9, 99.8, 98.4, 97.9, 98.6, 97.3, 96.8]

    snapshot = client._snapshot_from_series(
        series,
        source="unit-test",
        last_market_timestamp="2026-03-05T00:00:00+00:00",
    )

    assert snapshot["observed_volatility"] > 0
    assert snapshot["historical_volatility"] > 0
    assert snapshot["ewma_volatility"] > 0
    assert snapshot["expected_shortfall_95"] >= 0
    assert snapshot["ewma_lambda"] == 0.94


def test_transaction_debug_contains_es_metrics() -> None:
    base = datetime.fromisoformat("2026-03-01T10:00:00+08:00")
    rows = []
    for idx in range(30):
        rows.append(
            {
                "transaction_id": f"tx{idx}",
                "user_id": "tail_user",
                "amount": 100.0 + idx * 5,
                "city": "Kuala Lumpur",
                "timestamp": (base + timedelta(minutes=idx)).isoformat(),
            }
        )

    history = pd.DataFrame(rows)
    history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True).dt.tz_convert("Asia/Kuala_Lumpur")

    engine = RiskEngine(history)
    result = engine.analyze_transaction(
        TransactionRequest(
            user_id="tail_user",
            amount=400.0,
            city="Kuala Lumpur",
            timestamp=datetime.fromisoformat("2026-03-01T12:00:00+08:00"),
            metadata={},
        )
    )

    assert "var_95_amount" in result.debug
    assert "expected_shortfall_95_amount" in result.debug
    assert result.debug["expected_shortfall_95_amount"] >= result.debug["var_95_amount"]
