# Fiscal Policy Calculator — Roadmap

> An open-source platform for transparent fiscal policy scoring using CBO methodology, real IRS data, and FRB/US-calibrated dynamic analysis.

---

## Current state (March 2026)

### What's built

- **39 pre-built policy proposals** across 11 categories (TCJA, corporate, international, credits, estate, payroll, AMT, ACA, tax expenditures, IRS enforcement, drug pricing)
- **CBO-style three-stage scoring**: static + behavioral (ETI) + dynamic (FRB/US)
- **Distributional analysis**: TPC/JCT-style tables by quintile, decile, and dollar brackets
- **Interactive Streamlit app** with methodology documentation, sensitivity analysis, comparison tools, CSV export
- **25+ policies validated** against CBO/JCT/Treasury within 15%
- **382 tests**, ~57% coverage, ruff linting, GitHub Actions CI
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

### Trade and tariff policy
- Tariff revenue scoring (ad valorem and specific duties)
- Consumer price effects (pass-through rates by sector)
- Retaliation scenarios and trade flow modeling
- Industry-level employment impacts

### Microsimulation engine
- Individual-level tax calculation using CPS ASEC microdata
- Captures complex provision interactions (AMT + SALT + CTC phase-outs)
- More accurate distributional analysis
- Prototype exists (`microsim/`) — needs production hardening

### Multi-model comparison
- Run the same policy through CBO-style, TPC-style, and dynamic models side by side
- Explain why models diverge
- Model selector in the UI

### Additional policy modules
- **Climate/energy**: IRA clean energy credits, carbon pricing, EV incentives
- **Immigration**: Workforce effects on payroll tax base, GDP growth
- **Housing**: Mortgage deduction reform, first-time buyer credits, LIHTC
- **Wealth tax**: Unrealized gains, mark-to-market proposals

---

## Technical roadmap

### Test coverage to 70%+
- Streamlit component tests using `AppTest`
- Integration tests for full scoring pipeline
- Validation suite as automated CI tests

### Production hardening
- Docker containerization
- Dependency pinning (`pip-compile`)
- Security scanning (bandit)
- Structured logging throughout
- Data freshness monitoring

### API
- FastAPI endpoint for programmatic scoring
- JSON input/output for policy definitions
- Batch scoring for policy packages

### Long-run modeling
- Overlapping Generations (OLG) framework (Penn Wharton style)
- 30+ year projections for Social Security and Medicare
- Capital stock evolution and crowding out
- Generational accounting

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

1. **New policy modules** — Trade, climate, immigration, housing
2. **Microsimulation** — CPS-based individual tax calculation
3. **Test coverage** — Currently ~57%, target 70%+
4. **Data updates** — IRS SOI 2023 when available
