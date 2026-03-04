"""Zero-cost forex market network risk engine using NetworkX graph analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from models import ForexRiskRequest, ForexRiskResponse


@dataclass
class ForexRuleResult:
    flags: list[str]
    reasons: list[str]
    hidden_links: list[str]
    debug: dict[str, Any]


class ForexGraphRiskEngine:
    """Analyze forex risk by propagating stress on a currency connectivity graph."""

    def __init__(self) -> None:
        self.graph = nx.Graph()
        self._build_default_graph()

    def _build_default_graph(self) -> None:
        currencies = [
            "USD",
            "EUR",
            "JPY",
            "GBP",
            "CHF",
            "AUD",
            "NZD",
            "CAD",
            "CNY",
            "SGD",
            "MYR",
            "SEK",
            "NOK",
            "HKD",
            "INR",
            "KRW",
            "BRL",
            "ZAR",
            "MXN",
            "XAU",
            "XAG",
            "XPT",
            "XPD",
            "XBR",
            "XWT",
            "BTC",
            "ETH",
            "BNB",
            "SOL",
            "XRP",
        ]
        self.graph.add_nodes_from(currencies)

        edges = [
            ("USD", "EUR", 0.20),
            ("USD", "JPY", 0.22),
            ("USD", "GBP", 0.24),
            ("USD", "CHF", 0.18),
            ("USD", "AUD", 0.26),
            ("USD", "NZD", 0.27),
            ("USD", "CAD", 0.21),
            ("USD", "CNY", 0.30),
            ("USD", "SGD", 0.23),
            ("USD", "MYR", 0.28),
            ("EUR", "GBP", 0.19),
            ("EUR", "CHF", 0.17),
            ("AUD", "NZD", 0.15),
            ("SGD", "MYR", 0.18),
            ("CNY", "SGD", 0.25),
            ("XAU", "USD", 0.34),
            ("XAG", "USD", 0.33),
            ("XPT", "USD", 0.31),
            ("XPD", "USD", 0.31),
            ("XBR", "USD", 0.36),
            ("XWT", "USD", 0.36),
            ("XAU", "EUR", 0.28),
            ("XBR", "EUR", 0.3),
            ("USD", "SEK", 0.2),
            ("USD", "NOK", 0.2),
            ("USD", "HKD", 0.16),
            ("USD", "INR", 0.27),
            ("USD", "KRW", 0.27),
            ("USD", "BRL", 0.31),
            ("USD", "ZAR", 0.32),
            ("USD", "MXN", 0.29),
            ("EUR", "SEK", 0.19),
            ("EUR", "NOK", 0.19),
            ("BTC", "USD", 0.42),
            ("ETH", "USD", 0.4),
            ("BNB", "USD", 0.38),
            ("SOL", "USD", 0.41),
            ("XRP", "USD", 0.39),
            ("BTC", "ETH", 0.3),
            ("BTC", "XAU", 0.22),
            ("ETH", "XAU", 0.2),
        ]
        for left, right, contagion_weight in edges:
            self.graph.add_edge(left, right, contagion_weight=contagion_weight)

    @staticmethod
    def _status(score: int) -> str:
        if score <= 30:
            return "Low"
        if score <= 70:
            return "Medium"
        return "High"

    def _evaluate(self, request: ForexRiskRequest) -> ForexRuleResult:
        flags: list[str] = []
        reasons: list[str] = []
        hidden_links: list[str] = []
        observed_volatility = request.observed_volatility if request.observed_volatility is not None else 0.009
        spread_bps = request.spread_bps if request.spread_bps is not None else 8.0

        if request.base_currency not in self.graph or request.quote_currency not in self.graph:
            flags.append("coverage_gap")
            reasons.append("Currency pair outside current graph coverage; risk inferred with conservative fallback")

        if observed_volatility >= 0.015:
            flags.append("volatility_spike")
            reasons.append("Observed volatility is elevated versus normal FX ranges")

        if spread_bps >= 20:
            flags.append("liquidity_stress")
            reasons.append("Bid-ask spread indicates potential liquidity stress")

        centrality = nx.degree_centrality(self.graph)
        base_centrality = centrality.get(request.base_currency, 0.0)
        quote_centrality = centrality.get(request.quote_currency, 0.0)
        if base_centrality >= 0.4 or quote_centrality >= 0.4:
            flags.append("hub_exposure")
            reasons.append("Pair is exposed to a major liquidity hub, increasing contagion impact")

        path_risk = 0.0
        path_nodes: list[str] = []
        if request.base_currency in self.graph and request.quote_currency in self.graph:
            if nx.has_path(self.graph, request.base_currency, request.quote_currency):
                path_nodes = nx.shortest_path(self.graph, request.base_currency, request.quote_currency)
                if len(path_nodes) >= 3:
                    flags.append("hidden_link")
                    hidden_links.append(" -> ".join(path_nodes))
                    reasons.append("Indirect transmission path found through intermediary currencies")

                path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
                path_risk = sum(self.graph[left][right]["contagion_weight"] for left, right in path_edges)

        metadata = request.metadata or {}
        sentiment = float(metadata.get("news_sentiment", 0.0))
        macro_stress = float(metadata.get("macro_stress", 0.0))
        policy_uncertainty = float(metadata.get("policy_uncertainty", 0.0))
        geopolitical_risk = float(metadata.get("geopolitical_risk", 0.0))
        liquidity_risk = float(metadata.get("liquidity_risk", 0.0))
        commodity_shock = float(metadata.get("commodity_shock", 0.0))
        systemic_contagion = float(metadata.get("systemic_contagion", 0.0))
        fraud_pressure_index = float(metadata.get("fraud_pressure_index", 0.0))
        if sentiment < -0.25 or macro_stress > 0.6:
            flags.append("macro_sentiment_stress")
            reasons.append("Macro/news signals suggest elevated directional stress")
        if policy_uncertainty > 0.55:
            flags.append("policy_uncertainty")
            reasons.append("Policy uncertainty elevated from global central-bank and rates signals")
        if geopolitical_risk > 0.55:
            flags.append("geopolitical_risk")
            reasons.append("Geopolitical conditions imply higher contagion risk")
        if liquidity_risk > 0.55:
            flags.append("liquidity_risk")
            reasons.append("Liquidity-related stress signals are elevated")
        if commodity_shock > 0.55:
            flags.append("commodity_shock")
            reasons.append("Commodity-linked volatility likely to spill over into FX pairs")
        if systemic_contagion > 0.55:
            flags.append("systemic_contagion")
            reasons.append("Cross-market contagion pressure indicates systemic spillover risk")
        if fraud_pressure_index > 0.55:
            flags.append("fraud_pressure_index")
            reasons.append("Fraud pressure index suggests elevated manipulation or dislocation risk")

        score = 0.0
        score += min(observed_volatility * 2200, 35)
        score += min(spread_bps * 0.8, 20)
        score += min(path_risk * 45, 20)
        score += min((base_centrality + quote_centrality) * 20, 15)
        score += max(0.0, min((-sentiment * 20) + (macro_stress * 10), 15))
        score += min(policy_uncertainty * 8, 8)
        score += min(geopolitical_risk * 8, 8)
        score += min(liquidity_risk * 7, 7)
        score += min(commodity_shock * 7, 7)
        score += min(systemic_contagion * 10, 10)
        score += min(fraud_pressure_index * 10, 10)
        score = min(100.0, score)

        debug: dict[str, Any] = {
            "base_centrality": round(base_centrality, 3),
            "quote_centrality": round(quote_centrality, 3),
            "path_nodes": path_nodes,
            "path_risk": round(path_risk, 3),
            "sentiment": sentiment,
            "news_sentiment": sentiment,
            "macro_stress": macro_stress,
            "policy_uncertainty": policy_uncertainty,
            "geopolitical_risk": geopolitical_risk,
            "liquidity_risk": liquidity_risk,
            "commodity_shock": commodity_shock,
            "systemic_contagion": systemic_contagion,
            "fraud_pressure_index": fraud_pressure_index,
            "observed_volatility": round(observed_volatility, 6),
            "spread_bps": round(spread_bps, 2),
            "market_data_source": metadata.get("market_data_source", "manual_or_unknown"),
            "market_data_fetched_at_utc": metadata.get("market_data_fetched_at_utc"),
            "market_last_timestamp": metadata.get("market_last_timestamp"),
            "raw_score": round(score, 2),
        }

        return ForexRuleResult(
            flags=sorted(set(flags)),
            reasons=reasons,
            hidden_links=hidden_links,
            debug=debug,
        )

    def analyze(self, request: ForexRiskRequest) -> ForexRiskResponse:
        """Analyze one forex pair event and return network-aware risk output."""
        result = self._evaluate(request)
        score = int(round(float(result.debug["raw_score"])))
        status = self._status(score)
        return ForexRiskResponse(
            score=score,
            status=status,
            flags=result.flags,
            reasons=result.reasons,
            hidden_links=result.hidden_links,
            debug=result.debug,
        )
