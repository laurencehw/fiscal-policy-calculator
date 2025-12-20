# System Architecture

> Technical design for the multi-model fiscal policy platform

---

## Overview

The Fiscal Policy Calculator is designed as a **pluggable multi-model platform** where different scoring methodologies can be applied to the same policy definition (CBO-style, JCT-inspired microsimulation, TPC-style distribution, Yale Budget Lab-style macro + microsim + behavioral modules, PWBM OLG).

```
                     ┌─────────────────────────────┐
                     │      Policy Definition       │
                     │  (model-agnostic inputs)     │
                     └─────────────────────────────┘
                                   │
                                    ▼
                     ┌─────────────────────────────┐
                     │         Model Plugins        │
                     │  CBO | JCT | TPC | Yale |    │
                     │              PWBM            │
                     └─────────────────────────────┘
                                    │
                ┌───────────────────┼────────────────────┐
                ▼                   ▼                    ▼
        ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
        │ Budget Results  │  │ Macro Results   │  │ Distributional  │
        │ (10yr, annual)  │  │ (GDP, rates)    │  │ + Behavioral    │
        └────────────────┘  └────────────────┘  └────────────────┘
```

---

## Current Architecture (Phase 1-2)

### Module Structure

```
fiscal_model/
├── __init__.py           # Public API exports
├── baseline.py           # Baseline budget projections
├── policies.py           # Policy type definitions
├── scoring.py            # Main scoring engine
├── economics.py          # Dynamic effects & multipliers
├── uncertainty.py        # Uncertainty analysis
├── reporting.py          # Output formatting
│
├── data/                 # Data integration layer
│   ├── __init__.py
│   ├── irs_soi.py        # IRS Statistics of Income
│   ├── fred_data.py      # FRED API wrapper
│   └── validation.py     # Data quality checks
│
├── data_files/           # Static data files
│   └── irs_soi/
│       ├── table_1_1_2021.csv
│       ├── table_1_1_2022.csv
│       └── ...
│
└── validation/           # Model validation
    ├── __init__.py
    ├── cbo_scores.py     # Known official scores
    └── compare.py        # Comparison framework
```

### Core Classes

#### 1. Policy Hierarchy

```python
# policies.py

class Policy:
    """Base class for all fiscal policies"""
    name: str
    description: str
    policy_type: PolicyType
    start_year: int
    duration_years: int
    phase_in_years: int
    sunset: bool

class TaxPolicy(Policy):
    """Tax rate changes, credits, deductions"""
    rate_change: float
    affected_income_threshold: float
    affected_taxpayers_millions: float
    taxable_income_elasticity: float = 0.25

class SpendingPolicy(Policy):
    """Discretionary and mandatory spending"""
    annual_spending_change_billions: float
    gdp_multiplier: float = 1.0
    employment_per_billion: float = 10000

class TransferPolicy(Policy):
    """Social Security, Medicare, etc."""
    benefit_change_percent: float
    new_beneficiaries_millions: float
```

#### 2. Scoring Engine

```python
# scoring.py

class FiscalPolicyScorer:
    """Main scoring orchestrator"""
    
    def __init__(self, baseline, start_year=2025, use_real_data=True):
        self.baseline = baseline or CBOBaseline().generate()
        self.economic_model = EconomicModel(self.baseline)
    
    def score_policy(self, policy: Policy, 
                     dynamic: bool = False) -> ScoringResult:
        """Score a single policy"""
        # 1. Static effects
        static_revenue, behavioral = self._score_tax_policy(policy)
        
        # 2. Behavioral offset
        deficit_after_behavioral = static_deficit + behavioral
        
        # 3. Dynamic effects (optional)
        if dynamic:
            dynamic_effects = self.economic_model.calculate_effects(...)
            final_deficit -= dynamic_effects.revenue_feedback
        
        return ScoringResult(...)

class ScoringResult:
    """Container for complete scoring results"""
    policy: Policy
    baseline: BaselineProjection
    years: np.ndarray
    static_revenue_effect: np.ndarray
    static_spending_effect: np.ndarray
    behavioral_offset: np.ndarray
    dynamic_effects: Optional[DynamicEffects]
    final_deficit_effect: np.ndarray
    low_estimate: np.ndarray
    high_estimate: np.ndarray
```

#### 3. Economic Model

```python
# economics.py

class EconomicConditions:
    """State of economy affecting multipliers"""
    output_gap: float
    at_zero_lower_bound: bool
    debt_to_gdp: float
    unemployment_rate: float
    
    @classmethod
    def normal_times(cls) -> 'EconomicConditions'
    @classmethod
    def recession(cls) -> 'EconomicConditions'

class EconomicModel:
    """Dynamic effects calculator"""
    
    def calculate_effects(self, policy, budget_effect) -> DynamicEffects:
        """GDP, employment, revenue feedback"""
        
class DynamicEffects:
    """Container for macro effects"""
    gdp_level_change: np.ndarray
    gdp_percent_change: np.ndarray
    employment_change: np.ndarray
    revenue_feedback: np.ndarray
```

#### 4. Data Layer

```python
# data/irs_soi.py

class IRSSOIData:
    """IRS Statistics of Income data loader"""
    
    def get_data_years_available(self) -> list[int]
    def get_filers_by_bracket(self, year, threshold) -> dict
    def get_total_revenue(self, year) -> float

# data/fred_data.py

class FREDData:
    """FRED API wrapper with caching"""
    
    def get_gdp(self, nominal=True) -> pd.Series
    def get_unemployment(self) -> pd.Series
    def get_interest_rate(self) -> pd.Series
```

---

## Target Architecture (Phase 3+)

### Multi-Model Structure

```
fiscal_model/
├── models/
│   ├── __init__.py
│   ├── base.py           # Abstract base model
│   ├── cbo/              # CBO-style conventional
│   │   ├── __init__.py
│   │   ├── static.py
│   │   ├── behavioral.py
│   │   └── dynamic.py
│   ├── jct/              # JCT-inspired microsimulation (official scorer; implementation replicated via public docs)
│   │   ├── __init__.py
│   │   ├── microsim.py
│   │   ├── corporate.py
│   │   └── distributional.py
│   ├── pwbm/             # Penn Wharton OLG
│   │   ├── __init__.py
│   │   ├── olg.py
│   │   ├── household.py
│   │   └── equilibrium.py
│   ├── tpc/              # Tax Policy Center style
│   │   ├── __init__.py
│   │   ├── microsim.py
│   │   └── distributional.py
│   └── yale/             # Yale Budget Lab-style modules (macro + microsim + behavioral)
│       ├── __init__.py
│       ├── macro.py              # FRB/US & USMM-style macro adapter entrypoints
│       ├── microsim.py           # Tax microsimulation integration
│       ├── behavioral.py         # Capital gains realizations, income shifting, employment effects
│       ├── depreciation.py       # Tax depreciation / cost recovery model
│       ├── vat.py                # VAT revenue + distribution
│       ├── admin_burden.py       # Time burden / compliance modeling
│       └── trade.py              # Tariff revenue/incidence (subset of Yale work)
│
├── data/
│   ├── microdata/        # CPS, synthetic returns
│   ├── trade/            # Tariff schedules
│   ├── macro/            # Macro model inputs/outputs, scenario configs, cached runs
│   ├── parameters/       # Elasticities, incidence assumptions, documentation-linked defaults
│   └── ...
│
└── comparison/           # Cross-model analysis
    ├── __init__.py
    └── compare.py
```

### Model Interface

```python
# models/base.py

from abc import ABC, abstractmethod

class BaseScoringModel(ABC):
    """Abstract interface for all scoring models"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Model name (e.g., 'CBO', 'PWBM')"""
        
    @property
    @abstractmethod
    def methodology(self) -> str:
        """Brief methodology description"""
    
    @abstractmethod
    def score(self, policy: Policy) -> ModelResult:
        """Score a policy and return results"""
    
    @abstractmethod
    def get_assumptions(self) -> dict:
        """Return all model assumptions"""

class ModelResult:
    """Standard output format for all models"""
    model_name: str
    policy: Policy
    
    # Common outputs
    ten_year_cost: float
    annual_effects: np.ndarray
    uncertainty_range: tuple[float, float]
    
    # Model-specific extras
    extras: dict
```

---

## Macro-Model Adapters (FRB/US & USMM-Style)

Yale Budget Lab’s dynamic scoring work relies on large-scale macro models (e.g., FRB/US and USMM). In our architecture, we treat those as **external macro engines** behind a stable adapter interface:

```python
class MacroModelAdapter(ABC):
    """Run macro scenarios and return standardized macro/budget feedback outputs."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def run(self, scenario: "MacroScenario") -> "MacroRunResult": ...
```

**Key design choice**: the platform should support either:
- **Direct execution** (when a runnable model + license exists), or
- **Data-driven replication** via **published scenario inputs/outputs** and documented transformations (when only documentation + downloadable data is available).

---

## Yale Budget Lab Feature-Parity Checklist (Methodology → Modules → Artifacts)

This section maps Yale Budget Lab’s published methodology documentation to concrete implementation modules and the *minimum artifacts* needed to replicate results in a transparent way.

### Dynamic macroeconomic + budget feedback (FRB/US / USMM-style)

- **Source**: [Estimating Dynamic Economic and Budget Impacts of Long-Term Fiscal Policy Changes](https://budgetlab.yale.edu/research/estimating-dynamic-economic-and-budget-impacts-long-term-fiscal-policy-changes)
  - **Modules**: `models/yale/macro.py`, `data/macro/`, `models/yale/behavioral.py` (for scenario inputs that depend on behavior)
  - **Artifacts**
    - **Scenario definition**: baseline vs reform paths for receipts/outlays categories, plus fiscal rules/closure assumptions
    - **Macro outputs**: GDP level/% path, employment/unemployment, inflation, short/long rates, investment, capital stock
    - **Budget feedback**: revenue feedback decomposition and net interest dynamics assumptions
    - **Calibration/assumptions**: MPC out of interest income, debt ownership split, effective rate adjustment speed, etc. (documented defaults)

- **Source**: [Dynamic Scoring Using FRB/US Macroeconomic Model](https://budgetlab.yale.edu/research/dynamic-scoring-using-frbus-macroeconomic-model)
  - **Modules**: `models/yale/macro.py`
  - **Artifacts**
    - FRB/US scenario levers mapping (policy → model inputs)
    - Output extraction + normalization into `MacroRunResult`

### Tax microsimulation + budget estimates

- **Source**: [Tax Microsimulation (Budget Lab)](https://budgetlab.yale.edu/research/tax-microsimulation-budget-lab)
  - **Modules**: `models/yale/microsim.py`, `data/microdata/`, `data/parameters/`
  - **Artifacts**
    - Microdata schema (tax unit fields, weights) + provenance
    - Tax calculator logic versioning (current law, policy reforms)
    - Validation targets (aggregate receipts, distributional moments)

- **Source**: [Model Budget Estimates](https://budgetlab.yale.edu/research/model-budget-estimates)
  - **Modules**: `models/yale/microsim.py`, `models/yale/macro.py`, `comparison/`
  - **Artifacts**
    - Mapping: micro static estimates → dynamic macro feedback → final budget tables
    - Standard output tables (10-year totals, annual paths, definitions)

- **Source**: [Types of Budget Estimates](https://budgetlab.yale.edu/research/types-budget-estimates)
  - **Modules**: `models/base.py` (result types), `models/yale/__init__.py`
  - **Artifacts**
    - Taxonomy: conventional vs dynamic vs distributional vs long-run
    - Display contracts (what the UI/API can promise per estimate type)

### Distributional methodology

- **Source**: [Estimating Distributional Impact of Policy Reforms](https://budgetlab.yale.edu/research/estimating-distributional-impact-policy-reforms)
  - **Modules**: `models/yale/microsim.py`, `models/yale/behavioral.py`, `models/tpc/distributional.py` (shared table formats)
  - **Artifacts**
    - Income definition(s) (cash/expanded), unit of analysis, equivalence scales (if any)
    - Grouping definitions (quintiles/deciles, filers vs households)
    - Output tables: average $ change, % after-tax income change, winners/losers

### Behavioral responses

- **Source**: [Behavioral Responses: Capital Gains Realizations](https://budgetlab.yale.edu/research/behavioral-responses-capital-gains-realizations)
  - **Modules**: `models/yale/behavioral.py`, `models/cbo/behavioral.py` (shared primitives), `models/yale/microsim.py`
  - **Artifacts**
    - Realization elasticity parameterization + timing/lock-in mechanics
    - Short-run vs long-run treatment + validation targets

- **Source**: [Behavioral Responses: Income Shifting Across Business Entity Type](https://budgetlab.yale.edu/research/behavioral-responses-income-shifting-across-business-entity-type)
  - **Modules**: `models/yale/behavioral.py`, `models/yale/microsim.py`, `models/jct/corporate.py`
  - **Artifacts**
    - Entity-type classification (C-corp vs pass-through) + shifting function
    - Interaction with corporate/individual schedules

- **Source**: [Behavioral Responses: Microeconomic Employment Effects](https://budgetlab.yale.edu/research/behavioral-responses-microeconomic-employment-effects)
  - **Modules**: `models/yale/behavioral.py`, `models/yale/macro.py` (if fed into macro runs)
  - **Artifacts**
    - Employment elasticity assumptions by policy type
    - Aggregation logic (micro → macro channel, if any)

### Depreciation / cost recovery

- **Source**: [Budget Lab’s Model of Tax Depreciation](https://budgetlab.yale.edu/research/budget-labs-model-tax-depreciation)
  - **Modules**: `models/yale/depreciation.py`, `models/yale/microsim.py`, `data/parameters/`
  - **Artifacts**
    - Asset classes + service lives
    - PVDA / rental price calculations (documented formula + params)
    - Policy levers: bonus depreciation, expensing, interest deductibility

### VAT revenue + distribution

- **Source**: [Modeling Revenue and Distributional Implications of a Value-Added Tax](https://budgetlab.yale.edu/research/modeling-revenue-and-distributional-implications-value-added-tax)
  - **Modules**: `models/yale/vat.py`, `models/yale/microsim.py`, `data/parameters/`
  - **Artifacts**
    - Consumption base definition + exemptions/zero-rating
    - Pass-through/incidence assumptions (consumer vs producer)
    - Distributional mapping of VAT burden to tax units

### Administrative burden / time costs

- **Source**: [Estimating Time Burden of Tax Filing](https://budgetlab.yale.edu/research/estimating-time-burden-tax-filing)
  - **Modules**: `models/yale/admin_burden.py`
  - **Artifacts**
    - Time-cost model (minutes/hours by filer type, complexity drivers)
    - Output units and aggregation (total hours, $ valuation assumptions)

### Long-run human capital impacts (children / cash assistance)

- **Source**: [Simulating Long-Term Impact of Cash Assistance to Children on Future Earnings](https://budgetlab.yale.edu/research/simulating-long-term-impact-cash-assistance-children-future-earnings)
  - **Modules**: `models/yale/behavioral.py` (or a future `models/yale/human_capital.py`)
  - **Artifacts**
    - Causal effect parameterization (earnings impacts by age/cohort)
    - Projection horizon + discounting assumptions

### Model Implementations

```python
# models/cbo/__init__.py

class CBOModel(BaseScoringModel):
    """CBO-style conventional + dynamic scoring"""
    
    name = "CBO"
    methodology = "Static + ETI behavioral + optional macro feedback"
    
    def __init__(self, eti: float = 0.25, dynamic: bool = False):
        self.eti = eti
        self.dynamic = dynamic
    
    def score(self, policy: Policy) -> ModelResult:
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=self.dynamic)
        return ModelResult(
            model_name=self.name,
            policy=policy,
            ten_year_cost=result.total_10_year_cost,
            annual_effects=result.final_deficit_effect,
            uncertainty_range=(sum(result.low_estimate), sum(result.high_estimate)),
            extras={'dynamic_effects': result.dynamic_effects}
        )
```

```python
# models/pwbm/__init__.py

class PWBMModel(BaseScoringModel):
    """Penn Wharton OLG dynamic model"""
    
    name = "PWBM"
    methodology = "Overlapping generations with endogenous capital"
    
    def __init__(self, horizon: int = 30):
        self.horizon = horizon
        self.olg = OLGModel()
    
    def score(self, policy: Policy) -> ModelResult:
        steady_state = self.olg.solve_steady_state(policy)
        transition = self.olg.compute_transition(policy, T=self.horizon)
        return ModelResult(
            model_name=self.name,
            policy=policy,
            ten_year_cost=sum(transition.deficits[:10]),
            annual_effects=transition.deficits[:10],
            extras={
                'long_run_gdp': steady_state.gdp_effect,
                'generational_incidence': transition.by_cohort
            }
        )
```

```python
# models/tpc/__init__.py

class TPCModel(BaseScoringModel):
    """Tax Policy Center microsimulation"""
    
    name = "TPC"
    methodology = "Return-level microsimulation with distributional output"
    
    def score(self, policy: Policy) -> ModelResult:
        # Run microsimulation
        sim = Microsimulation(self.microdata)
        sim.apply_policy(policy)
        
        return ModelResult(
            model_name=self.name,
            policy=policy,
            ten_year_cost=sim.total_revenue_change * 10,
            extras={
                'distributional_table': sim.get_distributional_table(),
                'winners_losers': sim.get_winners_losers()
            }
        )
```

### Model Comparison

```python
# comparison/compare.py

class ModelComparison:
    """Compare results across models"""
    
    def __init__(self, models: list[BaseScoringModel]):
        self.models = models
    
    def compare(self, policy: Policy) -> ComparisonResult:
        results = {}
        for model in self.models:
            results[model.name] = model.score(policy)
        
        return ComparisonResult(
            policy=policy,
            results=results,
            divergence=self._calculate_divergence(results),
            explanation=self._explain_divergence(results)
        )
    
    def _calculate_divergence(self, results: dict) -> dict:
        """Calculate how much models disagree"""
        costs = [r.ten_year_cost for r in results.values()]
        return {
            'range': max(costs) - min(costs),
            'std': np.std(costs),
            'cv': np.std(costs) / np.mean(costs)
        }
```

---

## Data Architecture

### Current Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   IRS SOI CSV   │────▶│  IRSSOIData     │────▶│   TaxPolicy     │
│   (static)      │     │  (loader)       │     │ (auto-populate) │
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    FRED API     │────▶│   FREDData      │────▶│  CBOBaseline    │
│   (live)        │     │  (cached)       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Target Data Flow

```
                    ┌──────────────────────────────────┐
                    │         Data Warehouse           │
                    │  ┌──────┐ ┌──────┐ ┌──────┐     │
                    │  │ IRS  │ │ CPS  │ │TRADE │     │
                    │  │ SOI  │ │ ASEC │ │ DATA │     │
                    │  └──────┘ └──────┘ └──────┘     │
                    │  ┌──────┐ ┌──────┐ ┌──────┐     │
                    │  │ FRED │ │ BEA  │ │ CBO  │     │
                    │  └──────┘ └──────┘ └──────┘     │
                    └──────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌──────────┐   ┌──────────┐   ┌──────────┐
             │Aggregate │   │ Micro-   │   │  Trade   │
             │  Data    │   │  data    │   │  Flows   │
             └──────────┘   └──────────┘   └──────────┘
                    │              │              │
                    ▼              ▼              ▼
             ┌──────────┐   ┌──────────┐   ┌──────────┐
             │CBO Model │   │TPC Model │   │Yale Model│
             └──────────┘   └──────────┘   └──────────┘
```

### Microdata Pipeline (Future)

```python
# data/microdata/pipeline.py

class MicrodataPipeline:
    """Build synthetic tax return microdata"""
    
    def __init__(self):
        self.cps = CPSData()
        self.irs_targets = IRSSOIData()
    
    def build_synthetic_file(self, year: int) -> pd.DataFrame:
        """
        1. Load CPS ASEC as base
        2. Impute tax variables (TAXSIM or rules)
        3. Reweight to match IRS aggregates
        4. Validate against published tables
        """
        base = self.cps.load_asec(year)
        with_taxes = self._impute_taxes(base)
        reweighted = self._reweight_to_irs(with_taxes, year)
        self._validate(reweighted, year)
        return reweighted
```

---

## API Design

### Python API

```python
from fiscal_model import TaxPolicy, PolicyType, quick_score

# Simple API
policy = TaxPolicy(
    name="High Income Rate Increase",
    rate_change=0.026,
    affected_income_threshold=400_000,
    policy_type=PolicyType.INCOME_TAX
)

result = quick_score(policy, dynamic=True)
print(f"10-year cost: ${result.total_10_year_cost:.1f}B")
```

### REST API (Future)

```
POST /api/v1/score
{
    "policy": {
        "type": "income_tax",
        "rate_change": 0.026,
        "threshold": 400000
    },
    "options": {
        "model": "cbo",
        "dynamic": true
    }
}

Response:
{
    "ten_year_cost": -252.0,
    "annual_effects": [-22.0, -24.0, ...],
    "uncertainty": {
        "low": -280.0,
        "high": -220.0
    }
}
```

---

## Deployment

### Current (Streamlit Cloud)

```
┌─────────────────────────────────────────┐
│           Streamlit Cloud               │
│  ┌─────────────────────────────────┐   │
│  │         app.py                   │   │
│  │  ┌─────────────────────────┐    │   │
│  │  │     fiscal_model/       │    │   │
│  │  └─────────────────────────┘    │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Future (Multi-Service)

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                         │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Frontend    │    │   API Server  │    │   Worker      │
│  (Streamlit)  │    │   (FastAPI)   │    │  (Celery)     │
└───────────────┘    └───────────────┘    └───────────────┘
                              │                     │
                              ▼                     ▼
                     ┌───────────────┐    ┌───────────────┐
                     │    Redis      │    │   Postgres    │
                     │   (cache)     │    │   (results)   │
                     └───────────────┘    └───────────────┘
```

---

## Performance Considerations

### Current Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Simple tax score | <100ms | Single policy |
| Dynamic score | ~500ms | With macro feedback |
| Full validation suite | ~5s | All benchmark policies |

### Future Optimization

1. **Caching**: Redis cache for common policy results
2. **Precomputation**: Pre-score common parameter combinations
3. **Parallel**: Multi-process for policy packages
4. **JIT**: Numba for OLG solver inner loops

---

*Last Updated: December 2025*

