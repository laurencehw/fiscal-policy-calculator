# Fiscal Policy Impact Calculator

[![Tests](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml/badge.svg)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-77%25-brightgreen)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fiscal-policy-calculator.streamlit.app)
![Python 3.10-3.13](https://img.shields.io/badge/Python-3.10--3.13-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Estimate the 10-year budgetary and economic effects of U.S. tax and spending proposals using CBO methodology, IRS data, and FRB/US-calibrated dynamic scoring.

**[Launch the app](https://fiscal-policy-calculator.streamlit.app)**

---

## What it does

The calculator scores fiscal policy proposals through a three-stage pipeline:

1. **Static scoring** — Direct revenue effect of rate/policy changes using IRS Statistics of Income data
2. **Behavioral adjustment** — Taxpayer response via the Elasticity of Taxable Income (ETI = 0.25, [Saez et al. 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf))
3. **Dynamic feedback** *(optional)* — GDP, employment, and interest rate effects using FRB/US-calibrated multipliers

### 39 pre-built proposals across 11 policy areas

| Category | Examples | Count |
|----------|----------|-------|
| TCJA / Individual | Full extension (+\$4.6T), rates only, no SALT cap | 3 |
| Corporate | Biden 28% (-\$1.35T), Trump 15% | 2 |
| International Tax | GILTI reform, FDII repeal, Pillar Two, Biden package | 4 |
| Tax Credits | Biden CTC (\$1.6T), EITC expansion | 3 |
| Estate Tax | TCJA extension, Biden reform, full repeal | 3 |
| Payroll / SS | Donut hole, eliminate cap, expand NIIT | 4 |
| AMT | Extend TCJA relief, repeal individual/corporate | 3 |
| ACA / Healthcare | Extend enhanced PTCs, repeal all PTCs | 2 |
| Tax Expenditures | SALT cap, employer health, step-up basis, charitable | 4 |
| IRS Enforcement | IRA funding, double enforcement, high-income targeting | 3 |
| Drug Pricing | Expanded negotiation, insulin cap, reference pricing | 4 |

Plus fully custom policy design with adjustable parameters.

### Additional features

- **Tariff scoring** — 5 presets (universal 10%, China 60%, autos 25%, reciprocal), consumer price impact by income quintile
- **State-level modeling** — Combined federal + state effective rates for top 10 states, with SALT cap interaction
- **OLG model** — 30-period Auerbach-Kotlikoff-style generational accounting for Social Security and Medicare reform
- **Classroom Mode** — 7 interactive assignments (intro → advanced), Laffer curve explorer, PDF export; accessible at `streamlit run classroom_app.py`
- **Real-Time Bill Tracker** — Pulls active bills from congress.gov, extracts fiscal provisions via LLM, stores in SQLite
- **Shareable preset links** — Generate deep links for supported preset tax proposals and preset spending programs directly from the results tab

### Validation

25+ policies validated against official CBO/JCT/Treasury scores:

| Policy | Official | Model | Error |
|--------|----------|-------|-------|
| TCJA Full Extension | \$4,600B | \$4,582B | 0.4% |
| Biden Corporate 28% | -\$1,347B | -\$1,397B | 3.7% |
| Biden GILTI Reform | -\$280B | -\$271B | 3.2% |
| FDII Repeal | -\$200B | -\$200B | 0.0% |
| Repeal Corporate AMT | \$220B | \$220B | 0.0% |
| Cap Employer Health | -\$450B | -\$450B | 0.1% |
| Biden CTC 2021 | \$1,600B | \$1,743B | 8.9% |
| SS Donut Hole \$250K | -\$2,700B | -\$2,371B | 12.2% |

---

## Quick start

### Use the web app

Visit **[fiscal-policy-calculator.streamlit.app](https://fiscal-policy-calculator.streamlit.app)** — no installation needed.

### Run locally

```bash
git clone https://github.com/laurencehw/fiscal-policy-calculator.git
cd fiscal-policy-calculator
pip install -r requirements.txt
streamlit run app.py          # Main policy calculator
streamlit run classroom_app.py  # Classroom mode
```

The repository pins Python `3.12` for local development via `.python-version`. CI verifies `3.10` through `3.13`, and the recommended Streamlit Cloud runtime is also `3.12`.

### Use the REST API

```bash
uvicorn api:app --reload
```

Key routes:

- `GET /presets` lists the full preset library with official-score metadata where available.
- `POST /score` supports generic `income_tax`, `corporate_tax`, and `payroll_tax` custom policies.
- `POST /score/preset` routes preset scoring through the same preset factory used by the Streamlit UI, including specialized policy modules such as TCJA, credits, payroll, PTC, trade, and climate presets.
- `POST /score/tariff` uses the tariff policy model instead of a standalone rough formula.

### Use as a Python library

```python
from fiscal_model import FiscalPolicyScorer, TaxPolicy, PolicyType

# Score a custom policy
policy = TaxPolicy(
    name="Top Rate Increase",
    description="Restore 39.6% rate for income above $400K",
    policy_type=PolicyType.INCOME_TAX,
    rate_change=0.026,
    affected_income_threshold=400_000,
)

scorer = FiscalPolicyScorer()
result = scorer.score_policy(policy, dynamic=True)

print(f"10-year cost: ${result.total_10_year_cost:,.0f}B")
print(f"Revenue feedback: ${result.revenue_feedback_10yr:,.0f}B")
```

```python
# Score a pre-built proposal
from fiscal_model import create_tcja_extension

policy = create_tcja_extension(extend_all=True)
result = FiscalPolicyScorer().score_policy(policy)
print(f"TCJA extension: ${result.total_10_year_cost:,.0f}B")
```

```python
# OLG model for long-run analysis
from fiscal_model.long_run import OLGModel
model = OLGModel()
result = model.score_social_security_reform(payroll_tax_change=0.02)
```

---

## Architecture

```
Policy Definition → Static Scoring → Behavioral Offset (ETI) → Dynamic Feedback (FRB/US)
                         ↓                    ↓                        ↓
                   ΔRate × Base         -ETI × 0.5 × static      GDP × marginal rate
```

### Module structure

| Module | Purpose |
|--------|---------|
| `scoring.py` | Main scoring orchestrator |
| `policies.py` | Policy base classes (Tax, Spending, Transfer) |
| `baseline.py` | CBO 10-year budget projections |
| `economics.py` | Dynamic effects, multipliers, GDP feedback |
| `distribution.py` | TPC/JCT-style distributional tables |
| `trade.py` | Tariff scoring, consumer price impact, retaliation |
| `international.py` | GILTI, FDII, Pillar Two, UTPR |
| `enforcement.py` | IRS enforcement revenue ROI |
| `pharma.py` | Drug pricing, Medicare negotiation |
| `corporate.py` | Corporate rate, pass-through, book minimum |
| `tcja.py` | TCJA extension with component breakdown |
| `credits.py` | CTC, EITC with phase-in/out |
| `estate.py` | Estate tax with exemption modeling |
| `payroll.py` | SS cap, donut hole, NIIT |
| `amt.py` | Individual and corporate AMT |
| `ptc.py` | ACA premium tax credits |
| `tax_expenditures.py` | SALT, mortgage, employer health |
| `models/macro_adapter.py` | FRB/US-calibrated dynamic scoring |
| `models/olg.py` | Overlapping generations model (Auerbach-Kotlikoff) |
| `microsim/` | Vectorized individual-level tax calculator |
| `long_run/` | Solow growth model, generational accounting |
| `models/state/` | Combined federal + state tax calculator (top 10 states) |
| `constants.py` | All parameters with source citations |
| `classroom/` | Assignment engine, feedback, PDF export |
| `bill_tracker/` | congress.gov pipeline, LLM extraction, SQLite |

### Data sources

- **IRS Statistics of Income** — Taxpayer counts and income by bracket (Tables 1.1, 3.3)
- **FRED** — GDP and macroeconomic indicators (St. Louis Fed)
- **CBO Baseline** — 10-year revenue, spending, and deficit projections (Feb 2026)
- **congress.gov API** — Active bill text and status (Bill Tracker)

---

## Methodology

The full methodology is documented in the app's **Methodology** tab and in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md). Key parameters:

| Parameter | Default | Source |
|-----------|---------|--------|
| Elasticity of Taxable Income | 0.25 | Saez, Slemrod & Giertz (2012) |
| Capital gains elasticity | 0.8 short / 0.4 long | CBO (2012), Dowd et al. (2015) |
| Spending multiplier (Year 1) | 1.4 | FRB/US |
| Tax multiplier (Year 1) | 0.7 | FRB/US |
| Multiplier decay | 0.75/year | FRB/US calibration |
| Okun's Law coefficient | 0.5 | Ball, Leigh & Loungani (2017) |
| Marginal revenue rate | 0.25 | CBO |
| Corporate tax incidence | 75% capital / 25% labor | CBO/TPC |

### Parameter sensitivity

Revenue estimates are sensitive to key behavioral parameters. The table below shows how a ±50% change in each parameter shifts the 10-year estimate for a representative income tax reform:

| Parameter | Range tested | Revenue impact |
|-----------|-------------|----------------|
| Elasticity of Taxable Income (ETI) | 0.12 – 0.40 | ±12% |
| Capital gains elasticity (long-run) | 0.20 – 0.60 | ±18% |
| Spending multiplier | 0.7 – 2.0 | ±8% (dynamic only) |
| Corporate tax elasticity | 0.12 – 0.40 | ±10% |

The app includes interactive sensitivity sliders to explore these ranges.

### When to use this model

- **Directional policy analysis** — Order-of-magnitude estimates for comparing proposals
- **Teaching fiscal policy** — Classroom mode with 7 structured assignments
- **Rapid prototyping** — Quickly score new proposals before detailed CBO/JCT analysis

### When NOT to use this model

- **Official scoring** — Use CBO/JCT for legislative budget estimates
- **Precise distributional analysis** — Bracket-level aggregates, not individual-level microsimulation
- **State-level precision** — Top 10 states only; representative taxpayer, not microsim
- **Complex dynamic effects** — Reduced-form FRB/US multipliers, not structural general equilibrium

### Known limitations

1. **Bracket-level microsimulation** — Uses IRS bracket aggregates; CPS-based individual simulation is a planned upgrade
2. **Simplified corporate pass-through** — Pass-through income not fully modeled
3. **State modeling approximate** — Top 10 states only; uses representative taxpayer, not microsim
4. **Reduced-form dynamic scoring** — Calibrated FRB/US multipliers, not structural GE model
5. **2-year data lag** — IRS SOI data from 2022; updated annually following IRS release (typically Q3)

### Data freshness

| Source | Vintage | Update cadence |
|--------|---------|----------------|
| IRS Statistics of Income | 2022 | Annual (~Q3 following tax season) |
| CBO Baseline | February 2026 | Quarterly with CBO publications |
| FRED macro data | Live / cached | Daily when API key is set |
| congress.gov bills | Live | On-demand via `scripts/update_bills.py` |

---

## Development

### Runtime contract

- Supported package range: Python `3.10` to `3.13`
- Local default: `.python-version` -> `3.12`
- Recommended Streamlit Cloud runtime: `3.12`
- Deployment checklist and incident guide: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

### Run tests

```bash
pip install -r requirements.txt pytest pytest-cov
pytest tests/ -v                        # 1051 tests
pytest tests/ --cov=fiscal_model        # With coverage (~77%)
```

### Verify against CBO/JCT scores

```bash
python -c "from fiscal_model.validation import run_validation_suite; run_validation_suite()"
```

### Verify public app availability

```bash
# Optional: override default URL used by the check
export FISCAL_POLICY_APP_URL="https://your-app.streamlit.app"

python scripts/check_public_app.py
```

### Lint

```bash
pip install ruff
ruff check fiscal_model/ tests/
```

### Reproducibility (dependency lock strategy)

- CI now exports a `pip freeze` lock snapshot artifact for each Python version.
- Use that artifact as the exact dependency lock for reproducing a CI run locally.

### Deployment smoke tests

- GitHub Actions now runs a dedicated `smoke` job for `app.py` and the core Streamlit controller path before the full matrix suite.
- The smoke suite is `tests/test_app_entrypoints.py` plus `tests/test_ui_controller_smoke.py`.

### Project structure

```
fiscal-policy-calculator/
├── app.py                    # Main Streamlit entry point
├── classroom_app.py          # Classroom mode Streamlit app
├── api.py                    # FastAPI endpoints
├── fiscal_model/             # Core scoring engine
│   ├── ui/                   # Streamlit UI components
│   │   └── tabs/             # Tab renderers (results, analysis, methodology)
│   ├── models/               # Macro adapters (FRB/US)
│   ├── long_run/             # OLG model, Solow growth
│   ├── state/                # State-level rate modeling
│   ├── data/                 # IRS SOI, FRED, capital gains loaders
│   ├── validation/           # CBO score comparison framework
│   └── constants.py          # All parameters with citations
├── classroom/                # Assignment engine, feedback, PDF export
├── bill_tracker/             # congress.gov pipeline, LLM extraction
├── tests/                    # 1051 tests
├── docs/                     # Methodology, architecture docs
├── planning/                 # Roadmap, session notes
└── pyproject.toml            # Project config, ruff, pytest
```

---

## REST API

The project includes a FastAPI REST API for programmatic access:

```bash
uvicorn api:app --reload        # Start API server
# Visit http://localhost:8000/docs for interactive Swagger documentation
```

Endpoints include `/score` (custom policies), `/presets` (list pre-built proposals), and `/score/tariff` (tariff scoring).

---

## Contributing

Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup instructions and guidelines.

The most impactful areas:

- **Multi-model comparison** — CBO-style, TPC microsim, dynamic side-by-side
- **CPS microsimulation** — Individual-level tax calculation using CPS ASEC data
- **New policy modules** — Climate/energy, immigration, housing, wealth tax
- **Data updates** — IRS SOI 2023, CBO auto-loader

Please open an issue first to discuss significant changes.

---

## References

1. Saez, Slemrod & Giertz (2012). "The Elasticity of Taxable Income." *JEL*, 50(1).
2. Auerbach & Gorodnichenko (2012). "Measuring Output Responses to Fiscal Policy." *AEJ: EP*, 4(2).
3. Christiano, Eichenbaum & Rebelo (2011). "When Is the Spending Multiplier Large?" *JPE*, 119(1).
4. CBO (2026). "The Budget and Economic Outlook: 2026 to 2036."
5. Treasury (2024). "General Explanations of the Administration's FY2025 Revenue Proposals."
6. Yale Budget Lab. [Dynamic Scoring Using FRB/US](https://budgetlab.yale.edu/research/dynamic-scoring-using-frbus-macroeconomic-model).
7. Auerbach & Kotlikoff (1987). *Dynamic Fiscal Policy*. Cambridge University Press.

---

## License

[MIT](LICENSE)
