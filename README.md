# Fiscal Policy Impact Calculator

A web application for estimating the budgetary and economic effects of fiscal policy proposals using real IRS Statistics of Income data and FRED economic indicators.

## 🚀 Live Demo

**Coming soon:** `https://calculator.lwilsesamson.com`

## Features

- **Tax Policy Calculator** - Estimate revenue effects of tax rate changes
- **Real Data Integration** - Uses IRS SOI and FRED economic data
- **Interactive Charts** - Visualize year-by-year impacts
- **Auto-Population** - Automatically fills in taxpayer counts and income levels
- **Export Results** - Download as CSV or JSON

## How It Works

1. Select a tax rate change (-10% to +10%)
2. Choose income threshold (e.g., "$500K+")
3. Click "Calculate Impact"
4. See revenue effect, distributional impact, and charts

The calculator uses Congressional Budget Office (CBO) methodology and real IRS data from 2021-2022.

## Technology

- **Backend:** Python, NumPy, Pandas
- **Frontend:** Streamlit
- **Charts:** Plotly
- **Data:** IRS Statistics of Income, FRED API

## Data Sources

- IRS Statistics of Income (SOI) Individual Income Tax Statistics
- Federal Reserve Economic Data (FRED)
- CBO Budget and Economic Outlook

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

This app is deployed on Streamlit Cloud.

See `QUICK_DEPLOY.md` for deployment instructions.

## Project Structure

```
fiscal_model/
├── __init__.py           # Package exports
├── policies.py           # Policy parameter definitions
├── baseline.py           # Baseline budget projections
├── scoring.py            # Static and dynamic scoring engine
├── economics.py          # Economic feedback models
├── data/
│   ├── irs_soi.py       # IRS data loader
│   ├── fred_data.py     # FRED API integration
│   └── validation.py    # Data quality checks
└── data_files/
    └── irs_soi/         # IRS CSV data files

app.py                    # Streamlit web application
```

## Methodology

See `docs/METHODOLOGY.md` for detailed information on:
- Revenue estimation formulas
- Behavioral response parameters
- Fiscal multiplier calibration
- CBO methodology references

## License

MIT License

## Author

Built by [Your Name] | [lwilsesamson.com](https://lwilsesamson.com)

---

**Note:** This calculator is for educational and research purposes. Estimates may differ from official CBO scores due to simplified assumptions and data availability.
