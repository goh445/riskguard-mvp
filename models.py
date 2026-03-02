"""Pydantic models for request and response payloads."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TransactionRequest(BaseModel):
    """Input payload for transaction analysis."""

    user_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    city: str = Field(..., min_length=1)
    timestamp: datetime
    metadata: dict[str, Any] | None = None

    @field_validator("user_id", "city")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        """Normalize and validate non-empty text fields."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized

    @field_validator("timestamp")
    @classmethod
    def validate_malaysia_timezone(cls, value: datetime) -> datetime:
        """Ensure timestamp is timezone-aware and aligned to Malaysia UTC+08:00."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if value.utcoffset() != timedelta(hours=8):
            raise ValueError("timestamp must be Malaysia timezone (UTC+08:00)")
        return value


class RiskResponse(BaseModel):
    """Output payload for risk analysis."""

    score: int
    status: str
    flags: list[str]
    reasons: list[str]
    debug: dict[str, Any] | None = None
