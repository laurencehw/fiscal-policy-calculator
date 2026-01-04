# Fiscal Policy Calculator — Project Roadmap

> **Vision**: Create an open-source platform that replicates the methodologies of major budget scoring organizations (CBO, JCT, Penn Wharton, Yale Budget Lab, Tax Policy Center) and provides an interactive interface for anyone to estimate economic and distributional impacts of fiscal policy proposals.

---

## Table of Contents

1. [Project Vision](#project-vision)
2. [Target Methodologies](#target-methodologies)
3. [Current State](#current-state)
4. [Phase Roadmap](#phase-roadmap)
5. [Technical Architecture](#technical-architecture)
6. [Data Requirements](#data-requirements)
7. [Success Metrics](#success-metrics)

---

## Project Vision

### The Problem

Budget scoring is currently a black box. When the CBO, JCT, or think tanks release estimates, the public and policymakers cannot:
- Understand the assumptions driving the numbers
- Test alternative scenarios
- Compare methodologies across organizations
- Evaluate uncertainty ranges

### The Solution

An interactive, transparent fiscal policy calculator that:

1. **Replicates Official Methodologies** — Implement scoring approaches from CBO, JCT, Penn Wharton, Yale Budget Lab, and Tax Policy Center
2. **Uses Real Data** — IRS Statistics of Income, CPS, FRED, CBO projections
3. **Shows the Work** — Every assumption, elasticity, and multiplier is documented and adjustable
4. **Enables Comparison** — Run the same policy through multiple models side-by-side
5. **Democratizes Access** — Free, open-source, web-accessible

### Target Users

| User | Need |
|------|------|
| **Policy Analysts** | Quick estimates for policy briefs |
| **Journalists** | Verify/challenge official estimates |
| **Students** | Learn budget scoring methodology |
| **Advocates** | Model alternative proposals |
| **Researchers** | Baseline for academic work |

---

## Target Methodologies

### 1. Congressional Budget Office (CBO)

**Approach**: Conventional scoring with optional macroeconomic analysis

| Component | Description | Status |
|-----------|-------------|--------|
| Static Revenue Scoring | Direct effect of tax rate changes | ✅ Implemented |
| Behavioral Response (ETI) | Elasticity of Taxable Income | ✅ Implemented |
| Dynamic Scoring | Macroeconomic feedback via Solow model | ✅ Basic |
| Spending Multipliers | State-dependent fiscal multipliers | ✅ Implemented |
| Baseline Projections | Current-law budget path | ✅ Implemented |
| Uncertainty Analysis | Confidence intervals | ✅ Basic |

**Key CBO Sources**:
- [How CBO Produces Budget Estimates](https://www.cbo.gov/about/products/budget-economic-data)
- [Macroeconomic Analysis of Budget Proposals](https://www.cbo.gov/topics/macroeconomic-analysis)
- [The 2024 Long-Term Budget Outlook](https://www.cbo.gov/publication/60039)

### 2. Joint Committee on Taxation (JCT)

**Approach**: Microsimulation using tax return data

JCT is the **official congressional scorer** for tax legislation. Their methodology uses IRS Statistics of Income (SOI) microdata and sophisticated behavioral models. While JCT publishes methodology overviews, implementation details are internal — we reference TPC's transparent documentation as a guide for microsimulation implementation.

| Component | Description | Status |
|-----------|-------------|--------|
| Individual Tax Calculator | Return-level tax simulation | 🔄 Partial |
| Tax Return Microdata | Representative sample of filers | ❌ Not started |
| Bracket-Level Analysis | Income distribution by bracket | ✅ Basic (IRS SOI) |
| Corporate Tax Model | Corporate income effects | ❌ Not started |
| Distributional Tables | Burden by income group | ❌ Not started |

**Key JCT Sources**:
- [Overview of Revenue Estimation](https://www.jct.gov/about-us/overview/)
- [Revenue Estimating Process (PDF)](https://www.jct.gov/publications/2017/jcx-1-17/) — Detailed methodology
- [Distributional Methodology](https://www.jct.gov/publications/2023/jcx-1-23/)
- [JCX Revenue Estimates](https://www.jct.gov/publications/)

### 3. Penn Wharton Budget Model (PWBM)

**Approach**: Overlapping Generations (OLG) dynamic model

| Component | Description | Status |
|-----------|-------------|--------|
| OLG Framework | Lifecycle optimization | ❌ Not started |
| Capital Accumulation | Long-run capital stock effects | ❌ Not started |
| Labor Supply Response | Intensive/extensive margin | ❌ Not started |
| Debt Dynamics | Crowding out, interest rates | ✅ Basic |
| Generational Accounting | Impacts by birth cohort | ❌ Not started |
| Stochastic Model | Uncertainty via simulation | ❌ Not started |

**Key PWBM Sources**:
- [PWBM Technical Documentation](https://budgetmodel.wharton.upenn.edu/methodology)
- [OLG Model Description](https://budgetmodel.wharton.upenn.edu/issues/2020/6/1/pwbm-olg-model)
- [Dynamic Scoring Reports](https://budgetmodel.wharton.upenn.edu/estimates)

### 4. Yale Budget Lab

**Approach**: Comprehensive scoring with transparent methodology — dynamic macro, microsimulation, behavioral responses

Yale Budget Lab publishes detailed methodology documentation, making it an excellent reference for replication. They use FRB/US (Federal Reserve's open-source model) and USMM (S&P Global's macro model) for dynamic scoring.

| Component | Description | Status |
|-----------|-------------|--------|
| Dynamic Macro (FRB/US, USMM) | Long-run fiscal policy effects | ❌ Not started |
| Tax Microsimulation | Revenue and distributional analysis | ❌ Not started |
| Distributional Impact | Policy effects by income group | ❌ Not started |
| Behavioral Responses | Capital gains, income shifting, employment | ❌ Not started |
| Tax Depreciation Model | Investment incentive effects | ❌ Not started |
| Trade Policy | Tariff revenue and incidence | ❌ Not started |
| VAT Modeling | Value-added tax simulation | ❌ Not started |

**Key Yale Sources** (Methodology & Documentation):
- [Dynamic Scoring with USMM](https://budgetlab.yale.edu/research/estimating-dynamic-economic-and-budget-impacts-long-term-fiscal-policy-changes)
- [Dynamic Scoring with FRB/US](https://budgetlab.yale.edu/research/dynamic-scoring-using-frbus-macroeconomic-model)
- [Tax Microsimulation](https://budgetlab.yale.edu/research/tax-microsimulation-budget-lab)
- [Distributional Impact Estimation](https://budgetlab.yale.edu/research/estimating-distributional-impact-policy-reforms)
- [Capital Gains Behavioral Responses](https://budgetlab.yale.edu/research/behavioral-responses-capital-gains-realizations)
- [Income Shifting Across Entity Types](https://budgetlab.yale.edu/research/behavioral-responses-income-shifting-across-business-entity-type)
- [Employment Effects](https://budgetlab.yale.edu/research/behavioral-responses-microeconomic-employment-effects)
- [Tax Depreciation Model](https://budgetlab.yale.edu/research/budget-labs-model-tax-depreciation)
- [VAT Modeling](https://budgetlab.yale.edu/research/modeling-revenue-and-distributional-implications-value-added-tax)
- [Types of Budget Estimates](https://budgetlab.yale.edu/research/types-budget-estimates)
- [Model for Budget Estimates](https://budgetlab.yale.edu/research/model-budget-estimates)

### 5. Tax Policy Center (TPC)

**Approach**: Microsimulation with detailed distributional output

TPC is valuable because they publish **transparent methodology documentation** that can be replicated, unlike JCT which keeps implementation details internal.

| Component | Description | Status |
|-----------|-------------|--------|
| Tax Microsimulation | Return-level calculation | ❌ Not started |
| Distributional Tables | Standard TPC format | ❌ Not started |
| Revenue Tables | 10-year scoring | ✅ Implemented |
| Winners/Losers | Percentage affected | ❌ Not started |
| Interactive Calculator | Public-facing tool | ✅ Streamlit |

**Key TPC Sources**:
- [Tax Model Resources](https://taxpolicycenter.org/resources/tax-model-resources) — Full methodology documentation
- [Brief Description of Tax Model](https://www.taxpolicycenter.org/resources/brief-description-tax-model)
- [Distributional Estimates](https://www.taxpolicycenter.org/model-estimates)

---

## Current State

### ✅ What's Built (Phases 1-5 Complete)

```
fiscal_model/
├── scoring.py                  # Main scoring orchestrator
├── policies.py                 # Policy base classes
├── baseline.py                 # CBO baseline projections
├── economics.py                # Fiscal multipliers
├── tcja.py                     # TCJA extension scoring
├── corporate.py                # Corporate tax policies
├── credits.py                  # Tax credits (CTC, EITC)
├── estate.py                   # Estate tax policies
├── payroll.py                  # Payroll tax (SS, Medicare, NIIT)
├── amt.py                      # Alternative minimum tax
├── ptc.py                      # Premium tax credits (ACA)
├── tax_expenditures.py         # SALT, mortgage, step-up basis
├── distribution.py             # TPC/JCT-style distributional analysis
├── models/
│   └── macro_adapter.py        # FRB/US-calibrated dynamic scoring
├── data/
│   ├── irs_soi.py              # IRS Statistics of Income loader
│   ├── capital_gains.py        # Capital gains baseline
│   └── fred_data.py            # FRED API integration
└── validation/
    ├── cbo_scores.py           # Official CBO/JCT benchmarks (25+)
    └── compare.py              # Validation framework
```

**Capabilities**:
- ✅ 25+ validated policy types (TCJA, corporate, credits, estate, payroll, AMT, ACA, expenditures)
- ✅ Auto-population from IRS SOI data (2021-2022)
- ✅ Behavioral response via ETI, capital gains elasticity
- ✅ Dynamic scoring with FRB/US-calibrated multipliers
- ✅ Distributional analysis (TPC/JCT-style tables, winners/losers)
- ✅ Policy package builder with presets and export
- ✅ Compare to CBO feature with accuracy ratings
- ✅ 60 unit tests with GitHub Actions CI
- ✅ Streamlit web interface (deployed)

**Validation Status** (25+ policies within 15% of official):
| Policy | Official Score | Our Estimate | Error |
|--------|---------------|--------------|-------|
| TCJA Full Extension | $4,600B | $4,582B | 0.4% |
| Biden Corporate 28% | -$1,347B | -$1,397B | 3.7% |
| Biden CTC 2021 | $1,600B | $1,743B | 8.9% |
| SS Donut Hole $250K | -$2,700B | -$2,371B | 12.2% |
| Repeal Corporate AMT | $220B | $220B | 0.0% |
| Cap Employer Health | -$450B | -$450B | 0.1% |

---

## Phase Roadmap

### Phase 1: Core Calculator ✅ COMPLETE
*Shipped: December 2025*

- [x] Basic tax policy scoring
- [x] IRS SOI data integration
- [x] Dynamic scoring fundamentals
- [x] Streamlit deployment
- [x] CBO validation framework

### Phase 2: CBO Methodology Completion ✅ COMPLETE
*Shipped: January 2026*

- [x] 25+ policies validated against CBO/JCT benchmarks
- [x] Full policy type suite (capital gains, estate, credits, payroll, AMT, ACA, expenditures)
- [x] Corporate tax modeling (Biden 28%, Trump 15%, GILTI/FDII)
- [x] Capital gains with time-varying elasticity and step-up basis
- [x] Tax credits (CTC, EITC with phase-in/phase-out)
- [x] Estate tax (TCJA extension, Biden reform)
- [x] Payroll tax (SS cap, donut hole, NIIT)
- [x] AMT (individual and corporate)
- [x] Premium tax credits (ACA enhanced/original)
- [x] Tax expenditures (SALT, mortgage, step-up, charitable)

### Phase 3: Distributional Analysis ✅ COMPLETE
*Shipped: January 2026*

- [x] Income quintile/decile breakdown
- [x] JCT-style dollar brackets
- [x] Tax burden by income group
- [x] Winners/losers percentage
- [x] Effective tax rate changes
- [x] Top income breakout (1%, 0.1%)
- [x] TPC-style output tables
- [x] Streamlit UI integration

### Phase 4: Dynamic Scoring ✅ COMPLETE
*Shipped: January 2026*

- [x] FRB/US-calibrated multipliers (spending 1.4x, tax -0.7x)
- [x] GDP and employment effects
- [x] Revenue feedback modeling
- [x] Crowding out effects
- [x] 10-year projections

### Phase 5: Policy Tools ✅ COMPLETE
*Shipped: January 2026*

- [x] Compare to CBO feature with accuracy ratings
- [x] Policy package builder (6 presets)
- [x] Custom policy combinations
- [x] JSON/CSV export
- [x] 60 unit tests
- [x] GitHub Actions CI

### Phase 6: Documentation & Polish 🔄 CURRENT
*Target: Q1 2026*

- [x] GitHub Actions CI
- [x] README update
- [x] Example Jupyter notebooks (`notebooks/example_usage.ipynb`)
- [ ] METHODOLOGY.md update with dynamic scoring
- [ ] API documentation
- [ ] Docstrings for public functions

### Phase 7: Penn Wharton OLG Model
*Target: Q3-Q4 2026*

**Goals**:
- [ ] Implement overlapping generations framework
- [ ] Long-run capital stock effects
- [ ] Lifecycle labor supply
- [ ] Generational accounting
- [ ] 30+ year projections

**Technical Approach**:

1. **Household Problem**
   - Lifecycle consumption/savings optimization
   - Labor-leisure choice
   - Bequest motive

2. **Production**
   - Cobb-Douglas with capital and labor
   - Endogenous capital accumulation
   - TFP growth path

3. **Government**
   - Budget constraint
   - Debt dynamics
   - Future fiscal adjustment

4. **Equilibrium**
   - Factor prices (wages, interest rates)
   - Aggregation across cohorts
   - Transition dynamics

**Implementation**:
```python
# Conceptual structure
class OLGModel:
    def solve_steady_state(self, policy)
    def compute_transition(self, policy, T=75)
    def generational_incidence(self, policy)
```

### Phase 8: Trade Policy Calculator
*Target: Q4 2026*

**Goals**:
- [ ] Tariff revenue scoring
- [ ] Consumer price effects
- [ ] Trade flow modeling
- [ ] Retaliation scenarios
- [ ] Industry-level impacts

**Inspired by Yale Budget Lab's trade calculator**:
- Product-level tariff database
- Elasticity of substitution by product
- Pass-through rates
- Welfare decomposition (consumer loss, producer gain, tariff revenue)

### Phase 9: Multi-Model Platform
*Target: 2027*

**Goals**:
- [ ] Run same policy through CBO, JCT-inspired microsim, TPC, Yale Budget Lab-style modules, and PWBM
- [ ] Side-by-side comparison
- [ ] Explain divergence
- [ ] Model selector interface
- [ ] API for external integration

**Architecture**:
```
models/
├── cbo/           # CBO-style conventional + dynamic
├── jct/           # Microsimulation approach
├── pwbm/          # OLG dynamic model
├── tpc/           # Distributional microsim
├── yale/          # Macro + microsim + behavioral + VAT + depreciation + trade
└── comparison/    # Cross-model analysis
```

---

## Technical Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Streamlit)                      │
│  ┌─────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────┐ │
│  │ Tax Calc│ │Spending Calc│ │ Trade Calc   │ │ Compare  │ │
│  └─────────┘ └─────────────┘ └──────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Scoring Engine API                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  score_policy(policy, model="cbo", dynamic=True)    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┬─────────────────────┐
        ▼                     ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   CBO Model   │    │  PWBM Model   │    │   TPC Model   │    │  Yale Module  │
│ ┌───────────┐ │    │ ┌───────────┐ │    │ ┌───────────┐ │    │ ┌───────────┐ │
│ │ Static    │ │    │ │ OLG       │ │    │ │ Microsim  │ │    │ │ Macro     │ │
│ │ Behavioral│ │    │ │ Capital   │ │    │ │ Distrib   │ │    │ │ Behavioral│ │
│ │ Dynamic   │ │    │ │ Labor     │ │    │ │ Burden    │ │    │ │ VAT/Depr. │ │
│ └───────────┘ │    │ └───────────┘ │    │ └───────────┘ │    │ └───────────┘ │
└───────────────┘    └───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │                     │
        └─────────────────────┼─────────────────────┴─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ IRS SOI │ │  FRED   │ │   CPS   │ │   CBO   │ │ Macro  │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Model Agnostic Policy Definition**
   - Same `TaxPolicy` object works across all models
   - Models add their own parameters/assumptions

2. **Pluggable Model Architecture**
   - Each model is independent module
   - Common interface for scoring

3. **Transparent Assumptions**
   - All elasticities, multipliers, growth rates exposed
   - Users can override any parameter

4. **Validation First**
   - Every model validated against official scores
   - Automated regression tests

---

## Data Requirements

### Currently Integrated

| Source | Data | Update Freq | Status |
|--------|------|-------------|--------|
| IRS SOI | Tax returns by bracket | Annual | ✅ 2021-2022 |
| FRED | GDP, unemployment, rates | Daily | ✅ API |
| CBO | Baseline projections | 2x/year | ✅ Hardcoded |

### Needed for Full Implementation

| Source | Data | Use Case | Priority |
|--------|------|----------|----------|
| CPS ASEC | Individual microdata | Distributional | High |
| IRS PUF | Tax return sample | Microsimulation | High |
| BEA | National accounts | GDP components | Medium |
| BLS | Employment by industry | Spending effects | Medium |
| USITC | Trade data | Tariff modeling | Medium |
| Census ACS | Demographics | State-level | Low |
| SOI Wealth | Estate tax data | Estate tax | Low |

### Synthetic Data Strategy

For models requiring microdata (JCT/TPC-style):
1. Use CPS ASEC as base
2. Statistically match to IRS aggregates
3. Impute missing tax variables
4. Validate against published distributions

---

## Success Metrics

### Accuracy Targets

| Model | Benchmark | Target Error |
|-------|-----------|--------------|
| CBO Static | JCT estimates | < 10% |
| CBO Dynamic | CBO dynamic scores | < 15% |
| Distributional | TPC tables | < 0.5pp per quintile |
| Trade | Yale Budget Lab | < 10% |

### Usage Targets

| Metric | Year 1 | Year 2 |
|--------|--------|--------|
| Monthly Users | 1,000 | 10,000 |
| Policies Scored | 10,000 | 100,000 |
| API Calls | - | 50,000/mo |
| Academic Citations | 5 | 25 |

### Community Targets

| Metric | Target |
|--------|--------|
| GitHub Stars | 500 |
| Contributors | 10 |
| Documentation Pages | 50 |
| Tutorial Videos | 10 |

---

## Resources & References

### Academic Papers

- **ETI**: Saez, Slemrod, Giertz (2012) "The Elasticity of Taxable Income"
- **Fiscal Multipliers**: Auerbach & Gorodnichenko (2012) "Measuring the Output Responses to Fiscal Policy"
- **OLG Models**: Auerbach & Kotlikoff (1987) "Dynamic Fiscal Policy"
- **Dynamic Scoring**: CBO (2014) "How CBO Analyzes Macroeconomic Effects of Legislation"

### Official Methodology Docs

- [CBO Budget Scoring Process](https://www.cbo.gov/about/processes)
- [JCT Revenue Estimating Process](https://www.jct.gov/about-us/revenue-estimating/)
- [PWBM Technical Documentation](https://budgetmodel.wharton.upenn.edu/methodology)
- [TPC Microsimulation Model](https://www.taxpolicycenter.org/resources/brief-description-tax-model)

### Similar Projects & Tools

- [Tax-Calculator (PSL)](https://github.com/PSLmodels/Tax-Calculator) - Open-source microsimulation
- [OG-USA (PSL)](https://github.com/PSLmodels/OG-USA) - Open-source OLG model
- [taxsim (NBER)](https://taxsim.nber.org/) - Tax simulation
- [FRB/US](https://www.federalreserve.gov/econres/us-models-about.htm) - Federal Reserve's open-source macro model (used by Yale Budget Lab)

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

Priority areas for contribution:
1. CPS/IRS data processing
2. Distributional analysis module
3. OLG model implementation
4. Trade policy calculator
5. Documentation and tutorials

---

*Last Updated: January 4, 2026*
*Maintainer: Laurence Wilse-Samson*

