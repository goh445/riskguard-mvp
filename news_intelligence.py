"""Autonomous global news signal extraction for market risk tuning."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests


class GlobalNewsIntelligence:
    """Fetch public news feeds and derive risk signals for autonomous scoring."""

    DEFAULT_FEEDS = [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.skynews.com/feeds/rss/world.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.ft.com/rss/world",
    ]

    GOOGLE_NEWS_REGIONS = [
        ("US", "en"),
        ("GB", "en"),
        ("SG", "en"),
        ("MY", "en"),
        ("IN", "en"),
        ("JP", "en"),
        ("AU", "en"),
        ("AE", "en"),
    ]

    TOPIC_QUERIES = [
        "forex market volatility",
        "currency crisis sanctions",
        "central bank rate hike cut",
        "liquidity funding stress",
        "geopolitical conflict oil shock",
        "commodity prices gold oil",
        "crypto market liquidation",
        "emerging market debt risk",
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

    def __init__(
        self,
        timeout_seconds: int = 2,
        cache_ttl_seconds: int = 600,
        use_gemini_news: bool = False,
        gemini_api_key: str = "",
        gemini_model: str = "gemini-1.5-flash",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.use_gemini_news = use_gemini_news
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.feed_sources = list(self.DEFAULT_FEEDS)
        self._lock = Lock()
        self._cached_at_epoch = 0.0
        self._cached_signals: dict[str, Any] | None = None
        self._last_gemini_status = "disabled"
        self._last_gemini_reason = "USE_GEMINI_NEWS is false or missing key"

    def set_feed_sources(self, sources: list[str]) -> None:
        """Dynamically update whitelist feed sources without restart."""
        cleaned = [source.strip() for source in sources if source and source.strip()]
        if not cleaned:
            cleaned = list(self.DEFAULT_FEEDS)
        with self._lock:
            self.feed_sources = cleaned
            self._cached_signals = None
            self._cached_at_epoch = 0.0

    def get_feed_sources(self) -> list[str]:
        """Return current active feed sources."""
        with self._lock:
            return list(self.feed_sources)

    def derive_signals(self) -> dict[str, Any]:
        """Return cached or freshly derived global news risk signals."""
        now_epoch = datetime.now(timezone.utc).timestamp()
        with self._lock:
            if (
                self._cached_signals is not None
                and now_epoch - self._cached_at_epoch < self.cache_ttl_seconds
            ):
                return self._cached_signals

        static_sources = self.get_feed_sources()
        dynamic_sources = self._build_dynamic_news_queries(max_queries=24)
        merged_sources = list(dict.fromkeys(static_sources + dynamic_sources))

        headlines, successful_feed_count, active_feed_count = self._fetch_headlines(
            limit=120,
            sources=merged_sources,
        )
        signals = self._signals_from_headlines(
            headlines=headlines,
            successful_feed_count=successful_feed_count,
            active_feed_count=active_feed_count,
        )
        signals = self._maybe_enhance_with_gemini(signals, headlines)
        signals["ai_news_engine"] = True
        signals["static_feed_count"] = len(static_sources)
        signals["dynamic_feed_count"] = len(dynamic_sources)
        signals["gemini_enabled"] = bool(self.use_gemini_news and self.gemini_api_key)
        signals["gemini_status"] = self._last_gemini_status
        signals["gemini_reason"] = self._last_gemini_reason
        with self._lock:
            self._cached_signals = signals
            self._cached_at_epoch = now_epoch
        return signals

    def _build_dynamic_news_queries(self, max_queries: int = 24) -> list[str]:
        """Build dynamic global news discovery RSS endpoints across regions/topics."""
        urls: list[str] = []
        for region, language in self.GOOGLE_NEWS_REGIONS:
            for query in self.TOPIC_QUERIES:
                encoded_query = quote_plus(query)
                urls.append(
                    "https://news.google.com/rss/search"
                    f"?q={encoded_query}&hl={language}&gl={region}&ceid={region}:{language}"
                )
                if len(urls) >= max_queries:
                    return urls
        return urls

    def _maybe_enhance_with_gemini(self, baseline: dict[str, Any], headlines: list[str]) -> dict[str, Any]:
        """Enhance baseline signals using Gemini if configured."""
        if not self.gemini_api_key:
            self._last_gemini_status = "disabled"
            self._last_gemini_reason = "No Gemini API key found in env"
            return baseline
        if not self.use_gemini_news:
            self._last_gemini_status = "disabled"
            self._last_gemini_reason = "USE_GEMINI_NEWS is false"
            return baseline
        if not headlines:
            self._last_gemini_status = "skipped"
            self._last_gemini_reason = "No headlines available"
            return baseline

        prompt = (
            "You are a market risk analyst. Based on these recent global headlines, return JSON only with keys: "
            "news_sentiment (-1 to 1), macro_stress (0 to 1), policy_uncertainty (0 to 1), "
            "geopolitical_risk (0 to 1), liquidity_risk (0 to 1), commodity_shock (0 to 1), "
            "systemic_contagion (0 to 1), fraud_pressure_index (0 to 1). "
            "No markdown, no explanation.\n\nHeadlines:\n"
            + "\n".join(f"- {headline}" for headline in headlines[:35])
        )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
            f"?key={self.gemini_api_key}"
        )
        body = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(url, json=body, timeout=10)
            response.raise_for_status()
            payload = response.json()
            raw_text = (
                payload.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            extracted = self._extract_json_object(raw_text)
            if not extracted:
                return baseline

            model_signals = json.loads(extracted)
            merged = dict(baseline)
            for key in [
                "news_sentiment",
                "macro_stress",
                "policy_uncertainty",
                "geopolitical_risk",
                "liquidity_risk",
                "commodity_shock",
                "systemic_contagion",
                "fraud_pressure_index",
            ]:
                if key in model_signals:
                    value = float(model_signals[key])
                    if key == "news_sentiment":
                        merged[key] = round(max(-1.0, min(1.0, value)), 3)
                    else:
                        merged[key] = round(max(0.0, min(1.0, value)), 3)

            merged["news_source"] = f"{baseline.get('news_source', 'rss')}+gemini"
            merged["news_updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            self._last_gemini_status = "enabled"
            self._last_gemini_reason = "Gemini refinement applied"
            return merged
        except (requests.RequestException, ValueError, json.JSONDecodeError, KeyError, TypeError):
            self._last_gemini_status = "error"
            self._last_gemini_reason = "Gemini request failed; fallback to deterministic signals"
            return baseline

    @staticmethod
    def _extract_json_object(text: str) -> str | None:
        """Extract first JSON object from free-form model output."""
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        return match.group(0)

    def _fetch_headlines(
        self,
        limit: int = 50,
        sources: list[str] | None = None,
    ) -> tuple[list[str], int, int]:
        headlines: list[str] = []
        seen: set[str] = set()
        sources = sources if sources is not None else self.get_feed_sources()
        successful_feeds = 0
        for feed in sources:
            try:
                response = requests.get(feed, timeout=self.timeout_seconds)
                response.raise_for_status()
                xml_root = ElementTree.fromstring(response.text)
                successful_feeds += 1

                rss_titles = [item.text.strip() for item in xml_root.findall(".//item/title") if item.text]
                atom_titles = [entry.text.strip() for entry in xml_root.findall(".//entry/title") if entry.text]

                for title in rss_titles + atom_titles:
                    normalized = title.lower()
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    headlines.append(title)
                    if len(headlines) >= limit:
                        return headlines, successful_feeds, len(sources)
            except (requests.RequestException, ElementTree.ParseError):
                continue
        return headlines, successful_feeds, len(sources)

    @staticmethod
    def _count_matches(text: str, terms: set[str]) -> int:
        return sum(1 for term in terms if term in text)

    def _signals_from_headlines(
        self,
        headlines: list[str],
        successful_feed_count: int,
        active_feed_count: int,
    ) -> dict[str, Any]:
        if not headlines:
            return {
                "news_sentiment": -0.05,
                "macro_stress": 0.45,
                "policy_uncertainty": 0.4,
                "geopolitical_risk": 0.45,
                "liquidity_risk": 0.35,
                "commodity_shock": 0.35,
                "systemic_contagion": 0.4,
                "fraud_pressure_index": 0.35,
                "news_sample_size": 0,
                "news_source": "fallback:no_feed",
                "active_feed_count": active_feed_count,
                "successful_feed_count": successful_feed_count,
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
            "systemic_contagion": round(float(min(1.0, (geo_count + policy_count) / 16)), 3),
            "fraud_pressure_index": round(float(min(1.0, (neg_count + liquidity_count) / 20)), 3),
            "news_sample_size": len(headlines),
            "news_source": f"rss:{successful_feed_count}/{active_feed_count}",
            "active_feed_count": active_feed_count,
            "successful_feed_count": successful_feed_count,
            "news_updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
