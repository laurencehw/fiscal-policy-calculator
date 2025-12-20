# Next Session Priorities

> Current Phase: **Phase 2 — CBO Methodology Completion**
> 
> Last Updated: December 2025

---

## Immediate Priorities

### 1. 🎯 Complete CBO Validation Suite

**Goal**: Match 5+ official CBO/JCT scores within 10% error

**Current Status**:
| Policy | Official | Ours | Error | Status |
|--------|----------|------|-------|--------|
| Biden $400K+ | -$252B | ~-$250B | ~1% | ✅ |
| 1pp all brackets | -$960B | ~-$900B | ~6% | ✅ |
| TCJA Extension | $4,600B | TBD | TBD | 🔄 |
| Corporate 21%→28% | -$1,347B | TBD | TBD | ❌ |
| Capital gains 39.6% | -$456B | TBD | TBD | ❌ |

**Tasks**:
- [ ] Add TCJA extension scoring
- [ ] Implement corporate tax changes
- [ ] Add capital gains module
- [ ] Run validation script on all benchmark policies
- [ ] Document systematic biases

---

### 2. 🏗️ Capital Gains Tax Module

**Why**: Major gap in current model — capital gains taxes behave very differently from income taxes due to realization timing.

**Key Features**:
```python
class CapitalGainsPolicy(TaxPolicy):
    # Unique parameters
    realization_elasticity: float = 0.5  # Timing response
    lock_in_effect: float = 0.3          # Holding period effect
    step_up_at_death: bool = True        # Current law
    
    # Revenue calculation accounts for:
    # 1. Immediate behavioral response (realization timing)
    # 2. Long-run base effect
    # 3. Death tax interaction
```

**Implementation Steps**:
1. Add `CapitalGainsPolicy` class to `policies.py`
2. Add realization elasticity to behavioral offset
3. Handle step-up basis elimination (Biden proposal)
4. Validate against JCT capital gains estimates

---

### 3. 📊 Tax Credit Calculator

**Why**: Many popular policies are credits (CTC, EITC) not rate changes.

**Key Features**:
- Refundable vs non-refundable logic
- Phase-in and phase-out modeling
- Per-child / per-filer calculations
- Interaction with other credits

**Priority Credits**:
1. Child Tax Credit (CTC)
2. Earned Income Tax Credit (EITC)
3. Premium Tax Credits (ACA)
4. Education credits

---

### 4. 🔧 Corporate Tax Improvements

**Current State**: Basic corporate rate changes only

**Needed**:
- Pass-through income (S-corps, partnerships)
- GILTI/FDII international provisions
- R&D expensing
- Bonus depreciation
- Minimum book tax (15%)

---

## Medium-Term Goals (This Month)

### Documentation Sprint
- [ ] Complete `docs/METHODOLOGY.md` — full scoring methodology
- [ ] Create `docs/VALIDATION.md` — comparison to official scores
- [ ] Add docstrings to all public functions
- [ ] Create example notebooks

### Data Integration
- [ ] Add 2023 IRS SOI data when available
- [ ] Improve FRED data caching
- [ ] Add CBO baseline data loader (vs hardcoded)

### UI Improvements
- [ ] Add preset policy library (dropdown)
- [ ] Show methodology explanation in sidebar
- [ ] Add "Compare to CBO" feature
- [ ] Export results to CSV/PDF

---

## Backlog

### Phase 2 Remaining
- Estate tax module
- Payroll tax improvements (cap changes, new taxes)
- Alternative Minimum Tax (AMT)
- Tax expenditure scoring

### Phase 3 Preview (Distributional)
- Define income quintile/decile bins
- Build distribution engine
- Create TPC-style output tables
- Add winners/losers analysis

### Technical Debt
- Add comprehensive unit tests
- Set up CI/CD for validation
- Improve error handling in data loaders
- Add logging throughout

---

## Session Notes Template

```markdown
## Session: YYYY-MM-DD

### Accomplished
- 

### Blockers
- 

### Next Steps
- 

### Notes
- 
```

---

## Quick Reference

### Running the App
```bash
streamlit run app.py
```

### Running Validation
```python
from fiscal_model.validation import compare_to_cbo
results = compare_to_cbo()
```

### Key Files
| File | Purpose |
|------|---------|
| `app.py` | Streamlit interface |
| `fiscal_model/scoring.py` | Main scoring engine |
| `fiscal_model/policies.py` | Policy definitions |
| `fiscal_model/economics.py` | Dynamic effects |
| `fiscal_model/validation/cbo_scores.py` | Official benchmarks |

---

*Keep this file updated each session!*

