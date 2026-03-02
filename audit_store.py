"""SQLite audit store for analyzed transactions and ops summaries."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class AuditStore:
    """Persist transaction analysis outcomes to SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    client_id TEXT,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    city TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    flags TEXT NOT NULL,
                    reasons TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def log_decision(
        self,
        *,
        client_id: str,
        user_id: str,
        amount: float,
        city: str,
        timestamp: str,
        score: int,
        status: str,
        flags: list[str],
        reasons: list[str],
    ) -> None:
        """Store one analysis result row."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO analysis_audit
                (created_at, client_id, user_id, amount, city, timestamp, score, status, flags, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    client_id,
                    user_id,
                    amount,
                    city,
                    timestamp,
                    score,
                    status,
                    json.dumps(flags),
                    json.dumps(reasons),
                ),
            )
            connection.commit()

    def summary_last_24h(self) -> dict[str, Any]:
        """Return operational summary metrics for the last 24 hours."""
        start = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(AVG(score), 0),
                    SUM(CASE WHEN status = 'High' THEN 1 ELSE 0 END)
                FROM analysis_audit
                WHERE created_at >= ?
                """,
                (start,),
            )
            total, avg_score, high_risk_count = cursor.fetchone()

        return {
            "window_hours": 24,
            "total_analyzed": int(total or 0),
            "avg_score": round(float(avg_score or 0.0), 2),
            "high_risk_count": int(high_risk_count or 0),
        }
