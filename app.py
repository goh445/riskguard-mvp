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

COMMODITY_BASES = {
    "XAU", "XAG", "XPT", "XPD", "XBR", "XWT", "XCU", "XNG", "XRB", "XHO", "XKC", "XSU", "XCC",
    "XCT", "XOJ", "XWH", "XCN", "XSO", "XSM", "XSL", "XLE", "XHE", "XFE", "XAL", "XPB", "XUR",
    "XLI", "XNI", "XZN", "XPL", "XPA", "XSI",
}
CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOG", "DOT", "LTC", "TRX", "BCH", "UNI", "LNK",
    "XLM", "AVA", "MTA", "ICP", "ETC", "EOS", "ALG", "VET", "FIL", "APT", "ARB", "OPM", "NEA",
    "SUI", "TON", "ATM", "INJ", "XMR", "AAV", "MKR", "RND", "GRT", "SNX", "KAS", "PEPE", "SHIB",
    "BONK",
}
STOCK_BASES = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "MA", "UNH", "HD", "PG",
    "XOM", "JNJ", "LLY", "COST", "AVGO", "KO", "PEP", "MRK", "ABBV", "BAC", "WMT", "ORCL", "ADBE",
    "NFLX", "CRM", "AMD", "INTC",
}

FOREX_FLAG_CODES = {
    "USD": "us", "EUR": "eu", "JPY": "jp", "GBP": "gb", "CHF": "ch", "AUD": "au", "NZD": "nz",
    "CAD": "ca", "CNY": "cn", "SGD": "sg", "MYR": "my", "SEK": "se", "NOK": "no", "INR": "in",
    "KRW": "kr", "BRL": "br", "MXN": "mx", "ZAR": "za", "HKD": "hk", "TRY": "tr", "THB": "th",
    "IDR": "id", "PHP": "ph", "VND": "vn", "PLN": "pl", "HUF": "hu", "CZK": "cz", "AED": "ae",
    "SAR": "sa", "QAR": "qa", "ILS": "il", "DKK": "dk", "TWD": "tw", "ARS": "ar", "CLP": "cl",
    "COP": "co",
}

CRYPTO_ICON_CODES = {
    "BTC": "btc", "ETH": "eth", "SOL": "sol", "BNB": "bnb", "XRP": "xrp", "ADA": "ada", "DOG": "doge",
    "DOT": "dot", "LTC": "ltc", "TRX": "trx", "BCH": "bch", "UNI": "uni", "LNK": "link", "XLM": "xlm",
    "AVA": "avax", "MTA": "matic", "ICP": "icp", "ETC": "etc", "EOS": "eos", "ALG": "algo", "VET": "vet",
    "FIL": "fil", "APT": "apt", "ARB": "arb", "OPM": "op", "NEA": "near", "SUI": "sui", "TON": "ton",
    "ATM": "atom", "INJ": "inj", "XMR": "xmr", "AAV": "aave", "MKR": "mkr", "RND": "rndr", "GRT": "grt",
    "SNX": "snx", "KAS": "kas", "PEPE": "pepe", "SHIB": "shib", "BONK": "bonk",
}

COMMODITY_ICON_URLS = {
    "XAU": "https://img.icons8.com/color/96/gold-bars.png",
    "XAG": "https://img.icons8.com/color/96/silver-bars.png",
    "XPT": "https://img.icons8.com/color/96/metal.png",
    "XPD": "https://img.icons8.com/color/96/chemical.png",
    "XBR": "https://img.icons8.com/color/96/oil-industry.png",
    "XWT": "https://img.icons8.com/color/96/oil-industry.png",
    "XCU": "https://img.icons8.com/color/96/copper-ore.png",
    "XNG": "https://img.icons8.com/color/96/gas-industry.png",
    "XRB": "https://img.icons8.com/color/96/gas-station.png",
    "XHO": "https://img.icons8.com/color/96/fuel-cell.png",
    "XKC": "https://img.icons8.com/color/96/coffee-beans.png",
    "XSU": "https://img.icons8.com/color/96/sugar-cube.png",
    "XCC": "https://img.icons8.com/color/96/chocolate-bar.png",
    "XCT": "https://img.icons8.com/color/96/cotton.png",
    "XOJ": "https://img.icons8.com/color/96/orange-juice.png",
    "XWH": "https://img.icons8.com/color/96/wheat.png",
    "XCN": "https://img.icons8.com/color/96/corn.png",
    "XSO": "https://img.icons8.com/color/96/soy.png",
    "XSM": "https://img.icons8.com/color/96/agriculture.png",
    "XSL": "https://img.icons8.com/color/96/olive-oil.png",
    "XLE": "https://img.icons8.com/color/96/cow.png",
    "XHE": "https://img.icons8.com/color/96/pig.png",
    "XFE": "https://img.icons8.com/color/96/cattle.png",
    "XAL": "https://img.icons8.com/color/96/aluminum.png",
    "XPB": "https://img.icons8.com/color/96/rice-bowl.png",
    "XUR": "https://img.icons8.com/color/96/radioactive.png",
    "XLI": "https://img.icons8.com/color/96/lithium-ion-battery.png",
    "XNI": "https://img.icons8.com/color/96/nickel.png",
    "XZN": "https://img.icons8.com/color/96/zinc.png",
    "XPL": "https://img.icons8.com/color/96/metal.png",
    "XPA": "https://img.icons8.com/color/96/metal.png",
    "XSI": "https://img.icons8.com/color/96/silver-bars.png",
}

STOCK_LOGO_DOMAINS = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "GOOGL": "google.com", "AMZN": "amazon.com",
    "NVDA": "nvidia.com", "META": "meta.com", "TSLA": "tesla.com", "JPM": "jpmorganchase.com",
    "V": "visa.com", "MA": "mastercard.com", "UNH": "unitedhealthgroup.com", "HD": "homedepot.com",
    "PG": "pg.com", "XOM": "exxonmobil.com", "JNJ": "jnj.com", "LLY": "lilly.com", "COST": "costco.com",
    "AVGO": "broadcom.com", "KO": "coca-colacompany.com", "PEP": "pepsico.com", "MRK": "merck.com",
    "ABBV": "abbvie.com", "BAC": "bankofamerica.com", "WMT": "walmart.com", "ORCL": "oracle.com",
    "ADBE": "adobe.com", "NFLX": "netflix.com", "CRM": "salesforce.com", "AMD": "amd.com",
    "INTC": "intel.com",
}


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


def pair_category(pair: str) -> str:
    """Classify pair into Forex, Commodity, Crypto, or Stock."""
    try:
        base = pair.split("/")[0].upper()
    except (AttributeError, IndexError):
        return "Forex"
    if base in STOCK_BASES:
        return "Stock"
    if base in COMMODITY_BASES:
        return "Commodity"
    if base in CRYPTO_BASES:
        return "Crypto"
    return "Forex"


def asset_icon_url(asset_code: str) -> str | None:
    """Return URL icon for all asset classes from real image sources."""
    code = asset_code.upper()
    if code in FOREX_FLAG_CODES:
        return f"https://flagcdn.com/w40/{FOREX_FLAG_CODES[code]}.png"
    if code in STOCK_LOGO_DOMAINS:
        return f"https://logo.clearbit.com/{STOCK_LOGO_DOMAINS[code]}"
    if code in CRYPTO_ICON_CODES:
        symbol = CRYPTO_ICON_CODES[code]
        return f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{symbol}.png"
    if code in COMMODITY_ICON_URLS:
        return COMMODITY_ICON_URLS[code]
    return None


st.set_page_config(page_title="RiskGuard MVP", layout="wide")
st.title("RiskGuard MVP — Global Forex Fraud Detection & Risk Scoring")
st.caption(f"Latest UI refresh (UTC): {datetime.now(ZoneInfo('UTC')).isoformat(timespec='seconds')}")
st.info("AI auto-tuning is always ON: dynamic global news discovery + market data are automatically used in every analysis.")

if "forex_history" not in st.session_state:
    st.session_state.forex_history = []
if "leaderboard_cache" not in st.session_state:
    st.session_state.leaderboard_cache = None
if "asset_filter" not in st.session_state:
    st.session_state.asset_filter = "All"

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

tab_board, tab_analyze, tab_history = st.tabs(
    ["Live Multi-Asset Board", "Analyze One Asset Pair", "Risk History Timeline"]
)

with tab_board:
    st.subheader("Top Risk Board (Forex + Commodity + Crypto + Stocks)")
    refresh_now = st.button("Refresh Board", type="primary")
    if refresh_now or st.session_state.leaderboard_cache is None:
        try:
            with st.spinner("Loading multi-asset risk board..."):
                st.session_state.leaderboard_cache = call_top_pairs_api(
                    api_url=normalized_api_url,
                    api_key=api_key,
                    limit=200,
                )
        except requests.RequestException as exc:
            st.error(f"Failed to fetch leaderboard: {exc}")

    board = st.session_state.leaderboard_cache or {}
    st.caption(f"Scan date: {board.get('scan_date')}")
    st.caption(f"Latest leaderboard update (UTC): {board.get('latest_update_utc')}")
    rankings = board.get("rankings", [])
    if rankings:
        rows = []
        for row in rankings:
            pair = str(row.get("pair", ""))
            base, quote = pair.split("/") if "/" in pair else (pair, "")
            rows.append(
                {
                    "base_icon": asset_icon_url(base),
                    "quote_icon": asset_icon_url(quote),
                    "category": pair_category(pair),
                    "base_code": base,
                    "quote_code": quote,
                    "pair": pair,
                    "score": row.get("score"),
                    "status": row.get("status"),
                    "flags": ", ".join(row.get("flags", [])),
                }
            )

        filter_col_1, filter_col_2, filter_col_3, filter_col_4, filter_col_5 = st.columns(5)
        if filter_col_1.button("All", use_container_width=True):
            st.session_state.asset_filter = "All"
        if filter_col_2.button("Forex", use_container_width=True):
            st.session_state.asset_filter = "Forex"
        if filter_col_3.button("Commodity", use_container_width=True):
            st.session_state.asset_filter = "Commodity"
        if filter_col_4.button("Crypto", use_container_width=True):
            st.session_state.asset_filter = "Crypto"
        if filter_col_5.button("Stock", use_container_width=True):
            st.session_state.asset_filter = "Stock"

        filtered_rows = (
            rows
            if st.session_state.asset_filter == "All"
            else [row for row in rows if row["category"] == st.session_state.asset_filter]
        )

        total_count = len(filtered_rows)
        forex_count = sum(1 for row in filtered_rows if row["category"] == "Forex")
        commodity_count = sum(1 for row in filtered_rows if row["category"] == "Commodity")
        crypto_count = sum(1 for row in filtered_rows if row["category"] == "Crypto")
        stock_count = sum(1 for row in filtered_rows if row["category"] == "Stock")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Assets Shown", total_count, st.session_state.asset_filter)
        c2.metric("Forex", forex_count)
        c3.metric("Commodity", commodity_count)
        c4.metric("Crypto", crypto_count)
        c5.metric("Stock", stock_count)

        st.caption(f"Showing {len(filtered_rows)} assets in current filter")
        st.dataframe(
            filtered_rows,
            use_container_width=True,
            column_config={
                "base_icon": st.column_config.ImageColumn("Base"),
                "quote_icon": st.column_config.ImageColumn("Quote"),
            },
        )
    else:
        st.info("No rankings available yet.")

with tab_analyze:
    st.subheader("Analyze Pair Risk")
    with st.form("analyze_forex_form"):
        col1, col2 = st.columns(2)
        with col1:
            pair_preset = st.selectbox(
                "Pair Preset",
                options=[
                    "USD/MYR",
                    "EUR/USD",
                    "USD/JPY",
                    "GBP/USD",
                    "USD/CHF",
                    "AUD/USD",
                    "NZD/USD",
                    "USD/CAD",
                    "USD/INR",
                    "USD/KRW",
                    "USD/BRL",
                    "USD/MXN",
                    "USD/ZAR",
                    "USD/TRY",
                    "USD/THB",
                    "USD/IDR",
                    "USD/PHP",
                    "USD/PLN",
                    "USD/HUF",
                    "USD/CZK",
                    "USD/AED",
                    "USD/SAR",
                    "USD/TWD",
                    "XAU/USD",
                    "XAG/USD",
                    "XPT/USD",
                    "XPD/USD",
                    "XBR/USD",
                    "XWT/USD",
                    "XCU/USD",
                    "XNG/USD",
                    "XKC/USD",
                    "XWH/USD",
                    "XCN/USD",
                    "XSO/USD",
                    "BTC/USD",
                    "ETH/USD",
                    "SOL/USD",
                    "BNB/USD",
                    "XRP/USD",
                    "ADA/USD",
                    "DOT/USD",
                    "LTC/USD",
                    "TRX/USD",
                    "UNI/USD",
                    "SUI/USD",
                    "XMR/USD",
                    "AAV/USD",
                    "MKR/USD",
                    "RND/USD",
                    "GRT/USD",
                    "SNX/USD",
                    "KAS/USD",
                    "PEPE/USD",
                    "SHIB/USD",
                    "BONK/USD",
                    "AAPL/USD",
                    "MSFT/USD",
                    "GOOGL/USD",
                    "AMZN/USD",
                    "NVDA/USD",
                    "META/USD",
                    "TSLA/USD",
                    "JPM/USD",
                    "V/USD",
                    "MA/USD",
                    "UNH/USD",
                    "HD/USD",
                    "PG/USD",
                    "XOM/USD",
                    "JNJ/USD",
                    "LLY/USD",
                    "COST/USD",
                    "AVGO/USD",
                    "KO/USD",
                    "PEP/USD",
                    "MRK/USD",
                    "ABBV/USD",
                    "BAC/USD",
                    "WMT/USD",
                    "ORCL/USD",
                    "ADBE/USD",
                    "NFLX/USD",
                    "CRM/USD",
                    "AMD/USD",
                    "INTC/USD",
                    "Custom",
                ],
                index=0,
            )
            preset_base, preset_quote = (pair_preset.split("/") if pair_preset != "Custom" else ("USD", "MYR"))
            base_currency = st.text_input("Base Currency", value=preset_base)
            quote_currency = st.text_input("Quote Currency", value=preset_quote)
        with col2:
            timestamp = st.text_input(
                "Timestamp (ISO8601, Malaysia TZ)",
                value=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).isoformat(timespec="seconds"),
            )
            st.caption("No manual AI switch needed. Auto-tuning always runs in backend.")

        submitted = st.form_submit_button("Analyze Forex Risk")

    if submitted:
        payload = {
            "base_currency": base_currency,
            "quote_currency": quote_currency,
            "timestamp": timestamp,
            "metadata": {},
        }
        progress_text = st.empty()
        progress = st.progress(0)
        try:
            progress_text.info("Step 1/4 · Preparing market and news signal pipeline...")
            progress.progress(20)
            time.sleep(0.15)

            progress_text.info("Step 2/4 · Pulling global market context...")
            progress.progress(45)
            time.sleep(0.15)

            progress_text.info("Step 3/4 · Running graph contagion analysis...")
            progress.progress(70)
            result = call_analyze_api(api_url=normalized_api_url, payload=payload, api_key=api_key)

            progress_text.info("Step 4/4 · Finalizing risk score and insights...")
            progress.progress(100)
            time.sleep(0.1)
            progress_text.success("Analysis complete")

            headline_1, headline_2, headline_3 = st.columns(3)
            headline_1.metric("Risk Score", f"{result['score']}")
            headline_2.metric("Risk Status", result["status"])
            headline_3.metric("Pair", f"{base_currency.upper()}/{quote_currency.upper()}")

            debug_payload = result.get("debug", {})
            ai_col_1, ai_col_2, ai_col_3 = st.columns(3)
            ai_col_1.metric("Auto Parameter Tuning", "ON")
            ai_col_2.metric("AI News Engine", "ON" if debug_payload.get("ai_news_engine", True) else "OFF")
            ai_col_3.metric(
                "LLM Boost (Gemini)",
                "ON" if debug_payload.get("gemini_enabled") else "OFF",
            )
            st.caption(
                f"News feeds reached: {debug_payload.get('successful_feed_count', 0)}/{debug_payload.get('active_feed_count', 0)} "
                f"(static {debug_payload.get('static_feed_count', 0)} + dynamic {debug_payload.get('dynamic_feed_count', 0)})"
            )
            st.caption(
                f"News source: {debug_payload.get('news_source', 'unknown')} | "
                f"Headlines used: {debug_payload.get('news_sample_size', 0)}"
            )
            st.caption(
                f"Gemini status: {debug_payload.get('gemini_status', 'unknown')} | "
                f"Reason: {debug_payload.get('gemini_reason', 'unknown')}"
            )

            info_col_1, info_col_2 = st.columns(2)
            with info_col_1:
                st.markdown("### Reasons")
                if result.get("reasons"):
                    for reason in result["reasons"]:
                        st.write(f"- {reason}")
                else:
                    st.write("- No risk flags triggered.")
            with info_col_2:
                st.markdown("### Signal Flags")
                st.write(result.get("flags", []))
                st.markdown("### Hidden Links")
                st.write(result.get("hidden_links", []))

            with st.expander("Detailed Debug Data"):
                st.json(debug_payload)

            event_time = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
            st.session_state.forex_history.append(
                {
                    "analyzed_at": event_time,
                    "time": event_time.isoformat(timespec="milliseconds"),
                    "pair": f"{base_currency.upper()}/{quote_currency.upper()}",
                    "category": pair_category(f"{base_currency.upper()}/{quote_currency.upper()}"),
                    "score": result["score"],
                    "status": result["status"],
                    "flags": ", ".join(result.get("flags", [])),
                    "hidden_links": " | ".join(result.get("hidden_links", [])),
                    "market_source": debug_payload.get("market_data_source"),
                    "news_source": debug_payload.get("news_source"),
                    "headlines": debug_payload.get("news_sample_size", 0),
                    "auto_tuning": True,
                    "gemini": bool(debug_payload.get("gemini_enabled")),
                }
            )
        except requests.RequestException as exc:
            progress.progress(100)
            progress_text.error(
                "Analysis request failed. If using Render free plan, wait 30-60 seconds for cold start and try again. "
                f"Details: {exc}"
            )

with tab_history:
    st.subheader("Forex Risk History")
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
                "category",
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
        st.plotly_chart(fig, use_container_width=True)
        if point_count < 2:
            st.caption("Timeline currently has 1 data point; submit more analyses to see a trend line.")
        st.dataframe(chart_data, use_container_width=True)
    else:
        st.info("No forex risk events yet. Submit analysis to build timeline.")

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
