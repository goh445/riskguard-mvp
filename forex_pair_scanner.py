"""Daily operational scanner for major forex pairs."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from audit_store import AuditStore
from forex_graph_engine import ForexGraphRiskEngine
from forex_market_data import ForexMarketDataClient
from models import ForexRiskRequest


class ForexPairScanner:
    """Scan major forex pairs daily and expose top risk leaderboard."""

    MAJOR_PAIRS = [
        ("EUR", "USD"),
        ("USD", "JPY"),
        ("GBP", "USD"),
        ("USD", "CHF"),
        ("AUD", "USD"),
        ("USD", "CAD"),
        ("NZD", "USD"),
        ("USD", "CNY"),
        ("USD", "SGD"),
        ("USD", "MYR"),
        ("EUR", "GBP"),
        ("EUR", "CHF"),
        ("XAU", "USD"),
        ("XAG", "USD"),
        ("XPT", "USD"),
        ("XPD", "USD"),
        ("XBR", "USD"),
        ("XWT", "USD"),
    ]

    def __init__(
        self,
        *,
        audit_store: AuditStore,
        market_data: ForexMarketDataClient,
        graph_engine: ForexGraphRiskEngine,
    ) -> None:
        self.audit_store = audit_store
        self.market_data = market_data
        self.graph_engine = graph_engine

    @staticmethod
    def _today_kl() -> str:
        return datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).date().isoformat()

    @staticmethod
    def _derived_context(observed_volatility: float, spread_bps: float) -> tuple[float, float]:
        """Derive macro stress and sentiment proxy from market state."""
        macro_stress = max(0.0, min(1.0, (observed_volatility / 0.03) * 0.7 + (spread_bps / 30.0) * 0.3))
        news_sentiment = max(-1.0, min(1.0, 0.2 - macro_stress))
        return round(macro_stress, 3), round(news_sentiment, 3)

    def _scan_one(self, base: str, quote: str) -> None:
        metrics = self.market_data.fetch_snapshot(base, quote)
        observed_volatility = float(metrics["observed_volatility"])
        spread_bps = float(metrics["spread_bps"])
        macro_stress, news_sentiment = self._derived_context(observed_volatility, spread_bps)

        request = ForexRiskRequest(
            base_currency=base,
            quote_currency=quote,
            observed_volatility=observed_volatility,
            spread_bps=spread_bps,
            timestamp=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            metadata={
                "macro_stress": macro_stress,
                "news_sentiment": news_sentiment,
                "market_data_source": metrics["source"],
                "market_data_sample_size": metrics["sample_size"],
                "market_last_rate": metrics["last_rate"],
                "scan_mode": "daily_auto",
            },
        )
        result = self.graph_engine.analyze(request)
        self.audit_store.upsert_forex_scan(
            scan_date=self._today_kl(),
            pair=f"{base}/{quote}",
            score=result.score,
            status=result.status,
            flags=result.flags,
            reasons=result.reasons,
            hidden_links=result.hidden_links,
            debug=result.debug or {},
        )

    def ensure_daily_scan(self, *, force_refresh: bool = False) -> str:
        """Run daily scan once per day (or force refresh) and return scan date."""
        scan_date = self._today_kl()
        existing = self.audit_store.count_forex_scans_for_date(scan_date)
        if existing >= len(self.MAJOR_PAIRS) and not force_refresh:
            return scan_date

        for base, quote in self.MAJOR_PAIRS:
            self._scan_one(base, quote)
        return scan_date

    def top_risk_pairs(self, *, limit: int = 5, force_refresh: bool = False) -> dict[str, object]:
        """Return top daily risk pairs with automatic scan refresh."""
        safe_limit = max(1, min(limit, 20))
        scan_date = self.ensure_daily_scan(force_refresh=force_refresh)
        rankings = self.audit_store.get_top_risk_pairs(scan_date=scan_date, limit=safe_limit)
        latest_update_utc = None
        if rankings:
            latest_update_utc = max(str(row.get("updated_at", "")) for row in rankings)
        return {
            "scan_date": scan_date,
            "pair_count": len(rankings),
            "latest_update_utc": latest_update_utc,
            "rankings": rankings,
        }
