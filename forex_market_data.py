"""Free market data enrichment for forex risk analysis."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any

import requests


class ForexMarketDataClient:
    """Fetch daily FX rates from free endpoint and derive risk features."""

    BASE_URL = "https://api.frankfurter.app"
    YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=2mo&interval=1d"
    COMMODITY_TICKERS = {
        "XAU": "GC=F",  # Gold
        "XAG": "SI=F",  # Silver
        "XPT": "PL=F",  # Platinum
        "XPD": "PA=F",  # Palladium
        "XBR": "BZ=F",  # Brent crude
        "XWT": "CL=F",  # WTI crude
    }

    @staticmethod
    def _now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _build_snapshot(
        *,
        observed_volatility: float,
        spread_bps: float,
        sample_size: int,
        last_rate: float | None,
        source: str,
        last_market_timestamp: str | None,
    ) -> dict[str, Any]:
        return {
            "observed_volatility": round(observed_volatility, 6),
            "spread_bps": round(spread_bps, 2),
            "sample_size": sample_size,
            "last_rate": None if last_rate is None else round(last_rate, 6),
            "source": source,
            "last_market_timestamp": last_market_timestamp,
            "fetched_at_utc": ForexMarketDataClient._now_utc_iso(),
        }

    def _snapshot_from_series(
        self,
        series: list[float],
        *,
        source: str,
        last_market_timestamp: str | None,
    ) -> dict[str, Any]:
        if len(series) < 5:
            return self._fallback_snapshot(reason="insufficient_rate_history")

        returns = []
        for idx in range(1, len(series)):
            prev = series[idx - 1]
            current = series[idx]
            returns.append((current - prev) / prev)

        volatility = max(0.0005, float(pstdev(returns)))
        spread_proxy_bps = max(1.0, min(40.0, float(mean(abs(x) for x in returns) * 10000 * 0.6)))
        return self._build_snapshot(
            observed_volatility=volatility,
            spread_bps=spread_proxy_bps,
            sample_size=len(series),
            last_rate=series[-1],
            source=source,
            last_market_timestamp=last_market_timestamp,
        )

    def _fetch_commodity_snapshot(self, base: str, quote: str) -> dict[str, Any]:
        commodity_code = base if base in self.COMMODITY_TICKERS else quote
        ticker = self.COMMODITY_TICKERS[commodity_code]

        if {base, quote} != {commodity_code, "USD"}:
            return self._fallback_snapshot(reason="unsupported_commodity_cross")

        try:
            response = requests.get(self.YAHOO_CHART_URL.format(ticker=ticker), timeout=12)
            response.raise_for_status()
            payload = response.json()
            result = payload.get("chart", {}).get("result", [])
            if not result:
                return self._fallback_snapshot(reason="commodity_data_missing")

            timestamps = result[0].get("timestamp", [])
            closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
            series = [float(value) for value in closes if isinstance(value, (int, float)) and value > 0]
            if base == "USD" and quote == commodity_code:
                series = [1.0 / value for value in series if value > 0]

            last_market_timestamp = None
            if timestamps:
                last_market_timestamp = datetime.fromtimestamp(int(timestamps[-1]), tz=timezone.utc).isoformat()

            return self._snapshot_from_series(
                series,
                source=f"yahoo:{ticker}",
                last_market_timestamp=last_market_timestamp,
            )
        except requests.RequestException:
            return self._fallback_snapshot(reason="commodity_market_data_unavailable")

    def fetch_snapshot(self, base: str, quote: str) -> dict[str, Any]:
        """Return derived volatility and spread proxy from recent daily rates."""
        if base in self.COMMODITY_TICKERS or quote in self.COMMODITY_TICKERS:
            return self._fetch_commodity_snapshot(base, quote)

        end_date = date.today()
        start_date = end_date - timedelta(days=45)
        url = (
            f"{self.BASE_URL}/{start_date.isoformat()}..{end_date.isoformat()}"
            f"?from={base}&to={quote}"
        )

        try:
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            payload = response.json()
            rates_dict = payload.get("rates", {})

            rates = []
            for day_key in sorted(rates_dict.keys()):
                rate_value = rates_dict[day_key].get(quote)
                if isinstance(rate_value, (int, float)) and rate_value > 0:
                    rates.append(float(rate_value))

            return self._snapshot_from_series(
                rates,
                source="frankfurter",
                last_market_timestamp=payload.get("end_date"),
            )
        except requests.RequestException:
            return self._fallback_snapshot(reason="market_data_unavailable")

    def _fallback_snapshot(self, reason: str) -> dict[str, Any]:
        return self._build_snapshot(
            observed_volatility=0.009,
            spread_bps=8.0,
            sample_size=0,
            last_rate=None,
            source=f"fallback:{reason}",
            last_market_timestamp=None,
        )
