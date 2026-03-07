"""Streamlit frontend for RiskGuard MVP."""

from __future__ import annotations

from datetime import datetime
import json
import os
import re
import time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000/analyze-forex-risk")
API_KEY = os.getenv("BACKEND_API_KEY", "")
UI_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
UI_GEMINI_MODEL = os.getenv("GEMINI_SUMMARY_MODEL", "gemini-2.5-flash")

USAGE_GUIDE_LAST_UPDATED = "2026-03-07"
USAGE_GUIDE_CHANGELOG = [
    "Moved stress score interpretation into tooltip-based help icons for base_score/delta/stressed_score and removed verbose read columns.",
    "Expanded stress test to evidence-based global macro scenarios with explicit methodology and interpretation guidance.",
    "Added AI Assurance tab (NIST AI RMF + OECD self-assessment template and downloadable report).",
    "Added API subscription mode with webhook endpoint management and test trigger.",
    "Added stress test simulator and risk heat map for portfolio impact demonstration.",
    "Added tamper-evident audit trail view with hash-chain fields (prev_hash/entry_hash).",
    "Added ES/EWMA/AML metrics and interactive risk radar with hover explanations.",
    "Added low-confidence asset confirmation flow to avoid analyzing invalid symbols directly.",
]

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
    """Fetch top-risk pairs with timeout-tolerant retries and degraded fallback."""
    normalized = normalize_analyze_url(api_url)
    base_url = normalized
    for suffix in ["/analyze-forex-risk", "/analyze-transaction"]:
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break

    headers = {"X-API-Key": api_key} if api_key else None
    last_exception: Exception | None = None

    request_plan = [
        (limit, (10, 90)),
        (min(limit, 100), (10, 75)),
        (min(limit, 50), (10, 60)),
    ]

    for planned_limit, timeout_value in request_plan:
        endpoint = f"{base_url}/ops/top-risk-pairs?limit={planned_limit}&force_refresh=false"
        try:
            response = requests.get(endpoint, headers=headers, timeout=timeout_value)
            response.raise_for_status()
            payload = response.json()
            payload["requested_limit"] = planned_limit
            return payload
        except requests.RequestException as exc:
            last_exception = exc
            time.sleep(1)

    raise requests.RequestException(
        f"Failed after 3 attempts. Last error: {last_exception}"
    ) from last_exception


def _base_api_url(api_url: str) -> str:
    normalized = normalize_analyze_url(api_url)
    for suffix in ["/analyze-forex-risk", "/analyze-transaction"]:
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def call_ops_get(api_url: str, api_key: str, path: str, timeout: tuple[int, int] = (8, 45)) -> dict[str, object]:
    """Call one backend GET endpoint and return JSON payload."""
    endpoint = f"{_base_api_url(api_url)}{path}"
    headers = {"X-API-Key": api_key} if api_key else None
    response = requests.get(endpoint, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def call_ops_post(
    api_url: str,
    api_key: str,
    path: str,
    payload: dict[str, object],
    timeout: tuple[int, int] = (8, 45),
) -> dict[str, object]:
    """Call one backend POST endpoint and return JSON payload."""
    endpoint = f"{_base_api_url(api_url)}{path}"
    headers = {"X-API-Key": api_key} if api_key else None
    response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


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


def _yahoo_search_symbol(query: str) -> dict[str, object] | None:
    """Find best Yahoo Finance match for a symbol/name query."""
    try:
        response = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": query, "quotesCount": 8, "newsCount": 0},
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()
        quotes = payload.get("quotes", [])
        if not isinstance(quotes, list):
            return None

        exact = [item for item in quotes if str(item.get("symbol", "")).upper() == query.upper()]
        preferred = exact or quotes
        best = next((item for item in preferred if item.get("quoteType") in {"EQUITY", "ETF", "CRYPTOCURRENCY"}), None)
        if best:
            return best
        return preferred[0] if preferred else None
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def _yahoo_trend_text(symbol: str) -> str | None:
    """Get simple 1-month trend text from Yahoo chart."""
    try:
        response = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": "1mo", "interval": "1d"},
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()
        result = payload.get("chart", {}).get("result", [])
        if not result:
            return None
        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        valid_closes = [float(value) for value in closes if value is not None]
        if len(valid_closes) < 2:
            return None
        first_close = valid_closes[0]
        last_close = valid_closes[-1]
        if first_close <= 0:
            return None
        pct = ((last_close - first_close) / first_close) * 100
        direction = "uptrend" if pct >= 0 else "downtrend"
        return f"1M price trend: {direction}, {pct:+.2f}%"
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return None


def _coingecko_search_symbol(query: str) -> dict[str, object] | None:
    """Find best CoinGecko match for crypto symbol/name."""
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/search",
            params={"query": query},
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()
        coins = payload.get("coins", [])
        if not isinstance(coins, list) or not coins:
            return None

        exact = [item for item in coins if str(item.get("symbol", "")).upper() == query.upper()]
        return (exact[0] if exact else coins[0])
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def _coingecko_trend_text(coin_id: str) -> str | None:
    """Get 24h trend text for a CoinGecko asset."""
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json().get(coin_id, {})
        change_24h = payload.get("usd_24h_change")
        if change_24h is None:
            return None
        direction = "uptrend" if float(change_24h) >= 0 else "downtrend"
        return f"24h price trend: {direction}, {float(change_24h):+.2f}%"
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def resolve_asset_profile(base_code: str, quote_code: str) -> dict[str, str | float | bool]:
    """Resolve best-effort asset identity/background/trend for AI summary context."""
    base = base_code.upper().strip()
    quote = quote_code.upper().strip()

    commodity_names = {
        "XAU": "Gold", "XAG": "Silver", "XPT": "Platinum", "XPD": "Palladium", "XBR": "Brent Crude",
        "XWT": "WTI Crude", "XNG": "Natural Gas", "XCU": "Copper", "XWH": "Wheat", "XCN": "Corn",
        "XKC": "Coffee", "XSO": "Soybean",
    }

    if base in STOCK_BASES:
        symbol = base
        trend = _yahoo_trend_text(symbol) or "Recent trend unavailable"
        return {
            "detected_category": "Stock",
            "asset_name": symbol,
            "resolved_symbol": symbol,
            "background": "This is an equity ticker representing a listed company stock.",
            "trend": trend,
            "resolution_source": "builtin:stock",
            "confidence": 0.99,
            "needs_confirmation": False,
        }

    if base in COMMODITY_BASES:
        symbol = base
        mapped_name = commodity_names.get(base, base)
        trend = _yahoo_trend_text(f"{base}=F") or "Recent trend unavailable"
        return {
            "detected_category": "Commodity",
            "asset_name": mapped_name,
            "resolved_symbol": symbol,
            "background": "This is a commodity market instrument, typically driven by supply-demand, inventory, and macro factors.",
            "trend": trend,
            "resolution_source": "builtin:commodity",
            "confidence": 0.99,
            "needs_confirmation": False,
        }

    if base in CRYPTO_BASES:
        trend = _yahoo_trend_text(f"{base}-USD") or "Recent trend unavailable"
        return {
            "detected_category": "Crypto",
            "asset_name": base,
            "resolved_symbol": base,
            "background": "This is a cryptocurrency asset traded continuously with sentiment and liquidity sensitivity.",
            "trend": trend,
            "resolution_source": "builtin:crypto",
            "confidence": 0.99,
            "needs_confirmation": False,
        }

    if base in FOREX_FLAG_CODES and quote in FOREX_FLAG_CODES:
        return {
            "detected_category": "Forex",
            "asset_name": f"{base}/{quote}",
            "resolved_symbol": f"{base}/{quote}",
            "background": "This is a foreign-exchange pair representing relative value between two fiat currencies.",
            "trend": "FX trend context is derived from live rate and volatility signals.",
            "resolution_source": "builtin:forex",
            "confidence": 0.98,
            "needs_confirmation": False,
        }

    yahoo_match = _yahoo_search_symbol(base)
    if yahoo_match:
        quote_type = str(yahoo_match.get("quoteType", "")).upper()
        resolved_symbol = str(yahoo_match.get("symbol", base)).upper()
        shortname = str(yahoo_match.get("shortname", resolved_symbol))
        longname = str(yahoo_match.get("longname", shortname))
        trend = _yahoo_trend_text(resolved_symbol) or "Recent trend unavailable"
        if quote_type in {"EQUITY", "ETF"}:
            category = "Stock"
            background = f"{longname} is a publicly traded company/instrument represented by ticker {resolved_symbol}."
            confidence = 0.92 if resolved_symbol == base else 0.76
        elif quote_type == "CRYPTOCURRENCY":
            category = "Crypto"
            background = f"{longname} is a crypto asset represented by symbol {resolved_symbol}."
            confidence = 0.9 if resolved_symbol == base else 0.72
        else:
            category = "Forex"
            background = f"{longname} is the closest market instrument match for input symbol {base}."
            confidence = 0.62
        return {
            "detected_category": category,
            "asset_name": longname,
            "resolved_symbol": resolved_symbol,
            "background": background,
            "trend": trend,
            "resolution_source": "yahoo_search",
            "confidence": round(confidence, 2),
            "needs_confirmation": confidence < 0.8,
        }

    coin_match = _coingecko_search_symbol(base)
    if coin_match:
        coin_id = str(coin_match.get("id", ""))
        coin_name = str(coin_match.get("name", base))
        coin_symbol = str(coin_match.get("symbol", base)).upper()
        trend = _coingecko_trend_text(coin_id) or "Recent trend unavailable"
        return {
            "detected_category": "Crypto",
            "asset_name": coin_name,
            "resolved_symbol": coin_symbol,
            "background": f"{coin_name} is the closest crypto match for input symbol {base}.",
            "trend": trend,
            "resolution_source": "coingecko_search",
            "confidence": 0.74 if coin_symbol != base else 0.88,
            "needs_confirmation": coin_symbol != base,
        }

    return {
        "detected_category": pair_category(f"{base}/{quote}"),
        "asset_name": base,
        "resolved_symbol": base,
        "background": f"No exact market match found online; using {base} as provided input for risk interpretation.",
        "trend": "Recent trend unavailable",
        "resolution_source": "fallback:input",
        "confidence": 0.2,
        "needs_confirmation": True,
    }


def auto_adjust_asset_by_category(base_code: str, category: str) -> str:
    """Auto-adjust user-entered asset code to a valid symbol for selected category."""
    base = base_code.upper().strip()
    defaults = {
        "Forex": "EUR",
        "Stock": "AAPL",
        "Commodity": "XAU",
        "Crypto": "BTC",
    }

    if category == "Forex":
        return base if base in FOREX_FLAG_CODES else defaults["Forex"]
    if category == "Stock":
        if base in STOCK_BASES:
            return base
        yahoo_match = _yahoo_search_symbol(base)
        if yahoo_match and str(yahoo_match.get("quoteType", "")).upper() in {"EQUITY", "ETF"}:
            symbol = str(yahoo_match.get("symbol", defaults["Stock"])).upper()
            return symbol if symbol in STOCK_BASES or len(symbol) <= 10 else defaults["Stock"]
        return defaults["Stock"]
    if category == "Commodity":
        return base if base in COMMODITY_BASES else defaults["Commodity"]
    if category == "Crypto":
        if base in CRYPTO_BASES:
            return base
        coin_match = _coingecko_search_symbol(base)
        if coin_match:
            symbol = str(coin_match.get("symbol", defaults["Crypto"])).upper()
            return symbol if len(symbol) <= 10 else defaults["Crypto"]
        return defaults["Crypto"]
    return base


def _extract_json_object(text: str) -> str | None:
    """Extract first JSON object from model output."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    return match.group(0)


def _build_fallback_summary_and_strategy(pair: str, result: dict[str, object]) -> tuple[str, list[str]]:
    """Fallback summary and strategy when LLM generation is unavailable."""
    debug = result.get("debug", {}) if isinstance(result.get("debug", {}), dict) else {}
    score = int(result.get("score", 0))
    status = str(result.get("status", "Unknown"))
    base, quote = pair.split("/") if "/" in pair else (pair, "USD")

    sentiment = float(debug.get("news_sentiment", 0.0) or 0.0)
    macro_stress = float(debug.get("macro_stress", 0.0) or 0.0)
    volatility = float(debug.get("observed_volatility", 0.0) or 0.0)
    spread_bps = float(debug.get("spread_bps", 0.0) or 0.0)
    gemini_status = str(debug.get("gemini_status", "unknown"))
    news_source = str(debug.get("news_source", "unknown"))
    category = pair_category(pair)

    if score >= 75:
        regime = "high-risk regime"
    elif score >= 45:
        regime = "elevated-risk regime"
    else:
        regime = "controlled-risk regime"

    category_explanation = {
        "Forex": (
            "Forex means one currency priced against another (base/quote). "
            "Your selected pair shows how many quote-currency units are needed for 1 unit of the base currency."
        ),
        "Commodity": (
            "Commodity pairs track real-world raw materials (like gold, oil, gas, metals, or crops), "
            "usually quoted versus USD."
        ),
        "Crypto": (
            "Crypto pairs represent digital assets traded against a quote currency, with higher 24/7 volatility "
            "and stronger sentiment-driven moves."
        ),
        "Stock": (
            "Stock pairs represent listed company shares benchmarked versus USD in this risk model, "
            "so equity news and earnings events are key drivers."
        ),
    }

    summary = (
        f"你当前选择的是 {pair}（{category}），即 {base}/{quote}。{category_explanation.get(category, '')} "
        f"当前风险评分为 {score}（{status}），处于 {regime}。"
        f"宏观与新闻压力为 {macro_stress:.2f}，新闻情绪为 {sentiment:.2f}，"
        f"市场微观结构显示波动率 {volatility:.4f}、点差 {spread_bps:.2f} bps。"
        f"新闻来源为 {news_source}，Gemini 状态为 {gemini_status}。"
    )

    strategies: list[str] = []
    if score >= 75:
        strategies.append("Regime plan: defensive mode; reduce position size and avoid aggressive entries until score cools below 70.")
        strategies.append("Entry timing: wait for post-news stabilization (at least one full candle close after major release) and narrowing spread before entry.")
        strategies.append("Execution rule: avoid entries when spread is expanding rapidly; prefer limit/conditional orders near validated support-resistance retests.")
        strategies.append("Risk control: use tighter stop-loss (recent swing-based) and partial take-profit on first favorable impulse.")
        strategies.append("Invalidation: exit quickly if volatility spikes again and price closes beyond your invalidation level.")
    elif score >= 45:
        strategies.append("Regime plan: selective mode with smaller leverage and staggered entries.")
        strategies.append("Entry timing: prioritize pullback/retest entries after trend confirmation, not initial breakout chase.")
        strategies.append("Execution rule: place conditional orders around key levels and avoid opening new trades right before high-impact events.")
        strategies.append("Risk control: scale in with 2-3 tranches and trail stop once trade reaches initial reward target.")
        strategies.append("Invalidation: if spread or realized volatility expands materially, reduce exposure immediately.")
    else:
        strategies.append("Regime plan: baseline mode with standard risk limits and periodic monitoring.")
        strategies.append("Entry timing: enter on planned setup confirmation (breakout-hold or pullback-hold) during liquid session hours.")
        strategies.append("Execution rule: scale in gradually instead of all-at-once to improve average execution quality.")
        strategies.append("Risk control: keep pre-defined stop-loss and target levels with minimum reward-to-risk discipline.")
        strategies.append("Invalidation: close or hedge if a major surprise event shifts the pair into elevated-risk regime.")

    if category == "Stock":
        strategies.append("Stock-specific timing: avoid fresh entries just before earnings/FOMC; best entries are after volatility settles and direction confirms.")
        strategies.append("Stock-specific check: validate sector breadth and index trend before adding single-name exposure.")
    elif category == "Crypto":
        strategies.append("Crypto-specific timing: avoid thin-liquidity hours; entries are safer after funding/liquidation stress normalizes.")
        strategies.append("Crypto-specific check: prioritize deep-liquidity venues and avoid oversized overnight/weekend risk.")
    elif category == "Commodity":
        strategies.append("Commodity-specific timing: align entries with inventory data windows and major energy/macro headlines.")
        strategies.append("Commodity-specific check: confirm term-structure/news direction before adding to winners.")
    else:
        strategies.append("FX-specific timing: avoid entries right into central-bank speeches; favor post-announcement confirmation moves.")
        strategies.append("FX-specific check: monitor relative rate expectations and DXY trend alignment.")

    return summary, strategies


def build_ai_summary_and_strategy(
    pair: str,
    result: dict[str, object],
    gemini_api_key: str,
    gemini_model: str,
    asset_profile: dict[str, str] | None = None,
) -> tuple[str, list[str], str]:
    """Generate complete AI summary and strategy via Gemini, fallback when unavailable."""
    debug = result.get("debug", {}) if isinstance(result.get("debug", {}), dict) else {}
    score = int(result.get("score", 0))
    status = str(result.get("status", "Unknown"))
    category = pair_category(pair)
    base, quote = pair.split("/") if "/" in pair else (pair, "USD")
    resolved_profile = asset_profile or resolve_asset_profile(base, quote)
    resolved_category = resolved_profile.get("detected_category", category)

    if not gemini_api_key:
        summary, strategy = _build_fallback_summary_and_strategy(pair, result)
        return summary, strategy, "fallback:no_api_key"

    context = {
        "pair": pair,
        "category": resolved_category,
        "base": base,
        "quote": quote,
        "asset_profile": resolved_profile,
        "score": score,
        "status": status,
        "debug": {
            "news_sentiment": debug.get("news_sentiment", 0.0),
            "macro_stress": debug.get("macro_stress", 0.0),
            "observed_volatility": debug.get("observed_volatility", 0.0),
            "spread_bps": debug.get("spread_bps", 0.0),
            "news_source": debug.get("news_source", "unknown"),
            "gemini_status": debug.get("gemini_status", "unknown"),
            "reasons": result.get("reasons", []),
            "flags": result.get("flags", []),
            "hidden_links": result.get("hidden_links", []),
        },
    }

    prompt = (
        "你是专业多资产风险分析师。请仅输出JSON对象，不要Markdown，不要多余解释。"
        "JSON格式必须是: "
        '{"summary":"...","investment_strategy":["...","...","...","...","..."]}. '
        "要求: "
        "1) summary必须是完整自然语言段落，不要固定前缀，必须先讲清楚这个asset具体是什么；"
        "若为股票，必须包含公司背景和近期走势；若为商品/加密/外汇，也必须分别说明该资产本质与近期走势；"
        "若用户输入的symbol不在内置库，必须依据asset_profile中的解析结果说明最可能对应的资产；"
        "再解释当前风险状态与核心驱动；"
        "2) investment_strategy至少5条，且必须包含：进场时机、仓位管理、止损/止盈、加减仓条件、失效退出条件；"
        "3) 内容要具体、务实、可执行。"
        "\n\n输入数据:\n"
        + json.dumps(context, ensure_ascii=False)
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    endpoints = [
        (
            f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"
            f"?key={gemini_api_key}",
            None,
        ),
        (
            f"https://generativelanguage.googleapis.com/v1/models/{gemini_model}:generateContent",
            {"x-goog-api-key": gemini_api_key},
        ),
    ]

    for url, headers in endpoints:
        try:
            response = requests.post(url, json=body, headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
            candidates = payload.get("candidates", [])
            if not candidates:
                continue

            parts = candidates[0].get("content", {}).get("parts", [])
            raw_text = "\n".join(
                part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text")
            )
            extracted = _extract_json_object(raw_text)
            if not extracted:
                continue

            parsed = json.loads(extracted)
            summary = str(parsed.get("summary", "")).strip()
            strategy_items = parsed.get("investment_strategy", [])
            strategies = [str(item).strip() for item in strategy_items if str(item).strip()]
            if summary and len(strategies) >= 5:
                return summary, strategies, f"gemini:{gemini_model}"
        except (requests.RequestException, ValueError, json.JSONDecodeError, KeyError, TypeError):
            continue

    summary, strategies = _build_fallback_summary_and_strategy(pair, result)
    return summary, strategies, "fallback:model_error"


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
if "pending_analysis" not in st.session_state:
    st.session_state.pending_analysis = None
if "assurance_report" not in st.session_state:
    st.session_state.assurance_report = None

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
    cooperative_sharing_enabled = st.toggle(
        "Share anonymized risk signals to cooperative pool",
        value=False,
        help="Only aggregated/anonymous risk signals are shared.",
    )
    source_region = st.text_input("Signal region tag (optional)", value="MY")

tab_board, tab_analyze, tab_history, tab_assurance, tab_usage = st.tabs(
    [
        "Live Multi-Asset Board",
        "Analyze One Asset Pair",
        "Risk History Timeline",
        "AI Assurance & Audit",
        "Usage Guide",
    ]
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
    if board.get("requested_limit") and int(board.get("requested_limit", 0)) < 200:
        st.caption(f"Leaderboard fallback mode: loaded with limit={board.get('requested_limit')} to avoid timeout.")
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

        heat_df = pd.DataFrame(
            [
                {
                    "category": row["category"],
                    "status": str(row.get("status", "Unknown")),
                    "score": float(row.get("score", 0) or 0),
                }
                for row in filtered_rows
            ]
        )
        if not heat_df.empty:
            st.markdown("### Risk Heat Map")
            heat_fig = px.density_heatmap(
                heat_df,
                x="category",
                y="status",
                z="score",
                histfunc="avg",
                color_continuous_scale="YlOrRd",
                title="Average Risk Score by Asset Category and Risk Status",
            )
            heat_fig.update_layout(height=360)
            st.plotly_chart(heat_fig, use_container_width=True)

            st.markdown("### Stress Test Simulator")
            scenario_map = {
                "Custom": {
                    "mult": 1.0,
                    "add": 0.0,
                    "period": "User-defined",
                    "note": "Manual scenario with no predefined historical shock.",
                    "evidence": "No historical preset applied. Suitable for policy sandbox and bespoke what-if replay.",
                    "calibration_basis": "mult/add are user-neutral defaults; stress depends only on selected intensity.",
                    "transmission_channels": "User-selected channels only; no embedded macro regime assumption.",
                },
                "2008 Global Financial Crisis": {
                    "mult": 1.4,
                    "add": 12.0,
                    "period": "2008-2009",
                    "note": "Systemic credit freeze, deleveraging, and severe liquidity contraction.",
                    "evidence": "Global cross-asset volatility jumped to crisis regime and funding spreads widened abruptly.",
                    "calibration_basis": "High multiplier captures regime shift in volatility; additive shock captures liquidity and contagion premium.",
                    "transmission_channels": "Funding stress, forced deleveraging, USD funding squeeze, cross-asset correlation spike.",
                },
                "Asian Financial Crisis": {
                    "mult": 1.35,
                    "add": 11.0,
                    "period": "1997-1998",
                    "note": "Currency devaluations and funding pressure across emerging Asia.",
                    "evidence": "Large EMFX devaluations, reserve pressure, and regional contagion produced persistent risk premia.",
                    "calibration_basis": "Near-crisis multiplier for volatility clustering plus additive term for funding/liquidity stress spillover.",
                    "transmission_channels": "FX reserve drawdown, debt-refinancing pressure, regional confidence contagion.",
                },
                "Dot-com Bust": {
                    "mult": 1.18,
                    "add": 7.0,
                    "period": "2000-2002",
                    "note": "Equity valuation collapse with risk-off spillover into broader assets.",
                    "evidence": "Sustained equity drawdown and risk-aversion rise, but systemic funding stress was milder than 2008.",
                    "calibration_basis": "Moderate multiplier reflects elevated volatility without full systemic freeze; smaller additive term for spillover.",
                    "transmission_channels": "Equity beta repricing, sentiment deterioration, sector concentration unwind.",
                },
                "Eurozone Sovereign Debt": {
                    "mult": 1.24,
                    "add": 8.0,
                    "period": "2011-2012",
                    "note": "Sovereign-credit stress and policy uncertainty in Europe.",
                    "evidence": "Peripheral sovereign spreads and redenomination concerns amplified market fragmentation risk.",
                    "calibration_basis": "Medium-high multiplier for persistent volatility and additive term for policy/fragmentation premium.",
                    "transmission_channels": "Sovereign-bank nexus, policy uncertainty, funding fragmentation.",
                },
                "CHF Unpeg Shock": {
                    "mult": 1.28,
                    "add": 9.0,
                    "period": "2015",
                    "note": "SNB floor removal triggered abrupt FX gap and liquidity vacuum.",
                    "evidence": "Intraday gap moves and sharp execution slippage highlighted jump-risk and temporary liquidity collapse.",
                    "calibration_basis": "Higher multiplier for jump-vol regime and additive term for execution/liquidity shock.",
                    "transmission_channels": "Policy surprise, order-book thinning, stop cascade dynamics.",
                },
                "COVID Liquidity Shock": {
                    "mult": 1.3,
                    "add": 10.0,
                    "period": "2020",
                    "note": "Cross-asset liquidation wave and temporary market depth collapse.",
                    "evidence": "Global risk assets sold off synchronously; implied vol and funding stress surged during initial shock windows.",
                    "calibration_basis": "High multiplier for synchronized volatility spike and additive term for broad liquidity dislocation.",
                    "transmission_channels": "Cross-asset liquidation, margin calls, liquidity hoarding, correlation convergence.",
                },
                "Global Inflation & Rate Shock": {
                    "mult": 1.17,
                    "add": 6.5,
                    "period": "2022-2023",
                    "note": "Synchronized tightening cycle and rapid repricing of rates-sensitive assets.",
                    "evidence": "Fast policy-rate repricing increased term-premium volatility and cross-asset sensitivity to macro prints.",
                    "calibration_basis": "Lower multiplier than crisis events but persistent additive term for repricing and liquidity frictions.",
                    "transmission_channels": "Yield shock transmission, duration repricing, real-rate sensitivity.",
                },
                "Commodity Supply Shock": {
                    "mult": 1.22,
                    "add": 8.0,
                    "period": "Multiple episodes",
                    "note": "Energy/raw-material supply disruptions propagate to inflation and FX terms of trade.",
                    "evidence": "Commodity spikes historically pressure inflation expectations, trade balances, and import-sensitive currencies.",
                    "calibration_basis": "Medium-high multiplier for volatility pass-through and additive term for terms-of-trade/liquidity pressure.",
                    "transmission_channels": "Input-cost shock, inflation expectations, external-balance stress, policy reaction uncertainty.",
                },
            }
            sim_col_1, sim_col_2, sim_col_3 = st.columns(3)
            scenario_name = sim_col_1.selectbox(
                "Scenario",
                list(scenario_map.keys()),
                index=0,
                help=(
                    "Scenario presets are calibrated from stylized historical stress regimes, not arbitrary values. "
                    "Each preset combines: (1) multiplier for volatility-regime amplification and "
                    "(2) additive shock for liquidity/contagion premium. "
                    "Use this to test resilience under historically grounded macro transmission channels."
                ),
            )
            scenario_intensity = sim_col_2.slider(
                "Scenario intensity",
                min_value=0.5,
                max_value=2.0,
                value=1.0,
                step=0.05,
                help="0.5 = half shock, 1.0 = baseline historical shock, 2.0 = double shock severity.",
            )
            show_top_n = sim_col_3.slider("Top impacted assets", min_value=5, max_value=30, value=10, step=1)

            scenario = scenario_map[scenario_name]
            st.caption(
                f"Scenario period: {scenario['period']} | Note: {scenario['note']}"
            )
            st.caption(
                f"Calibration evidence: {scenario['evidence']}"
            )
            st.caption(
                f"Calibration basis: {scenario['calibration_basis']}"
            )
            st.caption(
                f"Transmission channels: {scenario['transmission_channels']}"
            )
            st.caption(
                "Stress methodology: stressed_score = clamp((base_score * scenario_multiplier + scenario_additive_shock) * intensity, 0, 100)."
            )
            st.caption(
                "Interpret intensity: increase => magnify historical shock impact; decrease => partial shock replay."
            )

            stressed_rows = []
            for row in filtered_rows:
                base_score = float(row.get("score", 0) or 0)
                stressed_score = min(100.0, max(0.0, (base_score * scenario["mult"] + scenario["add"]) * scenario_intensity))
                stressed_rows.append(
                    {
                        "pair": row.get("pair"),
                        "category": row.get("category"),
                        "base_score": round(base_score, 2),
                        "stressed_score": round(stressed_score, 2),
                        "delta": round(stressed_score - base_score, 2),
                    }
                )

            stressed_rows.sort(key=lambda item: float(item["stressed_score"]), reverse=True)
            stressed_top = stressed_rows[:show_top_n]
            st.dataframe(
                stressed_top,
                use_container_width=True,
                column_config={
                    "base_score": st.column_config.NumberColumn(
                        "base_score",
                        help=(
                            "Current model baseline risk before stress replay (0-100). "
                            "Higher base_score means the asset is already in a higher-risk regime."
                        ),
                    ),
                    "delta": st.column_config.NumberColumn(
                        "delta",
                        help=(
                            "Scenario incremental impact: delta = stressed_score - base_score. "
                            "Higher positive delta means stronger scenario amplification effect."
                        ),
                    ),
                    "stressed_score": st.column_config.NumberColumn(
                        "stressed_score",
                        help=(
                            "Stress-adjusted risk after applying historical scenario calibration and intensity. "
                            "Higher stressed_score implies tighter controls and smaller risk budget."
                        ),
                    ),
                },
            )

            if stressed_top:
                stressed_fig = px.bar(
                    stressed_top,
                    x="pair",
                    y="stressed_score",
                    color="category",
                    custom_data=["base_score", "delta"],
                    title="Stress Scenario Impact (Stressed Score)",
                )
                stressed_fig.update_traces(
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Stressed Score: %{y:.2f} (越高越风险)<br>"
                        "Base Score: %{customdata[0]:.2f} (当前风险基线)<br>"
                        "Delta: %{customdata[1]:.2f} (情景冲击增量)<extra></extra>"
                    )
                )
                stressed_fig.update_layout(height=360)
                st.plotly_chart(stressed_fig, use_container_width=True)
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

        submitted = st.form_submit_button("Analyze Forex Risk")

    if submitted:
        st.session_state.pending_analysis = {
            "base_currency": base_currency,
            "quote_currency": quote_currency,
            "timestamp": timestamp,
            "resolver_adjusted": False,
            "original_base_currency": base_currency,
            "original_quote_currency": quote_currency,
        }

    pending = st.session_state.pending_analysis
    if pending:
        pending_base = str(pending.get("base_currency", base_currency)).upper()
        pending_quote = str(pending.get("quote_currency", quote_currency)).upper()
        pending_timestamp = str(pending.get("timestamp", timestamp))

        precheck_profile = resolve_asset_profile(
            base_code=pending_base,
            quote_code=pending_quote,
        )

        if bool(precheck_profile.get("needs_confirmation", False)):
            st.warning(
                "Asset mapping confidence is low. Please confirm category so the system can auto-adjust to a valid market symbol."
            )
            conf_col_1, conf_col_2, conf_col_3 = st.columns(3)
            chosen_category = conf_col_1.selectbox(
                "Detected / Confirm Category",
                options=["Forex", "Stock", "Commodity", "Crypto"],
                index=["Forex", "Stock", "Commodity", "Crypto"].index(
                    str(precheck_profile.get("detected_category", "Forex"))
                    if str(precheck_profile.get("detected_category", "Forex")) in {"Forex", "Stock", "Commodity", "Crypto"}
                    else "Forex"
                ),
                key="asset_confirm_category",
            )
            suggested_base = conf_col_2.text_input(
                "Suggested Base",
                value=str(precheck_profile.get("resolved_symbol", pending_base)),
                key="asset_confirm_base",
            )
            suggested_quote = conf_col_3.text_input(
                "Quote",
                value=pending_quote,
                key="asset_confirm_quote",
            )

            confirm_col_1, confirm_col_2 = st.columns(2)
            if confirm_col_1.button("Confirm And Auto-Adjust"):
                adjusted_base = auto_adjust_asset_by_category(suggested_base, chosen_category)
                adjusted_quote = suggested_quote.upper().strip() or "USD"
                st.session_state.pending_analysis = {
                    "base_currency": adjusted_base,
                    "quote_currency": adjusted_quote,
                    "timestamp": pending_timestamp,
                    "resolver_adjusted": True,
                    "original_base_currency": pending.get("original_base_currency", pending_base),
                    "original_quote_currency": pending.get("original_quote_currency", pending_quote),
                    "confirmed_category": chosen_category,
                }
                st.rerun()
            if confirm_col_2.button("Cancel Analysis"):
                st.session_state.pending_analysis = None
                st.info("Analysis canceled. Please input a valid asset pair and retry.")
            st.stop()

        payload = {
            "base_currency": pending_base,
            "quote_currency": pending_quote,
            "timestamp": pending_timestamp,
            "metadata": {
                "resolver_adjusted": bool(pending.get("resolver_adjusted", False)),
                "original_base_currency": pending.get("original_base_currency", pending_base),
                "original_quote_currency": pending.get("original_quote_currency", pending_quote),
                "confirmed_category": pending.get("confirmed_category"),
            },
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

            resolved_profile = resolve_asset_profile(
                base_code=base_currency,
                quote_code=quote_currency,
            )
            st.caption(
                "Asset resolver: "
                f"{resolved_profile.get('detected_category', 'unknown')} | "
                f"{resolved_profile.get('asset_name', base_currency.upper())} | "
                f"source={resolved_profile.get('resolution_source', 'unknown')}"
            )

            st.markdown("### Quant Risk Metrics (ES / EWMA / AML)")
            historical_vol = float(debug_payload.get("historical_volatility", 0.0) or 0.0)
            ewma_vol = float(debug_payload.get("ewma_volatility", 0.0) or 0.0)
            ewma_scale = float(debug_payload.get("ewma_scale", 1.0) or 1.0)
            expected_shortfall_95 = float(debug_payload.get("expected_shortfall_95", 0.0) or 0.0)
            path_count = int(debug_payload.get("path_count_considered", 0) or 0)
            hidden_link_count = len(result.get("hidden_links", []))

            q_col_1, q_col_2, q_col_3, q_col_4, q_col_5 = st.columns(5)
            q_col_1.metric("EWMA Volatility", f"{ewma_vol:.4f}")
            q_col_2.metric("Historical Vol", f"{historical_vol:.4f}")
            q_col_3.metric("EWMA Scale", f"{ewma_scale:.2f}x")
            q_col_4.metric("Expected Shortfall 95", f"{expected_shortfall_95:.4f}")
            q_col_5.metric("AML Hidden Paths", hidden_link_count, f"considered {path_count}")

            st.caption(
                "Tail-risk model: ES(95) captures extreme downside tail; EWMA emphasizes recent volatility regime shifts."
            )

            radar_categories = [
                "Volatility",
                "Tail Loss (ES95)",
                "Liquidity Stress",
                "Contagion Path",
                "AML Chain",
            ]
            volatility_score = max(0.0, min(100.0, ewma_vol * 3000))
            tail_loss_score = max(0.0, min(100.0, expected_shortfall_95 * 5000))
            liquidity_score = max(0.0, min(100.0, float(debug_payload.get("spread_bps", 0.0) or 0.0) * 2.5))
            contagion_score = max(0.0, min(100.0, float(debug_payload.get("path_risk", 0.0) or 0.0) * 65))
            aml_score = max(0.0, min(100.0, hidden_link_count * 25))
            radar_values = [
                volatility_score,
                tail_loss_score,
                liquidity_score,
                contagion_score,
                aml_score,
            ]

            radar_explanations = [
                {
                    "meaning": "近期市场波动强度（EWMA）",
                    "impact": "越高代表短期不稳定性越强，风险分更容易被放大。",
                    "how_to_read": "<35 常态；35-65 需谨慎；>65 建议降杠杆并缩短持仓周期。",
                },
                {
                    "meaning": "95%预期损失（尾部风险）",
                    "impact": "衡量极端行情下的平均潜在损失，捕捉黑天鹅风险。",
                    "how_to_read": "越高越需保守仓位和更紧止损，优先保护回撤。",
                },
                {
                    "meaning": "流动性压力（点差代理）",
                    "impact": "越高说明交易成本和滑点风险更高，执行质量下降。",
                    "how_to_read": "高位时避免追单，优先限价单与分批成交。",
                },
                {
                    "meaning": "传染路径强度（图谱路径风险）",
                    "impact": "反映跨资产间风险传导强度，越高越容易被外部冲击带动。",
                    "how_to_read": "高位时减少单一主题暴露，注意相关资产共振。",
                },
                {
                    "meaning": "AML间接链路密度",
                    "impact": "多条共享中介节点路径意味着更复杂的间接传染/资金链风险。",
                    "how_to_read": "高位时加强来源核验与异常链路复核，缩小试探仓位。",
                },
            ]
            radar_customdata = [
                [item["meaning"], item["impact"], item["how_to_read"]] for item in radar_explanations
            ]

            radar_fig = go.Figure(
                data=[
                    go.Scatterpolar(
                        r=radar_values + [radar_values[0]],
                        theta=radar_categories + [radar_categories[0]],
                        fill="toself",
                        name="Risk Profile",
                        customdata=radar_customdata + [radar_customdata[0]],
                        hovertemplate=(
                            "<b>%{theta}</b><br>"
                            "Normalized Score: %{r:.1f}/100<br>"
                            "含义: %{customdata[0]}<br>"
                            "作用: %{customdata[1]}<br>"
                            "怎么看: %{customdata[2]}<extra></extra>"
                        ),
                    )
                ]
            )
            radar_fig.update_layout(
                title="Risk Radar (Normalized 0-100)",
                height=360,
                showlegend=False,
                polar=dict(
                    radialaxis=dict(range=[0, 100]),
                ),
            )
            st.plotly_chart(radar_fig, use_container_width=True)

            summary_text, strategy_points, summary_source = build_ai_summary_and_strategy(
                pair=f"{base_currency.upper()}/{quote_currency.upper()}",
                result=result,
                gemini_api_key=UI_GEMINI_API_KEY,
                gemini_model=UI_GEMINI_MODEL,
                asset_profile=resolved_profile,
            )
            st.markdown("### AI Summary")
            st.write(summary_text)
            st.markdown("### Investment Strategy")
            for strategy_item in strategy_points:
                st.write(f"- {strategy_item}")
            st.caption(f"Summary source: {summary_source}")

            if cooperative_sharing_enabled:
                try:
                    shared_payload = {
                        "pair": f"{base_currency.upper()}/{quote_currency.upper()}",
                        "category": resolved_profile.get("detected_category", pair_category(f"{base_currency.upper()}/{quote_currency.upper()}")),
                        "score": int(result.get("score", 0) or 0),
                        "status": str(result.get("status", "UNKNOWN")).upper(),
                        "flags": result.get("flags", []),
                        "expected_shortfall_95": float(debug_payload.get("expected_shortfall_95", 0.0) or 0.0),
                        "ewma_volatility": float(debug_payload.get("ewma_volatility", 0.0) or 0.0),
                        "aml_hidden_paths": len(result.get("hidden_links", [])),
                        "source_region": source_region.strip().upper() if source_region.strip() else None,
                        "metadata": {
                            "resolution_source": resolved_profile.get("resolution_source"),
                            "market_data_source": debug_payload.get("market_data_source"),
                        },
                    }
                    share_response = call_ops_post(
                        api_url=normalized_api_url,
                        api_key=api_key,
                        path="/ops/cooperative-risk/share",
                        payload=shared_payload,
                    )
                    st.caption(
                        f"Cooperative model shared: {share_response.get('shared')} | signal_id={share_response.get('signal_id')}"
                    )
                except requests.RequestException as exc:
                    st.warning(f"Cooperative sharing skipped: {exc}")

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

            st.session_state.pending_analysis = None

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
                    "ewma_volatility": debug_payload.get("ewma_volatility"),
                    "expected_shortfall_95": debug_payload.get("expected_shortfall_95"),
                    "aml_hidden_paths": len(result.get("hidden_links", [])),
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
                "ewma_volatility",
                "expected_shortfall_95",
                "aml_hidden_paths",
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

with tab_assurance:
    st.subheader("AI Assurance (NIST/OECD) + Regulatory Audit")
    st.markdown("### NIST AI RMF Self-Assessment")
    n_col_1, n_col_2, n_col_3, n_col_4 = st.columns(4)
    nist_govern = n_col_1.slider("GOVERN", min_value=0, max_value=100, value=62, step=1)
    nist_map = n_col_2.slider("MAP", min_value=0, max_value=100, value=58, step=1)
    nist_measure = n_col_3.slider("MEASURE", min_value=0, max_value=100, value=61, step=1)
    nist_manage = n_col_4.slider("MANAGE", min_value=0, max_value=100, value=59, step=1)

    st.markdown("### OECD AI Principles Alignment")
    o_col_1, o_col_2, o_col_3, o_col_4, o_col_5 = st.columns(5)
    oecd_transparency = o_col_1.slider("Transparency", min_value=0, max_value=100, value=64, step=1)
    oecd_robustness = o_col_2.slider("Robustness", min_value=0, max_value=100, value=63, step=1)
    oecd_accountability = o_col_3.slider("Accountability", min_value=0, max_value=100, value=60, step=1)
    oecd_fairness = o_col_4.slider("Fairness", min_value=0, max_value=100, value=57, step=1)
    oecd_safety = o_col_5.slider("Safety", min_value=0, max_value=100, value=65, step=1)

    nist_score = round((nist_govern + nist_map + nist_measure + nist_manage) / 4, 2)
    oecd_score = round((oecd_transparency + oecd_robustness + oecd_accountability + oecd_fairness + oecd_safety) / 5, 2)
    assurance_score = round((nist_score * 0.55) + (oecd_score * 0.45), 2)

    a_col_1, a_col_2, a_col_3 = st.columns(3)
    a_col_1.metric("NIST RMF Score", nist_score)
    a_col_2.metric("OECD Principles Score", oecd_score)
    a_col_3.metric("AI Assurance Composite", assurance_score)

    if assurance_score >= 75:
        assurance_level = "Strong"
    elif assurance_score >= 55:
        assurance_level = "Moderate"
    else:
        assurance_level = "Needs Improvement"

    st.caption(
        "AI Assurance positioning: converts compliance from cost center to premium assurance service for regulated clients."
    )

    report_payload = {
        "generated_at_utc": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
        "framework": "NIST AI RMF + OECD Principles",
        "nist": {
            "govern": nist_govern,
            "map": nist_map,
            "measure": nist_measure,
            "manage": nist_manage,
            "score": nist_score,
        },
        "oecd": {
            "transparency": oecd_transparency,
            "robustness": oecd_robustness,
            "accountability": oecd_accountability,
            "fairness": oecd_fairness,
            "safety": oecd_safety,
            "score": oecd_score,
        },
        "composite_score": assurance_score,
        "assurance_level": assurance_level,
        "recommended_actions": [
            "Document model governance and change-control evidence quarterly.",
            "Track ES/EWMA/AML indicators with threshold-based escalation policy.",
            "Maintain webhook and audit-chain logs for regulator-facing transparency.",
        ],
    }

    st.download_button(
        "Download AI Assurance Report (JSON)",
        data=json.dumps(report_payload, ensure_ascii=False, indent=2),
        file_name="riskguard_ai_assurance_report.json",
        mime="application/json",
    )

    st.markdown("### API Subscription Mode (Webhook)")
    s_col_1, s_col_2 = st.columns(2)
    webhook_url = s_col_1.text_input("Webhook URL", value="")
    webhook_secret = s_col_2.text_input("Webhook Secret (optional)", value="", type="password")
    webhook_events = st.multiselect(
        "Events",
        options=["risk.forex.analyzed", "risk.subscription.test"],
        default=["risk.forex.analyzed"],
    )
    if st.button("Save Webhook Subscription", type="primary"):
        if webhook_url.strip():
            try:
                save_result = call_ops_post(
                    api_url=normalized_api_url,
                    api_key=api_key,
                    path="/api/v1/subscriptions",
                    payload={
                        "url": webhook_url.strip(),
                        "events": webhook_events,
                        "secret": webhook_secret.strip() or None,
                        "enabled": True,
                        "description": "Saved via Streamlit assurance tab",
                    },
                )
                st.success(f"Subscription saved: id={save_result.get('subscription_id')}")
            except requests.RequestException as exc:
                st.error(f"Failed to save subscription: {exc}")
        else:
            st.warning("Webhook URL is required.")

    try:
        subscriptions_payload = call_ops_get(
            api_url=normalized_api_url,
            api_key=api_key,
            path="/api/v1/subscriptions",
        )
        st.dataframe(subscriptions_payload.get("subscriptions", []), use_container_width=True)
    except requests.RequestException as exc:
        st.info(f"Subscriptions unavailable: {exc}")

    st.markdown("### Cooperative Risk Model Summary")
    try:
        cooperative_summary = call_ops_get(
            api_url=normalized_api_url,
            api_key=api_key,
            path="/ops/cooperative-risk/summary",
        )
        c_sum_1, c_sum_2, c_sum_3 = st.columns(3)
        c_sum_1.metric("Shared Signals (30d)", cooperative_summary.get("total_shared_signals", 0))
        c_sum_2.metric("Avg Shared Score", cooperative_summary.get("avg_shared_score", 0))
        c_sum_3.metric("High-Risk Shared", cooperative_summary.get("high_risk_shared_count", 0))
        st.write("Top Shared Pairs")
        st.dataframe(cooperative_summary.get("top_pairs", []), use_container_width=True)
        st.write("Category Distribution")
        st.dataframe(cooperative_summary.get("category_distribution", []), use_container_width=True)
    except requests.RequestException as exc:
        st.info(f"Cooperative summary unavailable: {exc}")

    st.markdown("### Immutable Audit Trail")
    try:
        audit_payload = call_ops_get(
            api_url=normalized_api_url,
            api_key=api_key,
            path="/ops/audit-trail?limit=100",
            timeout=(8, 60),
        )
        audit_rows = audit_payload.get("rows", [])
        st.caption(
            "Tamper-evident chain fields: each row links to previous row via prev_hash and entry_hash for traceability."
        )
        st.dataframe(audit_rows, use_container_width=True)
    except requests.RequestException as exc:
        st.info(f"Audit trail unavailable: {exc}")

with tab_usage:
    st.subheader("RiskGuard Usage Guide")
    st.caption(f"Guide last updated: {USAGE_GUIDE_LAST_UPDATED}")
    st.info(
        "Maintenance rule: when new features/endpoint changes are released, update `USAGE_GUIDE_CHANGELOG` and this guide section in the same commit."
    )

    st.markdown("### Quick Start")
    st.markdown(
        """
1. Set backend analyze endpoint and API key in sidebar.
2. Use `Live Multi-Asset Board` to monitor top-risk assets and run stress simulation.
3. Use `Analyze One Asset Pair` for deep analysis, AI summary, strategy, ES/EWMA/AML diagnostics.
4. Use `AI Assurance & Audit` to generate compliance reports, manage webhook subscriptions, and inspect audit chains.
        """
    )

    st.markdown("### Core Tabs")
    st.markdown(
        """
- `Live Multi-Asset Board`: Filter assets by category, inspect scores, run heat map and scenario stress tests.
- `Analyze One Asset Pair`: Analyze selected pair with auto-tuned market/news signals and AI-generated summary.
- `Risk History Timeline`: Review historical score path and key model indicators over time.
- `AI Assurance & Audit`: NIST/OECD self-assessment, webhook setup, cooperative model summary, immutable audit trail.
        """
    )

    st.markdown("### API-First Endpoints")
    st.code(
        """GET  /health
POST /analyze-forex-risk
POST /api/v1/risk/forex
GET  /ops/top-risk-pairs?limit=200&force_refresh=false
GET  /ops/audit-trail?limit=100
POST /ops/cooperative-risk/share
GET  /ops/cooperative-risk/summary
POST /api/v1/subscriptions
GET  /api/v1/subscriptions
DELETE /api/v1/subscriptions/{subscription_id}
POST /api/v1/subscriptions/{subscription_id}/test""",
        language="text",
    )

    st.markdown("### Radar Hover Interpretation")
    st.markdown(
        """
- Hover each radar axis to see: `含义` (what it measures), `作用` (risk impact), `怎么看` (decision guideline).
- Higher `Tail Loss (ES95)` means larger expected loss in extreme tail scenarios.
- Higher `AML Chain` and `Contagion Path` imply stronger indirect transmission risk across connected assets.
        """
    )

    st.markdown("### Invalid Asset Code Handling")
    st.markdown(
        """
- If asset mapping confidence is low (for example `abcdefghi/USD`), analysis is paused.
- User must confirm category and suggested symbol first.
- System then auto-adjusts to a valid Forex/Stock/Commodity/Crypto symbol before analysis.
        """
    )

    st.markdown("### Cooperative Risk Model")
    st.markdown(
        """
- Enable `Share anonymized risk signals to cooperative pool` in sidebar.
- Only aggregated anonymous indicators are shared (no user identity or raw transaction details).
- Use cooperative summary in Assurance tab to view network-effect intelligence.
        """
    )

    st.markdown("### Recent Updates")
    for idx, note in enumerate(USAGE_GUIDE_CHANGELOG, start=1):
        st.write(f"{idx}. {note}")

    st.markdown("### Stress Test Methodology")
    st.markdown(
        """
- Baseline input is model-generated `base_score` (0-100) from current ES/EWMA/AML-aware risk engine.
- Scenario preset contributes two calibrated shock terms:
    1) multiplicative shock (`scenario_multiplier`) to reflect volatility-regime escalation,
    2) additive shock (`scenario_additive_shock`) to reflect liquidity/contagion spillover.
- User controls `intensity` to replay weaker/stronger versions of the historical shock.
- Final score uses bounded transformation:
    `stressed_score = clamp((base_score * multiplier + additive) * intensity, 0, 100)`.
- Preset calibration is anchored to stylized historical facts (crisis-period volatility/spread widening patterns), and is intended for decision support, not exact PnL forecasting.
        """
    )

    st.markdown("### Stress Table Tooltip Guide")
    st.markdown(
        """
- Hover the `?` icon on `base_score`, `delta`, and `stressed_score` column headers for on-demand definitions.
- `base_score`: current pre-stress model baseline risk.
- `delta`: incremental scenario impact (`stressed_score - base_score`).
- `stressed_score`: final stress-adjusted risk after calibrated scenario replay.
        """
    )

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
