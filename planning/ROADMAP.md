# Fiscal Policy Calculator — Roadmap

> An open-source platform for transparent fiscal policy scoring using CBO methodology, real IRS data, and FRB/US-calibrated dynamic analysis.

---

## Current state (April 2026)

### What's built

- **39 pre-built policy proposals** across 11 categories (TCJA, corporate, international, credits, estate, payroll, AMT, ACA, tax expenditures, IRS enforcement, drug pricing)
- **CBO-style three-stage scoring**: static + behavioral (ETI) + dynamic (FRB/US)
- **Distributional analysis**: TPC/JCT-style tables by quintile, decile, and dollar brackets
- **Tariff scoring**: 5 presets with consumer price impact by quintile
- **Microsimulation engine**: MFJ brackets, SALT, AMT, EITC, NIIT
- **FastAPI endpoints**: `/health`, `/presets`, `/score`, `/score/tariff`
- **OLG model**: 30-period Auerbach-Kotlikoff-style for SS/Medicare reform and generational accounting
- **Classroom Mode**: 7 assignments (intro → advanced), PDF export, 80 tests
- **State-Level Modeling**: top 10 states, SALT interaction, combined rate curves
- **Real-Time Bill Tracker**: congress.gov pipeline, LLM extraction, SQLite storage
- **Interactive Streamlit app** with methodology documentation, sensitivity analysis, comparison tools, CSV export
- **25+ policies validated** against CBO/JCT/Treasury within 15%
- **685 tests**, 72% coverage, ruff linting, GitHub Actions CI
- **Real data integration**: IRS Statistics of Income, FRED, CBO Baseline

### Policy modules

| Module | Policies | Validation |
|--------|----------|------------|
| `tcja.py` | Full extension, rates only, no SALT cap | 0.4% error |
| `corporate.py` | Biden 28%, Trump 15%, book minimum, R&D | 3.7% error |
| `international.py` | GILTI, FDII, Pillar Two, UTPR | 3.2% error |
| `credits.py` | CTC, EITC expansions | 8.9% error |
| `estate.py` | TCJA extension, Biden reform, repeal | 10.1% error |
| `payroll.py` | SS cap, donut hole, NIIT | 12.2% error |
| `amt.py` | Individual/corporate AMT | 0.0% error |
| `ptc.py` | ACA premium tax credits | Validated |
| `tax_expenditures.py` | SALT, employer health, step-up, charitable | 0.1% error |
| `enforcement.py` | IRS funding ROI with diminishing returns | Calibrated |
| `pharma.py` | Drug negotiation, insulin cap, reference pricing | Calibrated |

---

## Next priorities

### Multi-model comparison platform
Run the same policy through CBO-style, TPC-style (microsim), and FRB/US dynamic models side by side. Show divergences and explain why. This is the most impactful remaining architectural feature.

### CPS microsimulation
Replace IRS bracket-level data with CPS ASEC microdata for distributional analysis. Would significantly improve accuracy for complex provision interactions (AMT + SALT + CTC phase-outs).

### Additional policy modules
- **Climate/energy** — IRA clean energy credits, carbon pricing, EV incentives
- **Immigration** — Workforce effects on payroll tax base, GDP growth
- **Housing** — Mortgage deduction reform, first-time buyer credits, LIHTC
- **Wealth tax** — Unrealized gains, mark-to-market proposals

---

## Technical roadmap

### Production hardening
- Docker containerization
- `requirements-lock.txt` with pinned versions (`pip-compile`)
- Security scanning (bandit)
- Structured logging throughout
- Data freshness monitoring

### Data updates
- IRS SOI 2023 data (filed 2024, published ~2025)
- CBO baseline auto-loader from `cbo.gov`

---

## Architecture vision

```
                    ┌─────────────────┐
                    │   Streamlit UI  │
                    │   + FastAPI     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Policy Engine  │
                    │  (scoring.py)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
     │ Static Score  │ │Behavioral│ │  Dynamic    │
     │ (IRS data)    │ │ (ETI)    │ │ (FRB/US)   │
     └───────────────┘ └──────────┘ └─────────────┘
              │              │              │
     ┌────────▼──────────────▼──────────────▼──────┐
     │              Data Layer                      │
     │  IRS SOI  │  FRED  │  CBO  │  CPS ASEC     │
     └─────────────────────────────────────────────┘
```

---

## Contributing

See the [README](../README.md) for setup instructions. The most impactful contributions:

1. **Multi-model comparison** — CBO-style, TPC microsim, dynamic side-by-side
2. **New policy modules** — Climate, immigration, housing, wealth tax
3. **CPS microsimulation** — Individual-level tax calculation
4. **Data updates** — IRS SOI 2023, CBO auto-loader
