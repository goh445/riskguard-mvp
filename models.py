"""Pydantic models for request and response payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TransactionRequest(BaseModel):
    """Input payload for transaction analysis."""

    user_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    city: str = Field(..., min_length=1)
    timestamp: datetime
    metadata: dict[str, Any] | None = None


class RiskResponse(BaseModel):
    """Output payload for risk analysis."""

    score: int
    status: str
    flags: list[str]
    reasons: list[str]
    debug: dict[str, Any] | None = None
