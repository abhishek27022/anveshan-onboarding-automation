# Chemelex Demand Forecasting Cockpit — Executive Edition

Plain-English dashboard for senior leadership.
No jargon, no acronyms — just "how close to 100% accurate are we?"

## What's in the dashboard

| Tab | What it shows |
|-----|---------------|
| **📈 Executive Overview** | Top revenue contributor, most accurate zone, headline KPIs (forecast / actual / accuracy / plan vs reality), monthly trend and accuracy charts |
| **🆚 AI vs Manual Plan** | Three side-by-side charts — Actual sales, AI Forecast, Manual Plan — each with its own accuracy %. Headline KPIs: Manual Plan Accuracy, AI Forecast Accuracy, AI Improvement, Error Reduction. Auto-picks the best AI model |
| **🎯 Accuracy by Line** | Sortable table with traffic-light status (✅ / 🟡 / 🔴), downloadable CSV |
| **🔍 Drill Down** | Forecast vs actual by zone / plant / category |
| **📦 Forward Plan** | Looking ahead — what the AI and manual plan expect in upcoming months |

## Files needed

Place these next to `app.py`:

| File | Required? | Purpose |
|------|-----------|---------|
| `corrected_dashboard_forecast_accuracy_levelled.csv` | ✅ Required | Main data source |
| `ibp_vs_model_comparison_2025.csv` | Optional | Enriches AI-vs-Manual head-to-head table |
| `ibp_reconciliation.csv` | Optional | Reference / audit purposes |

If the main file is missing, the dashboard shows a prompt to upload one.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push `app.py`, `requirements.txt`, plus the data CSV files to a GitHub repo
2. Connect the repo at https://share.streamlit.io and point at `app.py`

## How accuracy is computed

`Accuracy = 100% − (total error ÷ total actual sales × 100%)`

Closer to 100% is always better. The dashboard uses positive accuracy framing throughout — there are no negative-coded metrics (errors, biases) shown to the user.

## What the CEO sees on the AI vs Manual tab

With current data, the headline KPIs read:

- **Manual Plan Accuracy:** 87.8% (5 months observed)
- **AI Forecast Accuracy:** 90.2% (auto-picked: LightGBM)
- **AI Improvement:** +2.4 pts → "AI is more accurate"
- **Error Reduction:** $377,648 less forecast error on the same products

## Built-in caveats (shown in-app where relevant)

- All numbers are US region only.
- The manual plan covers about 10% of US revenue. For a fair head-to-head, the AI forecast is rescaled to the same products in the AI-vs-Manual tab.
- Manual plan actuals exist for Jan–May 2025 only; later months show forecast only with greyed-out actual bars.
