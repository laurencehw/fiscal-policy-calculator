# Model Validation Report

> **Fiscal Policy Calculator — Comparison to Official CBO/JCT Estimates**
>
> Last Updated: September 1, 2026

---

## Executive Summary

The model is benchmarked against **30+ official estimates** from CBO, JCT, Treasury, PWBM, and TPC. Crucially, those benchmarks fall into **two epistemically different tiers**, and reporting them together overstates predictive power. Both are reproducible live: `python scripts/cold_holdout.py`. Tier 1 is additionally **pre-registered** (`fiscal_model/validation/preregistered.py`) and **CI-gated**.

### Tier 1 — Out-of-sample predictions (the genuine test)

Policies scored **bottom-up from IRS SOI** via raw rate/threshold auto-population (and, for capital gains, one frozen elasticity set), with **no fitting to the official target**. This is the only tier that measures predictive accuracy.

> **9 out-of-sample cases, mean abs error 44.8%, 5/9 within 15%, 6/9 within 25%.**
> There is deliberately no single "validated within X%" number: the distribution has a tight core and a long tail, and collapsing it would hide the tail.

| Case | Official | Model | Err | Source (date) | Baseline the source used | Pre-registered at |
|------|---------:|------:|----:|---------------|--------------------------|-------------------|
| Medicare surcharge 2pp (>$400K) | -$310B | -$315B | 2% | Treasury (2024) | Green Book FY2025 | `PHASE_A_SHA` |
| 1pp all brackets | -$960B | -$935B | 3% | JCT (2023-01) | CBO Feb 2023 | `be7e947` |
| 5pp top rate ($1M+) | -$700B | -$648B | 7% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| 2pp rate cut ($500K+) | +$400B | +$364B | 9% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| Biden top rate 39.6% ($400K+) | -$252B | -$284B | 13% | Treasury (2024-03) | Green Book FY2025 | `be7e947` |
| Warren surtax 3pp (AGI >$2M) | -$350B | -$284B | 19% | TPC (2020) | unstated (secondhand) | `PHASE_A_SHA` |
| Biden cap gains 39.6% + gains at death | -$456B | -$817B | 79% | Treasury (2024-03) | Green Book FY2025 | `be7e947`, first scored `PHASE_A_SHA` |
| Top rate to 45% (+8pp >$609,350) | -$420B | -$916B | 118% | TPC (2023) | unstated (secondhand) | `PHASE_A_SHA` |
| Treasury 39.6% + step-up repeal | -$322B | -$817B | 154% | Treasury (2021-05) | Green Book FY2022 | `d11bf2c`, first scored `PHASE_A_SHA` |

Live figures: `python scripts/cold_holdout.py`. Rows are the `Generic` category of the scorecard; every one has a row in [`fiscal_model/validation/preregistered.py`](../fiscal_model/validation/preregistered.py).

**What the tight core shows.** Ordinary-bracket rate changes (JCT 1pp, Biden $400K) score on the ordinary-income base (excludes preferential LTCG/QDIV); AGI-inclusive surtaxes (TPC $1M+/$500K+, Warren, the Medicare surcharge) score on the full taxable-income base that includes the preferential portion. The classification comes from how each source describes its base, not from which choice fits better — the `cold_holdout.py --ordinary-base` diagnostic shows the correction *worsens* the AGI-inclusive cases (7→30%, 9→30%, 2→29%), which is the tell. For ordinary and AGI-inclusive rate changes in this range, **treat uncalibrated custom policies as directional, ±15-20%.**

**What the tail shows.** Three cases miss badly and are kept rather than tuned away; each carries a `known_limitations` note in the scorecard:

- **Top rate to 45% (118%).** The uncalibrated path applies a single ETI (0.25) with the standard 0.5 factor, so an 8pp top-rate increase erodes by only ~12.5% while published top-rate estimates assume a much larger response at that rate level. The target is also suspect: at -$420B it is *smaller* than this database's own +5pp-above-$1M TPC figure (-$700B), i.e. a bigger rate increase on a wider base raising less. Part of this error is target error, and the provenance is a "TPC-range" figure with a bare homepage URL (Phase E).
- **The two capital-gains cases (79%, 154%).** Both are "39.6% above $1M plus step-up elimination", so the frozen-elasticity path necessarily produces the same prediction (-$817B) for both — while the two published targets differ from each other by 42% (-$322B vs -$456B, different Green Books three years apart). Treasury, JCT and PWBM all assume far stronger lock-in at a 43.4% top rate; the calibrated `CapitalGains` runner needs case-specific multipliers up to 5.3x to reproduce them. This is exactly the parameter Phase C is meant to cross-validate.

**Honest reading**: the model predicts ordinary and AGI-inclusive *rate* changes well and capital-gains *behavioural* responses badly. The four-case ~8% figure this table replaces was not wrong, but it was measured on four friendly shapes; widening the battery moved the mean to 44.8% and that is the more useful number.

### Pre-registration

Every Tier 1 case is registered in [`fiscal_model/validation/preregistered.py`](../fiscal_model/validation/preregistered.py) with the official target, the publishing source and date, the budget baseline *that source* was scored against, the commit and date at which the record entered the repository, and the commit of the first scoring run.

The discipline the manifest enforces (`assert_preregistered`, tested in `tests/test_preregistration.py`):

1. **A target may never be edited to match a model run.** If an official number genuinely changes, the old row is marked `superseded_by` and a **new row with a new `case_id`** is added. The history stays in the file and in the diff.
2. **No case may be scored out-of-sample without a row.** A Generic scorecard entry with no manifest row fails the test.
3. **Misses are kept.** A row is never removed because the model scores it badly.

Honest boundary, as with [`holdout.py`](../fiscal_model/validation/holdout.py): these are previously published numbers, and Phase A registered targets that already existed in the repository or in `CBO_SCORE_MAP`. What the manifest guarantees is that *from the entry commit onward* the target is frozen and any change is visible — not that nobody had ever seen the number.

**CI gate.** `.github/workflows/validation-dashboard.yml` runs `python scripts/cold_holdout.py --max-mean-error 60 --min-within-25pct 5` as a blocking step, and strict readiness (`scripts/check_readiness.py --strict`) no longer exempts Generic entries: an `Error` rating fails, and a `Poor` rating fails unless it carries a documented `known_limitations` note.

### Tier 2 — Calibrated reference models (reconstructions, not confirmations)

The specialized modules (TCJA, Corporate, Estate, Credits, AMT, Payroll, PTC, Capital Gains, Tax Expenditures) are parameterized so their components **reproduce the published decomposition**.

| Metric | Value |
|--------|-------|
| Calibrated benchmarks | 29 |
| Mean absolute error | 4.4% |
| Within 15% of official | 28/29 |
| Direction match rate | 29/29 |

The ~5% error here is **expected by construction** — these demonstrate the model's structure and provide auditable, source-linked reconstructions of official scores; they are **not** evidence the model would have predicted them cold. Best on income-tax/TCJA components (0.1–4%); weakest on payroll reforms (~12%, wage-distribution assumptions). Live figures: `python scripts/cold_holdout.py`.

**Scope note**: Distributional validation is currently benchmarked mainly against published TPC tables rather than a broader CBO distributional set. Payroll / estate scenarios remain higher-error checkpoints; the Biden CTC revenue residual from double-counting growth on window-average annuals is closed (see [VALIDATION_NOTES.md](VALIDATION_NOTES.md)).

**Calibration / holdout note**: The live scorecard and API credibility blocks distinguish specialized calibrated benchmark paths, generic parameterized paths, and the locked post-change holdout protocol (`revenue-scorecard-post-lock-2026-05-02`). Holdout labels are future regression checkpoints, not retroactive historical out-of-sample claims.

### Tier 2 (leave-one-out) — the same modules, held out

The 4.4% above is a bookkeeping number: each calibrated module carries **one hard-coded annual per benchmark**, so it reproduces its own targets because it was told the answer. Leave-one-out asks the question that number cannot: *holding out one benchmark, can the module's structural machinery — calibrated on the others — rebuild it?* Live figures: `python scripts/run_loo.py` (add `--donor-matrix` for the capital-gains diagnostic).

| Module | Kind | n derivable | Mean abs error | Cases (LOO error) |
|---|---|---|---|---|
| **Payroll** | structural | 3 | **3.8%** | eliminate cap −3.7%; $250K donut +1.3%; 90% coverage +6.3% |
| **Estate** | structural | 2 | **25.8%** | extend TCJA exemption +6.0%; Biden $3.5M/45% +45.6% |
| **AMT** | structural | 2 | **79.6%** | extend TCJA relief +73.2%; repeal individual AMT +86.0% |
| **Credits** | structural | 3 | **45.1%** | Biden CTC 2021 −64.1%; CTC extension −28.0%; childless EITC −43.1% |
| **Expenditures** | bottom-up | 5 | **39.4%** | mortgage −5.1%; SALT-cap repeal +4.0%; charitable cap +15.7%; SALT repeal +74.9%; employer-health cap +97.4% |
| **Capital gains** | structural (frozen elasticities) | 3 | **171.2%** | PWBM no step-up −22.6%; CBO +2pp −120.5%; PWBM with step-up −370.5% |

| Aggregate — derivable cases only | Value |
|---|---|
| Cases in aggregate | 18 |
| Not cross-validatable | 4 (reported alongside, never folded in) |
| Mean absolute error | **59.3%** |
| Median absolute error | 35.6% |
| Within 15% of official | 6/18 (33%) |
| CI ceiling (`--max-loo-mean-error`) | 75% |

**Read the three numbers separately and never collapse them**: Tier 1 out-of-sample, Tier 2 by construction (4.4%, n=29), Tier 2 leave-one-out (59.3%, n=18 derivable). The last is the honest statement of how much of the calibrated tier is structure and how much is a stored constant.

Four cases are **not cross-validatable** and carry a reason rather than a manufactured number: `expand_niit` (the module's only NIIT benchmark — nothing to calibrate the mechanism on), `eliminate_estate_tax` (the target is a model estimate, not a published score, and the machinery reproduces differences but not revenue *levels*), `repeal_corporate_amt` and `eliminate_step_up` (the base constant *is* the published target restated; a leakage guard in `loo.py` catches this mechanically). See [VALIDATION_NOTES.md](VALIDATION_NOTES.md) §6 for the per-module classification and what each error diagnoses.

---

## Validation Results by Policy Category

### 1. Income Tax Policies (Generic / out-of-sample path)

These rows are the **uncalibrated** bottom-up Generic scorer (`create_policy_from_score` → IRS SOI auto-pop). They are *not* hand-tuned reconstructions.

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| Medicare surcharge 2pp (>$400K) | -$310B | -$315B | 2% | Excellent | Treasury |
| 1pp all brackets | -$960B | -$935B | 3% | Excellent | JCT |
| 5pp top rate ($1M+) | -$700B | -$648B | 7% | Excellent | TPC |
| 2pp rate cut ($500K+) | +$400B | +$364B | 9% | Good | TPC |
| Biden $400K+ (2.6pp) | -$252B | -$284B | 13% | Acceptable | Treasury |
| Warren surtax 3pp (AGI >$2M) | -$350B | -$284B | 19% | Acceptable | TPC |
| Biden cap gains 39.6% + gains at death | -$456B | -$817B | 79% | Poor | Treasury |
| Top rate to 45% (+8pp) | -$420B | -$916B | 118% | Poor | TPC |
| Treasury 39.6% + step-up repeal | -$322B | -$817B | 154% | Poor | Treasury |

The three `Poor` rows are documented misses, not omissions — see the Tier 1 tail discussion above.

**Methodology Notes**:
- Uses IRS SOI data for taxpayer counts and income distributions
- Dispatch is on the record's *shape* (ordinary rate / capital gains / corporate rate / spending), not on a single `policy_type`; every `KNOWN_SCORES` record is either runnable or carries an explicit `runnable=False` reason
- Capital-gains cases use ONE frozen elasticity set (module defaults, short-run 0.8 / long-run 0.4), never the per-case tuples in `scenarios.py`
- Ordinary-bracket changes default to `ordinary_income_base=True` (exclude LTCG/QDIV)
- All-brackets (`threshold=0`) scored from total SOI taxable income, not `baseline × Δrate/0.18`
- Elasticity of Taxable Income (ETI) = 0.25 (Saez et al. 2012)
- Behavioral offset = ETI × 0.5 × static effect (signed; erodes magnitude)

Earlier docs that showed Biden at ~1% / −$250B used a hand-tuned path — that is **not** the Generic prediction.

---

### 2. TCJA Extension

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Full TCJA Extension** | **$4,600B** | **$4,582B** | **0.4%** | **Excellent** | CBO |
| TCJA without SALT cap | $5,700B | $5,738B | 0.7% | Excellent | Estimated |
| TCJA rates only | $3,185B | $3,200B | 0.5% | Excellent | Model |

**Component Breakdown (Full Extension)**:

| Component | 10-Year Cost | Notes |
|-----------|--------------|-------|
| Rate cuts | +$1,800B | All bracket reductions |
| Standard deduction | +$720B | Doubled from pre-TCJA |
| Pass-through (199A) | +$700B | 20% QBI deduction |
| Child Tax Credit | +$550B | $2K vs $1K baseline |
| AMT relief | +$450B | Higher exemptions |
| Estate exemption | +$167B | $14M vs $6.4M |
| **Subtotal (costs)** | **+$4,387B** | |
| SALT cap | -$1,100B | $10K cap on deduction |
| Personal exemption elimination | -$650B | Offset to std deduction |
| **Subtotal (offsets)** | **-$1,750B** | |
| **Calibration adjustment** | **+$1,963B** | To match CBO total |
| **Total** | **$4,600B** | |

**Key Insight**: CBO's baseline assumes TCJA expires after 2025. "Extension" is scored as a cost relative to that current-law baseline.

---

### 3. Corporate Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Biden 21% to 28%** | **-$1,347B** | **-$1,397B** | **3.7%** | **Excellent** | Treasury |
| Trump 21% to 15% | $1,920B | $1,920B | 0.0% | Excellent | Model |
| TCJA corporate repeal | -$1,400B | -$1,350B | 3.6% | Excellent | JCT |

**Methodology Notes**:
- Corporate elasticity = 0.25
- Pass-through effects modeled (S-corps reclassify income)
- GILTI/FDII international provisions included

---

### 4. Tax Credits

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Biden CTC 2021 (permanent)** | **$1,600B** | **$1,600B** | **0.0%** | **Excellent** | CBO |
| CTC extension | $600B | $600B | 0.0% | Excellent | CBO |
| **Biden EITC childless** | **$178B** | **$180B** | **0.9%** | **Excellent** | Treasury |

**Methodology Notes**:
- Refundable credits treated as outlays
- Phase-in and phase-out modeled explicitly
- Labor supply effects included (elasticity 0.1-0.3)

---

### 5. Estate Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| Extend TCJA exemption | $167B | $184B | 10.2% | Good | CBO |
| **Biden reform ($3.5M, 45%)** | **-$450B** | **-$450B** | **0.0%** | **Excellent** | Treasury |
| Eliminate estate tax | $350B | $385B | 10.0% | Good | Model |

**Current Law Context**:
- TCJA exemption: ~$14M per person (through 2025)
- Post-sunset: ~$6.4M per person
- Rate: 40%
- Taxable estates: ~7,000/year under TCJA, ~19,000 after sunset

---

### 6. Payroll Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **SS cap to 90%** | **-$800B** | **-$800B** | **0.0%** | **Excellent** | CBO |
| **SS donut hole $250K** | **-$2,700B** | **-$2,700B** | **0.0%** | **Excellent** | Trustees |
| **Eliminate SS cap** | **-$3,200B** | **-$3,200B** | **0.0%** | **Excellent** | Trustees |
| **Expand NIIT** | **-$250B** | **-$220B** | **12.1%** | **Acceptable** | JCT |

**Methodology Notes**:
- Current law: 12.4% on wages up to $176K (2025)
- Model assumes 4%/year wage growth
- Systematic underestimate likely due to wage concentration assumptions
- Labor supply elasticity = 0.15

**Why 12% Error?** Payroll tax estimates depend heavily on the distribution of wages above the cap. Official estimates use detailed SSA data; our model uses Census-based approximations.

---

### 7. Alternative Minimum Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Extend TCJA AMT relief** | **$450B** | **$451B** | **0.1%** | **Excellent** | JCT/CBO |
| **Repeal individual AMT** | **$450B** | **$451B** | **0.1%** | **Excellent** | CBO |
| **Repeal corporate AMT** | **$220B** | **$220B** | **0.0%** | **Excellent** | CBO |

**Key Parameters**:

| Parameter | TCJA (through 2025) | Post-Sunset (2026+) |
|-----------|---------------------|---------------------|
| Single exemption | $88,100 | ~$60,000 |
| MFJ exemption | $137,000 | ~$93,000 |
| Affected taxpayers | ~200,000 | ~7.3 million |
| Revenue | ~$5B/year | ~$60-75B/year |

Corporate AMT (CAMT): 15% book minimum tax on $1B+ corporations, ~$22B/year

---

### 8. Premium Tax Credits (ACA)

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Extend enhanced PTCs** | **$350B** | **$366B** | **4.6%** | **Excellent** | CBO |
| **Repeal all PTCs** | **-$1,100B** | **-$1,096B** | **0.3%** | **Excellent** | CBO |

**Key Parameters**:
- Enhanced PTCs (ARPA/IRA): 100%+ FPL eligible, 0-8.5% premium cap
- Original ACA: 100-400% FPL only
- ~22M marketplace enrollees, ~19M receiving PTCs
- Healthcare cost growth: 4%/year

---

### 9. Tax Expenditures

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Cap employer health** | **-$450B** | **-$450B** | **0.1%** | **Excellent** | CBO |
| Eliminate mortgage deduction | -$300B | -$330B | 10.1% | Good | CBO |
| **Repeal SALT cap** | **$1,100B** | **$1,156B** | **5.1%** | **Excellent** | JCT |
| Eliminate SALT deduction | -$1,200B | -$1,260B | 5.0% | Excellent | JCT |
| **Cap charitable at 28%** | **-$200B** | **-$201B** | **0.3%** | **Excellent** | Obama/Biden |
| **Eliminate step-up basis** | **-$500B** | **-$523B** | **4.7%** | **Excellent** | Biden |

**Major Tax Expenditures (JCT 2024 annual estimates)**:

| Expenditure | Annual Cost |
|-------------|-------------|
| 401(k) and DC plans | ~$251B |
| Capital gains/dividends | ~$225B |
| Employer health insurance | ~$250B |
| Defined benefit pensions | ~$122B |
| Charitable contributions | ~$70B |
| SALT (with $10K cap) | ~$25B |
| Mortgage interest | ~$25B |

---

### 10. Capital Gains

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| CBO +2pp all brackets | -$70B | -$83B | 19% | Acceptable | JCT |
| PWBM 39.6% (with step-up) | +$33B | +$30B | 9% | Good | PWBM |
| **PWBM 39.6% (no step-up)** | **-$113B** | **-$113B** | **0%** | **Excellent** | PWBM |

**Critical Insight: Step-Up Basis**

The Penn Wharton analysis demonstrates a fundamental asymmetry:
- **With step-up**: 39.6% rate *loses* $33B (lock-in effect dominates)
- **Without step-up**: Same rate *raises* $113B (can't avoid by holding)

**Time-Varying Elasticity** (CBO/JCT methodology):
- Years 1-3: elasticity = 0.8 (short-run timing effects)
- Years 4+: elasticity = 0.4 (long-run permanent response)
- PWBM no-step-up validation applies a 1.5x residual avoidance multiplier to capture remaining threshold timing and business-form shifting after constructive realization at death.

---

## Distributional Validation

### vs. TPC TCJA Analysis (2017)

Comparison of distributional shares with Tax Policy Center TCJA Conference Agreement analysis.

| Quintile | Model Share | TPC Share | Error | Status |
|----------|-------------|-----------|-------|--------|
| Lowest | 2.0% | 1.0% | 100% | Note 1 |
| Second | 5.0% | 4.0% | 25% | OK |
| **Middle** | **10.0%** | **10.0%** | **0%** | Excellent |
| Fourth | 18.0% | 17.0% | 5.9% | Good |
| Top | 65.0% | 68.0% | 4.4% | Good |

**Note 1**: Bottom quintile has very small absolute share; 100% error is only 1 percentage point.

**Overall Score: GOOD** - Model correctly captures that TCJA benefits skew heavily toward high-income taxpayers (65-68% to top quintile).

### Corporate Tax Incidence

Validation of 75/25 capital/labor incidence assumption:

| Source | Capital Share | Labor Share |
|--------|--------------|-------------|
| CBO | 75% | 25% |
| TPC | 75% | 25% |
| JCT | 75% | 25% |
| **Model** | **75%** | **25%** |

Capital income distribution matches Federal Reserve SCF data within 5%.

---

## Accuracy Rating Scale

| Rating | % Error | Interpretation |
|--------|---------|----------------|
| **Excellent** | <=5% | Model closely matches official estimates |
| **Good** | 5-10% | Model is reasonably accurate |
| **Acceptable** | 10-20% | Model provides directional guidance |
| **Poor** | >20% | Significant deviation - investigate methodology |

---

## Known Systematic Biases

### Underestimates
1. **Payroll tax revenue** (12% systematic): Model uses Census wage data; SSA has more detailed high-earner information
2. **Estate tax revenue** (10%): Wealth concentration at top is higher than model assumes

### Overestimates
1. **Tax credit costs** (9%): Take-up rates may be lower than 100%
2. **Capital gains revenue** (19% for all-bracket changes): JCT uses higher implied elasticity than academic literature

### Well-Calibrated
1. **TCJA extension** (0.4%): Explicitly calibrated to CBO
2. **AMT policies** (0.1%): Based on IRS/JCT taxpayer counts
3. **Tax expenditure caps** (0.1-5%): JCT baseline data embedded

---

## Data Sources

### Official Estimates
| Source | Used For | URL |
|--------|----------|-----|
| CBO | Budget projections, policy scores | [cbo.gov/cost-estimates](https://www.cbo.gov/cost-estimates) |
| JCT | Tax revenue estimates | [jct.gov/publications](https://www.jct.gov/publications/) |
| Treasury | Administration proposals | [treasury.gov](https://home.treasury.gov/) |
| TPC | Distributional analysis | [taxpolicycenter.org](https://www.taxpolicycenter.org/) |
| PWBM | Dynamic scoring, capital gains | [budgetmodel.wharton.upenn.edu](https://budgetmodel.wharton.upenn.edu/) |
| SSA Trustees | Payroll tax projections | [ssa.gov/oact/tr](https://www.ssa.gov/oact/tr/) |

### Model Data
| Data | Source | Vintage |
|------|--------|---------|
| Taxpayer counts | IRS SOI Table 1.1 | 2021-2022 |
| Income distributions | IRS SOI | 2021-2022 |
| Capital gains realizations | IRS SOI / CBO projections | 2022 |
| Wage distributions | Census CPS | 2023 |
| CBO baseline | CBO Budget Projections | February 2026 |

---

## Running Validation

### Quick Validation

```python
from fiscal_model.validation import compare_to_cbo
results = compare_to_cbo()
```

### Full Validation Suite

```python
from fiscal_model.validation.compare import (
    validate_all_tcja,
    validate_all_corporate,
    validate_all_credits,
    validate_all_estate,
    validate_all_payroll,
    validate_all_amt,
    validate_all_ptc,
    validate_all_expenditures,
    validate_all_capital_gains,
)

# Run all validation
tcja_results = validate_all_tcja(verbose=True)
corporate_results = validate_all_corporate(verbose=True)
credit_results = validate_all_credits(verbose=True)
estate_results = validate_all_estate(verbose=True)
payroll_results = validate_all_payroll(verbose=True)
amt_results = validate_all_amt(verbose=True)
ptc_results = validate_all_ptc(verbose=True)
expenditure_results = validate_all_expenditures(verbose=True)
capgains_results = validate_all_capital_gains(verbose=True)
```

### Manuscript Appendix Export

Use the appendix generator when you want a markdown artifact with benchmark provenance, follow-up checkpoints, and explicit evidence boundaries:

```bash
python scripts/generate_validation_appendix.py --output docs/validation_appendix_generated.md
```

Add `--include-core-database` if you want the broader legacy `validate_all()` score database as well as the curated cross-category suites.

### Custom Policy Validation

```python
from fiscal_model.validation.compare import quick_validate

# Validate a custom policy against an expected value
result = quick_validate(
    rate_change=0.026,           # +2.6pp
    income_threshold=400_000,    # $400K+
    expected_10yr=-252.0,        # -$252B (Treasury estimate)
    policy_name="Biden High-Income Tax"
)

print(result.get_summary())
# Biden High-Income Tax (Generic OOS): Official $-252B vs Model $-284B (~13%)
```

---

## Interpretation Guidelines

### When Model and Official Differ

1. **Check baseline assumptions**: CBO baseline assumes current law (TCJA expires). Model allows flexible baselines.

2. **Review behavioral parameters**: ETI, capital gains elasticity, labor supply elasticity all affect estimates. Official scorers may use different values.

3. **Consider data vintage**: IRS SOI data has 2-year lag. Economic conditions may have changed.

4. **Note policy complexity**: Multi-provision policies (like TCJA) require calibration factors that may not transfer to custom variants.

### Appropriate Use Cases

| Use Case | Reliability | Notes |
|----------|-------------|-------|
| Directional analysis | High | Model correctly identifies revenue/cost direction |
| Order of magnitude | High | Within factor of 2 for most policies |
| Precise scoring | Medium | 5-15% error typical; use for planning, not official scoring |
| Distributional | Medium | Validated mainly against TPC; broader CBO-style distributional benchmarking is still pending |
| Dynamic effects | Lower | FRB/US-calibrated, but macro uncertainty high |

---

## Comparison to Other Models

| Feature | This Model | CBO | JCT | TPC | PWBM |
|---------|------------|-----|-----|-----|------|
| Static scoring | Yes | Yes | Yes | Yes | Yes |
| Behavioral response | ETI-based | Detailed | Detailed | Detailed | Detailed |
| Dynamic macro | FRB/US-lite | Full FRB/US | Partial | Limited | OLG |
| Distributional | Quintiles/deciles | Limited | 10 groups | 5 quintiles | Limited |
| Open source | Yes | No | No | Partial | Partial |
| Real-time updates | Yes | Annual | Annual | Project | Project |

---

## CBO Methodology Reference

Key methodological points from CBO scoring practice:

### Sunsets Matter
- Temporary provisions (sunsets) significantly reduce 10-year scores
- Example: Build Back Better scored at $367B vs $3T+ if permanent
- **Implication**: Always check if provisions are temporary

### Timing Shifts
- Tax payment timing can alter 10-year scores
- Revenue timing affects scores even if total unchanged
- Example: Build It in America Act - increases deficits early, decreases later

### Authorization vs Appropriation
- Authorization bills set policy but don't spend money
- CBO scores only mandatory spending changes
- Example: NDAA authorizes $895B but CBO scores only $178M mandatory

### Pay-Fors
- New spending often offset by delayed/cancelled provisions
- Watch for offsetting provisions that may not be permanent
- Example: Medicare drug rebate delays used repeatedly as "pay-fors"

### IRS Enforcement
- IRS enforcement revenue typically not scored under budget rules
- Example: IRA expected ~$200B from enforcement but not in CBO score

---

## Future Validation Work

1. **2023 IRS SOI data**: Update taxpayer counts when available
2. **Next CBO baseline refresh**: Incorporate new projections as they are published
3. **Additional policies**: Expand validation database
4. **Distributional validation**: More TPC benchmarks
5. **Dynamic scoring**: Compare to CBO/JCT dynamic estimates

---

## References

1. Congressional Budget Office. (2024). *The Budget and Economic Outlook: 2024 to 2034*.
2. Joint Committee on Taxation. (2024). *Overview of the Federal Tax System*.
3. Saez, E., Slemrod, J., & Giertz, S. H. (2012). The elasticity of taxable income with respect to marginal tax rates. *Journal of Economic Literature*, 50(1), 3-50.
4. Penn Wharton Budget Model. (2021). *Revenue Effects of President Biden's Capital Gains Tax Increase*.
5. Tax Policy Center. (2024). *Distributional Analysis of Major Tax Proposals*.

---

*This validation report is maintained alongside the validation suite and refreshed as new official estimates are incorporated.*
