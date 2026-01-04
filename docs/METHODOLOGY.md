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

### FRB/US-Calibrated Approach

The model uses an **FRB/US-calibrated adapter** that implements multiplier effects consistent with the Federal Reserve's FRB/US macroeconomic model (used by Yale Budget Lab for dynamic scoring).

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Fiscal Shock   │ ──▶ │   GDP Effect    │ ──▶ │    Feedback     │
│                 │     │                 │     │                 │
│ Tax cut or      │     │ Apply FRB/US    │     │ Revenue from    │
│ spending change │     │ multipliers     │     │ GDP + crowding  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   $X billion/year        GDP × multiplier       + revenue feedback
                                                 - crowding out
```

### Fiscal Multipliers

The model uses FRB/US-calibrated multipliers with decay:

| Shock Type | Year 1 Multiplier | Decay Rate | Source |
|------------|------------------:|----------:|--------|
| **Spending** | 1.4 | 0.75/year | FRB/US |
| **Tax Cut** | 0.7 | 0.75/year | FRB/US |
| **Tax Increase** | -0.7 | 0.75/year | FRB/US |

**Multiplier Decay**:
```
multiplier(t) = base_multiplier × decay_rate^(t-1)

# Example: Spending multiplier
# Year 1: 1.40
# Year 2: 1.05
# Year 3: 0.79
# Year 4: 0.59
# ...
```

### GDP and Employment Effects

**GDP Effect Calculation**:
```python
# Annual GDP effect from fiscal shock
gdp_change_pct = (fiscal_shock_billions / baseline_gdp) * multiplier(t) * 100

# Example: $460B/year tax cut (TCJA extension)
# Year 1: ($460B / $32,500B) × 0.7 × 100 ≈ 0.99% GDP
```

**Employment Effects**:
```python
# Okun's Law coefficient (GDP → Employment)
okun_coefficient = 0.5  # 1% GDP → 0.5% employment

employment_change_pct = gdp_change_pct * okun_coefficient
employment_change_millions = employment_change_pct * labor_force / 100
# labor_force ≈ 165 million
```

### Revenue Feedback

GDP changes generate revenue feedback through the tax base:

```python
# Revenue feedback from GDP change
marginal_tax_rate = 0.25  # Combined federal revenue/GDP ratio

revenue_feedback_billions = gdp_change_billions * marginal_tax_rate

# Example: 1% GDP increase ≈ $325B
# Revenue feedback: $325B × 0.25 = $81B
```

### Crowding Out

Large fiscal expansions raise interest rates, partially offsetting GDP gains:

```python
# Crowding out from deficit increase
crowding_out_rate = 0.15  # 15% offset per cumulative deficit

cumulative_deficit = sum(annual_deficits)
interest_cost = cumulative_deficit * crowding_out_rate
gdp_offset = interest_cost × investment_sensitivity
```

**Net Budget Effect**:
```
Net Effect = Revenue Feedback - Interest Cost
```

### Code Example

```python
from fiscal_model.models.macro_adapter import FRBUSAdapterLite, MacroScenario
import numpy as np

# Initialize FRB/US-calibrated adapter
macro = FRBUSAdapterLite()

# Create scenario: TCJA extension ($460B/year tax cut)
scenario = MacroScenario(
    name="TCJA Extension",
    description="Full extension of TCJA provisions",
    receipts_change=np.array([460.0] * 10),  # Revenue loss each year
)

# Run dynamic simulation
result = macro.run(scenario)

# Results
print(f"Cumulative GDP Effect: {result.cumulative_gdp_effect:.2f}%-years")
print(f"Average Annual GDP: {np.mean(result.gdp_level_pct):.2f}%")
print(f"Revenue Feedback: ${result.cumulative_revenue_feedback:,.0f}B")
print(f"Employment Effect: {np.mean(result.employment_change_millions):.2f}M jobs")
```

**Sample Output** (TCJA Extension):
```
Cumulative GDP Effect: -40.30%-years
Average Annual GDP: -4.03%
Revenue Feedback: $-2,821B
Employment Effect: -2.58M jobs average
```

*Note: Negative values indicate deficit-financed tax cuts crowd out investment over the 10-year horizon.*

### MacroResult Outputs

The `MacroResult` object contains:

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

**Summary Properties**:
- `cumulative_gdp_effect`: Total GDP %-years over horizon
- `cumulative_revenue_feedback`: Total revenue feedback ($B)
- `net_budget_effect`: Revenue feedback minus interest cost

### Comparison to Other Models

| Feature | FRBUSAdapterLite | Full FRB/US | CBO Dynamic |
|---------|-----------------|-------------|-------------|
| Multipliers | Calibrated | Structural | Calibrated |
| Crowding out | Reduced-form | Endogenous | Endogenous |
| Expectations | Static | Rational | Mixed |
| Computation | Instant | Minutes | N/A |
| Validation | vs FRB/US | N/A | N/A |

### Economic Channels (Detailed)

1. **Labor Supply**
   - Tax changes affect after-tax wages
   - Labor supply elasticity: 0.15 (compensated)
   - Incorporated via Okun's Law coefficient

2. **Capital Formation**
   - Corporate tax affects investment
   - Capital elasticity: 0.25
   - Crowding out from deficit-financed policies

3. **Aggregate Demand**
   - Short-run multiplier effects (Keynesian)
   - Spending more potent than tax cuts
   - Decay reflects supply-side adjustment

4. **Interest Rates**
   - Deficits raise long-term rates
   - Crowds out private investment
   - Reduces net fiscal impact over time

### Production Function (Long-Run)

Long-run GDP effect (for supply-side policies):

```
%ΔGDP = labor_share × %ΔLabor + capital_share × %ΔCapital + ΔTFP
# labor_share = 0.65, capital_share = 0.35
```

---

## Distributional Analysis

### Income Group Definitions

The model supports multiple income grouping schemes:

| Group Type | Brackets | Usage |
|------------|----------|-------|
| Quintile | 5 equal-population groups | Standard TPC |
| Decile | 10 groups | Detailed analysis |
| JCT Dollar | $10K increments | JCT-style tables |
| Custom | User-defined | Targeted analysis |

**2024 Quintile Thresholds** (based on TPC/Census data):
- Lowest: $0-$35,000 (bottom 20%)
- Second: $35,000-$65,000 (20-40%)
- Middle: $65,000-$105,000 (40-60%)
- Fourth: $105,000-$170,000 (60-80%)
- Top: $170,000+ (top 20%)

### Distributional Metrics

For each income group, we calculate:

1. **Average Tax Change** ($): Per-return dollar impact
2. **Tax Change as % of Income**: After-tax income impact
3. **Share of Total Change**: Group's portion of total revenue effect
4. **Winners/Losers**: % with tax increase/decrease
5. **Effective Tax Rate Change**: Change in ETR (percentage points)

### Policy-Specific Handlers

Different policy types have specialized distributional logic:

| Policy Type | Distribution Logic |
|-------------|-------------------|
| `TaxPolicy` | Rate change × income above threshold |
| `TaxCreditPolicy` | Credit phase-in/phase-out by income |
| `TCJAExtensionPolicy` | TPC-based component distribution |
| `CorporateTaxPolicy` | 75/25 capital/labor incidence |
| `PayrollTaxPolicy` | Wage distribution up to SS cap |

### Corporate Tax Incidence

Following CBO/TPC assumptions:
- **75%** on capital owners (concentrated in top quintile)
- **25%** on workers (distributed with wage income)

Capital income shares by quintile (SCF data):
- Top quintile: 80%
- Fourth: 12%
- Middle: 5%
- Second: 2%
- Bottom: 1%

### Validation Against TPC

Distributional shares validated against TPC TCJA analysis:

| Quintile | Model | TPC | Error |
|----------|-------|-----|-------|
| Lowest | 2.0% | 1.0% | Higher |
| Second | 5.0% | 4.0% | 25% |
| Middle | 10.0% | 10.0% | **0%** |
| Fourth | 18.0% | 17.0% | 6% |
| Top | 65.0% | 68.0% | 4% |

Overall: **GOOD** accuracy for distributional shares.

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
| Dynamic macro | ✅ (on request) | ✅ FRB/US-calibrated |
| GDP effects | ✅ | ✅ |
| Employment effects | ✅ | ✅ |
| Revenue feedback | ✅ | ✅ |
| Crowding out | ✅ | ✅ |
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
| Distributional tables | ✅ | ✅ Phase 3 |
| Winners/losers | ✅ | ✅ Phase 3 |
| Public methodology | ✅ | ✅ |

**Distributional Validation** (vs TPC TCJA analysis):
- Middle quintile: 10% share (exact match)
- Top quintile: 65% vs 68% (4.4% error)
- Overall distributional share accuracy: GOOD

### vs. Penn Wharton

| Feature | PWBM | This Model |
|---------|------|------------|
| OLG model | ✅ | ❌ (planned) |
| 30+ year horizon | ✅ | ❌ (10-year) |
| Generational | ✅ | ❌ |
| Dynamic scoring | ✅ | ✅ FRB/US-calibrated |
| GDP/Employment | ✅ | ✅ |
| Crowding out | ✅ | ✅ |

### vs. Yale Budget Lab

Yale Budget Lab publishes **comprehensive transparent methodology** including dynamic macro (FRB/US, USMM), microsimulation, and behavioral response documentation.

| Feature | Yale | This Model |
|---------|------|------------|
| Dynamic macro (FRB/US) | ✅ | ✅ FRBUSAdapterLite |
| GDP effects | ✅ | ✅ |
| Employment effects | ✅ | ✅ |
| Revenue feedback | ✅ | ✅ |
| Crowding out | ✅ | ✅ |
| Tax microsimulation | ✅ | ❌ (planned) |
| Distributional analysis | ✅ | ✅ |
| Behavioral responses | ✅ | ✅ ETI + capital gains |
| Capital gains realization | ✅ | ✅ Time-varying elasticity |
| Trade policy | ✅ | ❌ (planned) |
| Public methodology | ✅ | ✅ |

**Macro Model Integration**: `fiscal_model/models/macro_adapter.py` provides:
- `FRBUSAdapterLite` for FRB/US-calibrated reduced-form analysis (instant computation)
- `MacroModelAdapter` abstract interface for pluggable models
- `FRBUSAdapter` for full FRB/US model connection (requires pyfrbus)

### Known Limitations

1. **No Microsimulation**: We use bracket-level IRS data, not return-level
2. **Simplified Corporate**: Pass-through income not fully modeled
3. **No State/Local**: Federal only
4. **No Trade**: Trade policy planned for future phase
5. **Reduced-Form Dynamic**: FRBUSAdapterLite uses calibrated multipliers rather than structural equations

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

### Dynamic Scoring Parameters (FRBUSAdapterLite)

| Parameter | Default | Source |
|-----------|---------|--------|
| Spending multiplier (Year 1) | 1.4 | FRB/US |
| Tax multiplier (Year 1) | 0.7 | FRB/US |
| Multiplier decay rate | 0.75/year | FRB/US |
| Okun's Law coefficient | 0.5 | Literature |
| Marginal tax rate (feedback) | 0.25 | CBO |
| Crowding out rate | 0.15 | Estimated |
| Labor force | 165M | BLS |
| Baseline GDP (2025) | $32,500B | CBO |

### Baseline Assumptions

| Parameter | 2025 | 2034 | Source |
|-----------|------|------|--------|
| Real GDP growth | 2.4% | 1.8% | CBO |
| Inflation | 2.3% | 2.0% | CBO |
| 10-year rate | 4.4% | 4.0% | CBO |
| Unemployment | 4.2% | 4.5% | CBO |

---

*Last Updated: January 4, 2026*

