# Next Session Priorities

> Current Phase: **Phase 7 — Advanced Modeling (Microsim & OLG)** 🔄 IN PROGRESS
>
> Last Updated: January 12, 2026

---

## Session: 2026-01-12 (Part 2)

### Accomplished
- ✅ **Microsimulation Engine Prototype**
  - Ingested real CPS ASEC 2024 microdata (135M weighted population)
  - Built `MicroTaxCalculator` for individual tax unit processing
  - Implemented vectorized tax logic (brackets, standard deduction, CTC)
  - Integrated into Streamlit app with "Impact by Family Size" visualization
- ✅ **UI/UX Overhaul**
  - Streamlined inputs with progressive disclosure
  - Created dashboard-style Results tab with "Big Number" banner
  - Side-by-side charts to reduce scrolling

### What's Next (Priority Order)
1. **Long-Run Growth (OLG Model)**:
   - Implement Solow/OLG framework to model capital stock evolution
   - Estimate long-run crowding out effects (30-year horizon)

2.  **Microsimulation Polish**:
    - Add itemized deduction imputation (for SALT cap analysis)
    - Improve filing status logic (Head of Household)

---

## Session: 2026-01-12 (Part 1)
- ✅ **Step-Up Basis Modeling Implementation**
  - Verified and polished `CapitalGainsPolicy` step-up logic
  - Confirmed `step_up_lock_in_multiplier` correctly increases elasticity (lock-in effect)
  - Confirmed `eliminate_step_up` removes lock-in and adds death revenue channel
  - Validated revenue estimates (~$21B revenue from death gains at 39.6% rate)
  - Updated default exemption to $1M (matching Biden proposal)
- ✅ **Optimized FRED Data Caching**
  - Refactored `FREDData` to use individual JSON files per series instead of monolithic cache
  - Improved performance and robustness (no large memory load)
  - Added robust cache freshness checking and clearing
- ✅ **Methodology Review**
  - Verified `METHODOLOGY.md` contains up-to-date Dynamic Scoring and Step-Up Basis sections

### What's Next (Priority Order)
1. **Data Updates**:
   - Add 2023 IRS SOI data when available (currently using 2022)
   - Add CBO baseline data loader (vs hardcoded)

2. **Final Polish**:
   - Run full test suite and validation scripts
   - Final review of all documentation

---

## Session: 2026-01-04

### Accomplished
- ✅ **Example Jupyter Notebook**: Created comprehensive `notebooks/example_usage.ipynb`
- ✅ **Fixed Notebook API**: Updated all examples to match actual module APIs
- ✅ **CI Verification**: All 6 recent workflow runs passed
- ✅ **Documentation Updates**: README updated with notebook reference
- ✅ **METHODOLOGY.md Expansion**: Comprehensive dynamic scoring documentation
- ✅ **VALIDATION.md Comprehensive Update**: Full comparison to official scores
- ✅ **Docstrings**: Added to remaining public factory functions
- ✅ **API Documentation**: Set up pdoc for auto-generated docs

---

## Immediate Priorities

### 1. 🎯 Complete CBO Validation Suite

**Goal**: Match 5+ official CBO/JCT scores within 10% error

**Current Status**:
| Policy | Official | Ours | Error | Status |
|--------|----------|------|-------|--------|
| Biden $400K+ | -$252B | ~-$250B | ~1% | ✅ |
| **TCJA Extension** | **$4,600B** | **$4,582B** | **-0.4%** | ✅ |
| **Corporate 21%→28%** | **-$1,347B** | **-$1,397B** | **-3.7%** | ✅ |
| **Biden CTC 2021** | **$1,600B** | **$1,743B** | **+8.9%** | ✅ |
| **Estate: Biden Reform** | **-$450B** | **-$496B** | **+10.1%** | ✅ |
| **SS Donut $250K** | **-$2,700B** | **-$2,371B** | **+12.2%** | ✅ |
| **PTC: Extend Enhanced** | **$350B** | **$366B** | **+4.6%** | ✅ |
| **Repeal SALT Cap** | **$1,100B** | **$1,156B** | **+5.1%** | ✅ |
| **Eliminate Step-Up** | **-$500B** | **-$523B** | **+4.7%** | ✅ |

**Tasks**:
- [x] Add TCJA extension scoring ✅ (0.4% error)
- [x] Implement corporate tax changes ✅ (3.7% error)
- [x] Tax credit calculator (CTC, EITC) ✅ (0.9-8.9% error)
- [x] Estate tax module ✅ (10.1-10.2% error)
- [x] Payroll tax module ✅ (12.1-12.2% error)
- [x] AMT module ✅ (0.0-0.1% error)
- [x] Premium Tax Credits module ✅ (0.3-4.6% error)
- [x] Tax expenditure scoring ✅ (0.1-10.1% error)
- [x] Step-up basis modeling ✅ (Verified)

---

## Backlog

### Phase 2 Remaining
- ✅ All core modules completed

### Phase 3 (Distributional)
- ✅ Distribution engine completed
- ✅ Validated against TPC

### Technical Debt
- [ ] Add 2023 IRS SOI data
- [x] Improve FRED caching ✅
- [ ] Add comprehensive unit tests for new modules

---

## Quick Reference

### Running the App
```bash
streamlit run fiscal-policy-calculator/app.py
```

### Running Validation
```python
from fiscal_model.validation import compare_to_cbo
results = compare_to_cbo()
```