"""Core deterministic risk scoring engine for transaction fraud rules."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pandas as pd

from config import settings
from data_utils import normalize_timestamp, user_average_amount, user_window_transactions, velocity_count_in_window
from models import RiskResponse, TransactionRequest

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import IsolationForest
except ImportError:  # pragma: no cover
    IsolationForest = None


@dataclass
class RuleEvaluation:
    """Result from rule checks."""

    flags: list[str]
    reasons: list[str]
    debug: dict[str, Any]


class RiskEngine:
    """Risk scoring engine with in-memory historical transaction state."""

    def __init__(self, history_df: pd.DataFrame) -> None:
        self.history_df = history_df.copy()
        if "timestamp" in self.history_df.columns and not self.history_df.empty:
            self.history_df["timestamp"] = pd.to_datetime(self.history_df["timestamp"], utc=True).dt.tz_convert(
                "Asia/Kuala_Lumpur"
            )
        self.ml_model = None
        self._train_optional_ml_model()

    def _train_optional_ml_model(self) -> None:
        """Train IsolationForest model when enabled."""
        if not settings.use_ml_anomaly:
            logger.debug("ML anomaly detection disabled via configuration")
            return
        if IsolationForest is None:
            logger.warning("scikit-learn not installed; ML anomaly detection disabled")
            return
        if self.history_df.empty:
            logger.warning("No history available; ML anomaly detection skipped")
            return

        training = self.history_df.copy()
        training["hour"] = training["timestamp"].dt.hour
        features = training[["amount", "hour"]]
        self.ml_model = IsolationForest(contamination=0.03, random_state=settings.random_seed)
        self.ml_model.fit(features)
        logger.info("IsolationForest model trained for optional anomaly debug")

    def _evaluate_rules(self, request: TransactionRequest) -> RuleEvaluation:
        tx_ts = normalize_timestamp(request.timestamp)
        flags: list[str] = []
        reasons: list[str] = []

        # Include incoming transaction in short-window checks by augmenting history.
        current_row = pd.DataFrame(
            [
                {
                    "transaction_id": "incoming",
                    "user_id": request.user_id,
                    "amount": request.amount,
                    "city": request.city,
                    "timestamp": tx_ts,
                }
            ]
        )
        combined_df = pd.concat([self.history_df, current_row], ignore_index=True)

        velocity_count = velocity_count_in_window(combined_df, request.user_id, tx_ts)
        if velocity_count > settings.velocity_threshold_count:
            flags.append("velocity")
            reasons.append(
                f"User has {velocity_count} transactions in the last {settings.velocity_window_seconds} seconds"
            )

        location_start = tx_ts - timedelta(minutes=settings.location_window_minutes)
        recent_user_df = user_window_transactions(
            df=combined_df,
            user_id=request.user_id,
            start_ts=location_start,
            end_ts=tx_ts,
        )
        unique_cities = set(recent_user_df["city"].astype(str).tolist())
        if len(unique_cities) > 1:
            flags.append("location")
            reasons.append(
                "User has transactions across different cities within 1 hour"
            )

        avg_amount = user_average_amount(self.history_df, request.user_id)
        high_value_threshold = avg_amount * settings.high_value_multiplier
        if avg_amount > 0 and request.amount > high_value_threshold:
            flags.append("high_value")
            reasons.append(
                f"Transaction amount {request.amount:.2f} exceeds {settings.high_value_multiplier:.1f}x user average {avg_amount:.2f}"
            )

        debug: dict[str, Any] = {
            "velocity_count": velocity_count,
            "velocity_threshold": settings.velocity_threshold_count,
            "location_unique_cities_last_hour": sorted(unique_cities),
            "user_avg_amount": round(avg_amount, 2),
            "high_value_threshold": round(high_value_threshold, 2),
        }

        if self.ml_model is not None:
            hour_value = tx_ts.hour
            prediction = int(self.ml_model.predict([[request.amount, hour_value]])[0])
            debug["ml_anomaly"] = prediction == -1

        return RuleEvaluation(flags=flags, reasons=reasons, debug=debug)

    @staticmethod
    def _score(flags: list[str]) -> int:
        score = 0
        if "velocity" in flags:
            score += 40
        if "location" in flags:
            score += 30
        if "high_value" in flags:
            score += 30
        return min(score, settings.risk_cap)

    @staticmethod
    def _status(score: int) -> str:
        if score <= 30:
            return "Low"
        if score <= 70:
            return "Medium"
        return "High"

    def analyze_transaction(self, request: TransactionRequest) -> RiskResponse:
        """Analyze a transaction and persist it into in-memory history."""
        evaluation = self._evaluate_rules(request)
        score = self._score(evaluation.flags)
        status = self._status(score)

        # Persist analyzed transaction for subsequent velocity/location checks.
        new_row = pd.DataFrame(
            [
                {
                    "transaction_id": f"live_{len(self.history_df) + 1}",
                    "user_id": request.user_id,
                    "amount": request.amount,
                    "city": request.city,
                    "timestamp": normalize_timestamp(request.timestamp),
                }
            ]
        )
        self.history_df = pd.concat([self.history_df, new_row], ignore_index=True)

        logger.info(
            "Analyzed transaction for user_id=%s amount=%.2f score=%s flags=%s",
            request.user_id,
            request.amount,
            score,
            evaluation.flags,
        )
        return RiskResponse(
            score=score,
            status=status,
            flags=evaluation.flags,
            reasons=evaluation.reasons,
            debug=evaluation.debug,
        )
