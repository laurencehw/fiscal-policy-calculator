# Fiscal Policy Impact Calculator

[![Tests](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml/badge.svg)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)
[![Coverage Gate](https://img.shields.io/badge/coverage_gate-85%25-brightgreen)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)
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

### 49 pre-built proposals across 14 policy areas

| Category | Examples | Count |
|----------|----------|-------|
| TCJA / Individual | Full extension (+\$4.6T), rates only, no SALT cap | 4 |
| Income Tax | Progressive millionaire tax, middle-class tax cut, flat tax reform | 3 |
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
| Trade / Tariffs | Universal 10%, China 60%, autos 25%, reciprocal tariffs | 5 |
| Climate / Energy | IRA repeal, carbon tax paths, methane fee repeal | 5 |

Plus fully custom policy design with adjustable parameters.

### Additional features

- **Tariff scoring** — 5 presets (universal 10%, China 60%, autos 25%, reciprocal), consumer price impact by income quintile
- **State-level modeling** — Combined federal + state effective rates for top 10 states, with SALT cap interaction
- **OLG model** — 30-period Auerbach-Kotlikoff-style generational accounting for Social Security and Medicare reform
- **Classroom Mode** — 7 interactive assignments (intro → advanced), Laffer curve explorer, PDF export; accessible at `streamlit run classroom_app.py`
- **Real-Time Bill Tracker** — Pulls active bills from congress.gov, extracts fiscal provisions via LLM, stores in SQLite
- **Shareable preset links** — Generate deep links for supported preset tax proposals and preset spending programs directly from the results tab; custom policies still fall back to export-only
- **Result-level validation evidence** — Each standard result summary surfaces the calibrated category, benchmark count, observed error band, holdout status, and known caveats before users interpret the headline score

### Validation

Two-dimensional validation — revenue-level and distributional — against published CBO, JCT, and Treasury analyses.

**Revenue accuracy** (25+ policies; see [`docs/VALIDATION.md`](docs/VALIDATION.md) for the full table):

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

**Distributional accuracy** — 6 benchmarks wired end-to-end against the distributional engine. Accuracy is the mean absolute share error across each benchmark's income groups; live numbers are exposed via `GET /benchmarks` and `scripts/run_validation_dashboard.py`.

| Benchmark | Source | Rating | Err (pp) |
|-----------|--------|--------|---------:|
| TCJA 2018, deciles | CBO 54796 | **excellent** | 0.00 |
| TCJA 2019, AGI class | JCT JCX-68-17 | good | 2.10 |
| ARP 2021, quintiles | CBO 56952 | acceptable | 7.54 |
| SALT cap repeal 2024, AGI class | JCT JCX-4-24 | **excellent** | 0.00 |
| Corporate 28% 2022, AGI class | JCT JCX-32-21 | good | 2.51 |
| TCJA ext 2026, deciles | CBO 60007 | **excellent** | 0.74 |

`≤ 2pp = excellent`, `≤ 5pp = good`, `≤ 10pp = acceptable`. See [`docs/VALIDATION_NOTES.md`](docs/VALIDATION_NOTES.md) for root-cause analysis of the ARP residual and the calibration work that brought every other benchmark below 3pp.

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

The repository pins Python `3.12` for local development via `.python-version`. CI verifies `3.10` through `3.13`, the `smoke` job exercises the Streamlit boot path before the full matrix, and the recommended Streamlit Cloud runtime is also `3.12`.

### Use the REST API

```bash
uvicorn api:app --reload
```

Key routes:

- `GET /presets` lists the full preset library with official-score metadata where available.
- `POST /score` supports generic `income_tax`, `corporate_tax`, and `payroll_tax` custom policies.
- `POST /score/preset` routes preset scoring through the same preset factory used by the Streamlit UI, including specialized policy modules such as TCJA, credits, payroll, PTC, trade, and climate presets.
- `POST /score/tariff` uses the tariff policy model instead of a standalone rough formula.
- Score responses include a `credibility` block with benchmark category, calibrated-vs-generic evidence type, implied uncertainty range, known limitations, and a `holdout_status` field backed by the locked post-change holdout protocol.
- `GET /validation/scorecard` exposes the consolidated revenue benchmark table, calibrated/generic/holdout counts, and a flattened `issues` list for material revenue benchmark problems.
- `GET /benchmarks` lists distributional benchmark accuracy and includes a flattened `issues` list if any benchmark needs improvement.
- `GET /summary` combines health, distributional benchmarks, microdata coverage, auth status, and a flattened `issues` list for dashboards.
- `GET /readiness` combines runtime, health, distribution benchmark, and revenue scorecard checks into one machine-readable verdict: `ready`, `ready_with_warnings`, or `not_ready`.
- `GET /health` exposes Python runtime compatibility, baseline vintage, IRS/FRED freshness, microdata coverage, fallback status, and a flattened health `issues` list.

Status-oriented endpoints use the same issue shape so dashboards can consume them without endpoint-specific parsing: `surface`, `severity`, `name`, `message`, and `details`.

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
| `scoring.py` | Public scoring facade re-exporting `scoring_engine.py` and `scoring_result.py` |
| `policies.py` | Public policy facade re-exporting `policies_core.py` and `policies_factory.py` |
| `baseline.py` | CBO 10-year budget projections |
| `economics.py` | Dynamic effects, multipliers, GDP feedback |
| `distribution.py` | Public distribution facade over core, grouping, effects, engine, and reporting modules |
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
| `tax_expenditures.py` | Public tax-expenditure facade over core tables and policy factories |
| `models/macro_adapter.py` | Public macro adapter facade over FRB/US, simple multiplier, and scenario-conversion modules |
| `models/olg.py` | Overlapping generations model (Auerbach-Kotlikoff) |
| `microsim/` | Vectorized individual-level tax calculator |
| `long_run/` | Solow growth model, generational accounting |
| `models/state/` | Combined federal + state tax calculator (top 10 states) |
| `validation/compare.py` | Compatibility facade over the refactored validation core, scenarios, reporting, and specialized suites |
| `ui/` | Controller-based Streamlit UI with decomposed input, settings, runtime logging, and share-link helpers |
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

1. **Current microsim is synthetic, not CPS-based** — The vectorized tax-unit engine captures bracket interactions (CTC, EITC, AMT, SALT, NIIT) but does not yet use CPS ASEC microdata
2. **Simplified corporate pass-through** — Pass-through income not fully modeled
3. **State modeling approximate** — Top 10 states only; uses representative taxpayer, not microsim
4. **Reduced-form dynamic scoring** — Calibrated FRB/US multipliers, not structural GE model
5. **Aging source data** — IRS SOI data currently tops out at 2022; updated annually following IRS release (typically Q3)
6. **Distributional benchmarks are still narrow** — Current distributional validation is benchmarked mainly to published TPC tables, not a broader CBO distributional set

### Data freshness

| Source | Vintage | Update cadence |
|--------|---------|----------------|
| IRS Statistics of Income | 2022 | Annual (~Q3 following tax season) |
| CBO Baseline | February 2026 | Quarterly with CBO publications |
| FRED macro data | Live / cached / bundled seed | Daily when API key is set; bundled seed covers offline smoke/readiness paths |
| congress.gov bills | Live | On-demand via `scripts/update_bills.py` |

### Manuscript readiness

For a citation-grade roadmap focused on manuscript quality rather than just app polish, see [planning/MANUSCRIPT_95_PLUS.md](planning/MANUSCRIPT_95_PLUS.md).

---

## Development

### Runtime contract

- Supported package range: Python `3.10` to `3.13`
- Local default: `.python-version` -> `3.12`
- Recommended Streamlit Cloud runtime: `3.12`
- Current CI contract: passing `smoke` job plus full `3.10`-`3.13` matrix on `main`
- The `/health` response includes a `runtime` component and marks unsupported Python versions, such as `3.14`, as `degraded`.
- Deployment checklist and incident guide: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

### Run tests

```bash
pip install -r requirements.txt pytest pytest-cov
python -m pytest tests/ -v
python -m pytest tests/ --cov=fiscal_model
```

### Verify against CBO/JCT scores

```bash
python -c "from fiscal_model.validation import run_validation_suite; run_validation_suite()"
```

### Verify release readiness

```bash
python scripts/check_readiness.py
python scripts/check_readiness.py --strict
python scripts/check_readiness.py --json > readiness-report.json
```

Default mode exits non-zero only when the verdict is `not_ready`. Strict mode is the CI release gate: it still reports every warning, but only blocks on actual failures or non-environmental warnings. A tracked FRED seed keeps isolated CI runners off the hardcoded GDP fallback; if the seed and cache are both unavailable, offline FRED/cache fallback warnings remain visible without failing strict CI.

### Verify public app availability

```bash
# Optional: override default URL used by the check
export FISCAL_POLICY_APP_URL="https://your-app.streamlit.app"

python scripts/check_public_app.py
```

The scheduled GitHub Actions public-health workflow runs the same check every six hours. Override the target deployment with the repository variable `FISCAL_POLICY_APP_URL`.
For an artifact-friendly report, run `python scripts/check_public_app.py --json`.

### Lint

```bash
pip install ruff
ruff check fiscal_model/ tests/
```

### Reproducibility (dependency lock strategy)

- `requirements-lock.txt` is the committed `pip-compile` lock for the Python `3.12` production/runtime path.
- The `smoke` CI job installs from `requirements-lock.txt`, so lockfile breakage is exercised before the full matrix suite runs.
- The broader `3.10`-`3.13` matrix still installs from `requirements.txt` to verify the supported version range.
- Refresh the lock intentionally from Python `3.12`:

```bash
python3.12 -m venv .lockvenv
.lockvenv/bin/pip install pip-tools
.lockvenv/bin/pip-compile --strip-extras --output-file=requirements-lock.txt requirements.txt
```

### Deployment smoke tests

- GitHub Actions now runs a dedicated `smoke` job for `app.py` and the core Streamlit controller path before the full matrix suite.
- The smoke suite is `tests/test_app_entrypoints.py` plus `tests/test_ui_controller_smoke.py`.
- The `readiness` job runs `python scripts/check_readiness.py --strict` on Python `3.12` and uploads `readiness-report.json`.
- The `smoke` job also runs `python scripts/check_streamlit_boot.py --timeout 45`, which starts Streamlit locally and checks the calculator and classroom-mode URLs return the app shell.
- The `validation-dashboard` and `public-app-health` workflows upload JSON artifacts with flattened `issues` arrays for monitoring and release triage.

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
├── tests/                    # Automated test suite
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

For production deployments, set `FISCAL_API_KEYS=label1:secret1,label2:secret2` to require an `X-API-Key` header on scoring endpoints. Rate limiting is always on (defaults: 60/min with burst 20, per-key when auth is on, per-IP otherwise). See [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the full API-hardening reference.

---

## Documentation

- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — three-stage scoring, parameter citations, behavioral and dynamic assumptions
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — module layout, dependency graph, extensibility patterns
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — full benchmark matrix against CBO/JCT/Treasury scores
- [`docs/VALIDATION_NOTES.md`](docs/VALIDATION_NOTES.md) — root-cause analysis for high-error outliers
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Streamlit Cloud + custom deployment notes
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — material changes to features and the API

---

## Contributing

Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup instructions and guidelines.

The most impactful areas:

- **Multi-model comparison platform** — Planned CBO/TPC/PWBM-style side-by-side scoring
- **CPS microsimulation upgrade** — Planned move from synthetic tax units to CPS ASEC-based microdata
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
