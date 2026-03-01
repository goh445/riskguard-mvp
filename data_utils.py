"""Utilities for historical transaction data management."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from config import settings

DATA_FILE = Path("data/mock_transactions.csv")
KUALA_LUMPUR_TZ = "Asia/Kuala_Lumpur"


def normalize_timestamp(timestamp: datetime) -> pd.Timestamp:
    """Convert input timestamp to timezone-aware pandas Timestamp in Malaysia timezone."""
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        ts = ts.tz_localize(KUALA_LUMPUR_TZ)
    else:
        ts = ts.tz_convert(KUALA_LUMPUR_TZ)
    return ts


def load_transactions(csv_path: Path | str = DATA_FILE) -> pd.DataFrame:
    """Load historical transactions from CSV."""
    path = Path(csv_path)
    if not path.exists():
        return pd.DataFrame(
            columns=["transaction_id", "user_id", "amount", "city", "timestamp"]
        )

    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(
            columns=["transaction_id", "user_id", "amount", "city", "timestamp"]
        )
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(KUALA_LUMPUR_TZ)
    return df


def user_average_amount(df: pd.DataFrame, user_id: str) -> float:
    """Return the average historical amount for a given user."""
    user_df = df[df["user_id"] == user_id]
    if user_df.empty:
        return 0.0
    return float(user_df["amount"].mean())


def user_window_transactions(
    df: pd.DataFrame,
    user_id: str,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> pd.DataFrame:
    """Query user transactions between start and end timestamps inclusive."""
    mask = (
        (df["user_id"] == user_id)
        & (df["timestamp"] >= start_ts)
        & (df["timestamp"] <= end_ts)
    )
    return df.loc[mask]


def velocity_count_in_window(df: pd.DataFrame, user_id: str, tx_ts: pd.Timestamp) -> int:
    """Get number of user transactions in velocity lookback window ending at tx_ts."""
    start_ts = tx_ts - timedelta(seconds=settings.velocity_window_seconds)
    window_df = user_window_transactions(df=df, user_id=user_id, start_ts=start_ts, end_ts=tx_ts)
    return int(len(window_df))
