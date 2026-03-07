"""Stress scenario regression tests for extreme market environments."""

from __future__ import annotations

from datetime import datetime

import pytest

from forex_graph_engine import ForexGraphRiskEngine
from models import ForexRiskRequest


def _request_payload(
    *,
    base: str,
    quote: str,
    observed_volatility: float,
    spread_bps: float,
    news_sentiment: float,
    macro_stress: float,
    policy_uncertainty: float,
    geopolitical_risk: float,
    liquidity_risk: float,
    systemic_contagion: float,
    fraud_pressure_index: float,
    expected_shortfall_95: float,
    ewma_volatility: float,
) -> ForexRiskRequest:
    return ForexRiskRequest(
        base_currency=base,
        quote_currency=quote,
        observed_volatility=observed_volatility,
        spread_bps=spread_bps,
        timestamp=datetime.fromisoformat("2026-03-07T12:00:00+08:00"),
        metadata={
            "news_sentiment": news_sentiment,
            "macro_stress": macro_stress,
            "policy_uncertainty": policy_uncertainty,
            "geopolitical_risk": geopolitical_risk,
            "liquidity_risk": liquidity_risk,
            "systemic_contagion": systemic_contagion,
            "fraud_pressure_index": fraud_pressure_index,
            "expected_shortfall_95": expected_shortfall_95,
            "ewma_volatility": ewma_volatility,
            "market_data_source": "stress-test",
            "news_source": "stress-test",
            "active_feed_count": 10,
            "successful_feed_count": 10,
        },
    )


@pytest.mark.parametrize(
    "name,scenario_request,expected_min_score,expected_status",
    [
        (
            "2008_global_financial_crisis",
            _request_payload(
                base="USD",
                quote="JPY",
                observed_volatility=0.038,
                spread_bps=38,
                news_sentiment=-0.85,
                macro_stress=0.95,
                policy_uncertainty=0.8,
                geopolitical_risk=0.55,
                liquidity_risk=0.9,
                systemic_contagion=0.9,
                fraud_pressure_index=0.7,
                expected_shortfall_95=0.03,
                ewma_volatility=0.045,
            ),
            80,
            "High",
        ),
        (
            "asian_financial_crisis",
            _request_payload(
                base="USD",
                quote="MYR",
                observed_volatility=0.034,
                spread_bps=34,
                news_sentiment=-0.78,
                macro_stress=0.9,
                policy_uncertainty=0.72,
                geopolitical_risk=0.45,
                liquidity_risk=0.82,
                systemic_contagion=0.88,
                fraud_pressure_index=0.62,
                expected_shortfall_95=0.026,
                ewma_volatility=0.041,
            ),
            75,
            "High",
        ),
        (
            "eurozone_debt_crisis",
            _request_payload(
                base="EUR",
                quote="USD",
                observed_volatility=0.024,
                spread_bps=24,
                news_sentiment=-0.58,
                macro_stress=0.75,
                policy_uncertainty=0.84,
                geopolitical_risk=0.4,
                liquidity_risk=0.66,
                systemic_contagion=0.7,
                fraud_pressure_index=0.52,
                expected_shortfall_95=0.018,
                ewma_volatility=0.029,
            ),
            65,
            "Medium",
        ),
        (
            "covid_liquidity_shock",
            _request_payload(
                base="BTC",
                quote="USD",
                observed_volatility=0.05,
                spread_bps=42,
                news_sentiment=-0.8,
                macro_stress=0.92,
                policy_uncertainty=0.62,
                geopolitical_risk=0.48,
                liquidity_risk=0.95,
                systemic_contagion=0.87,
                fraud_pressure_index=0.68,
                expected_shortfall_95=0.042,
                ewma_volatility=0.059,
            ),
            85,
            "High",
        ),
        (
            "global_rate_hike_shock",
            _request_payload(
                base="USD",
                quote="EUR",
                observed_volatility=0.02,
                spread_bps=21,
                news_sentiment=-0.44,
                macro_stress=0.68,
                policy_uncertainty=0.72,
                geopolitical_risk=0.32,
                liquidity_risk=0.58,
                systemic_contagion=0.6,
                fraud_pressure_index=0.44,
                expected_shortfall_95=0.015,
                ewma_volatility=0.024,
            ),
            55,
            "Medium",
        ),
        (
            "commodity_supply_shock",
            _request_payload(
                base="XBR",
                quote="USD",
                observed_volatility=0.03,
                spread_bps=29,
                news_sentiment=-0.62,
                macro_stress=0.8,
                policy_uncertainty=0.56,
                geopolitical_risk=0.66,
                liquidity_risk=0.64,
                systemic_contagion=0.72,
                fraud_pressure_index=0.5,
                expected_shortfall_95=0.022,
                ewma_volatility=0.035,
            ),
            70,
            "High",
        ),
    ],
)
def test_extreme_market_scenarios(
    name: str,
    scenario_request: ForexRiskRequest,
    expected_min_score: int,
    expected_status: str,
) -> None:
    """Validate that known extreme scenarios trigger expected elevated risk output."""
    engine = ForexGraphRiskEngine()
    result = engine.analyze(scenario_request)

    assert result.score >= expected_min_score, f"{name} score too low: {result.score}"
    if expected_status == "High":
        assert result.status == "High"
    else:
        assert result.status in {"Medium", "High"}


def test_stress_monotonicity_vs_baseline() -> None:
    """Ensure stress amplification increases score compared with calm baseline."""
    engine = ForexGraphRiskEngine()

    baseline = _request_payload(
        base="USD",
        quote="JPY",
        observed_volatility=0.008,
        spread_bps=9,
        news_sentiment=0.1,
        macro_stress=0.2,
        policy_uncertainty=0.2,
        geopolitical_risk=0.15,
        liquidity_risk=0.15,
        systemic_contagion=0.2,
        fraud_pressure_index=0.15,
        expected_shortfall_95=0.004,
        ewma_volatility=0.008,
    )
    stressed = _request_payload(
        base="USD",
        quote="JPY",
        observed_volatility=0.028,
        spread_bps=27,
        news_sentiment=-0.62,
        macro_stress=0.82,
        policy_uncertainty=0.7,
        geopolitical_risk=0.52,
        liquidity_risk=0.7,
        systemic_contagion=0.76,
        fraud_pressure_index=0.58,
        expected_shortfall_95=0.021,
        ewma_volatility=0.033,
    )

    baseline_result = engine.analyze(baseline)
    stressed_result = engine.analyze(stressed)

    assert stressed_result.score > baseline_result.score
    assert stressed_result.status in {"Medium", "High"}


def test_tail_loss_flag_triggers_under_extreme_es() -> None:
    """Expected shortfall tail-risk flag should trigger above threshold."""
    engine = ForexGraphRiskEngine()
    request = _request_payload(
        base="EUR",
        quote="USD",
        observed_volatility=0.016,
        spread_bps=14,
        news_sentiment=-0.3,
        macro_stress=0.52,
        policy_uncertainty=0.5,
        geopolitical_risk=0.3,
        liquidity_risk=0.35,
        systemic_contagion=0.4,
        fraud_pressure_index=0.36,
        expected_shortfall_95=0.02,
        ewma_volatility=0.019,
    )

    result = engine.analyze(request)

    assert "tail_loss_stress" in result.flags
    assert result.debug and result.debug.get("expected_shortfall_95", 0) >= 0.02
