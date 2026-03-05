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
            "XCU",
            "XNG",
            "XRB",
            "XHO",
            "XKC",
            "XSU",
            "XCC",
            "XCT",
            "XOJ",
            "XWH",
            "XCN",
            "XSO",
            "XSM",
            "XSL",
            "XLE",
            "XHE",
            "XFE",
            "XAL",
            "XPB",
            "XUR",
            "XLI",
            "XNI",
            "XZN",
            "XPL",
            "XPA",
            "XSI",
            "BTC",
            "ETH",
            "BNB",
            "SOL",
            "XRP",
            "ADA",
            "DOG",
            "DOT",
            "LTC",
            "TRX",
            "BCH",
            "UNI",
            "LNK",
            "XLM",
            "AVA",
            "MTA",
            "ICP",
            "ETC",
            "EOS",
            "ALG",
            "VET",
            "FIL",
            "APT",
            "ARB",
            "OPM",
            "NEA",
            "SUI",
            "TON",
            "ATM",
            "INJ",
            "XMR",
            "AAV",
            "MKR",
            "RND",
            "GRT",
            "SNX",
            "KAS",
            "PEPE",
            "SHIB",
            "BONK",
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "META",
            "TSLA",
            "JPM",
            "V",
            "MA",
            "UNH",
            "HD",
            "PG",
            "XOM",
            "JNJ",
            "LLY",
            "COST",
            "AVGO",
            "KO",
            "PEP",
            "MRK",
            "ABBV",
            "BAC",
            "WMT",
            "ORCL",
            "ADBE",
            "NFLX",
            "CRM",
            "AMD",
            "INTC",
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
            ("XCU", "USD", 0.35),
            ("XNG", "USD", 0.37),
            ("XRB", "USD", 0.38),
            ("XHO", "USD", 0.37),
            ("XKC", "USD", 0.34),
            ("XSU", "USD", 0.34),
            ("XCC", "USD", 0.34),
            ("XCT", "USD", 0.34),
            ("XOJ", "USD", 0.33),
            ("XWH", "USD", 0.33),
            ("XCN", "USD", 0.33),
            ("XSO", "USD", 0.33),
            ("XSM", "USD", 0.33),
            ("XSL", "USD", 0.33),
            ("XLE", "USD", 0.32),
            ("XHE", "USD", 0.32),
            ("XFE", "USD", 0.32),
            ("XAL", "USD", 0.35),
            ("XPB", "USD", 0.33),
            ("XUR", "USD", 0.36),
            ("XLI", "USD", 0.35),
            ("XNI", "USD", 0.35),
            ("XZN", "USD", 0.35),
            ("XPL", "USD", 0.34),
            ("XPA", "USD", 0.34),
            ("XSI", "USD", 0.34),
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
            ("ADA", "USD", 0.39),
            ("DOG", "USD", 0.41),
            ("DOT", "USD", 0.39),
            ("LTC", "USD", 0.39),
            ("TRX", "USD", 0.39),
            ("BCH", "USD", 0.39),
            ("UNI", "USD", 0.4),
            ("LNK", "USD", 0.4),
            ("XLM", "USD", 0.4),
            ("AVA", "USD", 0.41),
            ("MTA", "USD", 0.4),
            ("ICP", "USD", 0.41),
            ("ETC", "USD", 0.39),
            ("EOS", "USD", 0.39),
            ("ALG", "USD", 0.39),
            ("VET", "USD", 0.4),
            ("FIL", "USD", 0.4),
            ("APT", "USD", 0.41),
            ("ARB", "USD", 0.41),
            ("OPM", "USD", 0.41),
            ("NEA", "USD", 0.4),
            ("SUI", "USD", 0.41),
            ("TON", "USD", 0.4),
            ("ATM", "USD", 0.4),
            ("INJ", "USD", 0.41),
            ("XMR", "USD", 0.4),
            ("AAV", "USD", 0.41),
            ("MKR", "USD", 0.41),
            ("RND", "USD", 0.41),
            ("GRT", "USD", 0.4),
            ("SNX", "USD", 0.4),
            ("KAS", "USD", 0.41),
            ("PEPE", "USD", 0.42),
            ("SHIB", "USD", 0.42),
            ("BONK", "USD", 0.42),
            ("AAPL", "USD", 0.36),
            ("MSFT", "USD", 0.36),
            ("GOOGL", "USD", 0.36),
            ("AMZN", "USD", 0.37),
            ("NVDA", "USD", 0.39),
            ("META", "USD", 0.37),
            ("TSLA", "USD", 0.4),
            ("JPM", "USD", 0.34),
            ("V", "USD", 0.34),
            ("MA", "USD", 0.34),
            ("UNH", "USD", 0.34),
            ("HD", "USD", 0.34),
            ("PG", "USD", 0.33),
            ("XOM", "USD", 0.35),
            ("JNJ", "USD", 0.33),
            ("LLY", "USD", 0.35),
            ("COST", "USD", 0.34),
            ("AVGO", "USD", 0.37),
            ("KO", "USD", 0.33),
            ("PEP", "USD", 0.33),
            ("MRK", "USD", 0.34),
            ("ABBV", "USD", 0.34),
            ("BAC", "USD", 0.34),
            ("WMT", "USD", 0.33),
            ("ORCL", "USD", 0.35),
            ("ADBE", "USD", 0.36),
            ("NFLX", "USD", 0.37),
            ("CRM", "USD", 0.36),
            ("AMD", "USD", 0.38),
            ("INTC", "USD", 0.35),
            ("BTC", "ETH", 0.3),
            ("BTC", "XAU", 0.22),
            ("ETH", "XAU", 0.2),
            ("AAPL", "MSFT", 0.26),
            ("MSFT", "NVDA", 0.28),
            ("GOOGL", "META", 0.27),
            ("AMZN", "MSFT", 0.26),
            ("JPM", "BAC", 0.24),
            ("XOM", "XBR", 0.3),
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
        path_count_considered = 0
        if request.base_currency in self.graph and request.quote_currency in self.graph:
            if nx.has_path(self.graph, request.base_currency, request.quote_currency):
                candidate_paths: list[tuple[float, float, list[str]]] = []
                for idx, one_path in enumerate(
                    nx.all_simple_paths(self.graph, request.base_currency, request.quote_currency, cutoff=4)
                ):
                    path_edges = list(zip(one_path[:-1], one_path[1:]))
                    edge_sum = sum(self.graph[left][right]["contagion_weight"] for left, right in path_edges)
                    edge_avg = edge_sum / max(1, len(path_edges))
                    candidate_paths.append((edge_avg, edge_sum, one_path))
                    if idx >= 11:
                        break

                path_count_considered = len(candidate_paths)
                if candidate_paths:
                    candidate_paths.sort(key=lambda item: (item[0], item[1]), reverse=True)
                    best_avg, best_sum, best_path = candidate_paths[0]
                    path_nodes = best_path
                    path_risk = best_sum

                    aml_paths = []
                    intermediary_frequency: dict[str, int] = {}
                    for avg_weight, total_weight, selected_path in candidate_paths[:3]:
                        if len(selected_path) >= 3:
                            aml_paths.append(
                                f"{' -> '.join(selected_path)} | aml_path_avg={avg_weight:.3f} | aml_path_sum={total_weight:.3f}"
                            )
                            for intermediary in selected_path[1:-1]:
                                intermediary_frequency[intermediary] = intermediary_frequency.get(intermediary, 0) + 1

                    hidden_links.extend(aml_paths)
                    if len(best_path) >= 3:
                        flags.append("hidden_link")
                        reasons.append("Indirect transmission path found through intermediary assets")

                    repeated_intermediaries = [
                        node for node, count in intermediary_frequency.items() if count >= 2
                    ]
                    if repeated_intermediaries:
                        flags.append("aml_indirect_chain")
                        reasons.append(
                            "Multiple indirect contagion routes share intermediary nodes, indicating AML-style chain risk"
                        )
                        hidden_links.append(
                            "shared_intermediaries=" + ",".join(sorted(repeated_intermediaries)[:5])
                        )

                    if path_count_considered >= 3 and best_avg >= 0.27:
                        flags.append("multi_path_contagion")
                        reasons.append("Several high-weight indirect paths increase cross-asset contagion intensity")

        metadata = request.metadata or {}
        sentiment = float(metadata.get("news_sentiment", 0.0))
        macro_stress = float(metadata.get("macro_stress", 0.0))
        policy_uncertainty = float(metadata.get("policy_uncertainty", 0.0))
        geopolitical_risk = float(metadata.get("geopolitical_risk", 0.0))
        liquidity_risk = float(metadata.get("liquidity_risk", 0.0))
        commodity_shock = float(metadata.get("commodity_shock", 0.0))
        systemic_contagion = float(metadata.get("systemic_contagion", 0.0))
        fraud_pressure_index = float(metadata.get("fraud_pressure_index", 0.0))
        expected_shortfall_95 = float(metadata.get("expected_shortfall_95", 0.0) or 0.0)
        ewma_volatility = float(metadata.get("ewma_volatility", observed_volatility) or observed_volatility)
        historical_volatility = float(metadata.get("historical_volatility", observed_volatility) or observed_volatility)
        ewma_scale = ewma_volatility / observed_volatility if observed_volatility > 0 else 1.0
        ewma_scale = max(0.85, min(1.45, ewma_scale))
        active_feed_count = int(metadata.get("active_feed_count", 0) or 0)
        successful_feed_count = int(metadata.get("successful_feed_count", 0) or 0)
        news_reliability = (
            successful_feed_count / active_feed_count if active_feed_count > 0 else 1.0
        )
        news_weight = max(0.45, min(1.0, 0.45 + 0.55 * news_reliability))
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
        if expected_shortfall_95 > 0.012:
            flags.append("tail_loss_stress")
            reasons.append("Expected Shortfall indicates elevated tail-loss exposure under stressed moves")

        score = 0.0
        score += min(observed_volatility * ewma_scale * 2200, 35)
        score += min(spread_bps * 0.65, 16)
        score += min(path_risk * 38, 16)
        score += min((base_centrality + quote_centrality) * 14, 10)
        score += max(0.0, min(((-sentiment * 18) + (macro_stress * 8)) * news_weight, 14))
        score += min(policy_uncertainty * 7 * news_weight, 7)
        score += min(geopolitical_risk * 7 * news_weight, 7)
        score += min(liquidity_risk * 6 * news_weight, 6)
        score += min(commodity_shock * 6 * news_weight, 6)
        score += min(systemic_contagion * 8 * news_weight, 8)
        score += min(fraud_pressure_index * 8 * news_weight, 8)
        score += min(expected_shortfall_95 * 450, 8)
        if observed_volatility < 0.006 and spread_bps < 12:
            score -= 6
        elif observed_volatility < 0.008 and spread_bps < 16:
            score -= 3
        score = min(100.0, score)
        score = max(0.0, score)

        debug: dict[str, Any] = {
            "base_centrality": round(base_centrality, 3),
            "quote_centrality": round(quote_centrality, 3),
            "path_nodes": path_nodes,
            "path_risk": round(path_risk, 3),
            "path_count_considered": path_count_considered,
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
            "historical_volatility": round(historical_volatility, 6),
            "ewma_volatility": round(ewma_volatility, 6),
            "ewma_scale": round(ewma_scale, 3),
            "expected_shortfall_95": round(expected_shortfall_95, 6),
            "spread_bps": round(spread_bps, 2),
            "market_data_source": metadata.get("market_data_source", "manual_or_unknown"),
            "market_data_fetched_at_utc": metadata.get("market_data_fetched_at_utc"),
            "market_last_timestamp": metadata.get("market_last_timestamp"),
            "news_reliability": round(news_reliability, 3),
            "news_weight": round(news_weight, 3),
            "news_source": metadata.get("news_source", "unknown"),
            "news_sample_size": metadata.get("news_sample_size", 0),
            "active_feed_count": metadata.get("active_feed_count", 0),
            "successful_feed_count": metadata.get("successful_feed_count", 0),
            "static_feed_count": metadata.get("static_feed_count", 0),
            "dynamic_feed_count": metadata.get("dynamic_feed_count", 0),
            "ai_news_engine": metadata.get("ai_news_engine", True),
            "gemini_enabled": metadata.get("gemini_enabled", False),
            "gemini_status": metadata.get("gemini_status", "unknown"),
            "gemini_reason": metadata.get("gemini_reason", "unknown"),
            "auto_parameter_tuning": metadata.get("auto_parameter_tuning", False),
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
