# ✈️ RevenuePilot — STR Revenue Intelligence Platform

> End-to-end Revenue Management analytics system for a 50-unit short-term rental portfolio. Built to demonstrate applied ML, data engineering, and business intelligence in hospitality.

<p align="center">
  <a href="https://mikelcerio.github.io/revenue-pilot-str-analytics/">
    <img src="assets/img/dashboard_preview.png" alt="RevenuePilot Dashboard" width="800">
  </a>
</p>

<p align="center">
  <a href="https://mikelcerio.github.io/revenue-pilot-str-analytics/"><strong>🔗 Live Portfolio Page</strong></a> ·
  <a href="https://mikelcerio.github.io/revenue-pilot-str-analytics/outputs/RevenuePilot_Dashboard.html"><strong>⚡ Dashboard Demo</strong></a> ·
  <a href="https://mikelcerio.github.io/revenue-pilot-str-analytics/outputs/BilbaoMarketMap.html"><strong>🗺️ Market Map</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Power%20BI-PL--300-yellow?logo=powerbi" alt="Power BI">
  <img src="https://img.shields.io/badge/ML-LightGBM-green" alt="LightGBM">
  <img src="https://img.shields.io/badge/NLP-Multilingual-purple" alt="NLP">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

---

## 📌 Problem Statement

A portfolio of 50 tourist apartments across 5 buildings was operating with:
- **No centralized analytics** — revenue tracked in spreadsheets
- **Static pricing** — same rate applied regardless of seasonality or demand
- **No cancellation risk management** — no early warning system
- **No market benchmarking** — no systematic comparison vs. the local STR market

**Goal:** Build a full Revenue Management intelligence system from raw booking data to actionable recommendations.

---

## 🎯 What This Project Delivers

| Component | Description |
|-----------|-------------|
| 📊 **Power BI Dashboard** | 7-page report with 40+ DAX measures, star schema, RLS |
| 🤖 **ML Pipeline** | 3 LightGBM models: demand forecasting, cancellation risk, price recommendation |
| 🗺️ **Market Map** | Interactive Leaflet.js map — 1,561 listings from Inside Airbnb open data |
| 🔍 **NLP Review Analysis** | Sentiment + topic extraction from 6,298 multilingual guest reviews |
| 📈 **Demo Dashboard** | Standalone HTML SaaS-style demo (zero backend required) |
| 🌐 **Portfolio Landing Page** | GitHub Pages website showcasing the full project |

---

## 🗂️ Project Structure

```
revenue-pilot-str-analytics/
├── index.html                  # Portfolio landing page (GitHub Pages)
├── assets/                     # Landing page assets (CSS, JS, images)
├── scripts/                    # Python pipeline (phases 0-8)
│   ├── etl_phase0.py           # Data loading & cleaning
│   ├── kpis_phase1.py          # KPI computation (RevPAR, ADR, occupancy)
│   ├── patterns_phase2.py      # Booking patterns & seasonality
│   ├── pricing_phase3.py       # Pricing analysis & elasticity
│   ├── train_models_phase4.py  # ML model training (LightGBM)
│   ├── powerbi_phase5.py       # Star schema export for Power BI
│   ├── gastos_phase6.py        # Profitability analysis
│   ├── benchmark_rm_report.py  # Market benchmarking
│   ├── airbnb_market_analysis.py  # Inside Airbnb open-data pipeline
│   ├── build_market_map.py     # Leaflet.js map generator
│   └── reviews_nlp_phase8.py   # NLP review analysis (multilingual)
├── data/
│   └── public/                 # Anonymized exports (52 files, CSV + Parquet)
│       ├── fact_reservations   # 34K+ booking records
│       ├── fact_reviews        # 6,298 guest reviews with NLP output
│       ├── dim_property        # Building metadata (A-E, rounded coords)
│       └── ...
├── outputs/
│   ├── RevenuePilot_Dashboard.html   # Standalone demo dashboard
│   ├── BilbaoMarketMap.html          # Interactive market map
│   ├── LinkedIn_PostCalendar.html    # Content calendar demo
│   ├── figures/                      # 42 charts (PNG)
│   └── reports/                      # 11 markdown analysis reports
├── notebooks/
│   └── 01_kpis_base.ipynb      # KPI exploration notebook
├── requirements.txt
└── LICENSE
```
revenue-pilot-str-analytics/
├── index.html                  # 🌐 Portfolio landing page (GitHub Pages)
├── assets/                     # Landing page assets (CSS, JS, images)
├── scripts/                    # Python pipeline (phases 0–8)
│   ├── etl_phase0.py           # Data loading & cleaning
│   ├── kpis_phase1.py          # KPI computation (RevPAR, ADR, occupancy)
│   ├── patterns_phase2.py      # Booking patterns & seasonality
│   ├── pricing_phase3.py       # Pricing analysis & elasticity
│   ├── train_models_phase4.py  # ML model training (LightGBM)
│   ├── powerbi_phase5.py       # Star schema export for Power BI
│   ├── gastos_phase6.py        # P&L and profitability analysis
│   ├── benchmark_rm_report.py  # Market benchmarking vs local market
│   ├── reviews_nlp_phase8.py   # NLP review analysis (multilingual)
│   └── anonymize_for_github.py # Data anonymization pipeline
├── data/
│   └── public/                 # Anonymized exports (CSV + Parquet)
│       ├── fact_reservations    # 34K+ booking records
│       ├── fact_reviews         # 6,298 guest reviews with NLP
│       ├── dim_property         # Building metadata with coordinates
│       ├── predictions_export   # ML model predictions
│       └── ... (21 tables total)
├── outputs/
│   ├── RevenuePilot_Dashboard.html   # Standalone demo dashboard
│   ├── BilbaoMarketMap.html          # Interactive market map
│   ├── figures/                      # 86 Plotly charts (HTML + PNG)
│   └── reports/                      # Markdown analysis reports
├── notebooks/
│   └── 01_kpis_base.ipynb      # KPI exploration notebook
├── revenue_pilot.py            # Streamlit dashboard app
├── generar_datos_sinteticos.py  # Synthetic data generator
└── requirements.txt
```
revenue-pilot-str-analytics/
├── index.html                  # Portfolio landing page (GitHub Pages)
├── assets/                     # Landing page assets (CSS, JS, images)
├── scripts/                    # Python pipeline (phases 0-8)
│   ├── etl_phase0.py           # Data loading & cleaning
│   ├── kpis_phase1.py          # KPI computation (RevPAR, ADR, occupancy)
│   ├── patterns_phase2.py      # Booking patterns & seasonality
│   ├── pricing_phase3.py       # Pricing analysis & elasticity
│   ├── train_models_phase4.py  # ML model training (LightGBM)
│   ├── powerbi_phase5.py       # Star schema export for Power BI
│   ├── gastos_phase6.py        # Profitability analysis
│   ├── benchmark_rm_report.py  # Market benchmarking
│   ├── airbnb_market_analysis.py  # Inside Airbnb open-data pipeline
│   ├── build_market_map.py     # Leaflet.js map generator
│   └── reviews_nlp_phase8.py   # NLP review analysis (multilingual)
├── data/
│   └── public/                 # Anonymized exports (52 files, CSV + Parquet)
│       ├── fact_reservations   # 34K+ booking records
│       ├── fact_reviews        # 6,298 guest reviews with NLP output
│       ├── dim_property        # Building metadata (A-E, rounded coords)
│       └── ...
├── outputs/
│   ├── RevenuePilot_Dashboard.html   # Standalone demo dashboard
│   ├── BilbaoMarketMap.html          # Interactive market map
│   ├── LinkedIn_PostCalendar.html    # Content calendar demo
│   ├── figures/                      # 42 charts (PNG)
│   └── reports/                      # 11 markdown analysis reports
├── notebooks/
│   └── 01_kpis_base.ipynb      # KPI exploration notebook
├── requirements.txt
└── LICENSE
```

---

## 📊 Power BI Star Schema

```
revenue-pilot-str-analytics/
├── index.html                  # Portfolio landing page (GitHub Pages)
├── assets/                     # Landing page assets (CSS, JS, images)
├── scripts/                    # Python pipeline (phases 0-8)
│   ├── etl_phase0.py           # Data loading & cleaning
│   ├── kpis_phase1.py          # KPI computation (RevPAR, ADR, occupancy)
│   ├── patterns_phase2.py      # Booking patterns & seasonality
│   ├── pricing_phase3.py       # Pricing analysis & elasticity
│   ├── train_models_phase4.py  # ML model training (LightGBM)
│   ├── powerbi_phase5.py       # Star schema export for Power BI
│   ├── gastos_phase6.py        # Profitability analysis
│   ├── benchmark_rm_report.py  # Market benchmarking
│   ├── airbnb_market_analysis.py  # Inside Airbnb open-data pipeline
│   ├── build_market_map.py     # Leaflet.js map generator
│   └── reviews_nlp_phase8.py   # NLP review analysis (multilingual)
├── data/
│   └── public/                 # Anonymized exports (52 files, CSV + Parquet)
│       ├── fact_reservations   # 34K+ booking records
│       ├── fact_reviews        # 6,298 guest reviews with NLP output
│       ├── dim_property        # Building metadata (A-E, rounded coords)
│       └── ...
├── outputs/
│   ├── RevenuePilot_Dashboard.html   # Standalone demo dashboard
│   ├── BilbaoMarketMap.html          # Interactive market map
│   ├── LinkedIn_PostCalendar.html    # Content calendar demo
│   ├── figures/                      # 42 charts (PNG)
│   └── reports/                      # 11 markdown analysis reports
├── notebooks/
│   └── 01_kpis_base.ipynb      # KPI exploration notebook
├── requirements.txt
└── LICENSE
```
                    ┌─────────────┐
                    │  dim_date   │
                    └──────┬──────┘
                           │
┌──────────────┐    ┌──────▼──────────┐    ┌──────────────┐
│ dim_property │───▶│ fact_reservations│◀───│  dim_channel │
└──────────────┘    └──────┬──────────┘    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       fact_reviews  fact_gastos  fact_kpis_monthly
```
revenue-pilot-str-analytics/
├── index.html                  # Portfolio landing page (GitHub Pages)
├── assets/                     # Landing page assets (CSS, JS, images)
├── scripts/                    # Python pipeline (phases 0-8)
│   ├── etl_phase0.py           # Data loading & cleaning
│   ├── kpis_phase1.py          # KPI computation (RevPAR, ADR, occupancy)
│   ├── patterns_phase2.py      # Booking patterns & seasonality
│   ├── pricing_phase3.py       # Pricing analysis & elasticity
│   ├── train_models_phase4.py  # ML model training (LightGBM)
│   ├── powerbi_phase5.py       # Star schema export for Power BI
│   ├── gastos_phase6.py        # Profitability analysis
│   ├── benchmark_rm_report.py  # Market benchmarking
│   ├── airbnb_market_analysis.py  # Inside Airbnb open-data pipeline
│   ├── build_market_map.py     # Leaflet.js map generator
│   └── reviews_nlp_phase8.py   # NLP review analysis (multilingual)
├── data/
│   └── public/                 # Anonymized exports (52 files, CSV + Parquet)
│       ├── fact_reservations   # 34K+ booking records
│       ├── fact_reviews        # 6,298 guest reviews with NLP output
│       ├── dim_property        # Building metadata (A-E, rounded coords)
│       └── ...
├── outputs/
│   ├── RevenuePilot_Dashboard.html   # Standalone demo dashboard
│   ├── BilbaoMarketMap.html          # Interactive market map
│   ├── LinkedIn_PostCalendar.html    # Content calendar demo
│   ├── figures/                      # 42 charts (PNG)
│   └── reports/                      # 11 markdown analysis reports
├── notebooks/
│   └── 01_kpis_base.ipynb      # KPI exploration notebook
├── requirements.txt
└── LICENSE
```

---

## 🤖 ML Models

| Model | Task | Algorithm | Key Metric |
|-------|------|-----------|------------|
| **A** | Demand Forecasting | LightGBM Regressor | MAE ±17.8pp |
| **B** | Cancellation Risk | LightGBM Classifier | AUC 0.821 |
| **C** | Price Recommendation | LightGBM Regressor | MAE ±€43 |

Model C uses Model A's demand prediction as an input feature, creating a stacked pipeline architecture.

---

## 📈 Key Results

| Metric | Value |
|--------|-------|
| Portfolio revenue analyzed | ~€2.25M |
| Net operating margin | 41.1% |
| Revenue upside identified | +€195K/year |
| Occupancy vs. market benchmark | 77.8% vs 47.6% |
| Reviews processed (NLP) | 6,298 |
| ML features engineered | 47 total |
| Power BI DAX measures | 40+ |

---

## 🚀 Quick Start

```
revenue-pilot-str-analytics/
├── index.html                  # Portfolio landing page (GitHub Pages)
├── assets/                     # Landing page assets (CSS, JS, images)
├── scripts/                    # Python pipeline (phases 0-8)
│   ├── etl_phase0.py           # Data loading & cleaning
│   ├── kpis_phase1.py          # KPI computation (RevPAR, ADR, occupancy)
│   ├── patterns_phase2.py      # Booking patterns & seasonality
│   ├── pricing_phase3.py       # Pricing analysis & elasticity
│   ├── train_models_phase4.py  # ML model training (LightGBM)
│   ├── powerbi_phase5.py       # Star schema export for Power BI
│   ├── gastos_phase6.py        # Profitability analysis
│   ├── benchmark_rm_report.py  # Market benchmarking
│   ├── airbnb_market_analysis.py  # Inside Airbnb open-data pipeline
│   ├── build_market_map.py     # Leaflet.js map generator
│   └── reviews_nlp_phase8.py   # NLP review analysis (multilingual)
├── data/
│   └── public/                 # Anonymized exports (52 files, CSV + Parquet)
│       ├── fact_reservations   # 34K+ booking records
│       ├── fact_reviews        # 6,298 guest reviews with NLP output
│       ├── dim_property        # Building metadata (A-E, rounded coords)
│       └── ...
├── outputs/
│   ├── RevenuePilot_Dashboard.html   # Standalone demo dashboard
│   ├── BilbaoMarketMap.html          # Interactive market map
│   ├── LinkedIn_PostCalendar.html    # Content calendar demo
│   ├── figures/                      # 42 charts (PNG)
│   └── reports/                      # 11 markdown analysis reports
├── notebooks/
│   └── 01_kpis_base.ipynb      # KPI exploration notebook
├── requirements.txt
└── LICENSE
```bash
# Clone
git clone https://github.com/MikelCerio/revenue-pilot-str-analytics
cd revenue-pilot-str-analytics

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (uses anonymized data in data/public/)
python scripts/etl_phase0.py
python scripts/kpis_phase1.py
python scripts/train_models_phase4.py

# Open the portfolio page
open index.html

# Open the interactive dashboard demo
open outputs/RevenuePilot_Dashboard.html
```
revenue-pilot-str-analytics/
├── index.html                  # Portfolio landing page (GitHub Pages)
├── assets/                     # Landing page assets (CSS, JS, images)
├── scripts/                    # Python pipeline (phases 0-8)
│   ├── etl_phase0.py           # Data loading & cleaning
│   ├── kpis_phase1.py          # KPI computation (RevPAR, ADR, occupancy)
│   ├── patterns_phase2.py      # Booking patterns & seasonality
│   ├── pricing_phase3.py       # Pricing analysis & elasticity
│   ├── train_models_phase4.py  # ML model training (LightGBM)
│   ├── powerbi_phase5.py       # Star schema export for Power BI
│   ├── gastos_phase6.py        # Profitability analysis
│   ├── benchmark_rm_report.py  # Market benchmarking
│   ├── airbnb_market_analysis.py  # Inside Airbnb open-data pipeline
│   ├── build_market_map.py     # Leaflet.js map generator
│   └── reviews_nlp_phase8.py   # NLP review analysis (multilingual)
├── data/
│   └── public/                 # Anonymized exports (52 files, CSV + Parquet)
│       ├── fact_reservations   # 34K+ booking records
│       ├── fact_reviews        # 6,298 guest reviews with NLP output
│       ├── dim_property        # Building metadata (A-E, rounded coords)
│       └── ...
├── outputs/
│   ├── RevenuePilot_Dashboard.html   # Standalone demo dashboard
│   ├── BilbaoMarketMap.html          # Interactive market map
│   ├── LinkedIn_PostCalendar.html    # Content calendar demo
│   ├── figures/                      # 42 charts (PNG)
│   └── reports/                      # 11 markdown analysis reports
├── notebooks/
│   └── 01_kpis_base.ipynb      # KPI exploration notebook
├── requirements.txt
└── LICENSE
```

---

## 🔒 Data Sources & Privacy

This project combines two very different data sources, handled differently:

**1. Market data — public and open**
Market benchmarking uses [Inside Airbnb](http://insideairbnb.com) open data
(1,561 listings). This is publicly available and reproducible by anyone.

**2. Portfolio data — anonymized operational data**
Operational figures come from a real 50-unit short-term rental portfolio,
published here only after a scripted anonymization pass:

- Building and unit names replaced with neutral labels (A–E, `A-01`)
- Commercial and brand names removed from all files, including free-text reviews
- Guest names, contact details and staff names removed; guest IDs hashed
- Coordinates rounded to 2 decimals (~1.1 km) — enough for market-level
  mapping, not enough to locate a specific building
- Internal P&L, cost structure and financing data excluded entirely

Anonymization is enforced by script, not by hand, and every build runs an
automated check that fails if any identifying term reaches the public export.
Ratios and distributions are preserved so the analysis remains valid.

---

## 👤 Author

**Mikel Cerio** — Revenue Manager & Data Analyst
- 💼 [LinkedIn](https://linkedin.com/in/mikelcerio)
- 🐙 [GitHub](https://github.com/MikelCerio)
- 📧 mikelcchinchurreta@gmail.com

---

## 📄 License

MIT License — data files excluded (proprietary). Code is freely reusable.
