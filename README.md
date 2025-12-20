# Fiscal Policy Impact Calculator

A web application for estimating the budgetary and economic effects of fiscal policy proposals using real IRS Statistics of Income data and CBO methodology.

**🚀 Live App:** https://laurencehw-fiscal-policy-calculator.streamlit.app

---

## Features

### Tax Policy Calculator
- Estimate revenue effects of tax rate changes
- Auto-populates taxpayer counts from real IRS data (2021-2022)
- Behavioral response modeling (Elasticity of Taxable Income)
- Capital gains scoring with realizations elasticity + baseline ingestion
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
fiscal-policy-calculator/
├── app.py                    # Streamlit web application
├── fiscal_model/             # Core scoring engine
│   ├── baseline.py           # Baseline budget projections
│   ├── policies.py           # Policy definitions
│   ├── scoring.py            # Static/dynamic scoring
│   ├── economics.py          # Economic feedback models
│   ├── uncertainty.py        # Uncertainty analysis
│   ├── reporting.py          # Output formatting
│   ├── data/                 # Data integration
│   │   ├── irs_soi.py        # IRS SOI data loader
│   │   ├── capital_gains.py  # Capital gains baseline + rate proxies
│   │   ├── fred_data.py      # FRED API integration
│   │   └── validation.py     # Data quality checks
│   ├── data_files/           # Static data files
│   │   └── irs_soi/          # IRS Statistics of Income CSVs
│   │   └── capital_gains/    # IRS SOI prelim XLS + documented rate proxies
│   └── validation/           # Model validation
│       ├── cbo_scores.py     # Known CBO/JCT scores database
│       └── compare.py        # Comparison framework
├── planning/                 # Project planning
│   ├── ROADMAP.md            # Long-term vision & roadmap
│   └── NEXT_SESSION.md       # Current priorities
└── docs/                     # Documentation
    ├── METHODOLOGY.md        # Scoring methodology
    └── ARCHITECTURE.md       # System design
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
3. **Capital Gains Realizations** - Realizations elasticity model (timing/lock-in), with baseline net capital gains by AGI for 2022 and documented 2023/2024 estimation
4. **Dynamic Scoring** - GDP feedback effects on revenue
5. **Fiscal Multipliers** - State-dependent (recession vs normal times)

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for details.

---

## Roadmap

**Vision**: Replicate methodologies from CBO, JCT, Penn Wharton, Yale Budget Lab, and Tax Policy Center in an interactive, transparent platform.

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core calculator & deployment | ✅ Complete |
| 2 | CBO methodology completion | 🔄 Current |
| 3 | Distributional analysis (TPC-style) | Planned |
| 4 | Penn Wharton OLG model | Planned |
| 5 | Yale Budget Lab modules (macro + microsim + behavioral + VAT + depreciation + trade) | Planned |
| 6 | Multi-model comparison platform | Future |

See [`planning/ROADMAP.md`](planning/ROADMAP.md) for full roadmap with technical details.

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
| [`planning/ROADMAP.md`](planning/ROADMAP.md) | Long-term vision and feature roadmap |
| [`planning/NEXT_SESSION.md`](planning/NEXT_SESSION.md) | Current session priorities |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Scoring methodology details |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Multi-model system design |

---

## License

MIT License

---

## Author

Built by Laurence Wilse-Samson | [lwilsesamson.com](https://lwilsesamson.com)

---

**Note:** This calculator is for educational and research purposes. Estimates may differ from official CBO scores due to simplified assumptions and data availability.
