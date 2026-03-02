"""FastAPI entrypoint for RiskGuard MVP."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from audit_store import AuditStore
from config import settings
from data.generate_mock_data import save_mock_transactions
from data_utils import DATA_FILE, load_transactions
from models import RiskResponse, TransactionRequest
from risk_engine import RiskEngine
from service_controls import SlidingWindowRateLimiter, is_api_key_valid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RiskGuard MVP", version="1.0.0")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _build_engine() -> RiskEngine:
    if not DATA_FILE.exists():
        logger.info("Mock data CSV missing. Generating initial dataset...")
        save_mock_transactions(DATA_FILE)
    history = load_transactions(DATA_FILE)
    return RiskEngine(history)


engine = _build_engine()
rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
audit_store = AuditStore(settings.audit_db_path)


def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Require API key when configured via environment."""
    if is_api_key_valid(settings.api_key, api_key):
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


def enforce_rate_limit(request: Request) -> None:
    """Apply per-client request throttling."""
    client_id = request.client.host if request.client else "unknown"
    if rate_limiter.allow(client_id):
        return
    raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry later.")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/analyze-transaction", response_model=RiskResponse)
def analyze_transaction(
    payload: TransactionRequest,
    request: Request,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(enforce_rate_limit),
) -> RiskResponse:
    """Analyze an incoming transaction and return deterministic risk result."""
    result = engine.analyze_transaction(payload)

    client_id = request.client.host if request.client else "unknown"
    audit_store.log_decision(
        client_id=client_id,
        user_id=payload.user_id,
        amount=payload.amount,
        city=payload.city,
        timestamp=payload.timestamp.isoformat(),
        score=result.score,
        status=result.status,
        flags=result.flags,
        reasons=result.reasons,
    )
    return result


@app.get("/ops/summary")
def ops_summary(_auth: None = Depends(require_api_key)) -> dict[str, float | int]:
    """Operational summary for latest 24 hours of analyzed transactions."""
    return audit_store.summary_last_24h()
