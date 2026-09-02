# Scoring Methodology

> How the Fiscal Policy Calculator estimates budget impacts

---

## Table of Contents

1. [Overview](#overview)
2. [Static Scoring](#static-scoring)
3. [Behavioral Response](#behavioral-response)
4. [Dynamic Scoring](#dynamic-scoring)
5. [Distributional Analysis](#distributional-analysis)
6. [Microsimulation Engine](#microsimulation-engine)
7. [Corporate Tax](#corporate-tax)
8. [International Tax](#international-tax)
9. [Estate Tax](#estate-tax)
10. [Payroll Tax and Social Security](#payroll-tax-and-social-security)
11. [Alternative Minimum Tax](#alternative-minimum-tax)
12. [Tax Credits](#tax-credits)
13. [Tax Expenditures](#tax-expenditures)
14. [Premium Tax Credits (ACA)](#premium-tax-credits-aca)
15. [TCJA Extension](#tcja-extension)
16. [Tariff and Trade Policy](#tariff-and-trade-policy)
17. [IRS Enforcement](#irs-enforcement)
18. [Drug Pricing and Pharmaceutical Policy](#drug-pricing-and-pharmaceutical-policy)
19. [State-Level Modeling](#state-level-modeling)
20. [Overlapping Generations Model](#overlapping-generations-model)
21. [Spending Multipliers](#spending-multipliers)
22. [Uncertainty Analysis](#uncertainty-analysis)
23. [Comparison to Official Methods](#comparison-to-official-methods)
24. [Validation Results](#validation-results)
25. [References](#references)

---

## Overview

The Fiscal Policy Calculator uses a **three-stage approach** consistent with Congressional Budget Office (CBO) methodology:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Static Score   │ ──▶ │   Behavioral    │ ──▶ │    Dynamic      │
│                 │     │   Adjustment    │     │   Feedback      │
│ Direct revenue  │     │ ETI response    │     │ GDP/employment  │
│ effect of rate  │     │ to tax changes  │     │ feedback        │
│ changes         │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   $X billion              $X × (1-ETI×0.5)        + revenue feedback
```

### Key Principles

1. **Current Law Baseline**: All estimates are relative to current law (not current policy)
2. **10-Year Budget Window**: `FiscalPolicyScorer` defaults to `start_year=2025`, so the standard window is **FY2025–FY2034** — the same fiscal-year window JCT scores P.L. 119-21 over (see [VALIDATION.md](VALIDATION.md), “Scoring window”). Inputs are **tax-year** (calendar-year) SOI aggregates; outputs are fiscal-year totals, and the model carries the former into the latter without a calendar-to-fiscal conversion
3. **Conventional Scoring**: Behavioral but not macroeconomic by default
4. **Dynamic Scoring**: Optional macroeconomic feedback via FRB/US-calibrated adapter
5. **Tiered validation**: the calibrated modules *reconstruct* official CBO/JCT/Treasury estimates; a separate pre-registered battery *predicts* them cold. The tiers are reported separately and never averaged into one tolerance — see [Validation Results](#validation-results)

The calculator currently exposes 14 preset policy areas: TCJA / individual tax, general income tax, corporate, international, tax credits, estate tax, payroll / Social Security, AMT, ACA / healthcare, tax expenditures, IRS enforcement, drug pricing, trade / tariffs, and climate / energy.

---

## Static Scoring

### Tax Rate Changes

For income tax rate changes, the static revenue effect is:

```
ΔRevenue = ΔRate × Marginal_Income × Num_Taxpayers
```

Where:
- **ΔRate**: Change in tax rate (e.g., +0.026 for a 2.6 pp increase)
- **Marginal_Income**: Average income *above the threshold* for affected filers
- **Num_Taxpayers**: Number of taxpayers above the threshold

**Example**: Biden's $400K+ rate increase (37% → 39.6%)
```python
rate_change = 0.026  # 2.6 percentage points
threshold = 400_000
affected_filers = 1.8M  # From IRS SOI
avg_income = 1.2M       # Average total income of filers above $400K
marginal_income = 1.2M - 0.4M = 800K  # Income ABOVE threshold

static_revenue = 0.026 × 800,000 × 1,800,000 = $37.4B/year
```

Only income *above* the threshold is subject to the rate change. A filer earning $500K with a $400K threshold has only $100K of marginal income affected.

#### Ordinary vs. preferential income base (`ordinary_income_base`)

An *ordinary*-bracket rate change (e.g. restoring the 39.6% top rate) does **not** apply to long-term capital gains or qualified dividends, which are taxed at preferential rates. On the `TaxPolicy` dataclass the flag defaults to `False` for back-compat, but **production Generic scoring, validation (`create_policy_from_score`), custom UI/API income-tax paths, and preset fallbacks default to `True`** — excluding the preferentially-taxed share (sourced from `CapitalGainsBaseline`). That is the correct treatment for ordinary-rate proposals and cuts the Biden 39.6%-above-$400K out-of-sample error from ~62% to ~13%.

Set the flag `False` (UI: uncheck “Ordinary-income base”; or `CBOScore.agi_inclusive_base=True`) for AGI-inclusive surtaxes that tax capital gains as ordinary income. Reproduce the legacy-vs-corrected comparison with `python scripts/cold_holdout.py --ordinary-base`.

### Data Source: IRS SOI

We use IRS Statistics of Income (SOI) Table 1.1 and Table 3.3 to obtain:
- Number of returns by income bracket
- Total taxable income by bracket
- Tax liability by bracket

```python
from fiscal_model.data import IRSSOIData

irs = IRSSOIData()
bracket_info = irs.get_filers_by_bracket(year=2023, threshold=400_000)
# Returns: {'num_filers': 1.8M, 'avg_taxable_income': 1.2M, ...}
```

**Tax-year basis and data lag.** SOI tables are compiled on a **tax year**
(calendar-year) basis, while every score in this document is reported over a
**fiscal-year** budget window. The repository ships Table 1.1 and Table 3.3 for
tax years **2021, 2022 and 2023** (`fiscal_model/data_files/irs_soi/`), and
auto-population takes the **latest available year** unless a policy sets
`data_year` — so production scoring runs on **tax year 2023**
(`policies_core._estimate_from_irs_data`; confirmed by the `irs_soi` row of
`python scripts/run_validation_dashboard.py`, which reports `latest 2023`).
SOI runs roughly two years behind the current tax year.

### Credits and Deductions

For tax credits:
```
ΔRevenue = -Credit_Amount × Num_Beneficiaries × (1 if refundable else avg_liability_rate)
```

For deductions:
```
ΔRevenue = -Deduction_Amount × Marginal_Rate × Num_Beneficiaries
```

---

## Behavioral Response

### Elasticity of Taxable Income (ETI)

Taxpayers respond to rate changes by adjusting reported taxable income through a combination of labor supply, avoidance, and evasion channels:

```
%ΔTaxable_Income = -ETI × %Δ(1 - marginal_rate)
```

The **behavioral offset** reduces the static estimate:

```python
behavioral_offset = -static_effect × ETI × 0.5
```

The factor of 0.5 converts from the income elasticity to the revenue offset (accounting for the fact that the base only partially overlaps the rate change).

### ETI Values in the Literature

| Source | ETI Estimate | Context |
|--------|--------------|---------|
| Saez, Slemrod & Giertz (2012) | 0.25 | Preferred central estimate |
| Gruber & Saez (2002) | 0.40 | Upper bound from 1980s tax reform |
| CBO (2014) | 0.25 | Conventional scoring default |
| JCT | 0.25 | Revenue estimates |

**Default**: ETI = 0.25 (user-adjustable in policy definition)

### Capital Gains: Realizations Elasticity

Capital gains realizations respond more strongly than wage income due to timing flexibility (the lock-in effect). We model this with **time-varying elasticity** following CBO/JCT methodology:

```
R₁ = R₀ × ((1-τ₁)/(1-τ₀))^ε(t)
```

Where:
- R₀ = baseline realizations
- τ₀, τ₁ = baseline and reform tax rates
- ε(t) = elasticity that transitions from short-run to long-run

**Time-Varying Elasticity Parameters:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Short-run elasticity (years 1–3) | 0.8 | Timing and anticipation effects dominate |
| Long-run elasticity (years 4+) | 0.4 | Only permanent behavioral response |
| Transition period | 3 years | Linear interpolation |

**References:**
- CBO (2012): Short-run ε ≈ 0.7–1.0
- Dowd, McClelland & Muthitacharoen (2015): Long-run ε ≈ 0.3–0.5
- Penn Wharton Budget Model: Distinguishes transitory vs. permanent response

### Step-Up Basis at Death

Under current law, unrealized capital gains are forgiven at death (step-up basis), creating a much stronger lock-in effect because taxpayers can avoid tax entirely by holding until death.

We model this with a **lock-in multiplier** applied to the base elasticity:
```
ε_effective = ε_base × step_up_lock_in_multiplier
```

**The module default is 2.0×, not 5.3×.** `CapitalGainsPolicy.step_up_lock_in_multiplier`
defaults to `2.0` (`fiscal_model/policies_core.py:411`) and `get_elasticity_for_year`
applies it whenever `step_up_at_death=True` and `eliminate_step_up=False`. The `5.3×`
that earlier revisions of this file printed as “current law” is **not** a model
constant. Exactly one place in the codebase ever *sets* it — the
`pwbm_39_with_stepup` entry of `fiscal_model/validation/scenarios.py:89`, where it is a
per-case constant hand-fitted to reproduce PWBM's published revenue loss. (Grep will
also find `5.3` in `tests/test_loo.py` and `tests/test_policies.py`, which assert that
scenario's value, and in prose here and in
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md). Those are
references to the same one constant, not additional uses of it.) No scoring path
outside that single calibrated reconstruction runs on 5.3×.

| Setting | Lock-in multiplier | Effective ε (short / long run) | Where it applies |
|---|---|---|---|
| Step-up in force — **module default** | **2.0×** | 1.6 / 0.8 | The `CapitalGainsPolicy` default, the Tailor UI default (slider 1.0–6.0), every Tier 1 out-of-sample capital-gains case, and every leave-one-out run (`validation/loo.py:912` freezes it) |
| Step-up eliminated | 1.0× | 0.8 / 0.4 | `eliminate_step_up=True` switches to `no_step_up_avoidance_multiplier`, whose own default is 1.0 |
| Step-up eliminated, PWBM residual-avoidance calibration | 1.5× | 1.2 / 0.6 | The `pwbm_39_no_stepup` validation scenario only |
| Step-up in force, PWBM revenue-matching calibration | 5.3× | ~4.2 / ~2.1 | The `pwbm_39_with_stepup` validation scenario only — a fitted answer key, not a parameter |

**Which multiplier is behind which published result.** The two Tier 2a rows
“PWBM 39.6% capital gains (with step-up), +$33B official vs +$30B model” and
“(no step-up), −$113B vs −$113B” are the *only* results that use 5.3× and the 1.5×
residual-avoidance value respectively, and both are calibrated reconstructions.
Every Tier 1 out-of-sample capital-gains case — CBO Option 47, CBO Option 51,
`biden_capital_gains_39`, `treasury_capgains_39_plus_stepup_elim` — and every
leave-one-out row runs on the frozen `2.0` default together with the frozen
0.8 / 0.4 elasticity pair. That is what makes them predictions rather than fits.

**The 5.3× is a known defect, not a finding.** `python scripts/run_loo.py --donor-matrix`
shows it is the only donor tuple that can score the other two capital-gains cases
(mean absolute error on the others: 29.7% for the 5.3× donor, against 104.8% and
333.2% for the other two), and under the frozen defaults its own case flips sign at
−370.5%. Lane L1 of the
[modeling-improvement plan](../planning/MODELING_IMPROVEMENT.md) is to delete the
multiplier outright and let lock-in fall out of a stock of accrued gains with a
realization hazard.

The no-step-up PWBM validation case uses the residual-avoidance calibration because PWBM notes that threshold timing and business-form shifting remain even when constructive realization at death removes the full step-up lock-in channel.

When step-up is eliminated, gains become taxable at death:
```
Revenue_death = τ × Gains_at_death × (1 - exemption_share)
```

Key estimates:
- Annual gains at death: ~$54B (CBO)
- Biden proposal ($1M exemption): ~$14B/year additional revenue
- Full elimination (no exemption): ~$23B/year

---

## Dynamic Scoring

### When to Use Dynamic Scoring

CBO provides dynamic scores for major legislation (>0.25% of GDP) and at Congressional request. The calculator offers dynamic scoring as an option for all policies.

### Default engine vs. FRB/US comparison engine

The app ships **two** dynamic engines, and it matters which one the default "Dynamic scoring" toggle uses:

- **Default — `EconomicModel` (state-dependent, CBO-conventional).** The `dynamic=True` path on `FiscalPolicyScorer.score_policy` runs this engine. It uses normal-times multipliers of **1.0 (spending)** and **0.5 (tax)**, decomposes demand vs. supply effects, adds capital/labor channels, and raises the multipliers in recessions / at the zero lower bound (see [Spending Multipliers](#spending-multipliers)). All of its parameters are sourced from `constants.py`.
- **Comparison only — `FRBUSAdapterLite` (reduced-form FRB/US).** A separate reduced-form adapter implementing multiplier effects consistent with the Federal Reserve's FRB/US model (also used by the Yale Budget Lab), with **1.4 (spending)** and **0.7 (tax)** first-year multipliers and 0.75 annual decay. It is surfaced in the multi-model **Scoring Models** tab as a cross-check; it is *not* the default toggle.

The remainder of this section describes the FRB/US comparison engine; the default engine's parameters are detailed under [Spending Multipliers](#spending-multipliers) and [Uncertainty Analysis](#uncertainty-analysis).

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Fiscal Shock   │ ──▶ │   GDP Effect    │ ──▶ │    Feedback     │
│                 │     │                 │     │                 │
│ Tax cut or      │     │ Apply FRB/US    │     │ Revenue from    │
│ spending change │     │ multipliers     │     │ GDP + crowding  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Fiscal Multipliers (FRB/US comparison engine)

*These are the `FRBUSAdapterLite` parameters. The default dynamic engine uses the lower CBO-conventional normal-times values in [Spending Multipliers](#spending-multipliers).*

| Shock Type | Year 1 Multiplier | Decay Rate | Source |
|------------|------------------:|----------:|--------|
| Spending | 1.4 | 0.75/year | FRB/US |
| Tax Cut | 0.7 | 0.75/year | FRB/US |
| Tax Increase | −0.7 | 0.75/year | FRB/US |

Multiplier decay:
```
multiplier(t) = base_multiplier × decay_rate^(t-1)
# Spending multiplier: Year 1 = 1.40, Year 2 = 1.05, Year 3 = 0.79 ...
```

### GDP and Employment Effects

```python
# Annual GDP effect from fiscal shock
gdp_change_pct = (fiscal_shock_billions / baseline_gdp) * multiplier(t) * 100

# Employment via Okun's Law (coefficient = 0.5)
employment_change_pct = gdp_change_pct * 0.5
employment_change_millions = employment_change_pct * labor_force / 100  # ~165M
```

### Revenue Feedback and Crowding Out

```python
# Revenue feedback from GDP change
marginal_tax_rate = 0.25  # Combined federal revenue/GDP ratio
revenue_feedback_billions = gdp_change_billions * marginal_tax_rate

# Crowding out from cumulative deficit
crowding_out_rate = 0.15
interest_cost = cumulative_deficit * crowding_out_rate

# Net budget effect
net_effect = revenue_feedback - interest_cost
```

### Long-Run Production Function

```
%ΔGDP = labor_share × %ΔLabor + capital_share × %ΔCapital + ΔTFP
# labor_share = 0.65, capital_share = 0.35 (BLS)
```

### FRBUSAdapterLite Output Fields

| Field | Description | Units |
|-------|-------------|-------|
| `gdp_level_pct` | GDP change from baseline | % |
| `gdp_growth_ppts` | Change in growth rate | ppts |
| `employment_change_millions` | Employment change | millions |
| `unemployment_rate_ppts` | Unemployment rate change | ppts |
| `short_rate_ppts` | Federal funds rate change | ppts |
| `long_rate_ppts` | 10-year Treasury change | ppts |
| `revenue_feedback_billions` | Revenue from GDP | $B |
| `interest_cost_billions` | Higher interest costs | $B |
| `cumulative_gdp_effect` | Total GDP %-years over horizon | %-years |
| `cumulative_revenue_feedback` | Total revenue feedback | $B |
| `net_budget_effect` | Revenue feedback minus interest cost | $B |

---

## Distributional Analysis

The `DistributionalEngine` produces TPC/JCT-style tables by income group.

### Income Group Definitions

| Group Type | Brackets | Usage |
|------------|----------|-------|
| Quintile | 5 equal-population groups | Standard TPC |
| Decile | 10 groups | Detailed analysis |
| JCT Dollar | $10K increments | JCT-style tables |
| Custom | User-defined | Targeted analysis |

**2024 Quintile Thresholds** (TPC/Census data):
- Lowest: $0–$35,000
- Second: $35,000–$65,000
- Middle: $65,000–$105,000
- Fourth: $105,000–$170,000
- Top: $170,000+

### Distributional Metrics

For each income group:
1. **Average Tax Change** ($): Per-return dollar impact
2. **Tax Change as % of Income**: After-tax income impact
3. **Share of Total Change**: Group's portion of total revenue effect
4. **Winners/Losers**: Fraction with tax increase/decrease
5. **Effective Tax Rate Change**: Change in ETR (percentage points)

### Policy-Specific Handlers

| Policy Type | Distribution Logic |
|-------------|-------------------|
| `TaxPolicy` | Rate change × income above threshold |
| `TaxCreditPolicy` | Credit phase-in/phase-out by income |
| `TCJAExtensionPolicy` | TPC-based component distribution |
| `CorporateTaxPolicy` | 75/25 capital/labor incidence |
| `PayrollTaxPolicy` | Wage distribution up to SS cap |

### Corporate Tax Incidence

Following CBO/TPC assumptions:
- **75%** borne by capital owners (concentrated in top quintile)
- **25%** borne by workers (distributed with wage income)

Capital income shares by quintile (SCF data):
- Top quintile: 80%
- Fourth: 12%
- Middle: 5%
- Second: 2%
- Bottom: 1%

---

## Microsimulation Engine

The `MicroTaxCalculator` (`fiscal_model/microsim/engine.py`) is a vectorized, individual-level tax calculator that applies the full tax code to synthetic or actual taxpayer records. It captures interactions that aggregate bracket-level models miss: the SALT cap interaction with itemized deductions, AMT liability, EITC phase-in/phase-out, CTC phaseout, and NIIT.

### Inputs

The engine consumes a `DataFrame` with one row per tax unit:

| Column | Description |
|--------|-------------|
| `agi` | Adjusted gross income |
| `wages` | Wage and salary income |
| `married` | Filing status (bool) |
| `children` | Number of qualifying children |
| `weight` | CPS/IRS sampling weight |
| `age_head` | Age of the primary filer |
| `itemized_deductions` | Itemized deductions (before SALT cap) |
| `investment_income` | Investment income (for NIIT) |

### Outputs

The calculator returns per-unit estimates of:
- Regular tax liability (after brackets, standard/itemized deduction)
- AMT liability
- EITC credit
- CTC (refundable and non-refundable)
- NIIT surtax
- Final tax (regular or AMT, net of credits)
- Effective tax rate

### 2025 Parameters Built In

- Brackets: 10%, 12%, 22%, 24%, 32%, 35%, 37% (indexed for inflation)
- Standard deduction: $15,000 single / $30,000 MFJ
- SALT cap: $10,000
- AMT exemption: $88,100 single / $137,000 MFJ
- CTC: $2,000 per child, phases out above $200K/$400K at 5 cents per dollar
- NIIT: 3.8% on net investment income above $200K/$250K

### State Extension

`FederalStateCalculator` (`fiscal_model/models/state/calculator.py`) layers state income tax on top of the federal calculation. State taxable income starts from federal AGI, with state-specific standard deductions and bracket schedules. SALT interactions are modeled at the federal level before state tax is applied.

---

## Corporate Tax

The `CorporateTaxPolicy` module scores changes to the statutory corporate rate, pass-through treatment, and related provisions.

### Rate Change Scoring

```
ΔRevenue = ΔRate × Corporate_Taxable_Income × (1 - behavioral_offset)
```

Behavioral offset follows the ETI framework with `corporate_elasticity = 0.25`.

### Pass-Through Effects

Pass-through income (S-corps, partnerships, sole proprietorships) is partially affected by corporate rate changes through competitive and structural channels. The model applies a partial pass-through adjustment factor when `include_passthrough_effects=True`.

### Book Minimum Tax (CAMT)

The 15% Corporate Alternative Minimum Tax (IRA 2022) is modeled as a separate tax on adjusted financial statement income for firms with >$1B in profits, with a carve-out for R&D credits.

### Calibration

The Biden corporate rate increase from 21% to 28% is calibrated to CBO's −$1.347T/10yr estimate (model: −$1.397T, error 3.7%).

---

## International Tax

The `InternationalTaxPolicy` module (`fiscal_model/international.py`) models GILTI, FDII, Pillar Two, and profit-shifting provisions.

### GILTI (Global Intangible Low-Taxed Income)

Under current post-TCJA law, GILTI is taxed at a 10.5% effective rate (50% deduction on the 21% statutory rate). Biden's proposal raises the GILTI rate to 21% and eliminates the per-country blending that allows cross-crediting of foreign taxes.

Key modeling parameters:
- Gross GILTI base: ~$250B/year
- Current GILTI revenue (after FTCs): ~$25B/year
- Country-by-country revenue multiplier: 1.20 (eliminates cross-crediting)
- FTC offset rate: ~40% of incremental revenue is offset by foreign tax credits
- Calibration: Treasury FY2025 Green Book, ~$280B/10yr

### FDII (Foreign-Derived Intangible Income)

FDII provides a 37.5% deduction on export-related intangible income, yielding a 13.125% effective rate. Repeal raises the effective rate to 21%, estimated at ~$200B/10yr (exact match to JCT estimate).

### Pillar Two Global Minimum Tax

The OECD Pillar Two framework imposes a 15% global minimum on large multinationals (>€750M revenue). The model uses:
- Carve-out fraction: ~60% of profits after substance carve-outs (OECD guidance)
- UTPR capture rate: ~50% of undertaxed profits
- Behavioral offset: 0.30 (lower than domestic, due to anti-avoidance rules)

### Profit Shifting

Following Clausing (2020), the model estimates ~$300B in shifted profits taxed at ~5% in havens. Anti-avoidance provisions recapture a fraction of this base.

---

## Estate Tax

The `EstateTaxPolicy` module models changes to the estate tax exemption, marginal rate, and step-up basis.

### Static Revenue Calculation

```
ΔRevenue = ΔRate × Taxable_Estates × Num_Taxable_Estates_per_Year
         - ΔExemption × Marginal_Rate × New_Taxable_Estates_Brought_In
```

### Exemption-Based Modeling

When the exemption changes (e.g., TCJA doubled it to ~$13M per person), the model estimates:
1. Estates previously above the old exemption that fall below the new one (freed)
2. The average taxable estate value for the marginal group
3. Behavioral response (portfolio reallocation, charitable giving)

### Behavioral Response

Estate planning elasticity varies with exemption level. At higher exemptions, fewer estates are affected and avoidance is less prevalent. The model uses a conservative offset (20% behavioral reduction) consistent with CBO estimates.

**Calibration**: Biden estate reform (Treasury ~−$450B/10yr) scores −$450B (~0% — window-average annuals, no growth/behavioral double-count; two-regime taxable-amount blend for bottom-up path).

---

## Payroll Tax and Social Security

The `PayrollTaxPolicy` module (`fiscal_model/payroll.py`) scores changes to the Social Security taxable wage cap, donut hole provisions, and Net Investment Income Tax (NIIT).

### SS Wage Cap Changes

The Social Security payroll tax applies to wages up to the annual cap ($168,600 in 2024). Scoring removes or adjusts this cap:

```
ΔRevenue = rate × (Wages_above_cap) × Num_Workers_above_cap
         × (1 - behavioral_offset)
         × (benefit_offset_fraction)
```

The benefit offset accounts for the fact that higher earnings generate higher Social Security benefit entitlements, partially offsetting the revenue gain. This is a key difference from ordinary income tax scoring.

### Donut Hole Provision

The "donut hole" exempts wages between the current cap ($168,600) and a higher threshold (e.g., $400,000), then reapplies the payroll tax above that threshold. Revenue is lower than full cap removal because high earners between the two thresholds are exempt.

**Calibration**: SS donut hole at $250K scores $2,700B/10yr vs Trustees $2,700B (~0% — window-average annuals plus SSA-aligned covered-wage bands; see VALIDATION_NOTES §1).

### NIIT Expansion

The 3.8% Net Investment Income Tax expansion (applying NIIT to active pass-through income above $400K) is modeled using the IRS SOI distribution of pass-through income above the threshold.

---

## Alternative Minimum Tax

The `AMTPolicy` module (`fiscal_model/amt.py`) scores the individual AMT and the Corporate Alternative Minimum Tax (CAMT).

### Individual AMT

The individual AMT applies a parallel tax system using an alternative income measure (AMTI) with a flat rate (26%/28%) after a large exemption ($88,100 single in 2025). A taxpayer pays the higher of regular tax or AMT.

```
AMT_Liability = max(Regular_Tax, AMT_Rate × (AMTI - Exemption))
ΔRevenue_AMT = ΔExemption_or_Rate × (AMTI > Threshold) × Filers
```

TCJA dramatically reduced AMT exposure by doubling the exemption and adding a phaseout. Extending TCJA AMT relief versus reverting to pre-TCJA rules is calibrated to JCT estimates.

### Corporate AMT (CAMT)

The IRA 2022 established a 15% book minimum tax on adjusted financial statement income for corporations with >$1B in book profits. Scoring uses aggregate estimates from CBO (2022) of ~$35B/year in additional corporate minimum tax revenue.

**Calibration**: Repeal Corporate AMT estimated at +$220B/10yr (exact match to CBO).

---

## Tax Credits

The `TaxCreditPolicy` module (`fiscal_model/credits.py`) models the Child Tax Credit (CTC) and Earned Income Tax Credit (EITC), including phase-in, phaseout, refundability, and expansion scenarios.

### Child Tax Credit

```
CTC = min(credit_per_child × children, eligible_amount)
CTC_phaseout = max(0, CTC - phaseout_rate × max(0, AGI - phaseout_threshold))
```

**Key parameters (2025)**:
- $2,000 per child
- Phaseout: 5 cents per dollar above $200K (single) / $400K (MFJ)
- Refundable up to 15% of earnings above $2,500 (Additional CTC)

**Biden 2021 expansion** raised the credit to $3,000–$3,600 and made it fully refundable, calibrated to CBO's $1,600B/10yr estimate (model matches when the explicit annual is treated as a window average).

### Earned Income Tax Credit

The EITC is modeled by income quintile using IRS SOI data on the distribution of EITC recipients. Phase-in rates, maximum credits, and phaseout rates vary by filing status and number of children:

| Children | Phase-in Rate | Max Credit (2025) | Phaseout Rate |
|----------|-------------|----------|--------------|
| 0 | 7.65% | $632 | 7.65% |
| 1 | 34.0% | $3,995 | 15.98% |
| 2 | 40.0% | $6,604 | 21.06% |
| 3+ | 45.0% | $7,430 | 21.06% |

---

## Tax Expenditures

The `TaxExpenditurePolicy` module (`fiscal_model/tax_expenditures.py`) scores changes to major itemized deductions and exclusions.

### SALT Cap

The TCJA capped the State and Local Tax (SALT) deduction at $10,000, raising $1.9T/10yr compared to full deductibility. The model scores:
- Changes in the cap level ($10K → unlimited, or $20K–$25K)
- Distributional effects (primarily concentrated in high-tax states, top quintiles)
- SALT cap interaction with AMT (the AMT historically limited SALT for high earners anyway)

### Employer-Sponsored Health Insurance Exclusion

The employer health insurance exclusion costs ~$200–250B/year in foregone revenue. Capping the exclusion at the 75th percentile premium level (c. $15,000/year) raises ~$450B/10yr (model: $450B, 0.1% error vs. JCT-calibrated estimates).

### Mortgage Interest Deduction

The MID is modeled by applying the deduction to the distribution of mortgage interest claimed by bracket, multiplied by the filer's marginal rate.

### Step-Up Basis

See [Step-Up Basis at Death](#step-up-basis-at-death) in the Behavioral Response section.

---

## Premium Tax Credits (ACA)

The `PremiumTaxCreditPolicy` module (`fiscal_model/ptc.py`) scores changes to Affordable Care Act premium subsidies.

ACA premium tax credits are income-adjusted subsidies that reduce the cost of marketplace health insurance for households with income between 100–400% of the federal poverty line (expanded to 600% under IRA 2022). The model:

1. Estimates the number of affected marketplace enrollees by income band using Kaiser Family Foundation/CMS data
2. Calculates the per-enrollee credit change from the policy
3. Applies a take-up adjustment for the fraction of newly eligible households that enroll

**Calibration**: Extension of enhanced PTCs (ARP + IRA) estimated at ~$220B/10yr.

---

## TCJA Extension

The `TCJAExtensionPolicy` module (`fiscal_model/tcja.py`) scores extension or expiration of the Tax Cuts and Jobs Act (2017), which expires after 2025.

### Component Breakdown

| Component | 10-year Cost (extend) | Notes |
|-----------|----------------------|-------|
| Rate cuts (income brackets) | ~$1,200B | Lower rates at all brackets |
| Standard deduction increase | ~$800B | $15K/$30K vs ~$8K/$16K pre-TCJA |
| SALT cap ($10K) | −$1,900B | Saves revenue (relative to no cap) |
| AMT relief | ~$800B | Higher exemption, fewer filers |
| Estate tax exemption | ~$350B | $13M+ vs ~$7M without TCJA |
| Pass-through deduction (199A) | ~$600B | 20% deduction on qualified income |
| CTC expansion ($2K, no SALT interaction) | ~$750B | Broader eligibility |
| Other | ~$180B | Various smaller provisions |

Full extension calibrated to CBO's $4,600B/10yr estimate (model: $4,582B, 0.4% error).

### SALT Interaction

The SALT cap is politically contentious and modeled separately:
- `keep_salt_cap=True`: Full extension at $4.6T
- `keep_salt_cap=False`: Full extension without SALT cap (+$1.9T, totaling ~$6.5T)

---

## Tariff and Trade Policy

The `TariffPolicy` module (`fiscal_model/trade.py`) models revenue from new tariffs, consumer price effects, trade retaliation, and import volume responses.

### Revenue Model

```
Tariff_Revenue = Tariff_Rate × Import_Base × Coverage_Rate
               × (1 - Volume_Response)
               × (1 - Avoidance_Rate)
```

Where:
- **Coverage Rate**: ~70% of imports are effectively covered after exemptions, de minimis, and USMCA
- **Volume Response**: Imports decline as prices rise (elasticity = −0.5)
- **Avoidance Rate**: ~5% due to transshipment and rerouting

### Non-Linear Import Response

Above a 30% tariff rate, substitution accelerates (elasticity doubles). A floor ensures imports never fall below 20% of baseline, consistent with observed trade patterns under high tariff regimes.

### Consumer Price Pass-Through

Not all tariff costs are borne by US consumers. The model uses a 60% pass-through rate (consistent with Amiti, Redding & Weinstein 2019 for broad tariffs), meaning 60% of the tariff is reflected in higher consumer prices.

```
Household_Cost = Tariff_Rate × Import_Base × pass_through_rate / us_households
```

The model reports per-household consumer cost by income quintile (lower-income households spend a larger share of income on imported goods).

### Retaliation

Trading partners typically retaliate in kind. The model applies a 30% retaliation rate: US exporters lose revenue equal to 30% of the tariff shock, which is a net economic cost but does not directly affect the federal budget.

### Country-Specific Modeling

| Scenario | Import Base | Key Adjustments |
|----------|------------|-----------------|
| Universal 10% tariff | $3,200B (70% effective coverage) | Standard parameters |
| China 60% tariff | $430B (50% effective after existing tariffs) | High existing tariffs (~20% avg) already cover base |
| Auto 25% tariff | $380B (35% after USMCA exemption) | 65% of autos exempt under USMCA |
| Reciprocal tariffs (~20pp avg) | ~$2,000B effective base | Mixed coverage by country |

**Calibration**: Universal 10% tariff ~$2T/10yr (Tax Foundation/Yale Budget Lab); 60% China tariff ~$500B/10yr (Tax Foundation).

---

## IRS Enforcement

The `IRSEnforcementPolicy` module (`fiscal_model/enforcement.py`) models the revenue return from increased IRS enforcement investment.

### Revenue Multiplier Model

Unlike tax rate changes, enforcement spending yields a multiplied return by closing the tax gap rather than changing statutory rates.

```
Annual_Revenue = Enforcement_Spending × base_roi
               × diminishing_returns_factor^(n_years)
               × (1 + voluntary_compliance_boost)
               × phase_in_factor(t)
```

**Key parameters:**
- Base ROI: $5 revenue per $1 spent (first-dollar yield)
- Diminishing returns: 85% — each additional $1B yields 85% of the prior dollar
- Voluntary compliance boost: 15% (deterrence effect)
- Ramp-up: 3 years to reach full audit capacity (hiring and training)

### Tax Gap Context

- Annual gross tax gap: ~$600B (IRS 2022)
- Net tax gap (after enforcement and late payments): ~$440B
- Audit rate for returns >$1M: 2% in 2022 (vs. 16% in 2010)
- High-income and large partnership audits yield the highest per-return revenue

### Calibration

- IRA 2022 enforcement funding ($80B/10yr): ~$200B net revenue (CBO 2022) — model matches
- Doubling enforcement beyond IRA: ~$340B (Treasury 2021/Sarin-Summers, diminishing returns)

---

## Drug Pricing and Pharmaceutical Policy

The `PharmaPricingPolicy` module (`fiscal_model/pharma.py`) scores budget savings from pharmaceutical pricing reforms, primarily through Medicare.

### Medicare Drug Negotiation

The IRA 2022 authorized CMS to negotiate prices for high-spend Medicare Part D and Part B drugs. The model estimates savings as:

```
Savings = Current_Medicare_Spending_per_Drug
        × (1 - negotiated_price_ratio)
        × eligible_drugs_count
        × additional_drug_productivity_factor
```

The `additional_drug_productivity_factor` (0.6) captures that drugs negotiated beyond the first 20 in the IRA generate 60% as much savings per drug (smaller market share and less price room to negotiate).

**Calibration**: IRA negotiation (~$237B/10yr, CBO 2022). Extended negotiation scenarios scaled from this base.

### Part D Redesign

The IRA 2022 also redesigned Part D cost-sharing, capping out-of-pocket costs at $2,000 and shifting more liability to drug manufacturers (catastrophic coverage phase). The model estimates net budget impact from these transfers.

### Insulin Cap

The $35/month insulin cap applies to Medicare beneficiaries (approximately 40% of insulin users). Revenue impact is modest (around $6.4B/10yr) but significant for affected patients.

### International Reference Pricing

Reference pricing to international drug prices (US pays 1.25–1.5× international median) is modeled as a share of the price gap between US and comparable-country prices. The US pays ~2.56× international prices on average (RAND 2021).

---

## State-Level Modeling

The state-level module (`fiscal_model/models/state/`) computes combined federal + state effective tax rates for the top 10 states by population and income.

### Architecture

```
FederalStateCalculator
    ├── MicroTaxCalculator (federal)        # Full federal tax calculation
    └── StateTaxDatabase → StateTaxProfile  # State rates, deductions, exemptions
```

### State Tax Calculation

State taxable income typically conforms to federal AGI, with state-specific adjustments:

```
State_Taxable_Income = Federal_AGI
                     - State_Standard_Deduction
                     - Personal_Exemptions
                     + State_Add-backs (e.g., bonus depreciation in some states)
```

State income tax is calculated separately using the state bracket schedule and credits, then combined with federal tax for an effective combined rate.

### SALT Interaction

The TCJA SALT cap ($10,000) constrains the federal deductibility of state taxes, making high-state-tax residents effectively double-taxed on state taxes above the cap. The model explicitly computes this interaction:
- At $10,000 cap: High-income taxpayers in CA, NY, NJ, CT, IL face higher effective combined rates
- Without SALT cap: Federal deductibility reduces the after-federal-tax cost of state taxes

### Coverage and Limitations

- **10 states covered**: CA, NY, TX, FL, IL, PA, OH, GA, NC, WA
- **Local taxes**: Not modeled for NYC, Philadelphia, and similar cities; flagged as a caveat
- **State conformity**: Approximated; states differ on bonus depreciation, pension exclusions, and other itemized deductions
- **Synthetic population**: Uses IRS bracket-level data to approximate the population, not a true microsimulation of state returns

---

## Overlapping Generations Model

The `OLGModel` (`fiscal_model/models/olg.py`) is a 30-period Auerbach-Kotlikoff-style model that analyzes the long-run and intergenerational distribution of fiscal policy.

### Production Function

```
Y_t = A_t × K_t^α × L_t^(1-α)
```

Where α = 0.35 (capital share), A_t grows at 1.5%/year (TFP), and L_t grows at 0.7%/year.

Factor prices are set by marginal products:
```
w_t = (1-α) × Y_t / L_t        # Wage per worker
r_t = α × Y_t / K_t - δ        # Net return on capital (δ = 5% depreciation)
```

### Capital Accumulation

```
K_{t+1} = (1-δ)K_t + s × Y_t - G_t
```

Government borrowing (G_t) directly crowds out private capital. The model calibrates to a K/Y ratio of ~3.0 and an initial GDP of ~$29T (2025).

### Generational Accounts

The lifetime fiscal burden for a cohort born in year b:

```
GA_b = Σ_{a=0}^{T-1} [τ_w × w_{b+a} + τ_k × r_{b+a} × (K/L)_{b+a}
                       - SS_{b+a}] / (1+ρ)^a
```

Where τ_w = 0.25 (labor tax rate), τ_k = 0.20 (capital tax rate), SS = Social Security replacement (40% of wages), and ρ = 0.03 (individual discount rate). The sum runs over working years (40) plus retirement years (20).

### Crowding Out

Each dollar of additional government debt is estimated to crowd out ~$0.33 of private capital (CBO), reducing wages for future workers:
```
crowding_out_effect = (debt / GDP) × 0.33 × 100   # % of GDP
```

### Use Cases

The OLG model is used to analyze:
- Social Security reform (payroll tax changes, benefit cuts, retirement age)
- Long-horizon effects of deficit-financed tax cuts (TCJA extension)
- Generational redistribution in Medicare reform

**References**: Diamond (1965), Auerbach, Gokhale & Kotlikoff (1991), CBO (2023) Long-Term Budget Outlook.

---

## Spending Multipliers

### State-Dependent Multipliers

Fiscal multipliers vary with economic conditions:

| Condition | Spending Multiplier | Tax Multiplier |
|-----------|--------------------:|---------------:|
| Normal | 1.0 | 0.5 |
| Recession | 1.5–2.0 | 0.8–1.0 |
| At Zero Lower Bound | 2.0+ | 1.0+ |
| Overheating | 0.5 | 0.3 |

**Sources**: Auerbach & Gorodnichenko (2012) for state-dependent multipliers; Christiano, Eichenbaum & Rebelo (2011) for ZLB amplification; Blanchard & Leigh (2013) for fiscal consolidation evidence.

### Multiplier Decay

```python
year_effect = spending × multiplier × (decay_rate ** years_since_start)
# decay_rate = 0.7/year (standard multiplier decay)
```

---

## Uncertainty Analysis

### Sources of Uncertainty

1. **Baseline Uncertainty**: Economic projections diverge from actual outcomes
2. **Behavioral Uncertainty**: ETI estimates range 0.15–0.50 across the literature
3. **Dynamic Uncertainty**: Macro model predictions diverge significantly
4. **Data Uncertainty**: IRS data is typically 2 years lagged

### Uncertainty Ranges

```python
base_uncertainty = 0.10 + 0.02 × years_out  # Grows with horizon

policy_factor = 1.2 if tax_policy else 0.8  # Taxes more uncertain
dynamic_factor = 1.5 if dynamic else 1.0    # Dynamic adds uncertainty

total_uncertainty = base × policy_factor × dynamic_factor

low_estimate  = central × (1 - total_uncertainty × 0.9)
high_estimate = central × (1 + total_uncertainty × 1.1)  # Asymmetric: costs skew higher
```

---

## Comparison to Official Methods

### vs. CBO

| Feature | CBO | This Model |
|---------|-----|------------|
| Static scoring | ✅ | ✅ |
| ETI behavioral (0.25) | ✅ | ✅ |
| Dynamic macro (FRB/US) | ✅ on request | ✅ FRBUSAdapterLite |
| GDP and employment effects | ✅ | ✅ |
| Revenue feedback | ✅ | ✅ |
| Crowding out | ✅ | ✅ |
| 10-year window | ✅ | ✅ |
| Uncertainty ranges | ✅ | ✅ |
| Return-level microsimulation | ✅ (proprietary) | Bracket-level + synthetic |

### vs. JCT (Joint Committee on Taxation)

JCT is the official congressional scorer for tax legislation, using IRS SOI microdata with proprietary behavioral models.

| Feature | JCT | This Model |
|---------|-----|------------|
| Return-level microsimulation | ✅ | Bracket-level + synthetic |
| Distributional tables | ✅ | ✅ |
| Corporate model | ✅ | ✅ |
| International (GILTI/FDII/Pillar Two) | ✅ | ✅ |
| Public methodology | Partial | ✅ |

### vs. TPC (Tax Policy Center)

| Feature | TPC | This Model |
|---------|-----|------------|
| Microsimulation | ✅ | Bracket-level + synthetic |
| Distributional tables (quintile/decile) | ✅ | ✅ |
| Winners/losers | ✅ | ✅ |
| TCJA component breakdown | ✅ | ✅ |
| Public methodology | ✅ | ✅ |

**Distributional validation** is benchmarked against **seven published CBO/JCT
tables**, not against TPC alone. Mean absolute share errors span **0.00pp to
5.86pp** (`python scripts/run_validation_dashboard.py`; full table in
[VALIDATION.md](VALIDATION.md)). Two of the seven are **circular** and must not be
counted as skill: `distribution_effects.calculate_tcja_effect` builds its decile
tiers *out of* CBO 54796 and CBO 60007, so the 0.00pp against the first and the
0.74pp against the second are bookkeeping. The five non-circular tables run
2.10pp (JCT JCX-68-17) to 5.86pp (JCT JCX-4-24).

### vs. Penn Wharton Budget Model (PWBM)

| Feature | PWBM | This Model |
|---------|------|------------|
| OLG generational model | ✅ | ✅ |
| 30+ year horizon | ✅ | ✅ (80-year OLG simulation) |
| Generational accounts | ✅ | ✅ |
| Dynamic scoring | ✅ | ✅ FRB/US-calibrated |
| GDP and employment | ✅ | ✅ |
| Crowding out | ✅ | ✅ |
| Full GE microsimulation | ✅ | Reduced-form |

### vs. Yale Budget Lab

| Feature | Yale | This Model |
|---------|------|------------|
| Dynamic macro (FRB/US) | ✅ | ✅ FRBUSAdapterLite |
| GDP and employment effects | ✅ | ✅ |
| Revenue feedback and crowding out | ✅ | ✅ |
| Tax microsimulation | ✅ | Bracket-level + synthetic |
| Distributional analysis | ✅ | ✅ |
| Capital gains realization (time-varying ε) | ✅ | ✅ |
| Trade/tariff policy | ✅ | ✅ |
| International tax (GILTI, Pillar Two) | ✅ | ✅ |
| Drug pricing | Partial | ✅ |
| State-level modeling | Partial | ✅ (top 10 states) |
| Public methodology | ✅ | ✅ |

### Known Limitations

1. **Bracket-level microsimulation**: Uses IRS bracket aggregates rather than return-level data; CPS-based individual simulation is a planned upgrade
2. **Simplified corporate pass-through**: Pass-through income distribution not fully modeled at the return level
3. **State modeling approximate**: Top 10 states only; synthetic population rather than state-level microsimulation; local taxes (NYC, Philadelphia) not included
4. **Reduced-form dynamic scoring**: FRBUSAdapterLite uses calibrated multipliers rather than structural general-equilibrium equations
5. **Data lag**: IRS SOI data lags ~2 years (currently Tax Year 2023)

---

## Validation Results

Benchmarks fall into **four** epistemically different tiers, plus a separate
distributional number. We report them separately because conflating calibration
with prediction overstates the model's predictive power, and there is **no single
“validated within X%” figure for this model**. Every number below reproduces live
via `python scripts/cold_holdout.py`, `python scripts/run_loo.py` and
`python scripts/run_validation_dashboard.py`; see [`docs/VALIDATION.md`](VALIDATION.md)
for the full matrix.

### Tier 1 — Out-of-sample predictions (uncalibrated, bottom-up from IRS SOI)

No fitting to the official target — the genuine test of predictive accuracy.
Every case is pre-registered in `fiscal_model/validation/preregistered.py`, in a
commit that lands *before* the commit that first scores it.

| Policy | Official | Model | Error | Source |
|--------|---------:|------:|------:|--------|
| 1pp all brackets | −$960B | −$935B | 3% | JCT |
| Fiscal Responsibility Act 2023, discretionary caps | −$1,332B | −$1,254B | 6% | CBO |
| 5pp top rate ($1M+) | −$700B | −$648B | 7% | TPC |
| Social Security Fairness Act, WEP/GPO repeal | +$196B | +$215B | 10% | CBO |
| Biden top rate 39.6% ($400K+) | −$252B | −$285B | 13% | Treasury |
| All ordinary rates +1pp | −$1,185B | −$935B | 21% | CBO Options 2025–2034 #45 |
| Corporate rate +1pp | −$136B | −$200B | 47% | CBO Options 2025–2034 #64 |
| LTCG + qualified dividends +2pp | −$103B | −$206B | 99% | CBO Options 2025–2034 #47 |
| IIJA 2021, discretionary component | +$415B | +$1,894B | 356% | CBO |

**25 pre-registered cases, mean absolute error 52.6% (median 21.1%); 8 of 25
within 15%, 14 of 25 within 25%** (`scripts/cold_holdout.py`; full table in
[VALIDATION.md](VALIDATION.md)). Do **not** collapse this into one tolerance.
Ordinary-bracket and AGI-inclusive rate changes at conventional thresholds land at
**2–21%**; fast-spending discretionary funding cuts at **6–23%**; and everything
behavioral — capital-gains realizations, gains at death, payroll incidence,
corporate margins — misses by **47–154%** for documented structural reasons. One
case sits in a class of its own: **IIJA's 356%**, an enacted law's
budget-authority path scored with no budget-authority-to-outlay spend-out model
behind it. It is kept in the battery deliberately, as the sharpest available
evidence for that missing mechanism.

The mean moved from Phase B's 43.4% on 23 cases to 52.6% on 25 while the median
*fell* from 23.1% to 21.1%: `top_rate_45` was retired in Phase E (its −$420B target
appears in no TPC, CBO or JCT publication), `biden_capital_gains_39` was re-sourced
to the FY2025 Green Book's actual line item and got *worse* (79% → 142%), and three
enacted-law components joined. A mean that moves on one case while the median does
not is the tail, not a change in the core.

Ordinary-bracket rate changes score on the ordinary-income base (excluding
preferential LTCG/QDIV); AGI-inclusive surtaxes score on the full taxable-income
base — classified from how each source describes its base, never fitted. Treat
uncalibrated custom rate policies as directional, ±15–25%.

### Tier 2a — Calibrated reference models (fitted; low error by construction)

Specialized modules parameterized to reproduce the published decomposition. Useful
as auditable, source-linked reconstructions of official scores, *not* as
independent confirmation. **34 fitted benchmarks, mean absolute error 2.7%, 33 of
34 within 15%, 34 of 34 within 25%.** Twenty-nine of them reproduce a published
CBO/JCT/Treasury decomposition; the other five are fitted to a target that is
itself a model estimate, so those measure internal consistency only. (Earlier
revisions of this file quoted “≈ 5% across 29 benchmarks”; `scripts/cold_holdout.py`
is now the only place this figure should be read from.)

| Policy | Official Score | Model Score | Error | Status |
|--------|----------------|-------------|-------|--------|
| **TCJA Full Extension** | **$4,600B** | **$4,582B** | **0.4%** | calibrated |
| **Biden Corporate 28%** | **−$1,347B** | **−$1,397B** | **3.7%** | calibrated |
| Biden GILTI Reform | −$280B | −$271B | 3.2% | calibrated |
| FDII Repeal | −$200B | −$200B | 0.0% | calibrated |
| **Biden CTC 2021** | **$1,600B** | **$1,600B** | **0.0%** | calibrated |
| **Estate: Biden Reform** | **−$450B** | **−$450B** | **0.0%** | calibrated |
| **SS Donut Hole $250K** | **−$2,700B** | **−$2,700B** | **0.0%** | calibrated |
| **Repeal Corporate AMT** | **$220B** | **$220B** | **0.0%** | calibrated |
| **Cap Employer Health** | **−$450B** | **−$450B** | **0.1%** | calibrated |
| IRA Enforcement ($80B) | −$200B | −$200B | ~0% | calibrated |
| IRA Drug Negotiation | −$237B | −$237B | ~0% | calibrated |
| PWBM 39.6% cap gains (with step-up) | +$33B | +$30B | −9% | calibrated |
| PWBM 39.6% cap gains (no step-up) | −$113B | −$113B | 0% | calibrated |

*Positive values indicate deficit increase (cost); negative values indicate deficit reduction (savings). All estimates are 10-year totals.*

### Tier 2b — Unfitted module reconstructions (target never fitted to)

**20 policies, mean absolute error 250.8%, median 43.1%; 4 of 20 within 15%, 7 of
20 within 25%.** These are two populations and must never be read as one number:

- **Twelve Phase E sectoral presets** (international, trade, pharma, IRS
  enforcement, climate) at **394.1% mean / 57.1% median**. They ship in the app
  with an official figure attached and no module constant was ever fitted to any
  of them. Two — the universal insulin cap and international reference pricing —
  are off by three and one orders of magnitude respectively and diagnose real
  incidence bugs in `pharma.py`. The insulin *target* is also mis-signed: CBO
  publication 57957 scores a private-market insulin cap at about **+$11.4B**, i.e.
  as *adding* to the deficit, against the carried −$15B.
- **Eight Phase D P.L. 119-21 line items** (JCT JCX-35-25, transcribed with page
  references to `fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`)
  at **35.8% mean**, 2 of 8 within 15%, scored over JCT's own FY2025–2034 window.
  This is the sharpest available evidence that the calibrated tier is
  reconstruction rather than structure: the TCJA module reproduces CBO's $4.6T
  aggregate to **0.4%** and JCT's own component rows to **36%**, because one
  calibration factor is fitted to the aggregate and no factor is fitted to any
  component.

Nothing in either group was retuned to close a gap, and every row carries a
`known_limitations` note naming the structural cause.

### Tier 2c — Calibrated modules, held out (leave-one-out)

`python scripts/run_loo.py` refits each calibrated module's mechanism on the
*other* benchmarks in its module and asks it to rebuild the held-out one.
**18 derivable cases, mean absolute error 59.3%, median 35.6%, 6 of 18 within
15%**, plus **4 cases declared not cross-validatable** — no second benchmark to
calibrate on, or a base constant that is the published target restated — which are
reported and never folded into the aggregate.

| Module | Kind | n | Not x-val | LOO mean abs error |
|---|---|--:|--:|--:|
| Payroll | structural | 3 | 1 | 3.8% |
| Estate | structural | 2 | 1 | 25.8% |
| Expenditures | bottom-up | 5 | 1 | 39.4% |
| Credits | structural | 3 | 0 | 45.1% |
| AMT | structural | 2 | 1 | 79.6% |
| CapitalGains | structural | 3 | 0 | 171.2% |

Compare against the 2.7% in Tier 2a: that number measures bookkeeping, this one
measures whether the machinery predicts.

### Reading the tiers

**Report these separately and never collapse them:**

| Tier | What it measures | n | Mean | Median |
|---|---|--:|--:|--:|
| 1 — out-of-sample, pre-registered | prediction | 25 | **52.6%** | 21.1% |
| 2a — calibrated, fitted | bookkeeping (low by construction) | 34 | **2.7%** | 0.2% |
| 2b — unfitted module reconstructions | modules against targets they never saw | 20 | **250.8%** | 43.1% |
| 2c — calibrated, leave-one-out | how much of the calibration is structure | 18 | **59.3%** | 35.6% |

Distributional accuracy is a fifth, separate number: **seven published CBO/JCT
tables at 0.00–5.86pp** mean absolute share error, **two of which are circular**
(see [above](#vs-tpc-tax-policy-center)). There is no single “validated within X%”
figure for this model, and any document that states one is wrong.

---

## References

### Academic Literature

1. **Saez, E., Slemrod, J., & Giertz, S.H. (2012)**. "The Elasticity of Taxable Income with Respect to Marginal Tax Rates: A Critical Review." *Journal of Economic Literature*, 50(1), 3–50.

2. **Auerbach, A.J., & Gorodnichenko, Y. (2012)**. "Measuring the Output Responses to Fiscal Policy." *American Economic Journal: Economic Policy*, 4(2), 1–27.

3. **Christiano, L., Eichenbaum, M., & Rebelo, S. (2011)**. "When Is the Government Spending Multiplier Large?" *Journal of Political Economy*, 119(1), 78–121.

4. **Gruber, J., & Saez, E. (2002)**. "The Elasticity of Taxable Income: Evidence and Implications." *Journal of Public Economics*, 84(1), 1–32.

5. **Dowd, T., McClelland, R., & Muthitacharoen, A. (2015)**. "New Evidence on Long-Run Capital Gains Elasticities." *National Tax Journal*, 68(3), 511–540.

6. **Blanchard, O., & Leigh, D. (2013)**. "Growth Forecast Errors and Fiscal Multipliers." *American Economic Review*, 103(3), 117–120.

7. **Amiti, M., Redding, S.J., & Weinstein, D.E. (2019)**. "The Impact of the 2018 Tariffs on Prices and Welfare." *Journal of Economic Perspectives*, 33(4), 187–210.

8. **Clausing, K.A. (2020)**. "Profit Shifting Before and After the Tax Cuts and Jobs Act." *National Tax Journal*, 73(4), 1233–1266.

9. **Diamond, P.A. (1965)**. "National Debt in a Neoclassical Growth Model." *American Economic Review*, 55(5), 1126–1150.

10. **Auerbach, A.J., Gokhale, J., & Kotlikoff, L.J. (1991)**. "Generational Accounts: A Meaningful Alternative to Deficit Accounting." *Brookings Papers on Economic Activity*, 1991(1), 55–110.

11. **Auerbach, A.J., & Kotlikoff, L.J. (1987)**. *Dynamic Fiscal Policy*. Cambridge University Press.

12. **Ball, L., Leigh, D., & Loungani, P. (2017)**. "Okun's Law: Fit at 50?" *Journal of Money, Credit and Banking*, 49(7), 1413–1441.

### Official Methodology Documents

13. **CBO (2014)**. "How CBO Analyzes the Effects of Changes in Federal Fiscal Policies on the Economy." Congressional Budget Office.

14. **CBO (2022)**. "Estimated Budgetary Effects of H.R. 5376, the Inflation Reduction Act of 2022." Congressional Budget Office.

15. **CBO (2023)**. "The 2023 Long-Term Budget Outlook." Congressional Budget Office.

16. **CBO (2026)**. "The Budget and Economic Outlook: 2026 to 2036." Congressional Budget Office.

17. **JCT (2017)**. "Overview of Revenue Estimating Procedures and Methodologies." Joint Committee on Taxation. JCX-1-17.

18. **Treasury (2024)**. "General Explanations of the Administration's FY2025 Revenue Proposals (Green Book)." U.S. Department of the Treasury.

19. **TPC**. "Tax Model Resources." Tax Policy Center. https://taxpolicycenter.org/resources/tax-model-resources

20. **Yale Budget Lab**. "Methodology and Documentation." https://budgetlab.yale.edu/research

### Data Sources

21. **IRS Statistics of Income**. Individual Income Tax Statistics. Tables 1.1 and 3.3. https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics

22. **FRED**. Federal Reserve Economic Data. Federal Reserve Bank of St. Louis. https://fred.stlouisfed.org

23. **RAND (2021)**. "Prices Paid to US Hospitals by Medicare Advantage Plans." RAND Corporation.

24. **KFF (2024)**. "Medicare Drug Spending Dashboard." Kaiser Family Foundation.

---

## Appendix: Parameter Defaults

### Tax Parameters

| Parameter | Default | Source |
|-----------|---------|--------|
| ETI | 0.25 | Saez et al. (2012) |
| Labor supply elasticity | 0.15 | CBO |
| Capital elasticity | 0.25 | Literature |
| Marginal revenue rate | 0.25 | CBO |
| Corporate tax incidence (capital) | 75% | CBO/TPC |
| Corporate tax incidence (labor) | 25% | CBO/TPC |
| Capital gains elasticity (short-run) | 0.8 | CBO (2012) |
| Capital gains elasticity (long-run) | 0.4 | Dowd et al. (2015) |

### Dynamic Scoring Parameters (FRBUSAdapterLite)

| Parameter | Default | Source |
|-----------|---------|--------|
| Spending multiplier (Year 1) | 1.4 | FR
