# Fiscal Policy Impact Calculator

A web application for estimating the budgetary and economic effects of fiscal policy proposals using real IRS Statistics of Income data and CBO methodology.

**🚀 Live App:** https://laurencehw-fiscal-policy-calculator.streamlit.app

---

## Features

### Tax Policy Calculator
- Estimate revenue effects of tax rate changes
- Auto-populates taxpayer counts from real IRS data (2021-2022)
- Behavioral response modeling (Elasticity of Taxable Income)
- Static and dynamic scoring options

### Spending Policy Calculator
- Infrastructure, defense, and social program spending
- Fiscal multiplier effects on GDP
- One-time vs recurring spending analysis

### Policy Comparison Tool
- Compare 2-4 policies side-by-side
- 10-year budget impact charts
- Year-by-year timeline comparison

### Preset Policies
- TCJA 2017 High-Income Cut
- Biden 2025 Proposal
- Progressive Millionaire Tax
- Middle Class Tax Cut
- And more...

---

## Quick Start

### Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Use Online
Visit: https://laurencehw-fiscal-policy-calculator.streamlit.app

---

## Project Structure

```
Budget tool/
├── app.py                    # Streamlit web application
├── fiscal_model/             # Core scoring engine
│   ├── baseline.py           # Baseline budget projections
│   ├── policies.py           # Policy definitions
│   ├── scoring.py            # Static/dynamic scoring
│   ├── economics.py          # Economic feedback models
│   └── data/                 # Data integration
│       ├── irs_soi.py        # IRS SOI data loader
│       └── fred_data.py      # FRED API integration
├── planning/                 # Project planning
│   ├── ROADMAP.md            # Long-term vision & roadmap
│   └── NEXT_SESSION.md       # Current priorities
├── docs/                     # Documentation
│   ├── METHODOLOGY.md        # Scoring methodology
│   ├── ARCHITECTURE.md       # System design
│   └── DEPLOYMENT.md         # Deployment guide
└── archive/                  # Historical session notes
```

---

## Data Sources

| Source | Data | Usage |
|--------|------|-------|
| [IRS SOI](https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics) | Tax returns by income bracket | Auto-population, revenue estimates |
| [FRED](https://fred.stlouisfed.org) | GDP, unemployment, interest rates | Economic baseline, multipliers |
| [CBO](https://www.cbo.gov) | Budget projections, methodology | Scoring framework |

---

## Methodology

The calculator uses Congressional Budget Office (CBO) methodology:

1. **Static Scoring** - Direct revenue effect from rate changes
2. **Behavioral Response** - Taxpayer response via ETI (Elasticity of Taxable Income)
3. **Dynamic Scoring** - GDP feedback effects on revenue
4. **Fiscal Multipliers** - State-dependent (recession vs normal times)

See `docs/METHODOLOGY.md` for details.

---

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core calculator & deployment | ✅ Complete |
| 2 | CBO validation | 🔄 Current |
| 3 | Distributional analysis | Planned |
| 4 | Trade policy calculator | Planned |
| 5 | Multi-model platform | Future |

See `planning/ROADMAP.md` for full roadmap.

---

## Technology

- **Backend:** Python, NumPy, Pandas
- **Frontend:** Streamlit
- **Charts:** Plotly
- **Hosting:** Streamlit Cloud (free)
- **Data:** IRS SOI, FRED API

---

## Documentation

| Document | Description |
|----------|-------------|
| `planning/ROADMAP.md` | Long-term vision and feature roadmap |
| `planning/NEXT_SESSION.md` | Current session priorities |
| `docs/METHODOLOGY.md` | Scoring methodology details |
| `docs/ARCHITECTURE.md` | Multi-model system design |
| `docs/DEPLOYMENT.md` | Deployment and hosting guide |

---

## License

MIT License

---

## Author

Built by Laurence Wilse-Samson | [lwilsesamson.com](https://lwilsesamson.com)

---

**Note:** This calculator is for educational and research purposes. Estimates may differ from official CBO scores due to simplified assumptions and data availability.
