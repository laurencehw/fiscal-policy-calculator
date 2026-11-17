# Corporate class recalibration — marginal credit realization

**Status:** done (this PR).
**Does not retune** `BASELINE_TAXABLE_PROFITS_BILLIONS`, `PROFIT_SHIFTING_SEMI_ELASTICITY`, or `BASE_PER_DOLLAR_OF_RECEIPTS`.
**Does not apply** CBO's unpublished 0.85 / 0.80 loss-firm haircut.
**Holdout:** the four JCT *Options* +1pp rows (`cbo2019_opt24`, `cbo2021_opt19`, `cbo2023_opt50`, `cbo_opt64`).

## 1. Diagnosis

After PR #173 each of the four out-of-sample corporate +1pp rows reads the CBO Outlook its own *Options* volume was priced on. The leftover class mean of **40.3%** (0 of 4 within 15%) is one quantity read four times: the derived identity reaches **80.8%** of the vintage's average `receipts / τ` base, where JCT reaches 52.6–57.1% on the three non-COVID vintages.

Channels considered and not taken:

| Channel | Finding | Action |
|---|---|---|
| Receipts vintage | Closed by PR #173. | Untouched. |
| Profit-shifting semi-elasticity 0.8 | Already Heckemeyer / Tax Foundation's parameter; applying it only to an MNE share would *raise* scores. | Untouched. |
| IRC §6655 timing | JCT FY1 0.59 vs this module's 0.75 is 1–2% of the ten-year. | Untouched. |
| GILTI / profit shifting in the base | B5: GILTI is already inside the derived receipts identity. | Untouched. |
| CBO 0.85 / 0.80 loss-firm haircut | Unpublished; `tests/test_corporate_loss_firm_haircut.py` forbids it. | Untouched. |
| Fitting γ to JCT Option 64 (0.5785) or JCT's 0.590 | Memo §6 forbids both: they are JCT's answer read backwards. | **Held out.** |
| Constrained-tax share from Form 3800 | R5: linearly dependent; SOI excess-position tables stop at TY2010. | Not identified. Pub. 5108 Part II lines 7/11/16/17 transcribed as a *check*. |

What is left is **average-equals-marginal credit realization**. A statutory rate change unlocks (or, on a cut, locks) IRC §38(c) general-business-credit carryforwards — CBO 2018 Option 24 is the only *Options* narrative that names the channel. The receipts identity already books the *average* credit ratio. Marginal absorption exceeds that.

## 2. Calibration

γ is the ratio of the mean implied marginal share of three published **rate-only** houses that are **not** in the battery, to the mechanical +1pp share:

| House | Source | Window | Share |
|---|---|---|---|
| Tax Foundation | *Biden Budget Tax Proposals*, 21 June 2024, Table 4, −$935.8B | FY2025–2034 | 55.11% |
| PWBM | *President Biden's FY2025 Budget Proposal*, 22 May 2024, Table 1, −$1,093B | FY2025–2034 | 64.37% |
| Treasury OTA | FY2022 Green Book, the only rate-only Green Book row, −$857.817B | FY2022–2031 | 66.73% |
| **Mean** | | | **62.07%** |

Mechanical derived +1pp share (PR #121 identity, γ = 1): **80.84%**.
γ = 0.6207 / 0.8084 = **0.7679**.

Applied only in `_derived_rate_effect`. `reported` mode, the fitted $1,900B, β = 0.8, and the 4.80133 receipts-to-base ratio are untouched.

The implied extra absorption of pre-credit tax is `credit_realization_ratio × (1 − γ)` ≈ **16.4%**, between the average GBC claim rate (~12%) and the statutory 75% cap. Form 3800 Part II line 6 − line 17 is $91.2B of unused Part I credit, so the stock exists; the factor is not multiplied from that stock.

Forbidden numbers, asserted rather than described: the +1pp share is more than 1pp from 0.5785 and from 0.590; γ is more than 2pp from CBO's 0.80 haircut.

## 3. Outturn — every corporate validation case

### 3.1 Out-of-sample holdout (the `corporate` class)

| Row | Target | Before (PR #173) | After | Before err | After err |
|---|--:|--:|--:|--:|--:|
| `cbo2019_opt24_corporate_rate_1pp` | −$96.3B | −$147.8B | −$113.5B | 53.4% | **17.8%** |
| `cbo2021_opt19_corporate_rate_1pp` | −$99.3B | −$120.9B | −$92.8B | 21.8% | **6.5%** |
| `cbo2023_opt50_corporate_rate_1pp` | −$129.3B | −$183.1B | −$140.6B | 41.6% | **8.7%** |
| `cbo_opt64_corporate_rate_1pp` | −$135.7B | −$196.1B | −$150.6B | 44.5% | **11.0%** |
| **class mean** | | | | **40.3%** | **11.0%** |
| within 15% / 25% | | | | 0 / 1 | **3 / 4** |

The 2020 row is still a COVID-denominator reading (CBO projected FY2021 receipts at $122.8B against a $371.8B actual) and must be quoted with that clause.

### 3.2 Calibrated reconstructions (Decision 1, both modes)

`reported` is byte-identical. `derived` moves.

| Row | Target | Reported (unmoved) | Derived before | Derived after |
|---|--:|--:|--:|--:|
| `biden_corporate_28` (rate + GILTI) | −$1,347.0B | −$1,397.2B / 3.73% | −$1,292.6B / 4.04% | −$992.5B / **26.31%** |
| `biden_corporate_28_fy2022` (rate-only) | −$857.8B | −$1,397.2B / 62.88% | −$1,292.6B / 50.69% | −$992.5B / **15.71%** |
| `trump_corporate_15` (rate + bonus dep.) | +$673.1B | +$1,491.8B / 121.63% | +$1,632.3B / 129.57% | +$1,253.6B / **86.24%** |
| **mean abs** | | **62.75%** | **61.43%** | **42.75%** |

Derived still wins Decision 1's mean, now on two of three rows (FY2022 rate-only and the 15% cut). It loses the FY2025 rate-plus-GILTI row it is no longer close to, which is the honest reading of a rate-only identity scored against a bundled target. At the +7pp step every shipped corporate preset uses, derived −$992.5B is **inside** the four-house span −$1,349.9B to −$935.8B; reported −$1,397.2B is still outside.

`trump_corporate_15` remains a bundled run: the bonus-depreciation leg is a stated scope gap, not dropped.

## 4. What this is not

- Not a JCT fit. The four holdout rows improved because every published rate-only house sits below 80.8%; the leftover 11.0% is TF/PWBM/Treasury-rate-only vs JCT.
- Not an identification of the constrained-tax share. Form 3800 still cannot split it.
- Not a retune of β, of the $1,900B, or of 4.80133.
- Not a Decision 1 reversal. Derived still wins the mean and still sits inside the +7pp span.
- `biden_corporate_28` is reclassified `calibrated_to_target=False` on the H7 / PR #119 rule: `$1,900B` is fitted so *reported* hits this target, and the scorecard / app score *derived*. Leaving it fitted would have been a strict-readiness fail on a Poor fitted row. Reclassifying is composition of the fitted tier, named here, not a retune.

## 5. CI

`corporate` ceiling `ceil(11.01 × 1.25) = 14`, lowered 51 → 14.
Pooled floor `within-25 − 1` raised 35 → 38.
Pooled ceiling re-derives to itself at 20.
