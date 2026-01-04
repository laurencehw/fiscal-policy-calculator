# Fiscal Policy Impact Calculator

[![Tests](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml/badge.svg)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)

A professional-grade web application for estimating budgetary and economic effects of fiscal policy proposals. Uses real IRS Statistics of Income data and CBO/JCT methodology, with 25+ policies validated within 15% of official scores.

**Live App:** https://laurencehw-fiscal-policy-calculator.streamlit.app

---

## Features

### Policy Scoring Engine
- **25+ validated policies** — TCJA, corporate tax, credits, estate, payroll, AMT, ACA, tax expenditures
- **CBO/JCT methodology** — Static scoring, behavioral responses (ETI), dynamic feedback
- **Real IRS data** — Auto-populates taxpayer counts from 2021-2022 SOI tables
- **Compare to CBO** — Side-by-side model vs official score comparison with accuracy ratings

### Policy Types Supported
| Category | Examples | Validation |
|----------|----------|------------|
| Income Tax | Biden $400K+, TCJA extension | 0.4-1% error |
| Corporate | Biden 28%, Trump 15% | 3.7% error |
| Tax Credits | CTC, EITC expansions | 0.9-8.9% error |
| Estate Tax | TCJA extension, Biden reform | 10% error |
| Payroll | SS cap reforms, NIIT expansion | 12% error |
| AMT | Individual & corporate AMT | 0.1% error |
| ACA | Premium tax credits | 0.3-4.6% error |
| Tax Expenditures | SALT, mortgage, step-up basis | 0.1-10% error |

### Dynamic Scoring
- **FRB/US-calibrated multipliers** — Spending (1.4x), tax (-0.7x)
- **GDP and employment effects** — 10-year projections
- **Revenue feedback** — Macro effects on tax base
- **Crowding out** — Interest rate and deficit effects

### Distributional Analysis
- **TPC/JCT-style tables** — By quintile, decile, or dollar brackets
- **Winners/losers analysis** — Share of taxpayers affected
- **Top income breakout** — Top 1%, 0.1% detail

### Policy Package Builder
- **6 preset packages** — Biden FY2025, TCJA Extension, Progressive Revenue, etc.
- **Custom combinations** — Mix and match policies
- **Export** — JSON and CSV download

---

## Quick Start

### Run Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run fiscal-policy-calculator/app.py

# Run tests
pytest tests/ -v
```

### Use Online
Visit: https://laurencehw-fiscal-policy-calculator.streamlit.app

### Jupyter Notebook
See [`notebooks/example_usage.ipynb`](notebooks/example_usage.ipynb) for programmatic usage examples covering all policy types, distributional analysis, and dynamic scoring.

### API Documentation
Browse the [API docs](docs/api/index.html) or regenerate with:
```bash
python scripts/generate_docs.py
```

---

## Project Structure

```
fiscal-policy-calculator/
├── app.py                          # Streamlit web application
├── fiscal_model/                   # Core scoring engine
│   ├── scoring.py                  # Main scoring orchestrator
│   ├── policies.py                 # Policy base classes
│   ├── tcja.py                     # TCJA extension scoring
│   ├── corporate.py                # Corporate tax policies
│   ├── credits.py                  # Tax credits (CTC, EITC)
│   ├── estate.py                   # Estate tax policies
│   ├── payroll.py                  # Payroll tax (SS, Medicare, NIIT)
│   ├── amt.py                      # Alternative minimum tax
│   ├── ptc.py                      # Premium tax credits (ACA)
│   ├── tax_expenditures.py         # SALT, mortgage, step-up basis
│   ├── distribution.py             # Distributional analysis engine
│   ├── economics.py                # Economic feedback models
│   ├── baseline.py                 # CBO baseline projections
│   ├── models/
│   │   └── macro_adapter.py        # FRB/US integration
│   ├── data/
│   │   ├── irs_soi.py              # IRS SOI data loader
│   │   ├── capital_gains.py        # Capital gains baseline
│   │   └── fred_data.py            # FRED API integration
│   └── validation/
│       ├── cbo_scores.py           # Official CBO/JCT benchmarks
│       └── compare.py              # Validation framework
├── tests/                          # Unit tests (60 tests)
│   ├── test_distribution.py
│   └── test_macro_adapter.py
├── notebooks/
│   └── example_usage.ipynb         # Programmatic usage examples
├── planning/
│   ├── ROADMAP.md                  # Long-term vision
│   └── NEXT_SESSION.md             # Current priorities
├── scripts/
│   └── generate_docs.py            # API doc generator
└── docs/
    ├── METHODOLOGY.md              # Scoring methodology
    ├── VALIDATION.md               # CBO comparison report
    ├── ARCHITECTURE.md             # System design
    └── api/                        # Auto-generated API docs
```

---

## Validation Results

25+ policies validated against official CBO/JCT/TPC estimates:

| Policy | Official | Model | Error |
|--------|----------|-------|-------|
| TCJA Full Extension | $4,600B | $4,582B | 0.4% |
| Biden Corporate 28% | -$1,347B | -$1,397B | 3.7% |
| Biden CTC 2021 | $1,600B | $1,743B | 8.9% |
| SS Donut Hole $250K | -$2,700B | -$2,371B | 12.2% |
| Repeal Corporate AMT | $220B | $220B | 0.0% |
| Cap Employer Health | -$450B | -$450B | 0.1% |

See [`planning/NEXT_SESSION.md`](planning/NEXT_SESSION.md) for full validation table.

---

## Methodology

The calculator implements CBO/JCT scoring methodology:

1. **Static Scoring** — Direct revenue effect: `ΔRevenue = ΔRate × Base`
2. **Behavioral Response** — ETI-based offset: `Offset = -ETI × 0.5 × Static`
3. **Capital Gains** — Time-varying elasticity (0.8 short-run → 0.4 long-run)
4. **Dynamic Scoring** — FRB/US-calibrated GDP feedback
5. **Distributional** — TPC-style incidence by income group

Key parameters:
- **ETI**: 0.25 (Saez et al. 2012)
- **Spending multiplier**: 1.4 (FRB/US)
- **Tax multiplier**: -0.7 (FRB/US)
- **Corporate incidence**: 75% capital / 25% labor

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for details.

---

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core calculator & deployment | ✅ Complete |
| 2 | CBO methodology (25+ policies) | ✅ Complete |
| 3 | Distributional analysis | ✅ Complete |
| 4 | Dynamic scoring (FRB/US) | ✅ Complete |
| 5 | Policy packages & comparison | ✅ Complete |
| 6 | Documentation & CI/CD | 🔄 Current |
| 7 | Penn Wharton OLG model | Planned |
| 8 | Yale Budget Lab modules | Planned |

See [`planning/ROADMAP.md`](planning/ROADMAP.md) for full roadmap.

---

## Technology

- **Backend:** Python 3.10+, NumPy, Pandas, Pydantic
- **Frontend:** Streamlit, Plotly
- **Testing:** pytest (60 tests), GitHub Actions CI
- **Hosting:** Streamlit Cloud
- **Data:** IRS SOI, FRED API, CBO projections

---

## License

MIT License

---

## Author

Built by Laurence Wilse-Samson | NYU Wagner School of Public Policy

---

**Note:** This calculator is for educational and research purposes. Estimates may differ from official CBO scores due to simplified assumptions and data availability.
