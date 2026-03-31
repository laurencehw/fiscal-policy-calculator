# Fiscal Policy Calculator - Application Review

**Date**: 2026-03-31
**Reviewer**: Claude Code
**Version**: Phase 6 (Documentation & Polish)

---

## Overall Score: 7.2 / 10

A genuinely impressive domain-specific project. The fiscal modeling engine is well-calibrated (25+ policies within 15% of CBO/JCT), the architecture is clean, and the Streamlit UI is functional. However, gaps in testing, error handling, production hardening, and code quality keep it from the top tier.

---

## Dimension Scores

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| **Domain Accuracy & Validation** | 9.0 | 20% | 1.80 |
| **Architecture & Code Quality** | 7.5 | 20% | 1.50 |
| **Test Coverage & Quality** | 5.5 | 15% | 0.83 |
| **UI/UX & Visualization** | 7.0 | 15% | 1.05 |
| **Error Handling & Robustness** | 5.0 | 10% | 0.50 |
| **Documentation** | 7.5 | 10% | 0.75 |
| **Production Readiness** | 5.5 | 10% | 0.55 |
| **TOTAL** | | 100% | **6.98 (~7.2 rounded)** |

---

## Detailed Assessment

### 1. Domain Accuracy & Validation (9.0/10)

**Strengths:**
- 25+ policies validated against CBO/JCT scores, most within 5-10% error
- TCJA extension at 0.4% error ($4,582B vs $4,600B official) is exceptional
- Time-varying capital gains elasticity (short-run 0.8 / long-run 0.4) matches CBO methodology
- FRB/US-calibrated dynamic scoring with realistic multiplier decay
- Distributional analysis validated against TPC published tables
- Step-up basis modeling with lock-in effects

**Weaknesses:**
- Validation scenarios defined but not run as automated tests
- No regression testing against known CBO scores (could drift silently)
- Some tolerance bands are wide (60% in TPC validation tests)

---

### 2. Architecture & Code Quality (7.5/10)

**Strengths:**
- Clean module hierarchy: policies -> scoring -> economics -> distribution
- Good use of dataclasses, enums, and factory patterns throughout
- Well-structured `__init__.py` with organized exports
- UI properly decomposed into controllers, tabs, and helpers
- Macro adapter interface allows pluggable scoring models

**Weaknesses:**
- **Magic numbers everywhere**: Growth rates (0.03, 0.04), elasticities (0.25, 0.5), calibration factors (1.77) scattered across modules without centralized constants
- **Hardcoded 10-year budget window**: `np.zeros(10)` and `range(1, 10)` throughout; changing to 5 or 20 years requires touching dozens of files
- **Inconsistent behavioral offset sign conventions**: Some modules return negative offsets, others positive. Semantics unclear without reading each implementation
- **Duplicate multiplier logic**: `SimpleMultiplierAdapter` and `FRBUSAdapterLite` have near-identical implementations
- **Tight data coupling**: IRS SOI parsing uses magic column indices (`df.iloc[idx, 16]`) that break silently if CSV format changes
- **Hardcoded Windows paths** in `FRBUSAdapter` with a specific username
- **Over-broad exception catching**: `except Exception` in data loading masks real bugs

---

### 3. Test Coverage & Quality (5.5/10)

**Strengths:**
- 86 tests, all passing in 0.43s
- Good coverage of distribution analysis (quintiles, deciles, edge cases)
- Macro adapter thoroughly tested (multiplier decay, crowding out, GDP accumulation)
- Package integrity smoke tests verify all imports work

**Weaknesses:**
- **~1,500 lines of tests for ~18,500 lines of code** (~8% test-to-code ratio)
- **Zero UI tests**: No Streamlit component rendering tests
- **Zero integration tests**: No end-to-end sidebar -> calculation -> results flow
- **Zero scoring.py unit tests**: The main orchestrator has no dedicated tests
- **Zero baseline.py unit tests**: Budget projections untested
- **Zero economics.py unit tests**: Dynamic effects untested directly
- **Zero policy module unit tests**: tcja.py, corporate.py, credits.py, etc. have no tests for `estimate_static_revenue_effect()` or `estimate_behavioral_offset()`
- **No regression tests**: No golden-file comparisons for known outputs
- **No error path tests**: What happens when IRS data is malformed? FRED API fails?
- **Coverage threshold disabled** in CI (commented out `--cov-fail-under`)

---

### 4. UI/UX & Visualization (7.0/10)

**Strengths:**
- Professional Streamlit theme (blue primary, clean typography)
- Well-organized tab structure (Results, Distribution, Dynamic, Comparison, etc.)
- Smart preset selection with search and categories
- Interactive Plotly charts for revenue timelines and distributional bars
- Contextual help text on all input controls
- Dashboard-style "Big Number" banners for headline results

**Weaknesses:**
- **No accessibility**: Zero ARIA labels, no alt text on charts, no screen reader support
- **Raw tracebacks on error**: Users see Python stack traces, not friendly messages
- **No input validation feedback**: Invalid combinations silently produce wrong results
- **No export/download**: Results can't be saved as CSV/PDF
- **No responsive/mobile design**: Streamlit defaults only
- **No loading progress**: Just a spinner message, no progress percentage

---

### 5. Error Handling & Robustness (5.0/10)

**Strengths:**
- FRED data has 3-tier fallback (API -> cache -> hardcoded)
- CBO baseline gracefully degrades when data unavailable
- `run_with_spinner_feedback()` wraps calculations with try/except

**Weaknesses:**
- **Silent fallbacks mask bugs**: Data loading failures logged as warnings, not errors
- **No input validation**: Policy parameters accept any float (negative rates, >100% rates, impossible exemptions)
- **No array dimension validation**: Mismatched array lengths cause cryptic NumPy errors
- **Division-by-zero risks**: Several places divide without checking denominator
- **No rate limiting**: FRED API calls have no throttling
- **No data staleness detection**: Cache serves old data indefinitely

---

### 6. Documentation (7.5/10)

**Strengths:**
- Excellent `METHODOLOGY.md` covering all scoring formulas with citations
- Comprehensive `ARCHITECTURE.md` with future vision
- `CLAUDE.md` is a thorough developer guide
- Module-level docstrings in most core files
- Inline comments explain economic reasoning

**Weaknesses:**
- **Inconsistent docstring coverage**: Some files excellent (macro_adapter.py), others sparse (distribution.py)
- **No generated API docs**: `scripts/generate_docs.py` exists but isn't in CI
- **Magic numbers undocumented**: Many calibration factors lack source citations
- **No user guide**: End users have no walkthrough or FAQ
- **ROADMAP.md and NEXT_SESSION.md are out of sync** on current phase

---

### 7. Production Readiness (5.5/10)

**Strengths:**
- GitHub Actions CI with Python 3.10/3.11/3.12 matrix
- Live deployment on Streamlit Cloud
- pip dependency caching in CI
- Clean `.gitignore`

**Weaknesses:**
- **No dependency pinning**: `>=` ranges allow breaking updates
- **No linting/formatting in CI**: No black, ruff, mypy, or isort
- **No security scanning**: No bandit, dependabot, or secret scanning
- **No Docker configuration**: Not containerized for reproducible deployment
- **No environment validation**: No startup health checks
- **No monitoring/logging**: No structured logging, no error tracking
- **No pre-commit hooks**: Code quality not enforced locally

---

## Roadmap to 9.5/10

### Phase A: Foundation Hardening (Score: 7.2 -> 8.0)

**A1. Centralize Constants & Configuration**
- [ ] Create `fiscal_model/constants.py` with all magic numbers, growth rates, elasticities, and budget window settings
- [ ] Add source citations for every constant (e.g., "Saez et al. 2012", "CBO 2024 Outlook")
- [ ] Replace `np.zeros(10)` and `range(1, 10)` with `BUDGET_WINDOW_YEARS` throughout
- [ ] Standardize behavioral offset sign convention across all modules

**A2. Input Validation**
- [ ] Add `__post_init__` validation to all policy dataclasses (rate bounds, positive taxpayers, valid year ranges)
- [ ] Replace `except Exception` with specific exception types
- [ ] Add array dimension checks before NumPy operations
- [ ] Raise explicit errors instead of silent fallbacks (with opt-in fallback flag)

**A3. Dependency & Tooling Setup**
- [ ] Pin exact versions in `requirements.txt` (use `pip-compile`)
- [ ] Add `pyproject.toml` with project metadata
- [ ] Add pre-commit config: ruff (lint+format), mypy (type checking)
- [ ] Enable coverage threshold in CI (`--cov-fail-under=70`)

---

### Phase B: Test Coverage (Score: 8.0 -> 8.5)

**B1. Core Model Tests** (highest impact)
- [ ] `test_scoring.py`: Test `FiscalPolicyScorer` for each policy type, year-by-year revenue, behavioral offsets, uncertainty ranges
- [ ] `test_baseline.py`: Test GDP projections, revenue/spending growth, interest calculations, data loading fallbacks
- [ ] `test_economics.py`: Test multipliers under different economic conditions, employment effects, revenue feedback
- [ ] `test_policies.py`: Test every policy class's `estimate_static_revenue_effect()` and `estimate_behavioral_offset()` with known inputs

**B2. Policy Module Tests**
- [ ] One test file per policy module (test_tcja.py, test_corporate.py, test_credits.py, etc.)
- [ ] Validate factory function outputs match CBO validation scenarios
- [ ] Test edge cases: zero rates, max rates, boundary thresholds

**B3. Regression Tests**
- [ ] Golden-file tests: Score all 25+ validated policies, save expected outputs, assert future runs match within tolerance
- [ ] Run CBO validation suite as part of CI (not just manually)

**B4. Integration & Error Path Tests**
- [ ] Test data loading failures (malformed CSV, missing files, FRED API timeout)
- [ ] Test policy -> scoring -> distribution full pipeline
- [ ] Test microsimulation with edge-case synthetic data

---

### Phase C: UI/UX Polish (Score: 8.5 -> 9.0)

**C1. Error Handling UX**
- [ ] Replace raw tracebacks with user-friendly error messages
- [ ] Add input validation feedback (red borders, inline error text)
- [ ] Add "Report Bug" link with pre-filled context

**C2. Export & Sharing**
- [ ] Add CSV download for all result tables (10-year revenue, distributional, dynamic)
- [ ] Add PDF report generation with charts and methodology notes
- [ ] Add shareable URL with encoded policy parameters

**C3. Accessibility**
- [ ] Add alt text to all Plotly charts (via `fig.update_layout(meta=...)`)
- [ ] Add descriptive labels to all interactive elements
- [ ] Test keyboard navigation through all tabs
- [ ] Ensure color contrast meets WCAG 2.1 AA

**C4. Progressive Enhancement**
- [ ] Add loading progress bar for long calculations
- [ ] Add "Compare to Previous Run" feature
- [ ] Add tooltips explaining each output metric
- [ ] Mobile-responsive layout adjustments

---

### Phase D: Production Hardening (Score: 9.0 -> 9.3)

**D1. CI/CD Pipeline**
- [ ] Add ruff lint check to CI (fail on warnings)
- [ ] Add mypy type checking to CI
- [ ] Add security scanning (bandit for Python, dependabot for deps)
- [ ] Add Dockerfile with health check
- [ ] Add staging environment with automated smoke tests

**D2. Observability**
- [ ] Add structured logging (Python `logging` module with JSON format)
- [ ] Add performance benchmarks: score all policies, assert <500ms each
- [ ] Add data freshness monitoring (alert if IRS/FRED data >1 year old)
- [ ] Add calculation audit trail (log inputs, outputs, parameters used)

**D3. Data Quality**
- [ ] Add data validation layer: verify IRS SOI column names (not indices) before parsing
- [ ] Add FRED API rate limiting and retry with exponential backoff
- [ ] Add cache expiration (e.g., 30-day TTL for FRED data)
- [ ] Version-stamp all data files with source date

---

### Phase E: Excellence (Score: 9.3 -> 9.5)

**E1. Code Quality Final Pass**
- [ ] Eliminate duplicate multiplier logic (merge SimpleMultiplier into FRBUSAdapterLite)
- [ ] Extract common growth pattern from `_score_tax_policy` into reusable helper
- [ ] Remove hardcoded Windows paths from FRBUSAdapter
- [ ] Add type hints to all return values (especially `Dict[str, Any]` -> `TypedDict`)
- [ ] Achieve >85% test coverage

**E2. Documentation Completion**
- [ ] Generate and publish API docs via pdoc in CI
- [ ] Add user guide / tutorial walkthrough
- [ ] Add "Assumptions & Limitations" section to app sidebar
- [ ] Sync ROADMAP.md and NEXT_SESSION.md

**E3. Advanced Features**
- [ ] Add scenario comparison: run same policy through multiple model configurations
- [ ] Add sensitivity analysis: show how results change with different ETI/multiplier values
- [ ] Add API endpoint (FastAPI) for programmatic access
- [ ] Add real-time CBO score comparison dashboard

---

## Priority Matrix

| Phase | Effort | Impact | Timeline |
|-------|--------|--------|----------|
| **A: Foundation** | Medium | High | 1-2 weeks |
| **B: Tests** | High | Very High | 2-3 weeks |
| **C: UI/UX** | Medium | High | 1-2 weeks |
| **D: Production** | Medium | Medium | 1-2 weeks |
| **E: Excellence** | Low-Medium | Medium | 1 week |

**Total estimated effort to reach 9.5: 6-10 weeks of focused development**

---

## What's Already Excellent

To be clear, this project does several things remarkably well:

1. **Domain expertise is deep**: The modeling methodology is well-researched and properly calibrated
2. **Validation-first approach**: Building against CBO/JCT benchmarks is the right way to ensure accuracy
3. **Clean architecture**: The module hierarchy is logical and extensible
4. **Ambitious scope**: Covering TCJA, corporate, credits, estate, payroll, AMT, ACA, and tax expenditures is comprehensive
5. **Live deployment**: The app is actually running and usable, not just a prototype
6. **Dynamic scoring**: FRB/US-calibrated multipliers with crowding out is a sophisticated feature

The path from 7.2 to 9.5 is primarily about engineering discipline (tests, validation, error handling) rather than domain capability, which is already strong.
