"""Autonomous global news signal extraction for market risk tuning."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
from xml.etree import ElementTree

import requests


class GlobalNewsIntelligence:
    """Fetch public news feeds and derive risk signals for autonomous scoring."""

    FEEDS = [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ]

    POSITIVE_TERMS = {
        "growth",
        "recovery",
        "stabilize",
        "agreement",
        "optimism",
        "easing",
        "improve",
        "surplus",
    }
    NEGATIVE_TERMS = {
        "war",
        "conflict",
        "sanction",
        "crisis",
        "recession",
        "inflation",
        "default",
        "debt",
        "volatility",
        "cut",
        "downgrade",
        "uncertainty",
        "shock",
    }
    POLICY_TERMS = {"central bank", "rate hike", "rate cut", "fed", "ecb", "boj", "policy"}
    GEO_TERMS = {"war", "conflict", "border", "missile", "strike", "geopolitical"}
    LIQUIDITY_TERMS = {"liquidity", "funding", "margin", "credit", "banking"}
    COMMODITY_TERMS = {"oil", "gold", "energy", "commodity", "brent", "wti"}

    def __init__(self, timeout_seconds: int = 2, cache_ttl_seconds: int = 600) -> None:
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self._lock = Lock()
        self._cached_at_epoch = 0.0
        self._cached_signals: dict[str, Any] | None = None

    def derive_signals(self) -> dict[str, Any]:
        """Return cached or freshly derived global news risk signals."""
        now_epoch = datetime.now(timezone.utc).timestamp()
        with self._lock:
            if (
                self._cached_signals is not None
                and now_epoch - self._cached_at_epoch < self.cache_ttl_seconds
            ):
                return self._cached_signals

        headlines = self._fetch_headlines(limit=50)
        signals = self._signals_from_headlines(headlines)
        with self._lock:
            self._cached_signals = signals
            self._cached_at_epoch = now_epoch
        return signals

    def _fetch_headlines(self, limit: int = 50) -> list[str]:
        headlines: list[str] = []
        for feed in self.FEEDS:
            try:
                response = requests.get(feed, timeout=self.timeout_seconds)
                response.raise_for_status()
                xml_root = ElementTree.fromstring(response.text)
                for item in xml_root.findall(".//item/title"):
                    if item.text:
                        headlines.append(item.text.strip())
                        if len(headlines) >= limit:
                            return headlines
            except (requests.RequestException, ElementTree.ParseError):
                continue
        return headlines

    @staticmethod
    def _count_matches(text: str, terms: set[str]) -> int:
        return sum(1 for term in terms if term in text)

    def _signals_from_headlines(self, headlines: list[str]) -> dict[str, Any]:
        if not headlines:
            return {
                "news_sentiment": -0.05,
                "macro_stress": 0.45,
                "policy_uncertainty": 0.4,
                "geopolitical_risk": 0.45,
                "liquidity_risk": 0.35,
                "commodity_shock": 0.35,
                "news_sample_size": 0,
                "news_source": "fallback:no_feed",
                "news_updated_at_utc": datetime.now(timezone.utc).isoformat(),
            }

        joined = " ".join(headlines).lower()
        pos_count = self._count_matches(joined, self.POSITIVE_TERMS)
        neg_count = self._count_matches(joined, self.NEGATIVE_TERMS)
        policy_count = self._count_matches(joined, self.POLICY_TERMS)
        geo_count = self._count_matches(joined, self.GEO_TERMS)
        liquidity_count = self._count_matches(joined, self.LIQUIDITY_TERMS)
        commodity_count = self._count_matches(joined, self.COMMODITY_TERMS)

        total_sentiment_hits = max(1, pos_count + neg_count)
        sentiment = (pos_count - neg_count) / total_sentiment_hits

        macro_stress = min(1.0, max(0.0, (neg_count / total_sentiment_hits) * 0.7 + (geo_count > 0) * 0.15))
        policy_uncertainty = min(1.0, policy_count / 10)
        geopolitical_risk = min(1.0, geo_count / 8)
        liquidity_risk = min(1.0, liquidity_count / 8)
        commodity_shock = min(1.0, commodity_count / 10)

        return {
            "news_sentiment": round(float(sentiment), 3),
            "macro_stress": round(float(macro_stress), 3),
            "policy_uncertainty": round(float(policy_uncertainty), 3),
            "geopolitical_risk": round(float(geopolitical_risk), 3),
            "liquidity_risk": round(float(liquidity_risk), 3),
            "commodity_shock": round(float(commodity_shock), 3),
            "news_sample_size": len(headlines),
            "news_source": "rss:reuters_bbc",
            "news_updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
