# Horizon Features — Technical Design Document

> Fiscal Policy Calculator — Long-Horizon Feature Specifications
> Last Updated: April 2026
> Status: All four features implemented (April 2026). This document serves as the technical design reference.

This document covers the four major features that were planned for the 3–6 month horizon and have now been implemented. Each section documents the design decisions and architecture for reference.

---

## Table of Contents

1. [OLG (Overlapping Generations) Model](#1-olg-overlapping-generations-model)
2. [Classroom Mode](#2-classroom-mode)
3. [State-Level Modeling](#3-state-level-modeling)
4. [Real-Time Bill Tracker](#4-real-time-bill-tracker)

---

## 1. OLG (Overlapping Generations) Model

### 1.1 Motivation and Scope

The existing `SolowGrowthModel` (`fiscal_model/long_run/solow_growth.py`) captures crowding-out and capital accumulation over 30+ years, but it treats the economy as a representative household. OLG models distinguish generations explicitly, which matters for:

- **Social Security and Medicare reform** — costs and benefits fall asymmetrically on current vs. future workers/retirees
- **Deficit financing** — who actually bears the burden of debt depends on generational timing
- **Capital tax incidence** — an OLG model has an explicit saving decision, so capital tax changes affect the equilibrium capital stock endogenously rather than through a calibrated crowding-out parameter
- **Penn Wharton comparability** — PWBM's defining feature is their OLG model; implementing one closes the gap in the multi-model comparison

The target is a **30-period Auerbach-Kotlikoff-style model**, calibrated to US data (BLS, Social Security Administration), that integrates with the existing `BaseScoringModel` interface from `fiscal_model/models/base.py`.

**Not in scope (v1):** Heterogeneous agents within a cohort (HANK), international capital flows beyond a simple Feldstein-Horioka assumption, stochastic productivity.

---

### 1.2 Economic Model

#### Cohorts and Timing

- Model horizon: **T = 75 years** (steady-state to steady-state)
- Cohorts: **J = 55 periods** (enter labor force at age 25, retire at 65, live to 80)
  - Working ages: j = 1 ... 40 (ages 25–64)
  - Retirement ages: j = 41 ... 55 (ages 65–79)
- Population: cohort sizes follow SSA demographic projections (fertility + mortality tables)

#### Household Problem

Each cohort j solves:

```
max_{c_{j,t}, a_{j+1,t+1}}  sum_{j=1}^{J} beta^j * (c_{j,t+j-1}^(1-sigma) / (1-sigma))

subject to:
  (1 + tau_c) * c_{j,t} + a_{j+1,t+1} = (1 - tau_l) * w_t * e_j * n_j  (working years)
                                        + (1 + r_t*(1-tau_k)) * a_{j,t}
                                        + b_j  (retirement benefit)
  a_{1,t} = 0  (born with no assets)
  a_{J+1,t} = 0  (no bequest motive, v1)
```

**Parameters:**
- `beta`: Discount factor (~0.97, calibrated to match US wealth/income ratio ~4.0)
- `sigma`: CRRA coefficient (= 2.0, standard in public finance OLG)
- `e_j`: Age-efficiency profile (from BLS earnings by age, normalized to 1 at age 45)
- `n_j`: Labor supplied at each age (1.0 for working years, 0.0 for retirement; can extend to elastic labor)
- `tau_c`, `tau_l`, `tau_k`: Consumption, labor, and capital tax rates (policy levers)
- `w_t`, `r_t`: Factor prices (endogenous, from firm's problem)
- `b_j`: Social Security benefit (policy lever)

Household optimization is solved by **backward induction** on the Euler equation:

```
c_{j,t}^(-sigma) = beta * (1 + r_{t+1} * (1 - tau_k)) * c_{j+1,t+1}^(-sigma)
```

with the budget constraint binding at each age.

#### Firm Problem

Representative firm, Cobb-Douglas production:

```
Y_t = A_t * K_t^alpha * L_t^(1-alpha)
```

Factor prices from profit maximization:

```
r_t = alpha * Y_t / K_t - delta          (net return to capital)
w_t = (1-alpha) * Y_t / L_t             (wage per efficiency unit)
```

Parameters: `alpha = 0.35`, `delta = 0.05`, `A_t` grows at `g = 0.015` per year.

This is identical to the Solow model's production function — the difference is that factor demand/supply are endogenous (K is the sum of household savings, L is the sum of age-weighted labor supply weighted by efficiency).

#### Government Budget Constraint

```
G_t + B_t + INTEREST_t = tau_l * w_t * L_t + tau_k * r_t * K_t + tau_c * C_t + T_t
```

Where:
- `G_t`: Government spending (exogenous, from CBO baseline)
- `B_t`: Social Security + Medicare transfers
- `INTEREST_t`: r_t * D_t where D_t is government debt
- `T_t`: Lump-sum tax or residual (fiscal closure rule)

**Fiscal closure rule** (critical design choice): In steady state and along transition, the government must satisfy its budget constraint. Options:
1. **Lump-sum tax adjustment** (cleanest for theory, least realistic)
2. **Labor tax adjustment** (most common in applied OLG)
3. **Debt accumulates** with eventual stabilization (most realistic for 10-year window)

**Default v1**: Debt-accumulating with a long-run stabilization backstop (debt/GDP mean-reverts to 100% by year 75 via slow labor tax adjustment). This matches PWBM's approach.

#### Market Clearing

```
K_t + D_t = sum_j N_{j,t} * a_{j,t}     (asset market: capital + gov debt = household savings)
Y_t = C_t + I_t + G_t                   (goods market)
L_t = sum_j N_{j,t} * e_j * n_j         (labor market)
```

#### Generational Accounting

Following Auerbach, Gokhale, and Kotlikoff (1991), define the **generational account** of cohort born in year s:

```
GA_s = sum_{k=max(s,t)}^{s+J-1} (T_{k,s} - B_{k,s}) / (1+r)^(k-t)
```

Where T = taxes paid at age k, B = transfers received at age k, discounted to current year t. This is the present value of net lifetime fiscal burden.

**Output**: Generational accounts by birth year, relative to a baseline. Shows whether a reform shifts burden toward younger/future generations.

---

### 1.3 Solution Algorithm

The OLG model requires solving a **fixed-point problem** in factor prices across time:

```
1. Guess factor price path {w_t, r_t}_{t=0}^T
2. Solve all cohorts' household problems backward from T
3. Aggregate to get K_t^demand, L_t^supply
4. Update factor prices via firm's optimality conditions
5. Check government budget, iterate on fiscal closure
6. Repeat until convergence in factor prices (|Δr| < 1e-6)
```

**Primary algorithm**: Gauss-Seidel iteration with dampening (dampening = 0.3 to prevent oscillation). For a 75-year horizon with 55 cohorts, each iteration is ~O(75 × 55) = ~4,000 operations. Typically converges in 50–200 iterations, so total: ~200,000 operations. Very fast in NumPy.

**Fallback: Broyden's quasi-Newton method** — Gauss-Seidel can fail to converge for large policy shocks (e.g., a 20pp corporate rate cut that causes a large jump in the capital-labor ratio). When Gauss-Seidel has not converged after `max_gs_iterations = 300`, the solver auto-switches to Broyden:

```python
def solve_equilibrium(self, initial_guess, policy, max_gs_iter=300, tol=1e-6):
    prices = initial_guess
    for i in range(max_gs_iter):
        prices_new = self._gs_update(prices, policy)
        if np.max(np.abs(prices_new - prices)) < tol:
            return prices_new
        prices = prices_new
    # Gauss-Seidel did not converge — fall back to Broyden
    import scipy.optimize
    result = scipy.optimize.broyden1(
        lambda p: self._excess_demand(p, policy),
        prices,
        f_tol=tol,
        maxiter=500,
    )
    return result
```

Broyden requires `scipy.optimize` (already in requirements). It is slower (~3–5x per iteration) but has superlinear convergence near the solution. The two-solver design means small/moderate shocks stay fast while large shocks remain robust.

**Transition path**: Same algorithm but now the initial condition is the pre-reform steady state and the terminal condition is the post-reform steady state. Policies are announced at t=0 and either:
- **Permanent**: transition path from SS0 → SS1
- **Temporary**: transition path SS0 → intermediate → SS0 again (policy expires)
- **Phased in**: reform applied gradually over `phase_in_years`

---

### 1.4 Module Structure

```
fiscal_model/
└── models/
    └── pwbm/                     # Penn Wharton-style OLG module
        ├── __init__.py           # Exports OLGModel, OLGResult, PWBMModel
        ├── olg_model.py          # Core OLG solver
        ├── household.py          # Household optimization (Euler equations)
        ├── demographics.py       # Cohort sizes, survival probs, age profiles
        ├── calibration.py        # US calibration routines
        ├── generational_acct.py  # Generational accounting output
        └── equilibrium.py        # Market clearing + fiscal closure
```

#### Key Classes

```python
# olg_model.py

@dataclass
class OLGParameters:
    """All structural parameters for the OLG model."""
    # Preferences
    beta: float = 0.97           # Discount factor
    sigma: float = 2.0           # CRRA coefficient
    # Production
    alpha: float = 0.35          # Capital share
    delta: float = 0.05          # Depreciation
    tfp_growth: float = 0.015    # Annual TFP growth
    # Demographics
    T_work: int = 40             # Working periods (ages 25-64)
    T_retire: int = 15           # Retirement periods (ages 65-79)
    # Calibration targets
    target_ky_ratio: float = 4.0 # Capital/output ratio (US: ~4x)
    target_gy_ratio: float = 0.22 # Gov spending/GDP (US: ~22%)
    # Fiscal closure
    closure_rule: str = "labor_tax"  # "labor_tax" | "lump_sum" | "deficit"
    debt_target_pct: float = 1.0  # Long-run debt/GDP target

@dataclass
class OLGPolicy:
    """Policy change for OLG analysis."""
    # Tax rates (changes from baseline)
    delta_tau_l: float = 0.0     # Labor income tax rate change
    delta_tau_k: float = 0.0     # Capital income tax rate change
    delta_tau_c: float = 0.0     # Consumption tax rate change
    # Social Security
    delta_ss_benefit_pct: float = 0.0  # % change in SS benefits
    delta_payroll_rate: float = 0.0    # Change in payroll tax rate
    delta_fra: int = 0            # Change in full retirement age (years)
    # Spending
    delta_spending_billions: np.ndarray = None  # Annual spending change
    # Dynamics
    phase_in_years: int = 0
    sunset_year: int | None = None

@dataclass
class OLGResult:
    """Full OLG simulation output."""
    years: np.ndarray
    # Macroeconomic paths
    gdp: np.ndarray                  # GDP level
    gdp_pct_change: np.ndarray       # % change vs baseline
    capital_stock: np.ndarray
    wages: np.ndarray
    interest_rate: np.ndarray
    # Government
    deficits: np.ndarray             # Annual deficits ($B)
    debt: np.ndarray                 # Debt level ($B)
    debt_to_gdp: np.ndarray
    # Generational
    generational_accounts: pd.DataFrame   # By birth cohort
    welfare_by_cohort: pd.DataFrame       # EV by birth year
    # Budget
    ten_year_cost: float
    long_run_gdp_effect: float       # % at 30-year horizon

class OLGModel:
    """
    Auerbach-Kotlikoff OLG model calibrated to US data.

    Usage:
        model = OLGModel()
        baseline_ss = model.solve_steady_state()
        result = model.compute_transition(policy, baseline_ss)
    """
    def __init__(self, params: OLGParameters = None):
        self.params = params or OLGParameters()
        self.demographics = DemographicProfile.from_ssa_projections()

    def solve_steady_state(self, policy: OLGPolicy = None) -> SteadyState:
        """Solve for steady state under baseline or post-reform policy."""
        ...

    def compute_transition(self, policy: OLGPolicy,
                           initial_ss: SteadyState,
                           horizon: int = 75) -> OLGResult:
        """Compute transition path from initial_ss under policy."""
        ...

    def generational_accounts(self, result: OLGResult) -> pd.DataFrame:
        """Compute Auerbach-Gokhale-Kotlikoff generational accounts."""
        ...

# models/pwbm/__init__.py

class PWBMModel(BaseScoringModel):
    """Penn Wharton-style OLG dynamic model. Integrates with multi-model comparison."""

    name = "PWBM"
    methodology = "Overlapping Generations with endogenous capital and generational accounting"

    def __init__(self, horizon: int = 30, params: OLGParameters = None):
        self.olg = OLGModel(params)
        self.horizon = horizon

    def score(self, policy: Policy) -> ModelResult:
        olg_policy = self._translate_policy(policy)
        baseline_ss = self.olg.solve_steady_state()
        result = self.olg.compute_transition(olg_policy, baseline_ss, self.horizon)
        return ModelResult(
            model_name=self.name,
            policy=policy,
            ten_year_cost=result.ten_year_cost,
            annual_effects=result.deficits[:10],
            extras={
                'long_run_gdp': result.long_run_gdp_effect,
                'generational_accounts': result.generational_accounts,
                'welfare_by_cohort': result.welfare_by_cohort,
                'debt_to_gdp': result.debt_to_gdp,
            }
        )

    def _translate_policy(self, policy: Policy) -> OLGPolicy:
        """Map existing Policy objects to OLGPolicy. Key mappings:
        - PayrollTaxPolicy → delta_payroll_rate
        - TaxPolicy (labor income) → delta_tau_l
        - TaxPolicy (capital gains) → delta_tau_k
        - SpendingPolicy → delta_spending_billions
        - TransferPolicy (SS/Medicare) → delta_ss_benefit_pct
        """
        ...
```

---

### 1.5 Data Requirements and Calibration

| Data Needed | Source | Used For |
|-------------|--------|----------|
| Age-earnings profile | BLS NLSY79/CPS | e_j efficiency weights |
| Survival probabilities | SSA Period Life Tables (2024) | Cohort N_{j,t} |
| Population projections by age | SSA 2024 Trustees Report | N_{j,t} for t > 2024 |
| Aggregate capital stock | BEA Fixed Assets (Table 1.1) | Initial K calibration |
| Aggregate savings rate | BEA NIPA | Calibrate beta |
| Gov debt | CBO Baseline | Initial D_t |
| SS benefit schedule | SSA OACT | b_j parameters |
| Payroll tax rates | IRS/SSA | tau_l composition |

**Calibration procedure** (`calibration.py`):
1. Set `alpha`, `delta` from factor shares (BLS)
2. Solve steady state with initial guess for `beta`
3. Adjust `beta` until model produces K/Y = 4.0
4. Normalize `A` so that model GDP matches CBO 2025 baseline ($32.5T)
5. Set age profile `e_j` to match BLS median earnings by age group (normalized)
6. Validate: model SS benefits vs SSA published totals, model labor supply vs BLS hours

**Validation targets:**
- Steady-state K/Y ratio: 4.0 ± 0.2
- Wealth distribution (top 10% share): ~65% (SCF)
- Model SS revenue: within 5% of $1.2T/year (CBO)
- Model SS outlays: within 5% of $1.5T/year (CBO)
- 10-year SS reform cost vs PWBM published estimates: within 15%

---

### 1.6 UI/UX in Streamlit

**New tab**: "Generational Analysis" (added after "Long-Run Growth" tab)

```
┌─────────────────────────────────────────────────────────┐
│  GENERATIONAL ANALYSIS (OLG Model)                       │
│  ─────────────────────────────────────────────────────  │
│  "Estimates how costs and benefits fall across          │
│   current and future generations (PWBM-style)"         │
│                                                         │
│  Policy:  [TCJA Extension ▼]   [Run OLG Analysis]      │
│  Horizon: [30 yr] [75 yr]                               │
│                                                         │
│  ┌──────────────────────┐ ┌──────────────────────────┐  │
│  │  GDP Effect          │ │  Debt-to-GDP Path        │  │
│  │  [Line chart, 30yr]  │ │  [Line chart, 75yr]      │  │
│  └──────────────────────┘ └──────────────────────────┘  │
│                                                         │
│  Generational Burden (Net Present Value per Cohort)     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  [Bar chart: birth year on x-axis,                │  │
│  │   NPV of net taxes paid on y-axis,                │  │
│  │   comparison between baseline and reform]         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ⚠ Warning: OLG results are sensitive to calibration.   │
│    Treat as directionally informative, not precise.     │
│                                                         │
│  [ Advanced: Edit OLG Parameters ]                      │
│    beta (discount): [0.97]  sigma (risk aversion): [2]  │
│    Fiscal closure: [labor tax ▼]                        │
└─────────────────────────────────────────────────────────┘
```

**Sidebar controls** (when OLG tab is active):
- "Include generational accounting" toggle (adds ~2s compute)
- Horizon selector: 10 / 30 / 75 years
- "Compare to Solow model" toggle (shows both on same GDP chart)

---

### 1.7 Integration with Existing Code

1. `PWBMModel` extends `BaseScoringModel` — immediately compatible with multi-model comparison framework (`comparison/compare.py`)
2. `OLGPolicy._translate_policy()` maps existing `Policy` dataclasses — no changes to `policies.py` needed
3. OLG `ten_year_cost` is dropped into `ScoringResult.extras['olg']` — `app.py` can display it without touching the main scoring pipeline
4. `SolowGrowthModel` remains — OLG is an optional upgrade, not a replacement
5. The `LongRunResult` format from `solow_growth.py` is mirrored in `OLGResult` — charts in `long_run_growth.py` tab can reuse the same Plotly templates

---

### 1.8 Estimated Complexity

| Component | Effort | Notes |
|-----------|--------|-------|
| Demographics module + SSA data loading | 3 days | Mostly data wrangling |
| Household Euler equation solver | 4 days | Core math; needs careful testing |
| Market clearing + equilibrium iteration | 3 days | Fixed-point iteration |
| Fiscal closure + government budget | 2 days | Edge cases in closure rule |
| Generational accounting | 2 days | Straightforward once transition solved |
| Calibration to US data | 3 days | Iterative; needs validation |
| Streamlit UI tab | 2 days | Charts + parameter controls |
| Tests + validation | 3 days | Target 20 tests, 3 PWBM benchmarks |
| **Total** | **~22 days** | **~4.5 person-weeks** |

---

### 1.9 Risks and Open Questions

**Technical risks:**
- Convergence: Gauss-Seidel may not converge cleanly for large policy shocks. Mitigated by auto-switching to Broyden quasi-Newton after 300 failed iterations (see §1.3). Shooting algorithm is a further fallback if Broyden also fails, but has not been needed in testing.
- Compute time: 75-year horizon × Gauss-Seidel iteration could hit 10–30s per solve. Mitigation: JIT with Numba for inner loops, cache steady-state solutions.
- Calibration sensitivity: beta and sigma together determine a lot of behavior. Document uncertainty bands.

**Design open questions:**
- **Elastic vs inelastic labor supply**: Inelastic is simpler (v1); elastic is more policy-relevant for labor income tax changes. Recommendation: ship inelastic v1, add labor supply elasticity in v2.
- **Bequest motive**: Some OLG models add a bequest motive to match the observed wealth distribution better. Skip for v1.
- **Open vs closed economy**: Closed economy is standard for a first implementation. PWBM uses a partially open economy (Feldstein-Horioka style). Skip for v1.
- **What policies are OLG-specific?**: Social Security, Medicare, capital gains taxation, and corporate tax are where OLG adds the most value. Income tax rate changes on high earners add less. Should the UI flag which policies are "OLG-recommended"?

---

## 2. Classroom Mode

### 2.1 Motivation and Scope

The calculator is currently designed for researchers and policy analysts. A classroom mode repurposes it for **teaching fiscal policy** in undergraduate or MPP public economics courses. Laurence teaches at NYU Wagner, so this should fit the pedagogical style of a rigorous applied public econ course.

The goal is not to dumb the tool down — it's to **structure the experience** for learning objectives: scaffolded exercises, progressive complexity, immediate feedback, and assignment-grade-ready outputs.

**Target courses:**
- Undergraduate: Intro to Public Finance / Public Economics
- Graduate: MPP Fiscal Policy or Public Budgeting
- Executive ed: Policy analysis in a weekend seminar

**Not in scope (v1):** User accounts, grade syncing with LMS, multi-student dashboards with live tracking, authentication.

---

### 2.2 Mode Architecture

Classroom mode is activated via a **URL parameter**: `?mode=classroom&assignment=laffer_curve`. This avoids the need for login while allowing instructors to share direct assignment links.

```python
# app.py
import streamlit as st

params = st.query_params
mode = params.get("mode", "standard")
assignment_id = params.get("assignment", None)

if mode == "classroom":
    from fiscal_model.classroom import ClassroomController
    ClassroomController(assignment_id).render()
else:
    # existing app flow
    ...
```

Module structure:

```
fiscal_model/
└── classroom/
    ├── __init__.py
    ├── controller.py        # ClassroomController — top-level UI router
    ├── assignments.py       # Assignment registry + loader
    ├── exercises.py         # Exercise types (guided, open, problem set)
    ├── feedback.py          # Answer checking and pedagogical hints
    ├── templates/           # Assignment YAML definitions
    │   ├── laffer_curve.yaml
    │   ├── tcja_analysis.yaml
    │   ├── deficit_finance.yaml
    │   ├── spending_multiplier.yaml
    │   └── distributional_incidence.yaml
    └── export.py            # PDF/CSV export for submission
```

---

### 2.3 Assignment Template Format

Assignments are defined in YAML, making it easy to add new ones without touching Python:

```yaml
# fiscal_model/classroom/templates/laffer_curve.yaml

id: laffer_curve
title: "The Laffer Curve: When Do Tax Increases Lose Revenue?"
level: undergraduate        # undergraduate | graduate | advanced
course_context: |
  This exercise uses the Fiscal Policy Calculator to explore
  the Laffer Curve — the relationship between tax rates and
  revenue. You will discover the revenue-maximizing rate
  empirically.
estimated_minutes: 30
prerequisites: []            # Assignment IDs that should be done first

learning_objectives:
  - Understand why tax revenue is not monotonic in the tax rate
  - Quantify the elasticity of taxable income (ETI)
  - Distinguish static from behavioral scoring

setup:
  policy_type: income_tax
  lock_fields:              # Fields students cannot change
    - affected_income_threshold
    - duration_years
  default_values:
    affected_income_threshold: 400000
    duration_years: 10

questions:
  - id: q1
    type: exploration
    prompt: |
      Set the rate change to +5 percentage points. What is the static
      10-year revenue estimate? Now set ETI = 0.0 and re-score.
      Are the results the same? Why?
    hint: "ETI = 0 means no behavioral response. Static scoring assumes ETI = 0."

  - id: q2
    type: find_value
    prompt: |
      Increase the rate change in 2pp increments from 0% to 20%.
      Record the 10-year revenue at each level.
      At what rate change does revenue begin to fall?
    expected_behavior: revenue_peaks_before_max_rate
    hint: "As rates rise, behavioral response grows. At some point, the response is larger than the mechanical effect."

  - id: q3
    type: calculation
    prompt: |
      Using your results, estimate the revenue-maximizing top marginal
      rate (the 'Laffer peak'). How does this compare to the current
      top rate of 37%?
    validation:
      method: relative_to_model     # Check against live model.score(), not hardcoded range
      tolerance_pct: 2.0            # Accept if within ±2% of model output
      reference_policy:             # Policy to score for expected answer
        type: income_tax
        rate_change_sweep: true     # Find peak across rate_change range
      fallback_note: "With ETI=0.25, peak is ~60-65% for high earners (informational only)"

  - id: q4
    type: reflection
    prompt: |
      The ETI default is 0.25 (Saez et al. 2012). Some economists
      estimate it as low as 0.1 or as high as 0.5.
      How does the Laffer peak change under ETI = 0.1 vs ETI = 0.5?
      What does this imply for the uncertainty in revenue estimates?

submission:
  export_format: pdf
  include_charts: true
  fields_to_include:
    - revenue_by_rate_change_table
    - 10yr_chart
    - student_answers
```

---

### 2.4 Built-in Assignments (v1 Set)

| ID | Title | Level | Minutes | Concepts |
|----|-------|-------|---------|---------|
| `laffer_curve` | The Laffer Curve | Undergrad | 30 | ETI, behavioral response, revenue-maximizing rate |
| `tcja_analysis` | What Did TCJA Cost? | Undergrad/Grad | 45 | Static vs dynamic scoring, distributional incidence, SALT cap |
| `deficit_finance` | Deficit Financing and Crowding Out | Undergrad | 25 | Solow model, K/Y ratio, long-run GDP effects |
| `spending_multiplier` | Fiscal Multipliers in Recession vs. Expansion | Grad | 40 | State-dependent multipliers, ZLB, FRB/US calibration |
| `distributional_incidence` | Who Bears the Corporate Tax? | Grad | 35 | Capital/labor incidence, quintile tables, TPC methodology |
| `cbo_vs_dynamic` | Why Does Dynamic Scoring Matter? | Grad | 50 | CBO conventional vs FRB/US dynamic, when they diverge |
| `generational_burden` | Social Security Reform and Future Generations | Advanced | 60 | OLG model, generational accounts, PWBM-style analysis |

---

### 2.5 Progressive Complexity Levels

**Undergraduate mode** hides:
- ETI input (fixed at 0.25, explained in tooltip)
- Dynamic scoring toggle (shown as locked with explanation)
- Multi-model comparison
- Technical parameter panel

**Graduate mode** shows everything except:
- OLG parameters (those require "Advanced" level)
- FRB/US model internals

**Advanced mode** (researcher mode = current default): No restrictions.

Complexity is set by the assignment YAML's `level` field, or manually via a sidebar selector when not in an assignment.

---

### 2.6 Exercise Types

```python
# classroom/exercises.py

class ExerciseType(Enum):
    EXPLORATION  = "exploration"   # No right answer; student observes behavior
    FIND_VALUE   = "find_value"    # Student must find a specific parameter value
    CALCULATION  = "calculation"   # Student computes a result
    COMPARISON   = "comparison"    # Student compares two scenarios
    REFLECTION   = "reflection"    # Open-ended; requires text input
    BUILD        = "build"         # Student constructs a policy from scratch

class Exercise:
    def render(self, question: dict, current_result: ScoringResult):
        """Renders question prompt, input area, and optional hint button."""

    def check_answer(self, question: dict, student_answer,
                     scorer: FiscalPolicyScorer) -> FeedbackResult:
        """
        Validate student answer against live model output, not hardcoded ranges.

        For `validation.method = relative_to_model`:
          1. Reconstruct the reference policy from question.validation.reference_policy
          2. Call scorer.score_policy(reference_policy)
          3. Accept if abs(student_answer - model_answer) / model_answer <= tolerance_pct/100

        This means answer validation updates automatically when CBO baselines
        are refreshed — no manual maintenance of expected answer tables.
        """

@dataclass
class FeedbackResult:
    correct: bool | None        # None for open-ended questions
    message: str                # Feedback message
    hint_revealed: bool
    explanation: str            # Shown after correct answer or on request
```

---

### 2.7 Instructor Dashboard Concept

The instructor dashboard is accessed at `?mode=instructor&key=<hash>` where the hash is generated from a shared key in environment variables. This is intentionally low-security — it's for a classroom, not production auth.

**Dashboard features (v1):**
- List of available assignments with shareable URLs
- "Preview as student" button for each assignment
- Downloadable blank assignment PDFs (for in-class printing)
- Export of assignment YAML to customize

**Future (v2):** If students submit assignment exports (CSV/PDF), instructor can upload a batch and the dashboard shows aggregated class results (e.g., "70% of students found the Laffer peak above 50%").

---

### 2.8 UI/UX Wireframe

```
┌─────────────────────────────────────────────────────────┐
│  🎓 CLASSROOM MODE — NYU Wagner Public Economics        │
│  Assignment: The Laffer Curve                           │
│  ─────────────────────────────────────────────────────  │
│  LEARNING OBJECTIVES                                    │
│  ✓ Understand when tax increases lose revenue           │
│  ✓ Quantify elasticity of taxable income (ETI)          │
│                                                         │
│  BACKGROUND                                             │
│  [Collapsed expandable with 150-word context]           │
│                                                         │
│  ── QUESTION 1 of 4 ────────────────────────────────── │
│  Set the rate change to +5pp. What is the static        │
│  10-year revenue estimate?                              │
│                                                         │
│  [Calculator panel — locked fields greyed out]         │
│  Rate change: [+5pp ↕]   Threshold: $400K (locked)     │
│  ETI: [0.25 ↕]           Duration: 10 yr (locked)      │
│  [Calculate]                                            │
│                                                         │
│  Your answer: [$__________ billion]                     │
│  [Submit]  [Show Hint]                                  │
│                                                         │
│  ── Progress ────────────────────────────────────────── │
│  Q1 ● Q2 ○ Q3 ○ Q4 ○                                   │
│                                                         │
│  [Export My Work (PDF)]  [Start Over]                   │
└─────────────────────────────────────────────────────────┘
```

---

### 2.9 Dependencies on Existing Code

- Reads from `FiscalPolicyScorer` — no changes to scoring
- Uses `TaxPolicy`, `SpendingPolicy` from `policies.py` — no changes
- Reads `ScoringResult` output — no changes
- Adds new `?mode=classroom` routing in `app.py` (5-line change)
- New module `fiscal_model/classroom/` — all additive

---

### 2.10 Estimated Complexity

| Component | Effort | Notes |
|-----------|--------|-------|
| YAML assignment template format + loader | 2 days | Schema + pydantic validation |
| ClassroomController UI rendering | 3 days | Progressive disclosure logic |
| Exercise types + feedback engine | 2 days | Answer checking, hint system |
| 5 core assignment YAML files | 3 days | Writing good pedagogical content is the work |
| Instructor dashboard | 2 days | Simple read-only dashboard |
| Export (PDF/CSV) | 2 days | Use `reportlab` or HTML→PDF |
| Tests | 2 days | 15 tests: YAML loading, routing, feedback |
| **Total** | **~16 days** | **~3.5 person-weeks** |

---

### 2.11 Risks and Open Questions

**Pedagogical risks:**
- Assignments need to work on the live Streamlit app — if CBO baseline updates, some expected-answer ranges may shift. Mitigation: express expected answers as formulas (`"peak_above_current_rate_37pct"`) not fixed numbers.
- The calculator's defaults assume Saez ETI = 0.25. If students use different ETIs, answers diverge. Mitigation: assignments should either lock ETI or make ETI exploration the exercise.

**Design open questions:**
- **Submission mechanism**: Without user accounts, where do assignments go? Option 1: student exports PDF and submits to LMS. Option 2: student copies a "completion code" (hash of answers) to paste. Recommendation: PDF export v1, completion code v2.
- **Language localization**: Not needed for NYU context but could matter later.
- **Mobile UX**: Streamlit is marginal on mobile; classroom use is likely laptop-based. Don't optimize for mobile.

---

## 3. State-Level Modeling

### 3.1 Motivation and Scope

The calculator is currently federal-only. But fiscal policy analysis often requires understanding **federal-state interaction effects**:

- Federal SALT deduction changes directly affect state tax revenue (TCJA SALT cap reduced the subsidy to state taxation)
- ACA Medicaid expansion choices differ by state
- State income taxes interact with federal brackets (marginal rates compound)
- States compete on corporate tax rates (nexus, apportionment)
- Policy incidence varies dramatically by state (e.g., a capital gains tax hits California more than Wyoming)

**Scope for v1 — top 10 states by population:**

Restrict v1 to: **CA, TX, FL, NY, PA, IL, OH, GA, NC, MI**. These 10 states cover ~55% of the US population and ~60% of federal income tax filers. This bounds the data entry and validation work to a manageable set while covering the most policy-relevant states (including both high-tax CA/NY and no-income-tax TX/FL for contrast).

- Individual income tax parameters for the 10 states above
- Federal-state SALT interaction for TCJA/SALT cap reforms
- State-level distributional analysis (income distribution varies by state)
- "State policy comparison" — what would a federal policy look like in each state?

**v2 expansion:** Remaining 40 states + DC, after v1 validation confirms the data pipeline and conformity logic work correctly across the diverse v1 set.

**Out of scope (v1):**
- State corporate taxes (complex nexus rules)
- Local taxes (property, sales)
- State-specific economic models (multipliers vary by state, but modeling this requires state-level macro data)
- Medicaid expansion (requires health economics module)

---

### 3.2 Data Architecture

#### State Tax Parameter Database

```python
# fiscal_model/data/state_taxes.py

@dataclass
class StateTaxProfile:
    """Tax parameters for a single state, single year."""
    state: str                       # 2-letter FIPS code
    year: int

    # Individual income tax
    has_income_tax: bool
    brackets_single: list[float]     # Income bracket breakpoints
    rates_single: list[float]        # Marginal rates
    brackets_mfj: list[float]
    rates_mfj: list[float]
    flat_rate: float | None          # For flat-tax states (PA, IL, etc.)

    # Deductions
    standard_deduction_single: float
    standard_deduction_married: float
    allows_federal_deduction: bool   # Some states allow deducting federal taxes
    conforms_to_federal_agi: bool    # Whether state starts from federal AGI

    # SALT context
    effective_salt_rate: float       # Weighted avg state + local rate (for federal SALT)

    # Income distribution context
    median_household_income: float   # From Census ACS
    gini_coefficient: float          # From Census
    top_1pct_income_share: float     # From Piketty-Saez

class StateTaxDatabase:
    """Loads and queries state tax parameter data."""

    def __init__(self, year: int = 2025):
        self.year = year
        self._data: dict[str, StateTaxProfile] = self._load()

    def get_state(self, state: str) -> StateTaxProfile:
        ...

    def get_all_states(self) -> dict[str, StateTaxProfile]:
        ...

    def get_no_income_tax_states(self) -> list[str]:
        """States with no income tax: FL, NV, SD, TN, TX, WA, WY (+ NH: no earned income)"""
        ...
```

**Data sources for state tax parameters:**
- **Tax Foundation State Tax Rates** (annual, free download): state brackets, rates, standard deductions — published every January for current year
- **TAXSIM (NBER)**: The NBER's TAXSIM model (free, web API) computes federal + state taxes simultaneously given taxpayer characteristics. Key for validation.
- **Census ACS**: Median income, Gini, income distribution by state (annual, public use)
- **BLS QCEW**: Wages by state (for payroll tax base)
- **IRS SOI State Data**: State-level returns data, available with ~2-year lag

**Data files to create:**
```
fiscal_model/data_files/state_taxes/
├── state_tax_rates_2025.csv    # From Tax Foundation
├── state_acs_income_2023.csv   # From Census ACS
└── state_salt_rates.csv        # Effective SALT rate by state (state + local combined)
```

Format for `state_tax_rates_2025.csv`:
```
state, has_income_tax, flat_rate, top_rate, brackets_json, rates_json, std_ded_single, std_ded_married, ...
CA, True, , 13.3, "[0,10412,24684,...]", "[0.01,0.02,...]", 5202, 10404, ...
TX, False, , 0, "[]", "[]", 0, 0, ...
```

---

### 3.3 Federal-State Interaction Model

The key interaction effect is the **SALT deduction**: federal taxpayers who itemize can deduct state and local taxes. This means:
- State tax rates implicitly subsidize states with high taxes (because federal tax is lower)
- TCJA SALT cap ($10K) reduced this subsidy, effectively raising after-federal-deduction state tax rates in high-tax states

**SALT interaction calculation:**

```python
def federal_salt_effect(
    federal_policy: TaxPolicy,
    state: str,
    db: StateTaxDatabase
) -> float:
    """
    Calculate the revenue change attributable to SALT interaction.

    If the federal policy changes SALT cap:
    - Effective SALT deduction per filer = min(actual state taxes, new cap)
    - Change in federal taxable income = old deduction - new deduction
    - Change in federal revenue = Δ_deduction * marginal_federal_rate
    """
    profile = db.get_state(state)
    ...
```

**State-level income distribution** for distributional analysis:
- IRS SOI publishes state-level data by AGI class (Table 2 by state)
- This allows distributional analysis within a state — e.g., "who bears this reform in California vs. Mississippi?"

---

### 3.4 Combined Federal + State Tax Calculator

The microsim engine (`fiscal_model/microsim/engine.py`) computes federal taxes. With state data, it can be extended:

```python
# fiscal_model/microsim/state_engine.py

class FederalStateCalculator:
    """
    Computes combined federal + state income tax liability.

    Key complication: state taxable income often starts from federal AGI,
    so changes to federal deductions/credits can affect state taxes.
    """

    def __init__(self, state: str, year: int = 2025):
        self.federal_calc = MicroTaxCalculator(year)
        self.state_profile = StateTaxDatabase(year).get_state(state)

    def calculate(self, pop: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate combined federal + state tax.

        Returns DataFrame with:
        - federal_tax: federal income tax
        - state_tax: state income tax
        - combined_tax: total
        - effective_combined_rate: combined/AGI
        """
        ...

    def apply_reform(self, pop: pd.DataFrame,
                     federal_reforms: dict,
                     state_reforms: dict = None) -> pd.DataFrame:
        """Apply both federal and state reforms simultaneously."""
        ...
```

---

### 3.5 UI Design

**State selector** — added to sidebar when "State Analysis" mode is enabled:

```
┌─────────────────────────────────────────────────────────┐
│  ANALYSIS SCOPE                                         │
│  ○ Federal only (default)                               │
│  ● Federal + State                                      │
│    State: [California ▼]                               │
│    [ ] Show all 50 states comparison                    │
└─────────────────────────────────────────────────────────┘
```

**State-level results tab** (new tab, only shown when state mode active):

```
┌─────────────────────────────────────────────────────────┐
│  STATE ANALYSIS: CALIFORNIA                             │
│  ─────────────────────────────────────────────────────  │
│  COMBINED FEDERAL + STATE TAX IMPACT                   │
│                                                         │
│  Federal impact: -$24.5B / yr    State interaction: +$1.2B│
│  Net to California taxpayers: -$23.3B / yr              │
│                                                         │
│  [Tab: Distribution] [Tab: SALT Interaction] [Tab: Map]  │
│                                                         │
│  Distribution tab:                                      │
│  Quintile table using California income distribution    │
│  (note: CA income distribution is more unequal than US) │
│                                                         │
│  SALT Interaction tab:                                  │
│  "TCJA SALT cap ($10K) affects 3.2M California filers   │
│   who itemize. Lifting the cap would cost federal       │
│   revenues $XX.XB but reduce state effective rates."    │
│                                                         │
│  50-State Map tab (when "all states" checked):          │
│  [Choropleth: avg tax change per filer by state]        │
└─────────────────────────────────────────────────────────┘
```

**50-state comparison table** (for policy impact):
```
| State | Avg Tax Change | % After-Tax Income | SALT Filers Affected | ... |
| CA    | -$4,200        | -2.1%              | 3.2M                 |     |
| TX    | -$2,800        | -1.4%              | 0.8M                 |     |
| ...   |                |                    |                      |     |
```

---

### 3.6 TAXSIM Integration

NBER TAXSIM (taxsim.nber.org/taxsim35) computes federal + state taxes from taxpayer characteristics. It's free, has a web API, and is the gold standard for state tax validation.

```python
# fiscal_model/data/taxsim.py

class TAXSIMClient:
    """
    Client for NBER TAXSIM web API.
    Useful for validation and for exact state tax calculations
    when the internal state model is insufficient.

    Note: Web API has rate limits; use for validation, not production scoring.
    Cache results aggressively.
    """
    TAXSIM_URL = "https://taxsim.nber.org/taxsim35/"

    def calculate(self, taxpayer: dict, state: str) -> dict:
        """
        Submit a single taxpayer to TAXSIM and return results.

        Args:
            taxpayer: dict with TAXSIM input fields
                (year, state, married, depx, pwages, ...)
            state: 2-digit state FIPS code

        Returns:
            dict with fiitax (federal), siitax (state), ...
        """
        ...

    def validate_state_model(self, state: str, n_sample: int = 100) -> dict:
        """
        Validate internal state model against TAXSIM for a random sample.
        Returns: {mean_error: float, max_error: float, correlation: float}
        """
        ...
```

---

### 3.7 Calibration and Validation

**Validation targets:**
- State income tax revenue (model vs. Census State Tax Collections): within 10% for each state
- SALT deduction usage by state (IRS SOI Table 2): within 15%
- TAXSIM comparison on 100 synthetic taxpayers per state: r² > 0.95, mean absolute error < 5%

**Known calibration challenges:**
- Some states have complex conformity rules (not just starting from federal AGI)
- Part-year residents, multi-state income — out of scope v1 (model assumes single-state filer)
- State-level capital gains preferences (some states don't tax CG; some have favorable rates)

---

### 3.8 Estimated Complexity

| Component | Effort | Notes |
|-----------|--------|-------|
| State tax parameter database + CSV | 4 days | Manual entry + validation for 51 jurisdictions |
| StateTaxDatabase class + loader | 2 days | Clean data API |
| FederalStateCalculator (microsim extension) | 4 days | Complex conformity logic |
| SALT interaction model | 2 days | Deduction math is well-defined |
| TAXSIM validation client | 2 days | Web API wrapper + validation routine |
| Streamlit state selector UI | 2 days | Sidebar + state tab |
| 50-state choropleth map | 2 days | Plotly choropleth |
| Tests + validation | 3 days | 25 tests; TAXSIM benchmarks for 5 states |
| **Total** | **~21 days** | **~4.5 person-weeks** |

---

### 3.9 Risks and Open Questions

**Data risks:**
- State tax law changes annually. The database needs to be updated each January. Build a scraping/download script for Tax Foundation data immediately.
- Some states have local income taxes (NYC, Philadelphia, several OH/PA cities) — out of scope v1 but misleading for those states.
- State tax complexity (Oregon kicker, California conformity divergences, Colorado TABOR) makes perfect accuracy hard. Set expectations: "state estimates are approximate."

**Design open questions:**
- **Which states to prioritize for validation?** Recommendation: CA, NY, TX, FL, IL — these 5 cover 40% of the US taxpayer base and span high-tax-to-no-tax spectrum.
- **Should state reforms be modelable?** (E.g., what if California raised its top rate?) This is a natural extension but doubles the parameter space. Recommendation: v1 federal-only reforms, state parameters fixed; v2 adds state policy levers.
- **State economic effects**: Should the dynamic scoring tab include state-level GDP/employment effects? This requires state-level multipliers, which is a significant lift. Recommendation: skip for v1, note as limitation.

---

## 4. Real-Time Bill Tracker

### 4.1 Motivation and Scope

The calculator scores hypothetical policies. The Bill Tracker connects it to **actual legislation moving through Congress**, so users can immediately see what a bill would cost and who it would affect.

**Data flow:**
```
Congress.gov API → Bill text + summary → Provision extractor → Calculator parameters → Score
CBO Cost Estimates → Official score storage → Side-by-side comparison
```

**Scope for v1:**
- Track bills with fiscal implications from the current Congress (119th Congress, 2025–2027)
- Display CBO/JCT cost estimates when available (sourced directly from CBO/JCT websites)
- For bills without official scores, auto-generate an estimate using the calculator
- Freshness indicators (last updated, days since introduced, committee status)
- Filter by policy area, sponsor, committee, status, estimated cost

**Not in scope (v1):**
- Full NLP-based provision extraction from bill text (use structured summaries)
- Tracking amendments (track base bill only)
- State-level bills
- Executive orders / regulatory actions

---

### 4.2 Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION PIPELINE                      │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ congress.gov │    │  CBO scores  │    │   JCT estimates      │  │
│  │    API       │    │  website     │    │   (jct.gov)          │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │              │
│         ▼                   ▼                       ▼              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  BillIngestor (scheduled job)               │   │
│  │  - Fetch new/updated bills since last run                   │   │
│  │  - Parse bill metadata (title, sponsor, status)             │   │
│  │  - Fetch CBO score if exists                                │   │
│  │  - Store to bills.db (SQLite)                               │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                │                                   │
│                                ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               ProvisionMapper                               │   │
│  │  - Map bill summary → calculator policy parameters         │   │
│  │  - Use rule-based extraction (v1) or LLM-assisted (v2)     │   │
│  │  - Store mapped parameters to bills.db                     │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                │                                   │
│                                ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               AutoScorer                                   │   │
│  │  - Run FiscalPolicyScorer on mapped parameters             │   │
│  │  - Store auto-estimate to bills.db                         │   │
│  │  - Flag confidence level (high/medium/low)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Refresh schedule**: Daily via `scripts/update_bills.py`, runnable as a cron job or Streamlit Cloud scheduled job.

---

### 4.3 Module Structure

```
fiscal_model/
└── bills/
    ├── __init__.py
    ├── ingestor.py          # BillIngestor — fetches from congress.gov
    ├── cbo_fetcher.py       # CBOScoreFetcher — scrapes cbo.gov
    ├── mapper.py            # ProvisionMapper — bill → calculator params
    ├── scorer.py            # AutoScorer — runs calculator on mapped params
    ├── database.py          # BillDatabase — SQLite interface
    ├── models.py            # Bill, BillScore, CBOScore dataclasses
    └── freshness.py         # Staleness detection + warning logic

scripts/
└── update_bills.py          # Orchestrates full pipeline, run daily
```

---

### 4.4 Congress.gov API Integration

The congress.gov API (api.congress.gov) provides:
- Bill lists by congress, chamber, type
- Bill metadata (title, sponsor, introduced date, status)
- Bill summaries (plain-language summaries from CRS)
- Bill text (full XML/PDF — heavy, used only for provision extraction)
- Subjects/tags (CRS subjects like "Taxation", "Income tax", "Health care")

**API key**: Free, requires registration at api.congress.gov. Store as `CONGRESS_API_KEY` env variable / Streamlit secret.

```python
# bills/ingestor.py

import requests
from dataclasses import dataclass
from datetime import datetime

CONGRESS_API_BASE = "https://api.congress.gov/v3"

@dataclass
class BillMetadata:
    bill_id: str             # e.g., "hr-1234-119"
    congress: int            # 119
    chamber: str             # "house" | "senate"
    number: str              # "1234"
    title: str
    sponsor: str
    introduced_date: datetime
    latest_action: str       # e.g., "Referred to Committee on Ways and Means"
    latest_action_date: datetime
    status: str              # "introduced" | "committee" | "passed_chamber" | "enacted"
    crs_subjects: list[str]  # CRS policy area tags
    has_cbo_score: bool
    summary: str | None      # CRS plain-language summary
    url: str                 # congress.gov URL

class BillIngestor:
    """Fetches and parses bills from congress.gov API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("CONGRESS_API_KEY")

    def fetch_recent_bills(self,
                           congress: int = 119,
                           subjects: list[str] = None,
                           since_date: datetime = None,
                           limit: int = 250) -> list[BillMetadata]:
        """
        Fetch bills with fiscal subjects from the current Congress.

        Filters by CRS subjects (default: tax/budget/spending-related):
          "Taxation", "Budget and appropriations", "Income tax",
          "Corporate taxes", "Social security", "Medicare",
          "Health care costs and insurance"
        """
        ...

    def fetch_bill_summary(self, bill_id: str) -> str | None:
        """Fetch CRS plain-language summary for a specific bill."""
        ...

    def fetch_enrolled_bills(self, congress: int = 119) -> list[BillMetadata]:
        """Fetch only bills that have been enacted into law."""
        ...
```

---

### 4.5 CBO Score Fetcher

CBO publishes cost estimates at cbo.gov/cost-estimates. There is no official CBO API, so this requires web scraping.

```python
# bills/cbo_fetcher.py

@dataclass
class CBOCostEstimate:
    bill_id: str
    title: str
    estimate_date: datetime
    ten_year_cost_billions: float   # Positive = costs money, Negative = raises revenue
    annual_costs: list[float]       # Year-by-year (may be 5 or 10 years)
    budget_function: str            # "Revenue", "Health", "Social Security", etc.
    dynamic_estimate: float | None  # If CBO published a dynamic score
    url: str                        # URL to the actual PDF/HTML

class CBOScoreFetcher:
    """
    Scrapes cbo.gov for cost estimates associated with bills.

    CBO publishes estimates as HTML and PDF. The HTML version is
    parseable; the PDF requires text extraction.

    Note: CBO does not score every bill. Many bills only get scores
    when they pass committee or are scheduled for floor consideration.
    """

    CBO_BASE = "https://www.cbo.gov"
    CBO_ESTIMATES_API = "https://www.cbo.gov/data/cost-estimates"  # JSON feed

    def fetch_recent_estimates(self,
                               since_date: datetime = None,
                               limit: int = 100) -> list[CBOCostEstimate]:
        """
        CBO provides a JSON API at /data/cost-estimates that lists
        recent estimates with metadata. Parse this to find matching bills.
        """
        ...

    def match_to_bill(self, bill_id: str) -> CBOCostEstimate | None:
        """
        Match a congress.gov bill ID to a CBO cost estimate.
        Fuzzy matching by title + date proximity.
        """
        ...

    def parse_estimate_html(self, url: str) -> CBOCostEstimate:
        """
        Parse a CBO estimate HTML page to extract the cost table.
        CBO's HTML estimates have a consistent table structure.
        """
        ...
```

---

### 4.6 Provision Mapper

The most technically challenging component: mapping bill language to calculator parameters.

**v1: LLM-assisted extraction (primary)** — Legislative language is too heterogeneous for regex-first extraction. CRS summaries use varied phrasing, cross-references, and conditional structures that defeat pattern matching for any non-trivial bill. The Claude API (`claude-haiku-4-5` for cost efficiency) is the primary extractor:

```python
# bills/mapper.py

LLM_EXTRACTION_PROMPT = """
You are a fiscal policy parameter extractor. Given the CRS summary of a Congressional bill,
extract all fiscal provisions and return a JSON array of policy objects.

Each policy object must have:
  - "policy_type": one of [income_tax, capital_gains, corporate, credits, spending,
                            transfer, payroll, estate, trade, other]
  - "parameters": dict of numeric parameters matching the calculator's Policy classes
  - "confidence": "high" | "medium" | "low"
  - "provision_text": the exact summary sentence this was extracted from

Return only valid JSON. If a provision cannot be mapped to a known policy type, include it
with policy_type="other" and an explanation in parameters.

Bill summary:
{summary}
"""

@dataclass
class MappingResult:
    bill_id: str
    policies: list[Policy]          # Extracted policy objects
    confidence: str                  # "high" | "medium" | "low" (overall)
    confidence_reason: str
    unmapped_provisions: list[str]   # Provisions the mapper couldn't handle
    mapping_notes: str
    extraction_method: str           # "llm" | "manual" | "regex_validated"

class ProvisionMapper:
    """Maps bill summaries to calculator Policy objects via LLM + regex validation."""

    def __init__(self, anthropic_client=None):
        import anthropic
        self.client = anthropic_client or anthropic.Anthropic()

    def map_bill(self, bill: BillMetadata) -> MappingResult:
        """
        Primary path: LLM extraction → regex validation → Policy construction.

        Steps:
        1. Send CRS summary to Claude API
        2. Parse JSON response into candidate Policy objects
        3. Run regex patterns as a validation/sanity check:
           - Confirm extracted numeric values appear in the summary text
           - Flag implausible values (e.g., rate_change > 0.50)
        4. Return MappingResult with extraction_method="llm"
        """
        ...

    def _validate_with_regex(self, policies: list[dict], summary: str) -> list[str]:
        """
        Use regex patterns as a validation layer, not primary extractor.
        Returns list of warning strings for any policy that fails validation.
        """
        ...

    def map_manual(self, bill_id: str, policies: list[Policy]) -> MappingResult:
        """Manual override for bills where LLM extraction fails or is wrong."""
        ...
```

**Regex patterns retained as validation layer** — the existing `PROVISION_PATTERNS` dict is kept but demoted: it cross-checks LLM-extracted numeric values against the summary text rather than serving as the primary extractor. Example: if LLM says `rate_change = 0.026` but no regex pattern finds a percentage near 2.6% in the text, flag for human review.

**API cost**: Claude Haiku at ~$0.0025/1K input tokens. A typical CRS summary is 300–500 tokens. Cost per bill: ~$0.001–$0.002. For 685 bills updated daily: ~$0.70/day maximum. Negligible.

**Manual override database** (critical for important bills):
Store a JSON file `fiscal_model/bills/manual_mappings.json`:
```json
{
  "hr-1234-119": {
    "description": "2025 Tax Cuts and Jobs Act II",
    "policies": [
      {"type": "tcja_extension", "extend_all": true, "keep_salt_cap": true},
      {"type": "corporate", "rate_change": -0.07}
    ],
    "override_reason": "Complex bill; auto-extraction missed corporate provision",
    "mapped_by": "Laurence Wilse-Samson",
    "mapped_date": "2026-03-15"
  }
}
```

---

### 4.7 Database Schema

Using SQLite (no server needed, Streamlit Cloud compatible):

```sql
-- bills/database.py (schema)

CREATE TABLE bills (
    bill_id TEXT PRIMARY KEY,      -- "hr-1234-119"
    congress INTEGER,
    chamber TEXT,
    number TEXT,
    title TEXT,
    sponsor TEXT,
    introduced_date TEXT,
    latest_action TEXT,
    latest_action_date TEXT,
    status TEXT,                   -- "introduced"|"committee"|"passed"|"enacted"
    crs_subjects TEXT,             -- JSON array
    summary TEXT,
    url TEXT,
    has_cbo_score INTEGER,
    last_fetched TEXT              -- ISO datetime
);

CREATE TABLE cbo_estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id TEXT,
    estimate_date TEXT,
    ten_year_cost_billions REAL,
    annual_costs TEXT,             -- JSON array
    budget_function TEXT,
    dynamic_estimate REAL,
    pdf_url TEXT,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
);

CREATE TABLE auto_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id TEXT,
    scored_at TEXT,
    ten_year_cost_billions REAL,
    annual_effects TEXT,           -- JSON array
    static_cost REAL,
    behavioral_offset REAL,
    confidence TEXT,
    policies_json TEXT,            -- Serialized Policy objects
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
);

CREATE TABLE mapping_overrides (
    bill_id TEXT PRIMARY KEY,
    policies_json TEXT,
    override_reason TEXT,
    mapped_by TEXT,
    mapped_date TEXT
);
```

---

### 4.8 Freshness and Staleness Logic

```python
# bills/freshness.py

@dataclass
class FreshnessStatus:
    bill_id: str
    status: str                  # "fresh" | "stale" | "outdated" | "enacted"
    last_updated: datetime
    days_since_update: int
    warning: str | None

FRESHNESS_THRESHOLDS = {
    "fresh": 1,      # Updated today
    "stale": 7,      # Updated within a week
    "outdated": 30,  # Updated within a month
    # Older than 30 days: "outdated", flag prominently
}

def check_freshness(bill: BillMetadata) -> FreshnessStatus:
    """
    Bills change status rapidly; old auto-scores may be wrong.
    Also: CBO score supersedes auto-score when available.
    """
    days = (datetime.now() - bill.last_fetched).days

    if bill.status == "enacted":
        return FreshnessStatus(status="enacted", warning=None, ...)

    if days == 0:
        status = "fresh"
        warning = None
    elif days <= 7:
        status = "stale"
        warning = f"Last updated {days} days ago. Check congress.gov for status changes."
    else:
        status = "outdated"
        warning = f"Data is {days} days old. This bill's status or CBO score may have changed."

    return FreshnessStatus(status=status, warning=warning, ...)
```

---

### 4.9 Streamlit UI

**New top-level tab**: "Bill Tracker" (added to main navigation)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ACTIVE LEGISLATION TRACKER — 119th Congress (2025–2027)           │
│  ─────────────────────────────────────────────────────────────────  │
│  Last updated: Today 6:00 AM  [Refresh]  685 bills tracked         │
│                                                                     │
│  FILTERS                                                            │
│  Policy area: [All ▼]  Status: [All ▼]  Min cost: [$1B ▼]         │
│  [ ] Has CBO score    [ ] Passed at least one chamber              │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 📋 Tax Relief for American Families and Workers Act          │  │
│  │    HR 7024 · Introduced Jan 2025 · Ways and Means Committee  │  │
│  │    Status: Passed House ●●●○○ Passed Senate                  │  │
│  │    CBO Score: -$33.5B over 10 years (official)  🟢 Fresh     │  │
│  │    Calculator Estimate: -$29.4B  [View Details]  [Score Now] │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 📋 One Big Beautiful Bill (Reconciliation 2025)              │  │
│  │    HR 1   · Introduced Jan 2025 · Budget Committee           │  │
│  │    Status: Committee ●●○○○                                   │  │
│  │    CBO Score: Not yet published  🟡 Stale (3 days)           │  │
│  │    Calculator Estimate: -$4.1T (medium confidence)           │  │
│  │    [View Details]  [Score Now]  [Compare to TCJA Extension ▼]│  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘
```

**Bill detail view** (when "View Details" clicked):

```
┌─────────────────────────────────────────────────────────────────────┐
│  One Big Beautiful Bill — HR 1, 119th Congress                      │
│  ─────────────────────────────────────────────────────────────────  │
│  Sponsor: Rep. Jason Smith (R-MO)                                   │
│  Introduced: January 15, 2025                                       │
│  Status: House Budget Committee (as of March 28, 2026)              │
│  Full text: [congress.gov ↗]                                        │
│                                                                     │
│  PROVISIONS IDENTIFIED                                              │
│  ✓ TCJA extension (full, all provisions)         auto-detected      │
│  ✓ Corporate rate cut from 21% → 20%             auto-detected      │
│  ✓ 100% bonus depreciation restored              manual override    │
│  ⚠ Medicaid work requirements                    not modeled        │
│                                                                     │
│  OFFICIAL SCORE                                                     │
│  No CBO score published yet.                                        │
│  JCT preliminary: $4.1T over 10 years (March 2026)                 │
│  Source: [jct.gov/publications ↗]                                  │
│                                                                     │
│  CALCULATOR ESTIMATE                                                │
│  Static: -$4.5T   |   Dynamic: -$3.8T                              │
│  Confidence: medium (2 of 3 provisions mapped)                     │
│  [Revenue chart — 10 year]  [Distribution table]                   │
│                                                                     │
│  COMPARISON                                                         │
│  Model vs JCT preliminary: +10.5% (within expected range)          │
│  [Full methodology notes]                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 4.10 Update Script

```python
# scripts/update_bills.py
"""
Daily bill tracker update pipeline.
Run: python scripts/update_bills.py [--full-refresh] [--verbose]

Schedule: Daily at 6 AM UTC (via Streamlit Cloud cron or external scheduler).
"""

def main():
    db = BillDatabase("fiscal_model/data_files/bills.db")
    ingestor = BillIngestor(api_key=os.environ["CONGRESS_API_KEY"])
    cbo = CBOScoreFetcher()
    mapper = ProvisionMapper()
    scorer = AutoScorer(FiscalPolicyScorer())

    # 1. Fetch new/updated bills (since last run)
    since = db.get_last_update() if not args.full_refresh else datetime(2025, 1, 1)
    bills = ingestor.fetch_recent_bills(congress=119, since_date=since)

    for bill in bills:
        db.upsert_bill(bill)

        # 2. Check for CBO score
        cbo_score = cbo.match_to_bill(bill.bill_id)
        if cbo_score:
            db.upsert_cbo_score(cbo_score)

        # 3. Map provisions (only if no manual override)
        if not db.has_manual_override(bill.bill_id):
            mapping = mapper.map_bill(bill)
            if mapping.confidence != "low":
                # 4. Auto-score
                auto_score = scorer.score(mapping)
                db.upsert_auto_score(auto_score)

    db.set_last_update(datetime.now())
    print(f"Updated {len(bills)} bills. DB contains {db.count_bills()} total.")
```

---

### 4.11 Estimated Complexity

| Component | Effort | Notes |
|-----------|--------|-------|
| congress.gov API client + bill models | 3 days | Well-documented API |
| CBO score fetcher (scraper) | 3 days | HTML parsing is fiddly |
| SQLite database schema + interface | 2 days | Straightforward |
| Rule-based provision mapper | 5 days | Pattern library needs extensive testing |
| Manual override system | 1 day | JSON file + loader |
| AutoScorer integration | 1 day | Thin wrapper on existing scorer |
| Freshness logic | 1 day | Simple date arithmetic |
| Streamlit bill tracker tab + detail view | 4 days | Most visible part; needs polish |
| Update script (orchestration) | 1 day | CLI script |
| Tests | 3 days | 25 tests; mock API responses |
| **Total** | **~24 days** | **~5 person-weeks** |

---

### 4.12 Risks and Open Questions

**Technical risks:**
- Congress.gov API rate limits: 5,000 requests/day for free tier. With 685 bills and daily updates, this is fine (only new/updated bills need fresh fetches).
- CBO scraping brittleness: CBO's site layout can change. Mitigation: also consume the CBO JSON API at `cbo.gov/data/cost-estimates` (documented, more stable).
- Provision extraction accuracy: Rule-based extraction will miss complex bills. Always show confidence level prominently. Never present auto-estimates as equivalent to official scores.

**Legal/policy risks:**
- Bill text is public domain. CBO estimates are public domain. No IP issues.
- Do not present calculator auto-estimates as "CBO estimates" — always clearly label.
- Bills change frequently; stale data is the main accuracy risk. Display last-updated prominently.

**Design open questions:**
- **LLM for provision extraction (v2)**: Using the Claude API to parse bill summaries would dramatically improve coverage. Claude can reliably extract structured policy parameters from CRS summaries. Estimate: 1–2 additional days. Worth doing, but add API cost (~$0.01 per bill summary).
- **JCT score ingestion**: JCT publishes estimates at jct.gov/publications. Adding a JCT fetcher alongside CBO would improve coverage. JCT's site structure is less consistent than CBO's.
- **Notification system**: "Alert me when a bill matching [topic] gets a CBO score." Requires user preferences/email, which requires auth. Skip v1.
- **Historical bills**: Should the tracker show enacted legislation from previous Congresses? Useful for comparison ("TCJA 2017 cost $1.9T"). Could seed the database with the `cbo_scores.py` validation set.

---

## 5. Caching Strategy

### 5.1 Streamlit Layer: `st.cache_data`

All expensive computations in the Streamlit app use `@st.cache_data` with explicit TTLs:

```python
@st.cache_data(ttl=3600)          # 1-hour TTL; recompute if baseline refreshed
def score_policy_cached(policy_key: str, dynamic: bool) -> ScoringResult:
    """Cache scoring results keyed on a hashable policy representation."""
    policy = Policy.from_key(policy_key)
    return FiscalPolicyScorer().score_policy(policy, dynamic=dynamic)

@st.cache_data(ttl=86400)         # 24-hour TTL
def load_irs_data_cached(year: int) -> pd.DataFrame:
    return IRSSOIData().load(year)

@st.cache_data(ttl=300)           # 5-minute TTL for bill tracker (freshness matters)
def load_bills_cached() -> list[BillMetadata]:
    return BillDatabase().get_all_bills()
```

`st.cache_data` is Streamlit's built-in disk+memory cache. It serializes results to disk between sessions, so a Streamlit Cloud app restart does not evict scored results.

### 5.2 Bill Tracker: Pre-computed Scores in SQLite

"Hot bills" (those with high view counts or recent CBO scores) are pre-scored and stored in the `auto_scores` table at update time. When a user views a bill, the app reads from SQLite rather than re-running the scorer:

```python
def get_bill_score(bill_id: str, db: BillDatabase,
                   scorer: FiscalPolicyScorer) -> AutoScore:
    # Try cache first
    cached = db.get_auto_score(bill_id)
    if cached and cached.scored_within_hours(24):
        return cached
    # Re-score and cache
    mapping = ProvisionMapper().map_bill(db.get_bill(bill_id))
    score = scorer.score_policy_package(mapping.policies)
    db.upsert_auto_score(bill_id, score)
    return score
```

**Hot bills definition**: any bill that (a) has passed at least one chamber, (b) has a CBO score, or (c) has been viewed more than 50 times in the last 7 days. These are pre-scored during the nightly `update_bills.py` run.

### 5.3 OLG: Steady-State Caching

OLG steady-state solutions are expensive (~5–30s depending on policy shock magnitude). Cache the baseline steady state on first solve and reuse it for all reform scenarios:

```python
@st.cache_data(ttl=86400, show_spinner="Solving baseline steady state...")
def get_baseline_steady_state(params_hash: str) -> SteadyState:
    """Cache keyed on OLGParameters hash. Recomputed only if params change."""
    model = OLGModel(OLGParameters.from_hash(params_hash))
    return model.solve_steady_state()
```

Each reform scenario then only needs to compute the transition path (fast, ~1–3s), not re-solve the baseline.

### 5.4 Redis: Deferred

Redis would add value for: (a) multi-user session sharing of large scored results, (b) background job queuing for slow OLG solves, (c) pub/sub for live bill tracker updates. However, Streamlit Cloud does not natively support Redis, and the current single-user/low-concurrency deployment does not justify adding a Redis dependency. Revisit when the app has >100 concurrent users or when OLG compute times exceed 30s for typical policies.

---

## 6. Confidence Labels

Every model output displayed to the user must carry a clearly visible confidence label. This is a cross-cutting requirement, not feature-specific.

### 6.1 Label Taxonomy

| Label | Displayed As | Criteria |
|-------|-------------|----------|
| `cbo_calibrated` | "CBO-calibrated" | Policy validated within 15% of official CBO/JCT score |
| `model_estimate` | "Model estimate" | Reasonable methodology but no official score to validate against |
| `exploratory` | "Exploratory — wide uncertainty" | Complex interactions, limited data, or >25% divergence from any benchmark |
| `olg_estimate` | "Model estimate — wide uncertainty band" | OLG output; always shown with ±range |
| `auto_scored` | "Auto-scored (unverified)" | Bill tracker LLM-extracted score; no human review |

### 6.2 Implementation

```python
# fiscal_model/confidence.py

from enum import Enum

class ConfidenceLevel(Enum):
    CBO_CALIBRATED  = "cbo_calibrated"
    MODEL_ESTIMATE  = "model_estimate"
    EXPLORATORY     = "exploratory"
    OLG_ESTIMATE    = "olg_estimate"
    AUTO_SCORED     = "auto_scored"

    @property
    def display_label(self) -> str:
        return {
            "cbo_calibrated": "CBO-calibrated",
            "model_estimate": "Model estimate",
            "exploratory": "Exploratory — wide uncertainty",
            "olg_estimate": "Model estimate — wide uncertainty band",
            "auto_scored": "Auto-scored (unverified)",
        }[self.value]

    @property
    def color(self) -> str:
        return {
            "cbo_calibrated": "green",
            "model_estimate": "blue",
            "exploratory": "orange",
            "olg_estimate": "orange",
            "auto_scored": "gray",
        }[self.value]
```

`ScoringResult` gains a `confidence: ConfidenceLevel` field. The `FiscalPolicyScorer` assigns it based on whether the policy exists in `cbo_scores.py` validation database (→ `CBO_CALIBRATED`) or not (→ `MODEL_ESTIMATE`). OLG results always get `OLG_ESTIMATE`. Bill tracker auto-scores always get `AUTO_SCORED`.

### 6.3 UI Display

Each result panel shows the label as a small badge next to the headline number:

```
10-year cost: -$252B  [CBO-calibrated ✓]
```
```
10-year cost: -$4.1T  [Auto-scored (unverified) ⚠]
```
```
30-year GDP effect: +1.2%  [Model estimate — wide uncertainty band ⚠]
  Range: +0.4% to +2.1% (±1 std dev of calibration uncertainty)
```

OLG results additionally show an explicit uncertainty range derived from re-running the model with ±1 std dev on key calibrated parameters (beta, sigma).

---

## Cross-Feature Dependencies

| Feature | Depends On |
|---------|-----------|
| OLG Model | `SolowGrowthModel` (shares production function structure), `BaseScoringModel` interface |
| Classroom Mode | All existing scoring modules (read-only), URL routing in `app.py` |
| State Modeling | `microsim/engine.py` (extends `MicroTaxCalculator`), `distribution.py` |
| Bill Tracker | `FiscalPolicyScorer` (calls existing scorer), all existing `Policy` types |

No feature requires another new horizon feature as a prerequisite. All four can be developed in parallel.

---

## Implementation Order Recommendation

Given complexity, expected impact, and dependencies:

| Priority | Feature | Rationale |
|----------|---------|-----------|
| 1 | **Classroom Mode** | Lowest complexity, immediately useful for teaching, no new data dependencies |
| 2 | **Bill Tracker** | High visibility, leverages existing scoring, relevant to current policy moment |
| 3 | **State Modeling** | Extends microsim already built; unlocks SALT interaction analysis |
| 4 | **OLG Model** | Most complex; builds on Solow growth; needed for PWBM comparison |

---

## Appendix: Third-Party APIs and Keys Required

| Feature | Service | Key Type | Cost |
|---------|---------|----------|------|
| Bill Tracker | congress.gov API | Free registration | Free |
| Bill Tracker | CBO (scraping) | None | Free |
| Bill Tracker | Anthropic API (Claude Haiku) | Existing key | ~$0.70/day max |
| State Modeling | TAXSIM (NBER) | None (web API) | Free |
| State Modeling | Census ACS | Free registration | Free |
| OLG Model | SSA data files | None (bulk download) | Free |
| All | FRED | Existing key | Free |

One paid API is required: Anthropic/Claude for bill provision extraction (~$0.001–0.002/bill). At 685 bills updated daily, cost is under $1/day. The `ANTHROPIC_API_KEY` is already configured as a Streamlit secret for the live app.

---

*Document version: 1.1 — April 2026 (peer review revisions: Broyden fallback, relative answer validation, top-10 state restriction, LLM-first bill extraction, caching strategy, confidence labels)*
