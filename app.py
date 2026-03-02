"""Streamlit frontend for RiskGuard MVP."""

from __future__ import annotations

from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from data.generate_mock_data import save_mock_transactions


API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000/analyze-transaction")
DATA_FILE = "data/mock_transactions.csv"


@st.cache_data(show_spinner=False)
def load_trends_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and aggregate trends by day and hour."""
    if not pd.io.common.file_exists(DATA_FILE):
        save_mock_transactions(DATA_FILE)
    df = pd.read_csv(DATA_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    day_df = (
        df.assign(day=df["timestamp"].dt.date)
        .groupby("day", as_index=False)
        .size()
        .rename(columns={"size": "transactions"})
    )
    hour_df = (
        df.assign(hour=df["timestamp"].dt.hour)
        .groupby("hour", as_index=False)
        .size()
        .rename(columns={"size": "transactions"})
    )
    return day_df, hour_df


def check_backend_health(base_analyze_url: str) -> tuple[bool, str]:
    """Check backend health endpoint based on analyze URL."""
    health_url = base_analyze_url.replace("/analyze-transaction", "/health")
    try:
        response = requests.get(health_url, timeout=3)
        if response.status_code == 200:
            return True, health_url
    except requests.RequestException:
        pass
    return False, health_url


def call_analyze_api(api_url: str, payload: dict[str, object]) -> dict[str, object]:
    """Call backend analyze API with retries to handle cold starts."""
    last_exception: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.post(api_url, json=payload, timeout=(8, 45))
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
st.title("RiskGuard MVP — Fraud Detection & Risk Scoring")

with st.sidebar:
    st.header("API Settings")
    api_url = st.text_input("Analyze endpoint", value=API_URL)
    is_healthy, health_url = check_backend_health(api_url)
    if is_healthy:
        st.success(f"Backend OK: {health_url}")
    else:
        st.warning(f"Backend unreachable: {health_url}")

st.subheader("Analyze Transaction")
with st.form("analyze_form"):
    col1, col2 = st.columns(2)
    with col1:
        user_id = st.text_input("User ID", value="user_001")
        amount = st.number_input("Amount", min_value=0.01, value=120.0, step=1.0)
    with col2:
        city = st.text_input("City", value="Kuala Lumpur")
        timestamp = st.text_input(
            "Timestamp (ISO8601, Malaysia TZ)",
            value=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).isoformat(timespec="seconds"),
        )

    submitted = st.form_submit_button("Analyze")

if submitted:
    payload = {
        "user_id": user_id,
        "amount": float(amount),
        "city": city,
        "timestamp": timestamp,
        "metadata": {},
    }
    try:
        with st.spinner("Analyzing transaction... (first request may be slower due to backend cold start)"):
            result = call_analyze_api(api_url=api_url, payload=payload)

        st.metric(label="Risk Score", value=f"{result['score']} ({result['status']})")

        st.markdown("### Reasons")
        if result.get("reasons"):
            for reason in result["reasons"]:
                st.write(f"- {reason}")
        else:
            st.write("- No risk flags triggered.")

        st.markdown("### Flags")
        st.write(result.get("flags", []))
        with st.expander("Debug"):
            st.json(result.get("debug", {}))
    except requests.RequestException as exc:
        st.error(
            "Failed to call API after retries. If using Render free plan, wait 30-60 seconds for cold start and try again. "
            f"Details: {exc}"
        )

st.markdown("## Risk Trends")
day_data, hour_data = load_trends_data()

col_day, col_hour = st.columns(2)
with col_day:
    fig_day = px.line(day_data, x="day", y="transactions", title="Transactions by Day")
    st.plotly_chart(fig_day, width="stretch")

with col_hour:
    fig_hour = px.bar(hour_data, x="hour", y="transactions", title="Transactions by Hour")
    st.plotly_chart(fig_hour, width="stretch")
