"""Free market data enrichment for forex risk analysis."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Any

import requests


class ForexMarketDataClient:
    """Fetch daily FX rates from free endpoint and derive risk features."""

    BASE_URL = "https://api.frankfurter.app"

    def fetch_snapshot(self, base: str, quote: str) -> dict[str, Any]:
        """Return derived volatility and spread proxy from recent daily rates."""
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

            if len(rates) < 5:
                return self._fallback_snapshot(reason="insufficient_rate_history")

            returns = []
            for idx in range(1, len(rates)):
                prev = rates[idx - 1]
                current = rates[idx]
                returns.append((current - prev) / prev)

            volatility = max(0.0005, float(pstdev(returns)))
            spread_proxy_bps = max(1.0, min(40.0, float(mean(abs(x) for x in returns) * 10000 * 0.6)))

            return {
                "observed_volatility": round(volatility, 6),
                "spread_bps": round(spread_proxy_bps, 2),
                "sample_size": len(rates),
                "last_rate": round(rates[-1], 6),
                "source": "frankfurter",
            }
        except requests.RequestException:
            return self._fallback_snapshot(reason="market_data_unavailable")

    @staticmethod
    def _fallback_snapshot(reason: str) -> dict[str, Any]:
        return {
            "observed_volatility": 0.009,
            "spread_bps": 8.0,
            "sample_size": 0,
            "last_rate": None,
            "source": f"fallback:{reason}",
        }
