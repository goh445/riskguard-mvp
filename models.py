"""Pydantic models for request and response payloads."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
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


class ForexRiskRequest(BaseModel):
    """Input payload for forex market network risk analysis."""

    base_currency: str = Field(..., min_length=1, max_length=10)
    quote_currency: str = Field(..., min_length=1, max_length=10)
    observed_volatility: float | None = Field(default=None, ge=0)
    spread_bps: float | None = Field(default=None, ge=0)
    timestamp: datetime
    metadata: dict[str, Any] | None = None

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def normalize_currency_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9.-]{1,10}", normalized):
            raise ValueError("asset code must be 1-10 chars [A-Z0-9.-]")
        return normalized

    @field_validator("timestamp")
    @classmethod
    def validate_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class ForexRiskResponse(BaseModel):
    """Output payload for forex network risk analysis."""

    score: int
    status: str
    flags: list[str]
    reasons: list[str]
    hidden_links: list[str]
    debug: dict[str, Any] | None = None


class NewsSourceUpsertRequest(BaseModel):
    """Input payload for updating dynamic news source whitelist."""

    url: str = Field(..., min_length=8)
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        normalized = value.strip()
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            raise ValueError("url must start with http:// or https://")
        return normalized
