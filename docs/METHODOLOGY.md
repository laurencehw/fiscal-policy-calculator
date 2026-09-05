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
2. **10-Year Budget Window**: the app scores **FY2026–FY2035**, the window the CBO February 2026 baseline projects — `fiscal_model.baseline.APP_DEFAULT_START_YEAR`, which every app surface and the public API route through. The **validation suite keeps its own window**, `DEFAULT_VALIDATION_START_YEAR = 2025`: each benchmark is scored over the window its own document used, which for the P.L. 119-21 line items is JCT's **FY2025–FY2034** (see [VALIDATION.md](VALIDATION.md), “Scoring window”). The library defaults (`FiscalPolicyScorer`, `Policy.start_year`) stay at 2025 for that reason. Inputs are **tax-year** (calendar-year) SOI aggregates; outputs are fiscal-year totals, and the model carries the former into the latter without a calendar-to-fiscal conversion
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

**Two modes.** `AMTPolicy.mode` selects between `reported` — the fitted annual,
which reproduces the carried benchmark by construction — and `derived`, a
year-indexed affected-payer and average-liability path read from **TPC Table
T25-0049** ("Aggregate Alternative Minimum Tax Projections, 2024–2035", April
2025), transcribed to `fiscal_model/data_files/amt/tpc_t25_0049_aggregate_amt.csv`
with the table's own footnotes. The baseline leg is evaluated at the current-law
exemption and the policy leg at the reform exemption; revenue and payers are each
interpolated between the two regime anchors and the average liability is their
ratio (interpolating the average separately is unsafe — the two are individually
monotone in the exemption but their product turns upward, so an exemption
*increase* prices as a revenue gain).

The TPC table's baseline is the law in place as of 1 January 2025, so it carries
the TCJA sunset: AMT payers go from **0.2M in 2025 to 7.6M in 2026** — a cliff,
not a ramp — and the post-sunset path then grows from **$71.6B in 2026 to
$124.2B in 2035**. The derived ten-year cost of extending TCJA AMT relief is
therefore **$855.3B**, above the flat identity's ~$73B/yr, and full repeal from
2026 is **$948.9B**.

**`reported` is the app default, and stayed there when the targets were
corrected.** Owner Decision 1's rule is that a module keeps its fitted mode
until its derived error beats its fitted error, and across the three AMT
benchmarks it does not: **22.3% reported against 54.2% derived**.

| Benchmark | Target | Reported (fitted) | Err | Derived (structural) | Err |
|---|--:|--:|--:|--:|--:|
| `extend_tcja_amt` | $1,357.1B | $450.5B | **−66.8%** | **$855.3B** | **−37.0%** |
| `repeal_individual_amt` | $450.0B | $450.5B | +0.1% | $948.9B | +110.9% |
| `repeal_corporate_amt` | $220.0B | $220.1B | +0.05% | $252.2B | +14.6% |
| **Mean abs** | | | **22.3%** | | **54.2%** |

Read the two rows on which derived loses before treating that mean as evidence
for the fitted path: both are targets a constant was fitted to, so their ~0% is bookkeeping,
and `repeal_corporate_amt`'s derived path is the flat base `loo.py`'s leakage
guard already flags. **The one AMT benchmark whose target no constant was fitted
to is the one derived wins**, by a factor of 1.8. `AMT_SCORECARD_MODE` also stays
`reported`; `derived` is the default in the held-out validation path.

Not modelled: the phase-out thresholds. `phase_out_threshold_change` is declared
and never read, and under the post-sunset schedule the phase-out is what claws
the exemption back from high-income filers — but it needs a published phase-out
path, which T25-0049 does not carry.

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

### The derived path — per-unit over CPS ASEC tax units (Wave 3, lane L3)

`TaxCreditPolicy` carries a module-local `mode`. In `reported` mode — the app
default, unchanged — it returns the fitted annual. In `derived` mode it builds
**two** parameter sets, the counterfactual schedule and the reform schedule, runs
`MicroTaxCalculator` over the CPS ASEC tax units under each, and takes the
**weighted difference in final tax liability**. That is the right quantity rather
than a gross credit total: it carries the non-refundable credit's tax limit and
the refundable leg's earnings phase-in, which is precisely what a
`Δcredit × units × participation` identity omits and why the old path understated
every expansion.

**The counterfactual moves with the law.** IRC §24's $2,000 reverts to $1,000
after 2025 (P.L. 115-97 §11022(b)), so a ten-year window opening in 2025 is
scored against current law for one year and the pre-TCJA regime for nine. Against
a fixed $2,000 baseline the ARP credit costs **$883B**; against the
counterfactual the statute specifies, **$1,528B**. That single point is worth
more than 40 percentage points on the held-out `biden_ctc_2021` case, and both
legs are pinned by `tests/test_credits_microdata.py`.

**`expand_qualifying_age`, `include_childless_adults` and `take_up_rate_change`
are read now.** They were dataclass fields no code path touched, because the old
identity had nowhere to put an eligibility expansion and the microdata carried
only an under-17 headcount. `make_fully_refundable` and `remove_phase_out`
reached unreachable flat constants and now score $85.5B/yr and $70.1B/yr over the
CPS units.

**Microdata provenance (owner Decision 4: fetch, never vendor).**
`scripts/fetch_cps_asec.py` downloads the March 2024 CPS ASEC public-use archive
(`asecpub24csv.zip`, 148,664,101 bytes, SHA-256
`cdb39cdac34bef99dd0940ab28e306f692404c2eea44d85dfd634214872a0a09`) into a cache
**outside the repository**, verifies the checksum and extracts `pppub24.csv` and
`hhpub24.csv`; `data_builder.py` then rebuilds `tax_microdata_2024.csv` with five
new dependent age-band columns (under 6, 6–16, 17, 18, and 19–23 enrolled in
school). Every one of the twenty pre-existing columns comes back **byte for
byte**, and the SOI calibration ratios (119% of returns, 81% of AGI) did not
move — which is what makes fetch-not-vendor safe: a future rebuild that changes
an old column is a bug, and now it is a visible one.

### Earned Income Tax Credit

The EITC is modeled by income quintile using IRS SOI data on the distribution of EITC recipients. Phase-in rates, maximum credits, and phaseout rates vary by filing status and number of children (Rev. Proc. 2023-34 §2.06, tax year 2024):

| Children | Phase-in Rate | Max Credit | Phaseout Rate |
|----------|-------------|----------|--------------|
| 0 | 7.65% | $632 | 7.65% |
| 1 | 34.0% | $4,213 | 15.98% |
| 2 | 40.0% | $6,960 | 21.06% |
| 3+ | 45.0% | $7,830 | 21.06% |

`microsim/engine.py` reads this schedule from `credits_core` rather than
duplicating it. Two defects closed with that change: the engine had applied a
single 21.06% phaseout rate to *every* child count, and carried a stale vintage
of the maxima. A third is arithmetically larger — the engine counted the EITC's
**qualifying children** with the CTC's under-17 column, where IRC §32(c)(3)
counts children under 19, or under 24 and a full-time student. On the rebuilt
file that is **79.7M against 65.0M**, a 23% undercount of the population the
credit is scaled on. Fixing it raises baseline EITC and moves no benchmark,
because every EITC-relevant reform is differenced against the same baseline.

---

## Tax Expenditures

The `TaxExpenditurePolicy` module (`fiscal_model/tax_expenditures.py`) scores changes to major itemized deductions and exclusions.

### SALT Cap

The TCJA capped the State and Local Tax (SALT) deduction at $10,000, raising $1.9T/10yr compared to full deductibility. The model scores:
- Changes in the cap level ($10K → unlimited, or $20K–$25K)
- Distributional effects (primarily concentrated in high-tax states, top quintiles)
- SALT cap interaction with AMT (the AMT historically limited SALT for high earners anyway)

**The uncapped SALT level is derived, not stored.**
`uncapped_salt_expenditure_billions()` returns
`load_deduction_distribution("salt").implied_benefit_billions` — IRS **SOI Table
2.1 TY2023**'s total (unlimited) state-and-local-tax deduction, priced AGI class
by AGI class at the IRC §1 married-joint schedule as adjusted for 2025
(Rev. Proc. 2024-40) — which gives **$89.55B/yr**. It replaced a stored
`annual_cost_no_cap = 120.0` that was **exactly the carried $1,200B benchmark
divided by ten**: unsourced, and load-bearing once lane L6 made the `eliminate`
rule read it. The check that the method is not made up is that the *identical*
computation on SOI's **limited** column returns **$25.0B** against the base
table's own `annual_cost = 25.0` — two numbers with no common ancestor agreeing
to a tenth of a percent. Both are pinned in
`tests/test_tax_expenditure_units.py`. Nothing fitted moved: every preset scores
in `reported` mode and returns the same annual.

*The `annual_cost_no_limit = 100.0` on the mortgage record has not had the same
treatment.* It names no statute, is still dead, and stays unread until somebody
sources it — wiring it in would move `eliminate_mortgage` from −5.1% to about
+244% on an unsourced constant.

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

### Revenue Model — net, not gross (Wave 3, lane L8)

**The headline a tariff produces is net of the offsets CBO, JCT and Treasury
apply to any indirect tax.** Until Wave 3 the module returned gross customs duty
with a flat 5% avoidance haircut and stopped, which is not a budget effect. The
scored chain is now:

```
Δτ      = stated rate − duty already collected on the base
p       = border_pass_through × Δτ                       (pass-through frozen at 1.00)
V       = 1 + ε·p                                        for p ≤ 0.30
        = 1 + ε(0.30) + (p − 0.30)·ε·2                   above it, floored at 0.20
gross   = Import_Base × V × Δτ/(1 + Δτ)                  tax-inclusive rate
avoid   = avoidance_rate × gross
offset  = income_payroll_offset_rate × (gross − avoid)
retal   = MARGINAL_REVENUE_RATE × [retaliation_rate × Δτ × export_base]
net     = gross − avoid − offset − retal
```

One value per mechanism, cited, applied to every tariff policy; nothing is keyed
to a benchmark id.

| Parameter | Value | Source |
|---|---:|---|
| Border pass-through to duty-inclusive import prices | **1.00** | Amiti, Redding & Weinstein (2019); Fajgelbaum, Goldberg, Kennedy & Khandelwal (2020) — the duty-inclusive US import price rose one-for-one and foreign export prices did not fall |
| Import-demand elasticity | **−0.997** | Ghodsi, Grübler & Stehrer (2016), the binding US weighted average adopted by Tax Foundation FF861 p. 4; USITC pub. 5405 finds ≈−1 in year one |
| High-rate elasticity multiplier above 30pp | **2.0** | Boehm, Levchenko & Pandalai-Nayar (2023): −0.76 in year 1 converging to −1.75/−2.25 within 7-10 years |
| Duty avoidance / evasion | **0.05** | Module default; FF861 uses 8% noncompliance, so this is the conservative end |
| **Income-and-payroll offset** | **0.25** | The longstanding CBO/JCT/OTA convention: duty paid is income not paid to labour and capital, so the income and payroll bases shrink. FF861 p. 4 nn. 3 and 11 cite JCT **JCX-59-11** and **JCX-9-24**; Tax Foundation's own calculator gives 26.2% over this window, and the round 25% is used rather than 26.2% precisely because 26.2% is an output fitted to one of the benchmarks |
| Retaliation intensity | **0.30** | Module default |
| Federal receipts per dollar of lost export income | **0.25** | `constants.MARGINAL_REVENUE_RATE`, the app's own convention |

`jct.gov` and `cbo.gov` both return HTTP 403 to this environment, so the offset
convention is cited **secondhand** through Tax Foundation FF861 — already this
repository's transcribed benchmark source for the universal-tariff row — which
states the convention and names both JCT documents for it.

**Sign convention.** `estimate_behavioral_offset` carries the static effect's
sign, per this document's own rule for a behavioural offset. It used to return an
unsigned positive number, which the scorer added to `−static_revenue`: right for
a tariff increase and exactly wrong for a tariff **cut**, where a 5pp cut on a
$1,000B base scored $711B of deficit against a gross revenue loss of $553B. The
same cut now scores $394B — eroded, as it should be.

### The retaliation export base

`estimate_retaliation_cost` used to multiply `retaliation_rate × rate ×
$2,100B` — *total* US exports — for every policy, which implied retaliation
losses larger than the whole tariff base for a $50B steel tariff. `TariffPolicy`
now carries `retaliation_export_base_billions`: US goods exports **to the
targeted country** where the policy names one, and total goods exports scaled by
the affected import share otherwise.

### Non-Linear Import Response

Above a 30% tariff rate, substitution accelerates (elasticity doubles). A floor
ensures imports never fall below 20% of baseline. Note that with the elasticity
roughly doubled the `min_volume_factor = 0.20` floor now binds above about 55pp
where it previously bound only above 95pp; it is an unsourced constant doing more
work than it used to.

### Consumer Price Pass-Through (display, not score)

The **retail** pass-through is a different object from the border pass-through
above, and a lower number. The household-cost display uses 60% (Cavallo et al.
2021); the score's import-demand response uses the near-complete border
pass-through of 1.00.

```
Household_Cost = Tariff_Rate × Import_Base × pass_through_rate / us_households
```

The model reports per-household consumer cost by income quintile (lower-income households spend a larger share of income on imported goods).

### Country-Specific Modeling

Every level below is a **2024 Census measurement**
(`fiscal_model/data_files/trade/tariff_scoring_inputs.csv`, USA Trade Online /
Census API, retrieved 2026-09-02): general imports at customs value
(`GEN_VAL_YR`), effective duty rates as calculated duty over imports for
consumption (`CAL_DUT_YR / CON_VAL_YR`, which includes the Section 232 and 301
duties actually collected), exports as `ALL_VAL_YR`.

| Quantity | Value | Constant it replaced |
|---|---:|---|
| US goods imports, 2024 | **$3,263.9B** | 3,200.0 |
| US goods exports, 2024 | **$2,063.0B** | 2,100.0 |
| Average duty collected, all imports | **2.36%** | 0.03 |
| Imports from China | **$440.3B** | 430.0 |
| Duty collected on China imports | **10.93%** | 0.20 |
| US goods exports to China | **$143.3B** | *(new)* |
| ⇒ universal-tariff coverage, 1 − USMCA share | **0.7197** | `universal_coverage_rate` 0.70 (**was fitted**) |
| HS-87 vehicles and parts imports | **$384.9B** | 380.0 |
| HS-87 imports from Canada + Mexico, share | **48.42%** | `auto_usmca_exempt_share` 0.65 |
| HS-72 + HS-76 imports | **$58.9B** | 50.0 |
| Duty collected on HS-72 + HS-76 | **3.06%** | *(new — the Section 232 netting)* |
| — | — | `china_effective_coverage` 0.50 **deleted** |

**No constant in `TRADE_BASELINE` is fitted to a benchmark any more.**
`china_effective_coverage` was replaced by the incremental-rate identity a 60%
China tariff actually implies — 60pp *minus the duty already collected*, applied
to the whole base, not 40pp applied to half of it — and
`create_trump_china_60`'s per-case `import_elasticity=-0.7` override was deleted
with it. `reciprocal_coverage_rate = 0.50` is the one shape assumption left that
is not a measurement, because no published estimate scores a flat 20pp on half of
goods imports.

**What the change is worth, and what it costs.** Net/gross runs **0.599 to
0.655** across the five presets; the repository's own knowledge snapshot puts a
*fully* netted tariff score at 40-50% of gross, and that chain includes a GDP
feedback this module does not carry, so sitting above the band is the right side
to miss on. Retaliation returns **$111.4B** over ten years for the 10% universal
tariff against FF861's **$278B** — an export-value loss is not an income loss,
and the channel carries no multiplier and no supply-chain effect. Every shipped
tariff preset moved 28-49%, and a caption computed from the scored result ships
under the headline saying so.

**No GDP-feedback channel** is the single largest remaining piece.

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

A $35/month insulin cap is a **cost-sharing** cap: it moves a patient's liability
onto the plan, and the federal budget picks up only its share of that shift. The
module scores that share, not the retail-minus-cap differential:

```
Federal effect = ASPE Part D out-of-pocket relief ($734M/yr, 2020)
                 × Medicare's basic-benefit subsidy share (74.5%, statutory)
               + private-market cost shift
                 × marginal income-plus-payroll offset on premiums (32%)
```

Every input is transcribed with document, page and URL to
`fiscal_model/data_files/pharma/drug_pricing_incidence.csv` (HHS ASPE, *Report
on the Affordability of Insulin*; MedPAC, *Report to the Congress: Medicare
Payment Policy*; CBO budget option 58627). The result is a **deficit increase**
of about +$7B over ten years, which agrees in sign with CBO's own score of a
private-market cap — publication 57957 (H.R. 6833) puts it at +$6.566B of
outlays and −$4.793B of revenues, about **+$11.4B**. Not modelled: induced
utilisation, and growth in insulin cost and enrolment across the window (ASPE's
$734M is a single 2020 figure held flat).

*Prior specification, corrected 2026-09-01:* the module booked the whole
`($6,000 − $420) × 8.4M` retail differential as a federal outlay reduction, and
extending the cap to private insurance *raised* the modelled federal saving 2.5×.

### International Reference Pricing

Referencing Medicare drug prices to an international benchmark is scored on a
**net-price, brand-only, federal-share** basis. US unbranded generics are
*cheaper* than the OECD comparison (67% of comparison-country prices) and cannot
contribute savings, so only brand molecules are referenced; and the price ratio
applied is RAND's **net** brand ratio of **3.08** — US brand-name originator
prices at 422% of 33 OECD comparison countries before rebates, less a 37.2%
gross-to-net adjustment (RAND RR-A788-3 / ASPE, *International Prescription Drug
Price Comparisons: Estimates Using 2022 Data*, February 2024). The base is Part D
gross spending net of the 23% manufacturer-rebate share and restricted to the
80% brand share, plus Part B drug spending, each times the federal share of its
program.

*Prior specification, corrected 2026-09-01:* RAND's **gross list-price** all-drug
ratio (2.56) was applied to a **net** Part B + D base with no rebate adjustment
and no brand/generic split.

**Known limitation, unrepaired.** RAND's index is computed on presentations sold
in both markets, and the module applies it to all brand spending; no utilisation,
launch-delay or availability response is modelled on either this row or the
insulin row.

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

### Budget authority → outlays (spend-out)

A spending proposal states **budget authority**; a budget score reports
**outlays**. `SpendingPolicy` keeps the two distinct and converts between them
with a lagged convolution:

```
outlays_t = Σ_k s_k · BA_{t−k}
```

`s` is a first-year/out-year profile keyed by **account class** — the thing that
governs how fast an obligation becomes a disbursement. Pay and benefits disburse
at once; construction and capital take years.

| Account class | What it covers | s₀ | Σs | 10-yr outlay/authority on a level path |
|---|---|--:|--:|--:|
| `personnel_and_benefits` | pay, allowances, medical-care enrolment | 0.921 | 1.000 | 0.991 |
| `mandatory_benefit` | direct benefit payments, outlaid when owed | 0.977 | 1.000 | 0.998 |
| `operations_and_support` | agency operations, O&M, force structure, across-the-board caps | 0.539 | 0.977 | 0.893 |
| `grants_and_procurement` | project and formula grants, student aid, foreign assistance, procurement, R&D | 0.405 | 1.000 | 0.848 |
| `construction_and_capital` | construction, infrastructure and other capital grants | 0.022 | 0.973 | 0.663 |

**Provenance.** The profiles are fitted by non-negative least squares on the
14 options in CBO, *Options for Reducing the Deficit: 2025 to 2034*
([publication 60557](https://www.cbo.gov/publication/60557)) that publish both a
budget-authority row and an outlays row **and are not scored by the validation
battery**; the five that are scored never donate to any profile, and option 44 is
excluded because its outlays exceed its authority in every year. Class assignment
is a classification from the predominant account type each program funds, never
a fit. OMB Circular A-11 publishes no numeric outlay-rate table (see
[VALIDATION_NOTES.md](VALIDATION_NOTES.md) §5a); CBO's account-level spendout
rates (publications 61913 and 62256) are the open external cross-check.

The window truncates the **tail, not the head**: authority whose outlays fall
past the projection end is dropped — the truncation official 10-year totals
embed — while a policy that began before the window still spends its earlier
authority into it. `immediate` (the identity, `s₀ = 1`) remains available as an
explicit choice and is the default for nothing.

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
7.77pp** (`python scripts/run_validation_dashboard.py`; full table in
[VALIDATION.md](VALIDATION.md)). Two of the seven are **circular** and must not be
counted as skill: `distribution_effects.calculate_tcja_effect` builds its decile
tiers *out of* CBO 54796 and CBO 60007, so the 0.00pp against the first and the
0.74pp against the second are bookkeeping. The five non-circular tables run
2.10pp (JCT JCX-68-17) to 7.77pp (CBO 56952, the ARP bundle). **The ARP row rose
4.76pp → 7.77pp in Wave 3 and the rise is the honest number**: the Recovery
Rebate moved onto return-level data alongside the CTC and EITC, and the old
figure was ranking one of the three components by IRS return counts and the
other two by CPS tax units, so two universes were partly cancelling. Scored
consistently, the quintile dollar levels move from about a third of CBO's to
close to them and the bundle totals $485B (within 10% of the three provisions'
actual cost) while the share error grows, because the model's bottom quintile is
38.2M tax units against CBO's ~26M households. The tax-unit-versus-household
universe is the open item.

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
| Cut international affairs 25% | −$187B | −$187B | 0% | CBO Options 2025–2034 #37 |
| Cut selected nondefense discretionary | −$339B | −$333B | 2% | CBO Options 2025–2034 #42 |
| 1pp all brackets | −$960B | −$920B | 4% | JCT |
| 5pp top rate ($1M+) | −$700B | −$648B | 7% | TPC |
| Tax accrued gains at death | −$536B | −$581B | 8% | CBO Options 2025–2034 #51 |
| Social Security Fairness Act, WEP/GPO repeal | +$196B | +$215B | 10% | CBO |
| Fiscal Responsibility Act 2023, discretionary caps | −$1,332B | −$1,170B | 12% | CBO |
| Biden top rate 39.6% ($400K+) | −$252B | −$217B | 14% | Treasury |
| IIJA 2021, discretionary component | +$415B | +$340B | 18% | CBO |
| All ordinary rates +1pp | −$1,185B | −$920B | 22% | CBO Options 2025–2034 #45 |
| LTCG + qualified dividends +2pp | −$103B | −$57B | 45% | CBO Options 2025–2034 #47 |
| Corporate rate +1pp | −$136B | −$200B | 47% | CBO Options 2025–2034 #64 |
| Treasury 39.6% + step-up repeal | −$322B | −$1,022B | 218% | Treasury (Green Book FY2022) |

**26 pre-registered cases, mean absolute error 31.0% (median 15.1%); 13 of 26
within 15%, 19 of 26 within 25%** (`scripts/cold_holdout.py`; full table in
[VALIDATION.md](VALIDATION.md)). Do **not** collapse this into one tolerance.
Ordinary-bracket and AGI-inclusive rate changes at conventional thresholds land
at **2–22%**; discretionary funding changes, now scored through the
budget-authority-to-outlay spend-out model described above, land at **0–11%**
for the five CBO Options rows and **10–18%** for the three enacted-law
components; the tier's one tax-expenditure cap, CBO Option 56, lands at **24%**
on a named omission (the module evaluates its excess share once at the start
year, while CBO's chained-CPI-indexed limit lets a widening slice of every
premium rise above it); two rate cases whose source states a filing-status-specific boundary
the generic path cannot express land at **18%** and **45%**; **gains at death
now lands at 8%**, having been 84% before Wave 2 replaced a flat $54B/yr
constant with decedent wealth × an unrealized-gain share by estate size; and
what is left of the behavioral tail runs **45%** (a 2pp preferential-rate
change), **47%** (corporate margins), **54–56%** (payroll incidence) and
**135–218%** for the two step-up-elimination rows, whose whole residual is that
the model applies no behavioral response to the death channel while Treasury's
own score prices spousal and charitable carve-outs, the §121 residence
exclusion, tangible personal property and a family-business deferral.
Capital gains remains the tier's dominant error mass — 4 cases carrying 405.6 of
the tier's 805.8 units, 50.3% — but only its rate-and-step-up half.

The mean moved from Phase B's 43.4% on 23 cases to 52.6% on 25 while the median
*fell* from 23.1% to 21.1%: `top_rate_45` was retired in Phase E (its −$420B target
appears in no TPC, CBO or JCT publication), `biden_capital_gains_39` was re-sourced
to the FY2025 Green Book's actual line item and got *worse* (79% → 142%), and three
enacted-law components joined — one of them IIJA at **356%**, which was kept
deliberately as the sharpest available evidence for a missing mechanism.
**Wave 1 then built that mechanism** (2026-09-01/02): the spend-out model took
the mean to 45.3%, and superseding IIJA's shape input with the authorization
schedule CBO's own estimate states — a new manifest row, `.v1` → `.v2`, target
unchanged — took it to 34.4%, with within-15 rising 8 → 12. No tax row moved
and no target was edited. **Wave 2 (2026-09-02, PR #95) then did the same for
capital gains** and the mean fell to **31.3%**, the median to **14.1%** and
within-15 rose to **13**: the realizations base became IRS SOI Table 3.5's
bracket-priced income, the elasticity became the semi-log tax-rate form CRS
R48562 defines, the 5.3× lock-in multiplier became a derived 1.44× price wedge,
and the $54B gains-at-death constant became a decedent-wealth stock. Two rows
improved sharply, one barely moved and one got worse; no target was edited and
no per-case constant survives.

**Wave 3 (2026-09-02, PR #100) added a case rather than moving one.** CBO Option
56 had been excluded for *leakage* — the only expressible path ran through a
tax-expenditure annual fitted to that same reform — and lane L6 removed the
dependency, so a percentile cap is now the published expenditure level times a
share read off a premium distribution. It enters at **−$529.9B against
−$697.0B, 24.0%**, and no existing row moved by a cent: the mean falls to
**31.0%** because the new row is below it, and the median *rises* to **15.1%**
because the new row sits just above the old midpoint. The CI gate was
re-derived by the workflow's own rule to **`--max-mean-error 40
--min-within-25pct 18`** (PR #102).

Ordinary-bracket rate changes score on the ordinary-income base (excluding
preferential LTCG/QDIV); AGI-inclusive surtaxes score on the full taxable-income
base — classified from how each source describes its base, never fitted. Treat
uncalibrated custom rate policies as directional, ±15–25%.

### Tier 2a — Calibrated reference models (fitted; low error by construction)

Specialized modules parameterized to reproduce the published decomposition. Useful
as auditable, source-linked reconstructions of official scores, *not* as
independent confirmation. **28 fitted benchmarks, mean absolute error 2.0%, 28 of
28 within 15%, 28 of 28 within 25%.** Twenty-three of them reproduce a published
CBO/JCT/Treasury decomposition; the other five are fitted to a target that is
itself a model estimate, so those measure internal consistency only. (Earlier
revisions of this file quoted “≈ 5% across 29 benchmarks”, then 2.7% over 34,
then 2.8% over 33, then 2.2% over 30; `scripts/cold_holdout.py` is now the only
place this figure should be read from.)

**Quote the 28 with the rows that left it — there are three different reasons and
all are live.** First, `ScorecardSummary.revised_target_entries` is **3**: three
calibrated targets have been corrected through the Tier-2 revision ledger
(`fiscal_model/validation/target_revisions.py`), and a constant fitted to a
superseded figure is not fitted to its replacement — so the revised
`extend_tcja_amt` row reports in Tier 2b, where a miss is a finding rather than a
regression. Held in place instead, this tier reads **29 benchmarks at 4.3%, 28 of
29 within 15%**, the extra miss being that row at 66.8%. Second, **Wave 2 took
this tier 33 → 30**: deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural
tuples removed the only constants ever fitted to the three capital-gains
scenarios, so they now report in Tier 2b too. Third, **Wave 3's L8 lane took it
30 → 28**: `universal_coverage_rate` became a Census measurement and
`china_effective_coverage` was deleted for an incremental-rate identity, so the
two Trump tariff rows — which had been reading 1.1% and 6.2% off constants
fitted to them — now report in Tier 2b at 37.1% and 44.3%. The mean *fell*
2.8% → 2.2% → **2.0%** and the worst row is still `tcja_no_salt_cap` at 13.9%,
because every row that left was one this tier had been carrying. Composition,
not accuracy.

| Policy | Official Score | Model Score | Error | Status |
|--------|----------------|-------------|-------|--------|
| **TCJA Full Extension** | **$4,600B** | **$4,582B** | **0.4%** | calibrated |
| **Biden Corporate 28%** | **−$1,347B** | **−$1,397B** | **3.7%** | calibrated |
| **Biden CTC 2021** | **$1,600B** | **$1,600B** | **0.0%** | calibrated |
| **Estate: Biden Reform** | **−$450B** | **−$450B** | **0.0%** | calibrated |
| **SS Donut Hole $250K** | **−$2,700B** | **−$2,700B** | **0.0%** | calibrated |
| **Repeal Corporate AMT** | **$220B** | **$220B** | **0.0%** | calibrated |
| **Cap Employer Health** | **−$450B** | **−$450B** | **0.1%** | calibrated |
| IRA Enforcement ($80B) | −$200B | −$189B | 5.5% | calibrated |
| Eliminate mortgage deduction | −$300B | −$330B | 10.1% | calibrated |
| TCJA extension without the SALT cap | $5,700B | $6,495B | 13.9% | calibrated (worst fitted row) |

*Positive values indicate deficit increase (cost); negative values indicate deficit reduction (savings). All estimates are 10-year totals.*

*Rows this table used to carry that no longer belong in it:* the two Trump
tariff rows left in Wave 3 when L8 replaced their fitted coverage constants with
Census measurements, and report in Tier 2b at 37.1% and 44.3%; the two PWBM
capital-gains scenarios left in Wave 2 with the constants fitted to them and now
report in Tier 2b at −28.4% and +76.5%; Biden GILTI reform, FDII repeal and IRA
drug negotiation left earlier, in the Phase E provenance pass, and report in
Tier 2b at 17.8%, **44.7%** and 25.7%. `scripts/cold_holdout.py` prints the live
membership of both tiers and is the only place it should be read from.

### Tier 2b — Unfitted module reconstructions (target never fitted to)

**26 policies, mean absolute error 61.8%, median 38.0%; 5 of 26 within 15%, 9 of
26 within 25%.** Both the mean and the population moved in Wave 3, so the
constant-population comparison belongs beside them: on the 24 rows this tier held
before L8 it reads **63.6%**. These are four populations and must never be read
as one number:

- **Fourteen sectoral presets** (international, trade, pharma, IRS
  enforcement, climate) at **81.0% mean / 38.0% median** — twelve of them Phase
  E's, plus the two tariff rows L8 unfitted; **87.8% / 32.3%** on the constant
  12-row population, because L8 took it 104.8% → 84.6% by netting the tariff
  scores and L9 pushed it back up 3.2pp by giving FDII repeal Treasury's own
  published cost. They ship in the app
  with an official figure attached and no module constant was ever fitted to any
  of them. Two — the universal insulin cap and international reference pricing —
  diagnosed real federal-incidence bugs in `pharma.py`, and **Wave 1's L7 lane
  repaired both**, taking this subset from 394.1% to 113.8% without fitting a
  parameter to any of the three pharma targets. The insulin *target* was then
  corrected too: CBO publication 57957 scores a private-market insulin cap at
  about **+$11.4B**, i.e. as *adding* to the deficit, against the carried −$15B,
  and the model scores **+$7.0B** — so the row moved from 146.4% with the
  directions disagreeing to **39.0%** with them agreeing, taking this subset to
  104.8% / 40.0%. Reference pricing at −$746B against a −$100B `model_estimate`
  target is the family's largest remaining row; CBO scored H.R. 3's narrower
  international-reference cap at about $456B, which is where a broader policy
  should sit. **Wave 3 then moved two families and neither move was a
  calibration.** L8 took the tariff scores gross → net and the five trade rows
  from a summed 360.8 points of error to **191.9** (auto 152.3% → 82.2%, steel
  73.2% → 11.9%, reciprocal 128.0% → 16.4%, and the two formerly-fitted rows to
  37.1% and 44.3%). L9 gave FDII repeal the base × rate identity the module's
  own rate branch already used, on Treasury OTA's published $130,230M cost, and
  the row went **15.0% → 44.7%** while the package went **41.0% → 49.5%** — both
  pre-registered as regressions before the lane opened a file, because the
  identity moves toward the document and away from a target 54% above it.
- **Eight Phase D P.L. 119-21 line items** (JCT JCX-35-25, transcribed with page
  references to `fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`)
  at **35.8% mean**, 2 of 8 within 15%, scored over JCT's own FY2025–2034 window.
  This is the sharpest available evidence that the calibrated tier is
  reconstruction rather than structure: the TCJA module reproduces CBO's $4.6T
  aggregate to **0.4%** and JCT's own component rows to **36%**, because one
  calibration factor is fitted to the aggregate and no factor is fitted to any
  component.
- **Three capital-gains scenarios** at **39.6% mean** — CBO +2pp −14.0%, PWBM
  39.6% with step-up −28.4%, PWBM 39.6% without step-up +76.5%. They arrived in
  Wave 2, when `fiscal_model/validation/scenarios.py`'s per-case behavioural tuples were
  deleted: those tuples *were* the fit, so once they were gone
  `calibrated_to_target` became simply `False`. Because no per-case constant is
  left, these three figures are **identical** to the same three rows in Tier 2c,
  and `run_loo.py --donor-matrix` prints three identical rows — there is nothing
  to hold out.
- **One revised-target row**, `extend_tcja_amt`, at **66.8%**. Its target moved
  from $450B to CRS R48286's published $1,357.1B and the AMT constant — still
  fitted to the superseded figure — was deliberately not retuned, so it reports
  here rather than in Tier 2a. The module's *derived* path scores $855.3B,
  **−37.0%** against the same row.

Nothing in any of the four was retuned to close a gap, and every row carries a
`known_limitations` note naming the structural cause.

### Tier 2c — Calibrated modules, held out (leave-one-out)

`python scripts/run_loo.py` refits each calibrated module's mechanism on the
*other* benchmarks in its module and asks it to rebuild the held-out one.
**18 derivable cases, mean absolute error 28.4%, median 16.5%, 9 of 18 within
15%**, plus **4 cases declared not cross-validatable** — no second benchmark to
calibrate on, or a base constant that is the published target restated — which are
reported and never folded into the aggregate.

| Module | Kind | n | Not x-val | LOO mean abs error |
|---|---|--:|--:|--:|
| Payroll | structural | 3 | 1 | 3.8% |
| Estate | structural | 2 | 1 | 10.4% |
| Credits | structural (CPS ASEC per-unit) | 3 | 0 | **20.5%** |
| Expenditures | bottom-up | 5 | 1 | **30.2%** |
| CapitalGains | structural | 3 | 0 | 39.6% |
| AMT | structural | 2 | 1 | 73.9% |

Compare against the 2.0% in Tier 2a: that number measures bookkeeping, this one
measures whether the machinery predicts.

**Wave 3 moved two of the six modules, in opposite directions.** `Credits`
**45.1% → 20.5%**: lane L3 replaced `Δcredit × units × participation` with two
statutory parameter sets run through `MicroTaxCalculator` over CPS ASEC tax units
and differenced on final liability, which prices refundability, the tax limit on
the non-refundable leg and the qualifying-age expansions the identity had
nowhere to put. The single largest correction inside it is a **counterfactual**,
not a parameter: IRC §24's $2,000 reverts to $1,000 after 2025, so a window
opening in 2025 is scored against current law for one year and the pre-TCJA
regime for nine — $883B against a fixed baseline, **$1,528B** against the one the
statute specifies. `Expenditures` **28.8% (n=4) → 30.2% (n=5)**, and the rise is
the better state: PR #100 replaced `annual_cost_no_cap = 120.0` — exactly the
carried $1,200B target over ten — with **$89.55B** computed from IRS SOI Table
2.1 at the statutory schedule, `loo.py`'s untouched leakage guard stopped firing,
`eliminate_salt` re-entered at **+10.2%**, and `repeal_salt_cap` moved
**+4.0% → −29.4%** because its old +4.0% was `−(120.0 − 25.0)`, the same leaked
constant under a different benchmark. Held to the 17 cases the suite carried
before the readmission the mean is **29.5%**; the printed 28.4% over 18 is the
honest figure and the difference is composition.

**Wave 2 had moved three of the six, and one case had left the denominator.**
`CapitalGains` **171.2% → 39.6%** on one frozen literature elasticity set
replacing three hand-set tuples; `Estate` **25.8% → 10.4%** on a SOI-fitted
Pareto size distribution replacing a blend that was exactly invariant in the
exemption; `Expenditures` **39.4% → 28.8%** on declared cap units and SOI
benefit distributions, with `eliminate_salt` excluded for the leakage Wave 3
then closed.

**Before Wave 2 this aggregate had moved twice, and neither move was a model
change.** Wave 1
took it 59.3% → 61.7%, entirely on AMT (79.6% → 100.5%), and that rise was the
module becoming more structural rather than less accurate: L5 replaced a flat
steady-state identity (~$73B/yr) with TPC T25-0049's published year-indexed path.
The plan's hypothesis had been that a missing 2026 phase-in biased the derivation
high; the table shows a **cliff** (0.2M AMT payers in 2025, 7.6M in 2026)
followed by *growth* ($71.6B in 2026 to $124.2B in 2035), so the flat level was
the window's early-year value and indexing it by year **raises** the score. Both
rows therefore moved away from their carried $450B targets. Correcting
`extend_tcja_amt`'s target to the published $1,357.1B then took the aggregate to
58.7% and AMT to **73.9%**: the held-out derivation is **unchanged at $855.3B**
and only the figure it is measured against moved, so that row reads **−37.0%**
instead of +90.1%. Wave 2's 58.7% → **32.3%** is the first move that *is* the
model, with the case-count caveat above attached, and Wave 3's 32.3% → **28.4%**
is one model change and one provenance fix pulling against each other. See
[VALIDATION_NOTES.md](VALIDATION_NOTES.md) §6.

### Reading the tiers

**Report these separately and never collapse them:**

| Tier | What it measures | n | Mean | Median |
|---|---|--:|--:|--:|
| 1 — out-of-sample, pre-registered | prediction | 26 | **31.0%** | 15.1% |
| 2a — calibrated, fitted | bookkeeping (low by construction) | 28 | **2.0%** | 0.1% |
| 2b — unfitted module reconstructions | modules against targets they never saw | 26 | **61.8%** | 38.0% |
| 2c — calibrated, leave-one-out | how much of the calibration is structure | 18 | **28.4%** | 16.5% |

Three of the four changed population in Wave 3, so the constant-population
readings belong next to them: Tier 2b is **63.6%** over the 24 rows it held
before L8, its sectoral subset **87.8%** over the 12 it held, and Tier 2c would
read **29.5%** over the 17 it held had `eliminate_salt` not been readmitted. A
mean that moves because the population moved has not improved.

Distributional accuracy is a fifth, separate number: **seven published CBO/JCT
tables at 0.00–7.77pp** mean absolute share error, **two of which are circular**
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
