"""Streamlit frontend for RiskGuard MVP."""

from __future__ import annotations

from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

import plotly.express as px
import requests
import streamlit as st


API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000/analyze-forex-risk")
API_KEY = os.getenv("BACKEND_API_KEY", "")


def normalize_analyze_url(api_url: str) -> str:
    """Normalize analyze endpoint to forex-focused route."""
    cleaned = api_url.strip()
    if cleaned.endswith("/analyze-transaction"):
        return cleaned[: -len("/analyze-transaction")] + "/analyze-forex-risk"
    return cleaned


def check_backend_health(base_analyze_url: str, api_key: str) -> tuple[bool, str]:
    """Check backend health endpoint based on analyze URL."""
    health_url = normalize_analyze_url(base_analyze_url)
    for suffix in ["/analyze-forex-risk", "/analyze-transaction"]:
        if health_url.endswith(suffix):
            health_url = health_url[: -len(suffix)] + "/health"
            break
    headers = {"X-API-Key": api_key} if api_key else None
    try:
        response = requests.get(health_url, timeout=3, headers=headers)
        if response.status_code == 200:
            return True, health_url
    except requests.RequestException:
        pass
    return False, health_url


def call_analyze_api(api_url: str, payload: dict[str, object], api_key: str) -> dict[str, object]:
    """Call backend analyze API with retries to handle cold starts."""
    last_exception: Exception | None = None
    normalized_url = normalize_analyze_url(api_url)
    headers = {"X-API-Key": api_key} if api_key else None
    for attempt in range(1, 4):
        try:
            response = requests.post(normalized_url, json=payload, timeout=(8, 45), headers=headers)
            if response.status_code in {405, 422} and normalized_url.endswith("/analyze-transaction"):
                fallback_url = normalized_url[: -len("/analyze-transaction")] + "/analyze-forex-risk"
                response = requests.post(fallback_url, json=payload, timeout=(8, 45), headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exception = exc
            if attempt < 3:
                time.sleep(2)
    raise requests.RequestException(
        f"Failed after 3 attempts. Last error: {last_exception}"
    ) from last_exception


def call_top_pairs_api(api_url: str, api_key: str, limit: int = 10) -> dict[str, object]:
    """Fetch daily top-risk forex pairs from ops endpoint with retries."""
    normalized = normalize_analyze_url(api_url)
    base_url = normalized
    for suffix in ["/analyze-forex-risk", "/analyze-transaction"]:
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break

    endpoint = f"{base_url}/ops/top-risk-pairs?limit={limit}"
    headers = {"X-API-Key": api_key} if api_key else None
    last_exception: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.get(endpoint, headers=headers, timeout=(8, 45))
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exception = exc
            if attempt < 3:
                time.sleep(2)
    raise requests.RequestException(
        f"Failed after 3 attempts. Last error: {last_exception}"
    ) from last_exception


st.set_page_config(page_title="RiskGuard MVP", layout="wide")
st.title("RiskGuard MVP — Global Forex Fraud Detection & Risk Scoring")
st.caption(f"Latest UI refresh (UTC): {datetime.now(ZoneInfo('UTC')).isoformat(timespec='seconds')}")

if "forex_history" not in st.session_state:
    st.session_state.forex_history = []

with st.sidebar:
    st.header("API Settings")
    api_url = st.text_input("Analyze endpoint", value=API_URL)
    normalized_api_url = normalize_analyze_url(api_url)
    if normalized_api_url != api_url.strip():
        st.info(f"Legacy endpoint detected; auto-using: {normalized_api_url}")
    api_key = st.text_input("API Key (optional)", value=API_KEY, type="password")
    is_healthy, health_url = check_backend_health(normalized_api_url, api_key)
    if is_healthy:
        st.success(f"Backend OK: {health_url}")
    else:
        st.warning(f"Backend unreachable: {health_url}")
    auto_refresh = st.toggle("Auto refresh leaderboard", value=False)
    refresh_seconds = st.slider("Refresh interval (sec)", min_value=15, max_value=120, value=30, step=5)

st.subheader("Analyze Forex Market Risk")
with st.form("analyze_forex_form"):
    col1, col2 = st.columns(2)
    with col1:
        pair_preset = st.selectbox(
            "Pair Preset",
            options=[
                "USD/MYR",
                "EUR/USD",
                "USD/JPY",
                "USD/INR",
                "USD/KRW",
                "USD/BRL",
                "USD/MXN",
                "XAU/USD",
                "XAG/USD",
                "XBR/USD",
                "XWT/USD",
                "BTC/USD",
                "ETH/USD",
                "SOL/USD",
                "Custom",
            ],
            index=0,
        )
        preset_base, preset_quote = (pair_preset.split("/") if pair_preset != "Custom" else ("USD", "MYR"))
        base_currency = st.text_input("Base Currency", value=preset_base)
        quote_currency = st.text_input("Quote Currency", value=preset_quote)
    with col2:
        st.info("Autonomous AI mode: macro/news parameters are auto-derived from global feeds and market data.")
        timestamp = st.text_input(
            "Timestamp (ISO8601, Malaysia TZ)",
            value=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).isoformat(timespec="seconds"),
        )

    submitted = st.form_submit_button("Analyze Forex Risk")

if submitted:
    payload = {
        "base_currency": base_currency,
        "quote_currency": quote_currency,
        "timestamp": timestamp,
        "metadata": {},
    }
    try:
        with st.spinner("Analyzing forex market risk... (first request may be slower due to backend cold start)"):
            result = call_analyze_api(api_url=normalized_api_url, payload=payload, api_key=api_key)

        st.metric(label="Risk Score", value=f"{result['score']} ({result['status']})")

        st.markdown("### Reasons")
        if result.get("reasons"):
            for reason in result["reasons"]:
                st.write(f"- {reason}")
        else:
            st.write("- No risk flags triggered.")

        st.markdown("### Flags")
        st.write(result.get("flags", []))
        st.markdown("### Hidden Links")
        st.write(result.get("hidden_links", []))
        debug_payload = result.get("debug", {})
        st.markdown("### AI Auto-Tuning Status")
        ai_col_1, ai_col_2, ai_col_3 = st.columns(3)
        ai_col_1.metric("Auto Parameter Tuning", "ON" if debug_payload.get("auto_parameter_tuning") else "OFF")
        ai_col_2.metric(
            "Gemini News Enhance",
            "ON" if debug_payload.get("gemini_enabled") else "OFF",
        )
        ai_col_3.metric(
            "News Feeds",
            f"{debug_payload.get('successful_feed_count', 0)}/{debug_payload.get('active_feed_count', 0)}",
        )
        st.caption(
            f"News source: {debug_payload.get('news_source', 'unknown')} | "
            f"Headlines used: {debug_payload.get('news_sample_size', 0)}"
        )
        market_source = debug_payload.get("market_data_source", "unknown")
        market_ts = debug_payload.get("market_last_timestamp")
        fetched_ts = debug_payload.get("market_data_fetched_at_utc")
        st.caption(
            f"Market source: {market_source} | Market timestamp: {market_ts} | Data fetched at (UTC): {fetched_ts}"
        )
        with st.expander("Debug"):
            st.json(debug_payload)

        event_time = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
        st.session_state.forex_history.append(
            {
                "analyzed_at": event_time,
                "time": event_time.isoformat(timespec="milliseconds"),
                "pair": f"{base_currency.upper()}/{quote_currency.upper()}",
                "score": result["score"],
                "status": result["status"],
                "flags": ", ".join(result.get("flags", [])),
                "hidden_links": " | ".join(result.get("hidden_links", [])),
                "market_source": debug_payload.get("market_data_source"),
                "news_source": debug_payload.get("news_source"),
                "headlines": debug_payload.get("news_sample_size", 0),
                "auto_tuning": bool(debug_payload.get("auto_parameter_tuning")),
                "gemini": bool(debug_payload.get("gemini_enabled")),
            }
        )
    except requests.RequestException as exc:
        st.error(
            "Failed to call API after retries. If using Render free plan, wait 30-60 seconds for cold start and try again. "
            f"Details: {exc}"
        )

st.markdown("## Forex Risk History")
if st.session_state.forex_history:
    chart_data = sorted(st.session_state.forex_history, key=lambda row: row["analyzed_at"])
    point_count = len(chart_data)
    chart_common_args = {
        "data_frame": chart_data,
        "x": "analyzed_at",
        "y": "score",
        "color": "pair",
        "title": "Forex & Commodity & Crypto Risk Score Timeline",
        "hover_data": [
            "time",
            "status",
            "flags",
            "hidden_links",
            "market_source",
            "news_source",
            "headlines",
            "auto_tuning",
            "gemini",
        ],
    }
    if point_count < 2:
        fig = px.scatter(**chart_common_args)
        fig.update_traces(marker=dict(size=10))
    else:
        fig = px.line(**chart_common_args, markers=True)
        fig.update_traces(line=dict(width=3), marker=dict(size=9))
    fig.update_layout(
        height=460,
        yaxis=dict(range=[0, 100], title="Risk Score"),
        xaxis=dict(title="Analysis Time (Asia/Kuala_Lumpur)", tickformat="%Y-%m-%d %H:%M:%S"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")
    if point_count < 2:
        st.caption("Timeline currently has 1 data point; submit more analyses to see a trend line.")
    st.markdown("### Timeline Details")
    st.dataframe(chart_data)
else:
    st.info("No forex risk events yet. Submit analysis above to build timeline.")

st.markdown("## Daily Top Risk Pairs")
if st.button("Refresh Daily Risk Leaderboard"):
    try:
        with st.spinner("Fetching top risk pairs..."):
            top_pairs = call_top_pairs_api(api_url=normalized_api_url, api_key=api_key, limit=10)
        st.caption(f"Scan date: {top_pairs.get('scan_date')}")
        st.caption(f"Latest leaderboard update (UTC): {top_pairs.get('latest_update_utc')}")
        rankings = top_pairs.get("rankings", [])
        if rankings:
            table_rows = [
                {
                    "pair": row.get("pair"),
                    "score": row.get("score"),
                    "status": row.get("status"),
                    "flags": ", ".join(row.get("flags", [])),
                }
                for row in rankings
            ]
            st.dataframe(table_rows)
        else:
            st.info("No rankings available yet.")
    except requests.RequestException as exc:
        st.error(f"Failed to fetch leaderboard: {exc}")

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
