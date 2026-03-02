"""Application configuration for RiskGuard MVP."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings and thresholds."""

    velocity_threshold_count: int = int(os.getenv("VELOCITY_THRESHOLD_COUNT", "5"))
    velocity_window_seconds: int = int(os.getenv("VELOCITY_WINDOW_SECONDS", "60"))
    location_window_minutes: int = int(os.getenv("LOCATION_WINDOW_MINUTES", "60"))
    high_value_multiplier: float = float(os.getenv("HIGH_VALUE_MULTIPLIER", "3.0"))
    risk_cap: int = int(os.getenv("RISK_CAP", "100"))
    use_ml_anomaly: bool = os.getenv("USE_ML_ANOMALY", "false").lower() == "true"
    random_seed: int = int(os.getenv("RANDOM_SEED", "42"))
    api_key: str = os.getenv("RISKGUARD_API_KEY", "")
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    audit_db_path: str = os.getenv("AUDIT_DB_PATH", "data/riskguard_audit.db")


settings = Settings()
