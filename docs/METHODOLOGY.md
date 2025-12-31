# Scoring Methodology

> How the Fiscal Policy Calculator estimates budget impacts

---

## Table of Contents

1. [Overview](#overview)
2. [Static Scoring](#static-scoring)
3. [Behavioral Response](#behavioral-response)
4. [Dynamic Scoring](#dynamic-scoring)
5. [Spending Multipliers](#spending-multipliers)
6. [Uncertainty Analysis](#uncertainty-analysis)
7. [Comparison to Official Methods](#comparison-to-official-methods)
8. [References](#references)

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

1. **Current Law Baseline**: All estimates relative to current law (not current policy)
2. **10-Year Budget Window**: Standard FY2025-2034 window
3. **Conventional Scoring**: Behavioral but not macroeconomic (default)
4. **Dynamic Scoring**: Optional macroeconomic feedback

---

## Static Scoring

### Tax Rate Changes

For income tax rate changes, static revenue effect is:

```
ΔRevenue = ΔRate × Marginal_Income × Num_Taxpayers
```

Where:
- **ΔRate**: Change in tax rate (e.g., +0.026 for 2.6pp increase)
- **Marginal_Income**: Average income *above threshold* for affected filers
- **Num_Taxpayers**: Number of taxpayers above threshold

**Example**: Biden's $400K+ rate increase (37% → 39.6%)
```python
rate_change = 0.026  # 2.6 percentage points
threshold = 400_000
affected_filers = 1.8M  # From IRS SOI
avg_income = 1.2M       # Average total income of filers above $400K
marginal_income = 1.2M - 0.4M = 800K  # Income ABOVE threshold

static_revenue = 0.026 × 800,000 × 1,800,000 = $37.4B/year
```

**Key Insight**: Only income *above* the threshold is subject to the rate change. A filer earning $500K with a $400K threshold has only $100K of marginal income affected.

### Data Source: IRS SOI

We use IRS Statistics of Income (SOI) Table 1.1 and Table 3.3 to get:
- Number of returns by income bracket
- Total taxable income by bracket
- Tax liability by bracket

```python
from fiscal_model.data import IRSSOIData

irs = IRSSOIData()
bracket_info = irs.get_filers_by_bracket(year=2022, threshold=400_000)
# Returns: {'num_filers': 1.8M, 'avg_taxable_income': 1.2M, ...}
```

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

Taxpayers respond to rate changes by adjusting taxable income:

```
%ΔTaxable_Income = -ETI × %Δ(1 - marginal_rate)
```

The **behavioral offset** reduces the static estimate:

```python
behavioral_offset = -static_effect × ETI × 0.5
```

Where `0.5` converts from income elasticity to revenue offset.

### ETI Values by Literature

| Source | ETI Estimate | Context |
|--------|--------------|---------|
| Saez et al. (2012) | 0.25 | Preferred estimate |
| Gruber & Saez (2002) | 0.40 | Upper bound |
| CBO (2014) | 0.25 | Conventional scoring |
| JCT | 0.25 | Revenue estimates |

**Default**: ETI = 0.25 (adjustable in policy definition)

### Behavioral Response Intuition

- **Tax Increase**: People reduce taxable income → less revenue than static estimate
- **Tax Cut**: People increase taxable income → less revenue loss than static estimate

The behavioral response always *dampens* the static effect.

### Capital Gains: Realizations Elasticity

Capital gains realizations respond more strongly than wage income due to timing flexibility (lock-in effect). We model this with **time-varying elasticity**:

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
| Short-run elasticity (years 1-3) | 0.8 | Timing/anticipation effects dominate |
| Long-run elasticity (years 4+) | 0.4 | Only permanent behavioral response |
| Transition period | 3 years | Linear interpolation |

**References:**
- CBO (2012): Short-run ε ≈ 0.7-1.0
- Dowd, McClelland, Muthitacharoen (2015): Long-run ε ≈ 0.3-0.5
- Penn Wharton Budget Model: Distinguishes transitory vs permanent response

**Step-Up Basis at Death**

Under current law, unrealized capital gains are forgiven at death (step-up basis). This creates a much stronger lock-in effect because taxpayers can avoid tax entirely by holding until death.

We model this with a **lock-in multiplier** applied to the base elasticity:
```
ε_effective = ε_base × step_up_lock_in_multiplier
```

| Scenario | Lock-in Multiplier | Effective ε |
|----------|-------------------|-------------|
| With step-up (current law) | 5.3x | ~4.2 short-run |
| Step-up eliminated | 1.0x | 0.8 short-run |

**Revenue from Step-Up Elimination**

When step-up is eliminated, gains become taxable at death:
```
Revenue_death = τ × Gains_at_death × (1 - exemption_share)
```

Key estimates:
- Annual gains at death: ~$54B (CBO)
- Biden proposal ($1M exemption): ~$14B/year additional revenue
- Full elimination (no exemption): ~$23B/year

**Validation Results (December 2024):**

| Scenario | Official | Model | Error | Rating |
|----------|----------|-------|-------|--------|
| CBO +2pp (all brackets) | -$70B | -$83B | -19% | Acceptable |
| PWBM 39.6% (with step-up) | +$33B | +$30B | -9% | **Good** |
| PWBM 39.6% (no step-up) | -$113B | -$139B | -23% | Poor |

The model now correctly predicts that raising capital gains rates to 39.6% with step-up basis **loses revenue** (+$30B deficit), while eliminating step-up raises revenue.

---

## Dynamic Scoring

### When to Use Dynamic Scoring

CBO provides dynamic scores for:
- Major legislation (>0.25% of GDP)
- At Congressional request

Our model offers dynamic scoring as an option for all policies.

### Economic Channels

1. **Labor Supply**
   - Tax changes affect after-tax wages
   - Labor supply elasticity: 0.15 (compensated)
   
2. **Capital Formation**
   - Corporate tax affects investment
   - Capital elasticity: 0.25

3. **Aggregate Demand**
   - Short-run multiplier effects
   - GDP feedback to revenue

### Revenue Feedback

GDP growth generates additional revenue:

```python
revenue_feedback = gdp_change × marginal_revenue_rate
# marginal_revenue_rate ≈ 0.25 (combined federal taxes)
```

### Production Function

Long-run GDP effect:

```
%ΔGDP = labor_share × %ΔLabor + capital_share × %ΔCapital + ΔTFP
# labor_share = 0.65, capital_share = 0.35
```

---

## Spending Multipliers

### State-Dependent Multipliers

Fiscal multipliers vary with economic conditions:

| Condition | Spending Multiplier | Tax Multiplier |
|-----------|--------------------:|---------------:|
| Normal    | 1.0 | 0.5 |
| Recession | 1.5 - 2.0 | 0.8 - 1.0 |
| At ZLB    | 2.0+ | 1.0+ |
| Overheating | 0.5 | 0.3 |

### Sources
- **Auerbach & Gorodnichenko (2012)**: Recession multipliers 1.5-2.0
- **Christiano, Eichenbaum & Rebelo (2011)**: ZLB multipliers 2-3x higher
- **Blanchard & Leigh (2013)**: IMF underestimated multipliers in crisis

### Implementation

```python
from fiscal_model.economics import EconomicConditions

# Normal conditions
conditions = EconomicConditions.normal_times()
# multiplier ≈ 1.0

# Recession
conditions = EconomicConditions.recession()
# multiplier ≈ 1.5-2.0
```

### Multiplier Decay

Spending multipliers decay over time:

```python
year_effect = spending × multiplier × (decay_rate ** years_since_start)
# decay_rate = 0.7 (annual)
```

---

## Uncertainty Analysis

### Sources of Uncertainty

1. **Baseline Uncertainty**: Economic projections diverge from actual
2. **Behavioral Uncertainty**: ETI estimates range 0.15 - 0.50
3. **Dynamic Uncertainty**: Macro models diverge significantly
4. **Data Uncertainty**: IRS data is lagged 2 years

### Uncertainty Ranges

We provide low/high estimates using:

```python
base_uncertainty = 0.10 + 0.02 × years_out  # Grows with horizon

# Adjustments
policy_factor = 1.2 if tax_policy else 0.8  # Taxes more uncertain
dynamic_factor = 1.5 if dynamic else 1.0    # Dynamic adds uncertainty

total_uncertainty = base × policy × dynamic

low_estimate = central × (1 - uncertainty × 0.9)
high_estimate = central × (1 + uncertainty × 1.1)  # Asymmetric: costs usually higher
```

---

## Comparison to Official Methods

### vs. CBO

| Feature | CBO | This Model |
|---------|-----|------------|
| Static scoring | ✅ | ✅ |
| ETI behavioral | ✅ (0.25) | ✅ (0.25 default) |
| Dynamic macro | ✅ (on request) | ✅ (optional) |
| Microsimulation | ❌ | ❌ (planned) |
| 10-year window | ✅ | ✅ |
| Uncertainty | Ranges provided | ✅ |

### vs. JCT (Joint Committee on Taxation)

JCT is the **official congressional scorer** for tax legislation. They use IRS SOI microdata with proprietary behavioral models.

| Feature | JCT | This Model |
|---------|-----|------------|
| Microsimulation | ✅ | ❌ (planned) |
| Return-level | ✅ | ❌ |
| Distributional | ✅ | ❌ (planned) |
| Corporate model | ✅ | 🔄 Basic |

### vs. TPC (Tax Policy Center)

TPC publishes **transparent methodology documentation** that serves as a reference for microsimulation implementation.

| Feature | TPC | This Model |
|---------|-----|------------|
| Microsimulation | ✅ | ❌ (planned) |
| Distributional tables | ✅ | ❌ (planned) |
| Winners/losers | ✅ | ❌ (planned) |
| Public methodology | ✅ | ✅ |

### vs. Penn Wharton

| Feature | PWBM | This Model |
|---------|------|------------|
| OLG model | ✅ | ❌ (planned) |
| 30+ year horizon | ✅ | ❌ |
| Generational | ✅ | ❌ |
| Dynamic | ✅ | ✅ Basic |

### vs. Yale Budget Lab

Yale Budget Lab publishes **comprehensive transparent methodology** including dynamic macro (FRB/US, USMM), microsimulation, and behavioral response documentation.

| Feature | Yale | This Model |
|---------|------|------------|
| Dynamic macro (FRB/US) | ✅ | ❌ (planned) |
| Tax microsimulation | ✅ | ❌ (planned) |
| Distributional analysis | ✅ | ❌ (planned) |
| Behavioral responses | ✅ | ✅ Basic (ETI) |
| Capital gains realization | ✅ | ❌ (planned) |
| Trade policy | ✅ | ❌ (planned) |
| Public methodology | ✅ | ✅ |

### Known Limitations

1. **No Microsimulation**: We use bracket-level IRS data, not return-level
2. **Simplified Corporate**: Pass-through income not fully modeled
3. **Limited Credits**: Credit calculator not complete
4. **No State/Local**: Federal only
5. **No Trade**: Trade policy coming in Phase 5

---

## References

### Academic Literature

1. **Saez, E., Slemrod, J., & Giertz, S.H. (2012)**. "The Elasticity of Taxable Income with Respect to Marginal Tax Rates: A Critical Review." *Journal of Economic Literature*, 50(1), 3-50.

2. **Auerbach, A.J., & Gorodnichenko, Y. (2012)**. "Measuring the Output Responses to Fiscal Policy." *American Economic Journal: Economic Policy*, 4(2), 1-27.

3. **Christiano, L., Eichenbaum, M., & Rebelo, S. (2011)**. "When Is the Government Spending Multiplier Large?" *Journal of Political Economy*, 119(1), 78-121.

4. **Gruber, J., & Saez, E. (2002)**. "The Elasticity of Taxable Income: Evidence and Implications." *Journal of Public Economics*, 84(1), 1-32.

### Official Methodology Documents

5. **CBO (2014)**. "How CBO Analyzes the Effects of Changes in Federal Fiscal Policies on the Economy." Congressional Budget Office.

6. **JCT (2017)**. "Overview of Revenue Estimating Procedures and Methodologies." Joint Committee on Taxation. https://www.jct.gov/publications/2017/jcx-1-17/

7. **TPC**. "Tax Model Resources." Tax Policy Center. https://taxpolicycenter.org/resources/tax-model-resources

8. **Yale Budget Lab**. "Methodology and Documentation." https://budgetlab.yale.edu/research — Includes:
   - [Dynamic Scoring with USMM](https://budgetlab.yale.edu/research/estimating-dynamic-economic-and-budget-impacts-long-term-fiscal-policy-changes)
   - [Tax Microsimulation](https://budgetlab.yale.edu/research/tax-microsimulation-budget-lab)
   - [Distributional Impact](https://budgetlab.yale.edu/research/estimating-distributional-impact-policy-reforms)
   - [Capital Gains Behavioral Responses](https://budgetlab.yale.edu/research/behavioral-responses-capital-gains-realizations)

9. **CBO (2024)**. "The Budget and Economic Outlook: 2024 to 2034." Congressional Budget Office.

### Data Sources

8. **IRS Statistics of Income**. Individual Income Tax Statistics. https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics

9. **FRED**. Federal Reserve Economic Data. https://fred.stlouisfed.org

---

## Appendix: Parameter Defaults

### Tax Parameters

| Parameter | Default | Source |
|-----------|---------|--------|
| ETI | 0.25 | Saez et al. (2012) |
| Labor supply elasticity | 0.15 | CBO |
| Capital elasticity | 0.25 | Literature |
| Marginal revenue rate | 0.25 | CBO |

### Economic Parameters

| Parameter | Default | Source |
|-----------|---------|--------|
| Labor share | 0.65 | BLS |
| Capital share | 0.35 | BLS |
| TFP growth | 1% | CBO |
| Spending multiplier (normal) | 1.0 | Literature |
| Multiplier decay | 0.7/year | Estimated |

### Baseline Assumptions

| Parameter | 2025 | 2034 | Source |
|-----------|------|------|--------|
| Real GDP growth | 2.4% | 1.8% | CBO |
| Inflation | 2.3% | 2.0% | CBO |
| 10-year rate | 4.4% | 4.0% | CBO |
| Unemployment | 4.2% | 4.5% | CBO |

---

*Last Updated: December 2025*

