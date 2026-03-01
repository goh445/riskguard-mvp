"""Unit tests for RiskGuard deterministic risk rules."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from models import TransactionRequest
from risk_engine import RiskEngine


def _history(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("Asia/Kuala_Lumpur")
    return df


def test_no_flags_low_risk() -> None:
    history = _history(
        [
            {
                "transaction_id": "tx1",
                "user_id": "u1",
                "amount": 100.0,
                "city": "Kuala Lumpur",
                "timestamp": "2026-03-01T12:00:00+08:00",
            }
        ]
    )
    engine = RiskEngine(history)
    result = engine.analyze_transaction(
        TransactionRequest(
            user_id="u1",
            amount=110.0,
            city="Kuala Lumpur",
            timestamp=datetime.fromisoformat("2026-03-01T12:20:00+08:00"),
            metadata={},
        )
    )

    assert result.score == 0
    assert result.status == "Low"
    assert result.flags == []


def test_velocity_flag() -> None:
    base = datetime.fromisoformat("2026-03-01T13:00:00+08:00")
    rows = []
    for idx in range(5):
        rows.append(
            {
                "transaction_id": f"tx{idx}",
                "user_id": "u2",
                "amount": 20.0,
                "city": "Kuala Lumpur",
                "timestamp": (base + timedelta(seconds=idx * 10)).isoformat(),
            }
        )
    history = _history(rows)
    engine = RiskEngine(history)
    result = engine.analyze_transaction(
        TransactionRequest(
            user_id="u2",
            amount=25.0,
            city="Kuala Lumpur",
            timestamp=base + timedelta(seconds=50),
            metadata={},
        )
    )

    assert "velocity" in result.flags
    assert result.score == 40
    assert result.status == "Medium"


def test_location_flag() -> None:
    history = _history(
        [
            {
                "transaction_id": "tx1",
                "user_id": "u3",
                "amount": 70.0,
                "city": "Kuala Lumpur",
                "timestamp": "2026-03-01T10:00:00+08:00",
            }
        ]
    )
    engine = RiskEngine(history)
    result = engine.analyze_transaction(
        TransactionRequest(
            user_id="u3",
            amount=75.0,
            city="Johor Bahru",
            timestamp=datetime.fromisoformat("2026-03-01T10:45:00+08:00"),
            metadata={},
        )
    )

    assert "location" in result.flags
    assert result.score == 30
    assert result.status == "Low"


def test_high_value_flag() -> None:
    history = _history(
        [
            {
                "transaction_id": "tx1",
                "user_id": "u4",
                "amount": 100.0,
                "city": "Ipoh",
                "timestamp": "2026-03-01T09:00:00+08:00",
            },
            {
                "transaction_id": "tx2",
                "user_id": "u4",
                "amount": 110.0,
                "city": "Ipoh",
                "timestamp": "2026-03-01T10:00:00+08:00",
            },
        ]
    )
    engine = RiskEngine(history)
    result = engine.analyze_transaction(
        TransactionRequest(
            user_id="u4",
            amount=400.0,
            city="Ipoh",
            timestamp=datetime.fromisoformat("2026-03-01T11:00:00+08:00"),
            metadata={},
        )
    )

    assert "high_value" in result.flags
    assert result.score == 30
    assert result.status == "Low"


def test_combined_flags_high_risk() -> None:
    base = datetime.fromisoformat("2026-03-01T15:00:00+08:00")
    rows = []
    for idx in range(5):
        rows.append(
            {
                "transaction_id": f"tx{idx}",
                "user_id": "u5",
                "amount": 50.0,
                "city": "Kuala Lumpur",
                "timestamp": (base + timedelta(seconds=idx * 10)).isoformat(),
            }
        )
    history = _history(rows)
    engine = RiskEngine(history)
    result = engine.analyze_transaction(
        TransactionRequest(
            user_id="u5",
            amount=500.0,
            city="George Town",
            timestamp=base + timedelta(seconds=50),
            metadata={},
        )
    )

    assert set(result.flags) == {"velocity", "location", "high_value"}
    assert result.score == 100
    assert result.status == "High"
