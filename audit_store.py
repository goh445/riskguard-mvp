"""SQLite audit store for analyzed transactions and ops summaries."""

from __future__ import annotations

import hashlib
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
                    reasons TEXT NOT NULL,
                    prev_hash TEXT,
                    entry_hash TEXT
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cooperative_risk_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    category TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    flags TEXT NOT NULL,
                    expected_shortfall_95 REAL,
                    ewma_volatility REAL,
                    aml_hidden_paths INTEGER,
                    source_region TEXT,
                    metadata TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    events TEXT NOT NULL,
                    secret TEXT,
                    enabled INTEGER NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_delivery_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    subscription_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    destination_url TEXT NOT NULL,
                    status_code INTEGER,
                    success INTEGER NOT NULL,
                    response_preview TEXT,
                    payload TEXT NOT NULL
                )
                """
            )

            self._ensure_column(connection, "analysis_audit", "prev_hash", "TEXT")
            self._ensure_column(connection, "analysis_audit", "entry_hash", "TEXT")
            connection.commit()

    def _ensure_column(self, connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        """Add column to SQLite table if it does not exist."""
        cursor = connection.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cursor.fetchall()}
        if column not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _hash_audit_entry(
        *,
        prev_hash: str,
        created_at: str,
        client_id: str,
        user_id: str,
        amount: float,
        city: str,
        timestamp: str,
        score: int,
        status: str,
        flags: list[str],
        reasons: list[str],
    ) -> str:
        """Create deterministic SHA-256 hash for tamper-evident audit chaining."""
        payload = {
            "prev_hash": prev_hash,
            "created_at": created_at,
            "client_id": client_id,
            "user_id": user_id,
            "amount": round(float(amount), 6),
            "city": city,
            "timestamp": timestamp,
            "score": int(score),
            "status": status,
            "flags": flags,
            "reasons": reasons,
        }
        blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

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
            cursor.execute("SELECT entry_hash FROM analysis_audit ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = str(row[0]) if row and row[0] else "GENESIS"
            entry_hash = self._hash_audit_entry(
                prev_hash=prev_hash,
                created_at=now,
                client_id=client_id,
                user_id=user_id,
                amount=amount,
                city=city,
                timestamp=timestamp,
                score=score,
                status=status,
                flags=flags,
                reasons=reasons,
            )
            cursor.execute(
                """
                INSERT INTO analysis_audit
                (created_at, client_id, user_id, amount, city, timestamp, score, status, flags, reasons, prev_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    prev_hash,
                    entry_hash,
                ),
            )
            connection.commit()

    def list_audit_trail(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return latest tamper-evident audit rows for frontend/regulatory review."""
        safe_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, created_at, client_id, user_id, amount, city, timestamp, score, status, flags, reasons, prev_hash, entry_hash
                FROM analysis_audit
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            )
            rows = cursor.fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": int(row[0]),
                    "created_at": row[1],
                    "client_id": row[2],
                    "user_id": row[3],
                    "amount": float(row[4]),
                    "city": row[5],
                    "timestamp": row[6],
                    "score": int(row[7]),
                    "status": row[8],
                    "flags": json.loads(row[9]),
                    "reasons": json.loads(row[10]),
                    "prev_hash": row[11],
                    "entry_hash": row[12],
                }
            )
        return results

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

    def insert_cooperative_signal(
        self,
        *,
        pair: str,
        category: str,
        score: int,
        status: str,
        flags: list[str],
        expected_shortfall_95: float | None,
        ewma_volatility: float | None,
        aml_hidden_paths: int | None,
        source_region: str | None,
        metadata: dict[str, Any],
    ) -> int:
        """Insert one anonymized cooperative risk signal row and return row id."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO cooperative_risk_pool
                (created_at, pair, category, score, status, flags, expected_shortfall_95, ewma_volatility, aml_hidden_paths, source_region, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    pair,
                    category,
                    score,
                    status,
                    json.dumps(flags),
                    expected_shortfall_95,
                    ewma_volatility,
                    aml_hidden_paths,
                    source_region,
                    json.dumps(metadata),
                ),
            )
            row_id = int(cursor.lastrowid)
            connection.commit()
        return row_id

    def cooperative_summary_last_30d(self) -> dict[str, Any]:
        """Return anonymized cooperative pool summary over last 30 days."""
        start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(AVG(score), 0),
                    SUM(CASE WHEN status = 'HIGH' THEN 1 ELSE 0 END)
                FROM cooperative_risk_pool
                WHERE created_at >= ?
                """,
                (start,),
            )
            total, avg_score, high_count = cursor.fetchone()

            cursor.execute(
                """
                SELECT pair, COUNT(*) AS cnt, ROUND(AVG(score), 2) AS avg_score
                FROM cooperative_risk_pool
                WHERE created_at >= ?
                GROUP BY pair
                ORDER BY cnt DESC, avg_score DESC
                LIMIT 5
                """,
                (start,),
            )
            top_pairs_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT category, COUNT(*)
                FROM cooperative_risk_pool
                WHERE created_at >= ?
                GROUP BY category
                ORDER BY COUNT(*) DESC
                """,
                (start,),
            )
            category_rows = cursor.fetchall()

        return {
            "window_days": 30,
            "total_shared_signals": int(total or 0),
            "avg_shared_score": round(float(avg_score or 0.0), 2),
            "high_risk_shared_count": int(high_count or 0),
            "top_pairs": [
                {"pair": row[0], "signal_count": int(row[1]), "avg_score": float(row[2])}
                for row in top_pairs_rows
            ],
            "category_distribution": [
                {"category": row[0], "count": int(row[1])}
                for row in category_rows
            ],
        }

    def create_webhook_subscription(
        self,
        *,
        url: str,
        events: list[str],
        secret: str | None,
        enabled: bool,
        description: str | None,
    ) -> int:
        """Create or update one webhook subscription endpoint."""
        now = datetime.now(timezone.utc).isoformat()
        event_blob = json.dumps(sorted(set(events)))
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO webhook_subscriptions (url, events, secret, enabled, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url)
                DO UPDATE SET
                    events = excluded.events,
                    secret = excluded.secret,
                    enabled = excluded.enabled,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (url, event_blob, secret, 1 if enabled else 0, description, now, now),
            )
            cursor.execute("SELECT id FROM webhook_subscriptions WHERE url = ?", (url,))
            row = cursor.fetchone()
            connection.commit()
        return int(row[0]) if row else 0

    def list_webhook_subscriptions(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        """List configured webhook subscriptions."""
        query = "SELECT id, url, events, secret, enabled, description, created_at, updated_at FROM webhook_subscriptions"
        args: tuple[object, ...] = ()
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY id ASC"

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(query, args)
            rows = cursor.fetchall()

        return [
            {
                "id": int(row[0]),
                "url": row[1],
                "events": json.loads(row[2]),
                "secret": row[3],
                "enabled": bool(row[4]),
                "description": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            }
            for row in rows
        ]

    def delete_webhook_subscription(self, subscription_id: int) -> int:
        """Delete webhook subscription by id and return affected rows."""
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM webhook_subscriptions WHERE id = ?", (subscription_id,))
            deleted = cursor.rowcount
            connection.commit()
        return int(deleted or 0)

    def log_webhook_delivery(
        self,
        *,
        subscription_id: int,
        event_type: str,
        destination_url: str,
        status_code: int | None,
        success: bool,
        response_preview: str,
        payload: dict[str, Any],
    ) -> int:
        """Persist one webhook delivery attempt for operational audit."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO webhook_delivery_audit
                (created_at, subscription_id, event_type, destination_url, status_code, success, response_preview, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    subscription_id,
                    event_type,
                    destination_url,
                    status_code,
                    1 if success else 0,
                    response_preview[:240],
                    json.dumps(payload),
                ),
            )
            row_id = int(cursor.lastrowid)
            connection.commit()
        return row_id
