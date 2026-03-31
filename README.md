# Fiscal Policy Impact Calculator

[![Tests](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml/badge.svg)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://laurencehw-fiscal-policy-calculator.streamlit.app)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Estimate the 10-year budgetary and economic effects of U.S. tax and spending proposals using CBO methodology, IRS data, and FRB/US-calibrated dynamic scoring.

**[Launch the app](https://laurencehw-fiscal-policy-calculator.streamlit.app)**

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

Visit **[laurencehw-fiscal-policy-calculator.streamlit.app](https://laurencehw-fiscal-policy-calculator.streamlit.app)** — no installation needed.

### Run locally

```bash
git clone https://github.com/laurencehw/fiscal-policy-calculator.git
cd fiscal-policy-calculator
pip install -r requirements.txt
streamlit run app.py
```

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
| `constants.py` | All parameters with source citations |

### Data sources

- **IRS Statistics of Income** — Taxpayer counts and income by bracket (Tables 1.1, 3.3)
- **FRED** — GDP and macroeconomic indicators (St. Louis Fed)
- **CBO Baseline** — 10-year revenue, spending, and deficit projections (Feb 2024)

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

### Known limitations

1. **No microsimulation** — Uses bracket-level IRS data, not individual tax returns
2. **Simplified corporate** — Pass-through income not fully modeled
3. **Federal only** — No state or local tax interactions
4. **Reduced-form dynamic scoring** — Calibrated multipliers, not structural GE model
5. **2-year data lag** — IRS SOI data from 2022

---

## Development

### Run tests

```bash
pip install -r requirements.txt pytest pytest-cov
pytest tests/ -v                        # 382 tests
pytest tests/ --cov=fiscal_model        # With coverage (~57%)
```

### Lint

```bash
pip install ruff
ruff check fiscal_model/ tests/
```

### Project structure

```
fiscal-policy-calculator/
├── app.py                    # Streamlit entry point
├── fiscal_model/             # Core scoring engine
│   ├── ui/                   # Streamlit UI components
│   │   └── tabs/             # Tab renderers (results, analysis, methodology)
│   ├── models/               # Macro adapters (FRB/US)
│   ├── data/                 # IRS SOI, FRED, capital gains loaders
│   ├── validation/           # CBO score comparison framework
│   └── constants.py          # All parameters with citations
├── tests/                    # 382 tests
├── docs/                     # Methodology, architecture docs
├── planning/                 # Roadmap, session notes
└── pyproject.toml            # Project config, ruff, pytest
```

---

## Contributing

Contributions welcome. The most impactful areas:

- **New policy modules** — Trade policy, immigration, climate/energy
- **Microsimulation** — Individual-level tax calculation using CPS data
- **Test coverage** — Currently ~57%, targeting 70%+
- **Accessibility** — Screen reader support, mobile responsive

Please open an issue first to discuss significant changes.

---

## References

1. Saez, Slemrod & Giertz (2012). "The Elasticity of Taxable Income." *JEL*, 50(1).
2. Auerbach & Gorodnichenko (2012). "Measuring Output Responses to Fiscal Policy." *AEJ: EP*, 4(2).
3. Christiano, Eichenbaum & Rebelo (2011). "When Is the Spending Multiplier Large?" *JPE*, 119(1).
4. CBO (2024). "The Budget and Economic Outlook: 2024 to 2034."
5. Treasury (2024). "General Explanations of the Administration's FY2025 Revenue Proposals."
6. Yale Budget Lab. [Dynamic Scoring Using FRB/US](https://budgetlab.yale.edu/research/dynamic-scoring-using-frbus-macroeconomic-model).

---

## License

[MIT](LICENSE)
