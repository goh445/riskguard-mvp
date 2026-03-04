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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS forex_scan_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_date TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    flags TEXT NOT NULL,
                    reasons TEXT NOT NULL,
                    hidden_links TEXT NOT NULL,
                    debug TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(scan_date, pair)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS news_source_whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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

    def upsert_forex_scan(
        self,
        *,
        scan_date: str,
        pair: str,
        score: int,
        status: str,
        flags: list[str],
        reasons: list[str],
        hidden_links: list[str],
        debug: dict[str, Any],
    ) -> None:
        """Insert or update one forex daily scan row."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO forex_scan_audit
                (scan_date, pair, score, status, flags, reasons, hidden_links, debug, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scan_date, pair)
                DO UPDATE SET
                    score = excluded.score,
                    status = excluded.status,
                    flags = excluded.flags,
                    reasons = excluded.reasons,
                    hidden_links = excluded.hidden_links,
                    debug = excluded.debug,
                    updated_at = excluded.updated_at
                """,
                (
                    scan_date,
                    pair,
                    score,
                    status,
                    json.dumps(flags),
                    json.dumps(reasons),
                    json.dumps(hidden_links),
                    json.dumps(debug),
                    now,
                ),
            )
            connection.commit()

    def count_forex_scans_for_date(self, scan_date: str) -> int:
        """Return number of scanned forex pairs for a given date."""
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM forex_scan_audit WHERE scan_date = ?
                """,
                (scan_date,),
            )
            value = cursor.fetchone()[0]
        return int(value or 0)

    def get_top_risk_pairs(self, scan_date: str, limit: int) -> list[dict[str, Any]]:
        """Return top forex risk pairs for a specific scan date."""
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT pair, score, status, flags, reasons, hidden_links, debug, updated_at
                FROM forex_scan_audit
                WHERE scan_date = ?
                ORDER BY score DESC, pair ASC
                LIMIT ?
                """,
                (scan_date, limit),
            )
            rows = cursor.fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "pair": row[0],
                    "score": int(row[1]),
                    "status": row[2],
                    "flags": json.loads(row[3]),
                    "reasons": json.loads(row[4]),
                    "hidden_links": json.loads(row[5]),
                    "debug": json.loads(row[6]),
                    "updated_at": row[7],
                }
            )
        return results

    def seed_news_sources(self, urls: list[str]) -> None:
        """Seed whitelist with defaults when table is empty."""
        now = datetime.now(timezone.utc).isoformat()
        cleaned = [url.strip() for url in urls if url and url.strip()]
        if not cleaned:
            return

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM news_source_whitelist")
            existing_count = int(cursor.fetchone()[0] or 0)
            if existing_count > 0:
                return

            for url in cleaned:
                cursor.execute(
                    """
                    INSERT INTO news_source_whitelist (url, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (url, 1, now, now),
                )
            connection.commit()

    def list_news_sources(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        """List configured news source URLs."""
        query = "SELECT url, enabled, created_at, updated_at FROM news_source_whitelist"
        args: tuple[object, ...] = ()
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY url ASC"

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(query, args)
            rows = cursor.fetchall()

        return [
            {
                "url": row[0],
                "enabled": bool(row[1]),
                "created_at": row[2],
                "updated_at": row[3],
            }
            for row in rows
        ]

    def upsert_news_source(self, url: str, enabled: bool) -> None:
        """Create or update one news source whitelist entry."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO news_source_whitelist (url, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(url)
                DO UPDATE SET
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (url, 1 if enabled else 0, now, now),
            )
            connection.commit()

    def delete_news_source(self, url: str) -> int:
        """Delete one source URL from whitelist and return number of deleted rows."""
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM news_source_whitelist WHERE url = ?", (url,))
            deleted = cursor.rowcount
            connection.commit()
        return int(deleted or 0)
