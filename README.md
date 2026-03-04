# RiskGuard MVP

Financial fraud detection and risk scoring system built with FastAPI + Streamlit.

## Features

- Deterministic fraud rules: velocity, location anomaly, high-value amount.
- Risk score mapping: Low / Medium / High.
- Synthetic historical data generation (1000 transactions).
- Optional IsolationForest anomaly debug (`USE_ML_ANOMALY=true`).
- Optional API key authentication (`X-API-Key`).
- Per-client rate limiting with configurable thresholds.
- SQLite audit trail and 24-hour ops summary endpoint.
- Zero-cost forex risk graph analytics with hidden-link detection (`networkx`).
- Free market data enrichment from Frankfurter API with fallback model.
- Commodity-linked coverage (Gold/Silver/Platinum/Palladium/Brent/WTI) with free Yahoo market feed.
- Autonomous AI parameter tuning using global news + market data (no manual slider tuning).
- Optional Gemini API enhancement for broader news interpretation and parameter refinement.
- Streamlit dashboard with score display and trend charts.

## Project Structure

```
RiskGuard MVP/
├─ app.py
├─ config.py
├─ data/
│  ├─ generate_mock_data.py
│  └─ mock_transactions.csv
├─ data_utils.py
├─ main.py
├─ models.py
├─ README.md
├─ requirements.txt
├─ risk_engine.py
├─ tests/
│  ├─ test_api.py
│  └─ test_risk_engine.py
└─ .gitignore
```

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python data/generate_mock_data.py
```

## Run API

```bash
uvicorn main:app --reload
```

## Run Streamlit

```bash
streamlit run app.py
```

Then open:

- Frontend UI: `http://127.0.0.1:8501`
- Backend docs: `http://127.0.0.1:8000/docs`

## Procfile-like Start Command

Use this command for process managers:

```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## API Endpoint

`POST /analyze-transaction`

`POST /analyze-forex-risk`

`GET /forex/market-snapshot?base_currency=USD&quote_currency=MYR`

Additional operational endpoint:

- `GET /ops/summary`
- `GET /ops/top-risk-pairs?limit=10&force_refresh=false`
- `GET /ops/news-sources?enabled_only=false`
- `POST /ops/news-sources`
- `DELETE /ops/news-sources?url=<feed_url>`

### Forex network risk request example

```bash
curl -X POST http://127.0.0.1:8000/analyze-forex-risk \
  -H "Content-Type: application/json" \
  -d '{
    "base_currency": "MYR",
    "quote_currency": "EUR",
    "timestamp": "2026-03-01T12:34:56+08:00",
    "metadata": {
      "news_sentiment": -0.2,
      "macro_stress": 0.5
    }
  }'
```

`observed_volatility` and `spread_bps` are optional; backend auto-enriches from free market data.
Response includes `hidden_links` and network debug fields to expose indirect contagion paths.

## Daily Operational Scan

`/ops/top-risk-pairs` will automatically run a daily scan of major FX pairs (once per day, KL date) and persist rankings.
It includes major commodity-linked pairs as well (e.g., `XAU/USD`, `XBR/USD`).

- `limit`: number of pairs to return (1-20)
- `force_refresh=true`: rerun full scan immediately

Response includes:

- `latest_update_utc`: latest update timestamp among ranked rows

Example:

```bash
curl "http://127.0.0.1:8000/ops/top-risk-pairs?limit=10"
```

## How to use `macro_stress` and `news_sentiment`

- `macro_stress` (`0.0` to `1.0`): systemic stress gauge (rates shock, policy uncertainty, liquidity tightening).
- `news_sentiment` (`-1.0` to `1.0`): directional media/signal bias for the pair.

Are they necessary?

- **Not mandatory**: backend can run without manual inputs and auto-derive from market data.
- **High value in production**: adding these two signals improves early warning during regime shifts where pure price stats lag.

Practical usage guide:

- `macro_stress`
  - 0.0-0.3: stable regime
  - 0.3-0.6: caution (policy/event sensitivity rising)
  - 0.6-1.0: stressed regime (tighten limits, increase monitoring)

- `news_sentiment`
  - 0.2 to 1.0: positive flow
  - -0.2 to 0.2: neutral flow
  - -1.0 to -0.2: negative pressure (watch gap risk and liquidity thinning)

Recommended policy:

- keep `macro_stress` as system-level signal (hourly/daily updates)
- keep `news_sentiment` as event overlay (major headlines)
- escalate review when both are stressed (`macro_stress > 0.6` and `news_sentiment < -0.25`)

In this system, these values are now produced automatically by backend AI tuning:

- `news_sentiment`: derived from global RSS headline polarity
- `macro_stress`: derived from global risk terms + market stress context
- extra auto parameters: `policy_uncertainty`, `geopolitical_risk`, `liquidity_risk`, `commodity_shock`
  plus `systemic_contagion`, `fraud_pressure_index`

Manual tuning is no longer required in the Streamlit UI.

## Backend Production Config

Set these environment variables on Render:

- `RISKGUARD_API_KEY` = strong secret value (enables API key auth)
- `RATE_LIMIT_REQUESTS` = max requests per window (default `60`)
- `RATE_LIMIT_WINDOW_SECONDS` = window size in seconds (default `60`)
- `AUDIT_DB_PATH` = SQLite file path (default `data/riskguard_audit.db`)
- `AUTO_PARAMETER_TUNING` = backward-compatible env var (forex analyze endpoint now always auto-tunes)
- `NEWS_FETCH_TIMEOUT_SECONDS` = news fetch timeout (default `2`)
- `NEWS_CACHE_TTL_SECONDS` = cache TTL seconds (default `600`)
- `USE_GEMINI_NEWS` = `true|false` (default `false`)
- `GEMINI_API_KEY` = your Gemini API key
- `GEMINI_MODEL` = model name (default `gemini-2.5-flash`)

## Gemini API Key Placement (Important)

Do **not** commit API keys into GitHub.

Where to set keys:

- Render backend: Dashboard → Environment → add `GEMINI_API_KEY`
- Streamlit Cloud frontend (if needed): App settings → Secrets
- Local dev: create `.env` from `.env.example` and keep it untracked

About `RISKGUARD_API_KEY` and `BACKEND_API_KEY`:

- `RISKGUARD_API_KEY`: backend API protection key (set on Render env vars)
- `BACKEND_API_KEY`: frontend key used to call backend (set on Streamlit secrets or local `.env`)
- If not set, backend currently allows unauthenticated calls (development mode)

Gemini usage in current system:

- `USE_GEMINI_NEWS=true` and valid `GEMINI_API_KEY` => backend uses Gemini to refine news-derived parameters.
- `USE_GEMINI_NEWS=false` or missing key => system falls back to deterministic RSS intelligence only.
- Auto tuning of market + news signals is always enabled for `/analyze-forex-risk` and does not require any frontend toggle.

Current AI status fields (returned in `debug` from `/analyze-forex-risk`):

- `auto_parameter_tuning`
- `gemini_enabled`
- `news_source`
- `news_sample_size`
- `active_feed_count`
- `successful_feed_count`

Default RSS coverage includes Reuters, BBC, CNBC, Sky News, Al Jazeera, and FT.

Will app still work if key is not pushed?

- Yes. Deployed services read keys from platform environment variables/secrets, not from Git commits.
- This is the correct and secure production pattern.

## Dynamic News Source Whitelist (Runtime)

You can add/remove feed URLs without redeploying backend.

Add or update one source:

```bash
curl -X POST http://127.0.0.1:8000/ops/news-sources \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/rss.xml","enabled":true}'
```

Delete one source:

```bash
curl -X DELETE "http://127.0.0.1:8000/ops/news-sources?url=https://example.com/rss.xml"
```

## Timeline Display Notes

`Forex Risk History` now uses true datetime axis and shows milliseconds.

- 1 data point: chart shows a single scatter point (no line yet)
- 2+ data points: chart switches to line + markers trend view

This avoids the previous visual issue where same-second values looked like a flat/empty timeline.

Observability headers returned on every API response:

- `X-Request-ID`
- `X-Process-Time-Ms`

Input validation hardening:

- `timestamp` must be timezone-aware and in Malaysia offset (`UTC+08:00`)
- `user_id` and `city` are trimmed and cannot be blank

When `RISKGUARD_API_KEY` is set, include header:

`X-API-Key: <your-key>`

### Sample curl

```bash
curl -X POST http://127.0.0.1:8000/analyze-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "amount": 450.5,
    "city": "Kuala Lumpur",
    "timestamp": "2026-03-01T12:34:56+08:00",
    "metadata": {"channel": "mobile"}
  }'
```

### Expected output shape

```json
{
  "score": 30,
  "status": "Low",
  "flags": ["high_value"],
  "reasons": ["Transaction amount ... exceeds 3.0x user average ..."],
  "debug": {
    "velocity_count": 1,
    "velocity_threshold": 5,
    "location_unique_cities_last_hour": ["Kuala Lumpur"],
    "user_avg_amount": 120.25,
    "high_value_threshold": 360.75
  }
}
```

### High-risk combined example

```bash
curl -X POST http://127.0.0.1:8000/analyze-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_010",
    "amount": 900.0,
    "city": "Johor Bahru",
    "timestamp": "2026-03-01T12:35:20+08:00",
    "metadata": {"channel": "web"}
  }'
```

Possible expected output:

```json
{
  "score": 100,
  "status": "High",
  "flags": ["velocity", "location", "high_value"],
  "reasons": [
    "User has 6 transactions in the last 60 seconds",
    "User has transactions across different cities within 1 hour",
    "Transaction amount 900.00 exceeds 3.0x user average 180.00"
  ],
  "debug": {
    "velocity_count": 6,
    "velocity_threshold": 5,
    "location_unique_cities_last_hour": ["Johor Bahru", "Kuala Lumpur"],
    "user_avg_amount": 180.0,
    "high_value_threshold": 540.0
  }
}
```

## Run Tests

```bash
pytest -q
```

## Deploy to Streamlit Community Cloud

Required deploy files in repo root:

- `app.py`
- `requirements.txt`
- `runtime.txt` (set to `python-3.11`)

1. Push this project to GitHub.
2. Go to `https://share.streamlit.io` and sign in.
3. Click **New app** and select your repo.
4. Set **Main file path** to `app.py`.
5. Click **Deploy**.

After deployment, your frontend URL will look like:
`https://<your-app-name>.streamlit.app`

### Backend URL for cloud frontend

In deployed Streamlit app, set **API Settings → Analyze endpoint** to your public backend endpoint, for example:

`https://<your-backend-domain>/analyze-transaction`

Optional (recommended): set Streamlit Cloud Secrets or environment variable:

`BACKEND_API_URL = "https://<your-backend-domain>/analyze-transaction"`
`BACKEND_API_KEY = "<your-api-key-if-enabled>"`

If backend is not reachable, the UI still loads trends and shows a warning in sidebar.
On Render free tier, first request can be delayed by cold start; app includes retry and longer read timeout.

## Deploy Backend to Render

This repository includes `render.yaml` and `requirements.api.txt` for FastAPI backend deployment.

### Option A: Blueprint (recommended)

1. Open: `https://dashboard.render.com/blueprint/new?repo=https://github.com/goh445/riskguard-mvp`
2. Connect GitHub repo and click **Apply**.
3. Wait for build and deploy.

After deployment, you will get a backend URL like:
`https://riskguard-api.onrender.com`

Validate endpoints:

- `https://<your-render-url>/health`
- `https://<your-render-url>/docs`
- `https://<your-render-url>/analyze-transaction`

Then set Streamlit sidebar endpoint to:
`https://<your-render-url>/analyze-transaction`

## Quick Local Frontend Preview

To view the same Streamlit page locally:

```bash
streamlit run app.py
```

## Notes

- No secrets are stored in this repository.
- Timestamps are normalized to Malaysia time zone (`Asia/Kuala_Lumpur`).
