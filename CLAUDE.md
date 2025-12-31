# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fiscal Policy Impact Calculator — a web app that estimates budgetary and economic effects of tax and spending proposals. Current draft Live at: https://laurencehw-fiscal-policy-calculator.streamlit.app

**Current Phase**: Phase 2 (CBO Methodology Completion) — see `planning/ROADMAP.md` for full roadmap.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run app locally
streamlit run app.py

# Run validation against CBO scores
python -c "from fiscal_model.validation import compare_to_cbo; compare_to_cbo()"
```

## Architecture

### Core Scoring Flow

```
Policy Definition → Static Scoring → Behavioral Offset (ETI) → Dynamic Feedback (optional)
                         ↓                    ↓                        ↓
                   ΔRate × Base         -ETI × 0.5 × static      GDP feedback × 0.25
```

### Module Structure

| Module | Purpose |
|--------|---------|
| `app.py` | Streamlit UI — policy inputs, results charts, comparison tool |
| `fiscal_model/scoring.py` | `FiscalPolicyScorer` — main scoring orchestrator |
| `fiscal_model/policies.py` | Policy classes: `TaxPolicy`, `CapitalGainsPolicy`, `SpendingPolicy`, `TransferPolicy` |
| `fiscal_model/baseline.py` | `CBOBaseline` — 10-year budget projections |
| `fiscal_model/economics.py` | `EconomicModel` — dynamic effects, multipliers, GDP feedback |
| `fiscal_model/data/irs_soi.py` | `IRSSOIData` — loads IRS Statistics of Income CSVs |
| `fiscal_model/data/capital_gains.py` | Capital gains baseline + realizations elasticity model |
| `fiscal_model/data/fred_data.py` | FRED API wrapper with caching |
| `fiscal_model/tcja.py` | `TCJAExtensionPolicy` — TCJA extension scoring with component breakdown |
| `fiscal_model/corporate.py` | `CorporateTaxPolicy` — Corporate rate changes, GILTI/FDII, pass-through |
| `fiscal_model/validation/cbo_scores.py` | Database of known CBO/JCT scores for validation |
| `fiscal_model/validation/compare.py` | Comparison framework (model vs official) |

### Data Files

- `fiscal_model/data_files/irs_soi/` — IRS SOI tables (Table 1.1 2021-2022)
- `fiscal_model/data_files/capital_gains/` — IRS SOI preliminary XLS + documented rate proxies

### Key Classes

```python
# Policy definition (model-agnostic)
TaxPolicy(
    name, rate_change, affected_income_threshold,
    taxable_income_elasticity=0.25, duration_years=10
)

CapitalGainsPolicy(
    name, rate_change, affected_income_threshold,
    baseline_realizations_billions, baseline_capital_gains_rate,
    # Time-varying elasticity (CBO/JCT methodology)
    short_run_elasticity=0.8,  # Years 1-3: timing effects
    long_run_elasticity=0.4,   # Years 4+: permanent response
    transition_years=3,
    # Step-up basis at death (Biden proposal)
    step_up_at_death=True,           # Current law
    eliminate_step_up=False,         # Set True to model step-up elimination
    step_up_exemption=1_000_000,     # Biden: $1M per person
    gains_at_death_billions=54.0,    # CBO estimate
    step_up_lock_in_multiplier=2.0,  # 5.3x matches PWBM revenue loss
)

# TCJA Extension (calibrated to CBO $4.6T)
from fiscal_model import create_tcja_extension
policy = create_tcja_extension(extend_all=True, keep_salt_cap=True)  # Full extension
policy = create_tcja_extension(extend_all=True, keep_salt_cap=False)  # No SALT cap (+$1.9T)
policy = create_tcja_extension(extend_all=False, extend_rate_cuts=True)  # Rates only (~$3.2T)

# Corporate Tax (calibrated to CBO -$1.35T for 21%→28%)
from fiscal_model import create_biden_corporate_rate_only, CorporateTaxPolicy
policy = create_biden_corporate_rate_only()  # Biden 21%→28% (-$1.35T)
policy = CorporateTaxPolicy(
    name="Custom Corporate",
    rate_change=0.07,  # +7pp
    corporate_elasticity=0.25,
    include_passthrough_effects=True,
    gilti_rate_change=0.105,  # Increase GILTI
    eliminate_fdii=True,  # Repeal FDII
)

# Scoring
scorer = FiscalPolicyScorer(baseline=None, use_real_data=True)
result = scorer.score_policy(policy, dynamic=False)
# result.static_revenue_effect, result.behavioral_offset, result.final_deficit_effect

# Auto-population from IRS
irs = IRSSOIData()
bracket_info = irs.get_filers_by_bracket(year=2022, threshold=400000)
# Returns: {'num_filers': 1.8M, 'avg_taxable_income': 1.2M, ...}
```

## Methodology Reference

Standard parameters (see `docs/METHODOLOGY.md`):
- **ETI**: 0.25 (Saez et al. 2012)
- **Capital gains elasticity**: time-varying (short-run 0.8, long-run 0.4)
- **Spending multiplier**: 1.0 normal, 1.5-2.0 recession
- **Marginal revenue rate** (dynamic feedback): 0.25
- **Labor/capital shares**: 0.65/0.35

Static revenue formula:
```
ΔRevenue = ΔRate × (Avg_Income - Threshold) × Num_Taxpayers
```

Behavioral offset (income tax):
```
Offset = -ETI × 0.5 × Static_Effect
```

Capital gains behavioral offset (time-varying):
```
R₁ = R₀ × ((1-τ₁)/(1-τ₀))^ε(t)
where ε(t) transitions from short_run to long_run over transition_years
```

## Current Development Priorities

From `planning/NEXT_SESSION.md`:
1. Complete CBO validation suite (match 5+ scores within 10%)
2. Capital gains tax module (realization elasticity, lock-in, step-up basis)
3. Tax credit calculator (CTC, EITC, phase-outs)
4. Corporate tax improvements (pass-through, GILTI/FDII, depreciation)

## Target Validation

| Policy | Official Score | Model Score | Error | Status |
|--------|----------------|-------------|-------|--------|
| Biden $400K+ (2.6pp) | -$252B | ~-$250B | ~1% | ✅ |
| **TCJA Extension** | **$4,600B** | **$4,582B** | **0.4%** | ✅ |
| Capital gains +2pp | -$70B | -$83B | 19% | ✅ |
| **Corporate 21%→28%** | **-$1,347B** | **-$1,397B** | **3.7%** | ✅ |

## Future Architecture (Phase 3+)

Multi-model platform with pluggable scoring engines:
- `models/cbo/` — CBO-style conventional + dynamic
- `models/jct/` — JCT-inspired microsimulation
- `models/tpc/` — Tax Policy Center distributional
- `models/pwbm/` — Penn Wharton OLG
- `models/yale/` — Yale Budget Lab macro + microsim + behavioral

See `docs/ARCHITECTURE.md` for full design including Yale Budget Lab feature-parity checklist.
