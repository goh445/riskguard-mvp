"""FastAPI entrypoint for RiskGuard MVP."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from audit_store import AuditStore
from config import settings
from data.generate_mock_data import save_mock_transactions
from data_utils import DATA_FILE, load_transactions
from forex_market_data import ForexMarketDataClient
from forex_graph_engine import ForexGraphRiskEngine
from forex_pair_scanner import ForexPairScanner
from news_intelligence import GlobalNewsIntelligence
from models import ForexRiskRequest, ForexRiskResponse, NewsSourceUpsertRequest, RiskResponse, TransactionRequest
from risk_engine import RiskEngine
from service_controls import SlidingWindowRateLimiter, is_api_key_valid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RiskGuard MVP", version="1.0.0")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    """Attach request ID and latency metadata to every HTTP response."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.exception("Unhandled error request_id=%s path=%s", request_id, request.url.path)
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        response.headers["X-Request-ID"] = request_id
        return response

    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    response.headers["X-Request-ID"] = request_id
    return response


def _build_engine() -> RiskEngine:
    if not DATA_FILE.exists():
        logger.info("Mock data CSV missing. Generating initial dataset...")
        save_mock_transactions(DATA_FILE)
    history = load_transactions(DATA_FILE)
    return RiskEngine(history)


engine = _build_engine()
forex_graph_engine = ForexGraphRiskEngine()
forex_market_data = ForexMarketDataClient()
news_intelligence = GlobalNewsIntelligence(
    timeout_seconds=settings.news_fetch_timeout_seconds,
    cache_ttl_seconds=settings.news_cache_ttl_seconds,
    use_gemini_news=settings.use_gemini_news,
    gemini_api_key=settings.gemini_api_key,
    gemini_model=settings.gemini_model,
)
rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
audit_store = AuditStore(settings.audit_db_path)
audit_store.seed_news_sources(GlobalNewsIntelligence.DEFAULT_FEEDS)
news_intelligence.set_feed_sources(
    [item["url"] for item in audit_store.list_news_sources(enabled_only=True)]
)
forex_pair_scanner = ForexPairScanner(
    audit_store=audit_store,
    market_data=forex_market_data,
    graph_engine=forex_graph_engine,
    news_intelligence=news_intelligence,
)


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


@app.get("/ops/top-risk-pairs")
def top_risk_pairs(
    limit: int = 5,
    force_refresh: bool = False,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(enforce_rate_limit),
) -> dict[str, object]:
    """Return today's highest-risk major FX pairs with automatic daily scan."""
    return forex_pair_scanner.top_risk_pairs(limit=limit, force_refresh=force_refresh)


@app.get("/ops/news-sources")
def list_news_sources(
    enabled_only: bool = False,
    _auth: None = Depends(require_api_key),
) -> dict[str, object]:
    """List dynamic news source whitelist entries."""
    sources = audit_store.list_news_sources(enabled_only=enabled_only)
    return {
        "count": len(sources),
        "sources": sources,
        "active_sources": news_intelligence.get_feed_sources(),
    }


@app.post("/ops/news-sources")
def upsert_news_source(
    payload: NewsSourceUpsertRequest,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(enforce_rate_limit),
) -> dict[str, object]:
    """Create or update one news source whitelist entry."""
    audit_store.upsert_news_source(url=payload.url, enabled=payload.enabled)
    active = [item["url"] for item in audit_store.list_news_sources(enabled_only=True)]
    news_intelligence.set_feed_sources(active)
    return {
        "updated": True,
        "active_source_count": len(active),
        "active_sources": active,
    }


@app.delete("/ops/news-sources")
def delete_news_source(
    url: str,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(enforce_rate_limit),
) -> dict[str, object]:
    """Delete one source from whitelist and refresh active feed list."""
    deleted = audit_store.delete_news_source(url=url.strip())
    active = [item["url"] for item in audit_store.list_news_sources(enabled_only=True)]
    news_intelligence.set_feed_sources(active)
    return {
        "deleted": deleted,
        "active_source_count": len(active),
        "active_sources": active,
    }


@app.post("/analyze-forex-risk", response_model=ForexRiskResponse)
def analyze_forex_risk(
    payload: ForexRiskRequest,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(enforce_rate_limit),
) -> ForexRiskResponse:
    """Analyze forex market risk using network contagion and hidden-link logic."""
    metrics = forex_market_data.fetch_snapshot(payload.base_currency, payload.quote_currency)
    news_signals = news_intelligence.derive_signals() if settings.auto_parameter_tuning else {}
    user_metadata = payload.metadata or {}

    merged_metadata = {
        **user_metadata,
        **news_signals,
        "market_data_source": metrics["source"],
        "market_data_sample_size": metrics["sample_size"],
        "market_last_rate": metrics["last_rate"],
        "market_last_timestamp": metrics.get("last_market_timestamp"),
        "market_data_fetched_at_utc": metrics.get("fetched_at_utc"),
        "auto_parameter_tuning": settings.auto_parameter_tuning,
    }

    enriched_payload = payload.model_copy(
        update={
            "observed_volatility": payload.observed_volatility
            if payload.observed_volatility is not None
            else metrics["observed_volatility"],
            "spread_bps": payload.spread_bps if payload.spread_bps is not None else metrics["spread_bps"],
            "metadata": merged_metadata,
        }
    )
    return forex_graph_engine.analyze(enriched_payload)


@app.get("/forex/market-snapshot")
def forex_market_snapshot(
    base_currency: str,
    quote_currency: str,
    _auth: None = Depends(require_api_key),
    _limit: None = Depends(enforce_rate_limit),
) -> dict[str, float | int | str | None]:
    """Get free-market derived risk features for a currency pair."""
    return forex_market_data.fetch_snapshot(base_currency.upper(), quote_currency.upper())
