"""FastAPI entrypoint for RiskGuard MVP."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from data.generate_mock_data import save_mock_transactions
from data_utils import DATA_FILE, load_transactions
from models import RiskResponse, TransactionRequest
from risk_engine import RiskEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RiskGuard MVP", version="1.0.0")


def _build_engine() -> RiskEngine:
    if not DATA_FILE.exists():
        logger.info("Mock data CSV missing. Generating initial dataset...")
        save_mock_transactions(DATA_FILE)
    history = load_transactions(DATA_FILE)
    return RiskEngine(history)


engine = _build_engine()


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/analyze-transaction", response_model=RiskResponse)
def analyze_transaction(payload: TransactionRequest) -> RiskResponse:
    """Analyze an incoming transaction and return deterministic risk result."""
    return engine.analyze_transaction(payload)
