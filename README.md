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

Additional operational endpoint:

- `GET /ops/summary`

## Backend Production Config

Set these environment variables on Render:

- `RISKGUARD_API_KEY` = strong secret value (enables API key auth)
- `RATE_LIMIT_REQUESTS` = max requests per window (default `60`)
- `RATE_LIMIT_WINDOW_SECONDS` = window size in seconds (default `60`)
- `AUDIT_DB_PATH` = SQLite file path (default `data/riskguard_audit.db`)

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
