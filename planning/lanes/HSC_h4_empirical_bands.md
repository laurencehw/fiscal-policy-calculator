# H4 — Empirically calibrated bands, by policy class

*Wave C of `planning/HIGH_STAKES_ACCURACY.md` §3. Branch `ui/hs-c-h4-bands`, from `main` @ `2d13e60`
(PRs #140–#147 merged; H2 and H2b landed, which this lane must follow because the bands are read off
the post-H2 Tier 1 distribution).*

*Written before any file in the repository was edited. Every figure below is from one of six runs on
that commit — `python scripts/cold_holdout.py --json`, `python scripts/run_validation_dashboard.py`,
a 53-preset × 2-mode sweep through `composer._build_preset_policy` → `_scorer_for` → `score_policy`,
a **band table** that calls `credibility.get_credibility_for_result` and
`results_summary._sensitivity_band` directly for all 53 presets and the three generic shapes §1.3
tabulates, `scripts/check_readiness.py --strict` and `scripts/check_streamlit_boot.py` — or from a
`file:line` in the tree. Nothing here is recalled.*

---

## 0. What was measured first, and what it showed

Two of the three defects §3 H4 names are confirmed. **The third is not what the plan says it is, and
the correction makes the case stronger rather than weaker.**

### 0.1 The plan's three claims, checked

| Claim (§3 H4) | Verdict |
|---|---|
| The category `ConfidenceBand` uses the **mean as the median** by its own admission | **Confirmed.** `credibility.py:174-176` writes the mean into `median_abs_pct_error` with a comment saying so |
| It is computed over `summary.by_category`, which **mixes fitted bookkeeping with reconstructions** | **Confirmed**, and it is worse than "Estate: n=3, 0.0%": after H9 moved six targets the live categories read `Estate n=3 4.68% **Excellent**`, `Credits n=3 3.16% **Excellent**`, `Payroll n=4 22.31%`, `Corporate n=3 62.75%` — each a blend of fitted and unfitted rows under one rating word |
| The ETI branch **returns nothing** for every calibrated preset | **Refuted as stated.** It returns nothing *from the ETI branch*, and then falls through to `result.low_estimate` / `result.high_estimate`, which always has width. Measured across all 56 rows: **0 of 56 print no band** |

### 0.2 What the two shipped bands actually are: fixed fractions of the point estimate

The band table is the measurement the plan did not have. Across all 53 presets and the three generic
shapes, **both branches return a constant proportion of the headline, and the proportion is a
property of the module rather than of the model's accuracy**:

| Branch | Rows | Width as a share of \|headline\| |
|---|--:|---|
| `ETI 0.15–0.35`, plain `TaxPolicy` | 11 | **11.43% on every single one** — Flat Tax Reform (+\$6,239.4B) and the Medicare surcharge (−\$426.6B) get the identical ribbon |
| `ETI 0.15–0.35`, other modules | 18 | 3.8% (SALT repeal), 4.2% (enforcement ×3), 14.1% (international ×4), 19.1% (PTC repeal), 22.9% (charitable cap), 42.2–53.6% (tariffs ×5) — one constant per module's own elasticity |
| `model uncertainty band` | 27 | 38.0% (climate, pharma), **45.6%** (estate, credits, payroll), 46.8–47.1% (TCJA, AMT, PTC, step-up) |

The arithmetic for the first row is closed-form and explains why it can never carry information:
with `behavioral = −ETI × 0.5 × static`, the headline is `0.875 × static` and the ETI ±0.1 sweep has
width `0.8 × 0.125 × static = 0.1 × static`, i.e. **exactly `0.1 / 0.875 = 11.43%` of the headline for
any policy, any rate, any threshold**. It is a restatement of the elasticity, printed as if it were a
statement about accuracy.

### 0.3 The sharpest defect is one the plan does not list

`get_band_for_result` falls back to `Generic` for every preset area with no specialised validator, and
`Generic` **is the Tier 1 tier** — 26 rows, 14.73% mean. So **31 of the 56 rows print "±14.7% across 26
calibrated runs"**, and they include every tariff, pharma, international, enforcement and climate
preset — **none of which has a single Tier 1 row behind it.** The worst instance is on a shipped
surface: **💊 International Reference Pricing** prints a `±14.7%` accuracy band and a
`−$918.9B to −$683.1B` range while its own scorecard row is **701.0%** from its target.

That is the claim this lane exists to remove: an accuracy figure attached to a policy the measured
battery does not measure.

### 0.4 The live Tier 1 distribution, by class (the raw material)

`cold_holdout.py --json`, 26 rows, mean 14.7%, classes exactly as §2 reports them (6/4/4/1/3/5/2/1):

| class | n | rows (\|error\|, %) |
|---|--:|---|
| AGI-inclusive surtax | 6 | 2.9, 7.4, 18.3, 20.2, 24.8, 31.8 |
| capital gains | 4 | 10.5, 18.4, 20.3, 32.8 |
| ordinary rate change | 4 | 1.9, 14.9, 18.0, 24.5 |
| corporate | 1 | 44.5 |
| enacted-law spending | 3 | 9.8, 12.2, 18.2 |
| discretionary spending | 5 | 0.0, 1.7, 2.6, 8.1, 10.8 |
| payroll | 2 | 7.5, 8.1 |
| tax expenditure | 1 | 13.1 |

---

## 1. Mechanism

### 1.1 The band is the class's own out-of-sample error distribution

A headline's band is read off **Tier 1 only** — the 26 pre-registered, uncalibrated rows — restricted
to the **policy class** of the thing being scored, keyed by the **same routing the CI gate uses**.
Nothing fitted and nothing reconstructed enters it, because agreement in those tiers is bookkeeping
and cannot be evidence about a number the user just produced.

**Two half-widths, and coverage is measured rather than asserted.**

* **Inner half-width = the class's mean absolute percent error.** This is the statistic §2's table,
  `--max-class-mean-error`'s eight ceilings, `cold_holdout.py`'s own class block and CLAUDE.md all
  quote; using a second statistic for the shipped band would put the app a decimal away from the
  published record for no gain. At n = 1–6 a quantile is not estimable, which is the honest reason
  not to reach for one.
* **Outer half-width = the class's maximum absolute percent error** — the worst miss on the record.
  It contains 100% of the class's rows by construction, and it is the number that stops the inner
  band being read as a bound.
* **The inner band's coverage is computed from the distribution and printed**: "2 of the 6 rows fall
  inside". It is **not** ≥ 50% for every class and the copy must not imply it is — `ordinary rate
  change` covers **1 of 4**, because its mean is dragged by `illustrative_1pp_all` at 24.5% and its
  median is 16.4%. The median is carried on the object beside the mean so a reader can see the skew.

Both statistics are computed on each row's error **as reported** — rounded to one decimal, the figure
`cold_holdout.py` prints and every lane doc quotes — for the reason that script already records.

**No cap, and that is a change.** `estimate_uncertainty_dollars` clamps the half-width at
`|point_estimate|` so the interval "never implies the sign could flip". A class whose worst row is
44.5% cannot reach that clamp, so the clamp is inert on every band this lane ships and is dropped
rather than carried as dead code with a comment about a case that no longer exists.

### 1.2 The class routing: an allowlist by policy class, never by `policy_type` alone

`scripts/cold_holdout.py::classify_policy` maps a **benchmark id** to a class off its `CBOScore`
record. The app needs the same eight slugs for a **live policy object**, so the routing moves to
`fiscal_model/validation/policy_classes.py` — the script imports it and its behaviour stays
byte-identical — and gains `classify_policy_object`.

**`policy_type` alone would be wrong, and the tree says so out loud.** Four modules carry a
`policy_type` that does not describe the reform they price:

| Module | `policy_type` | Where a type-only rule would send it | Why that is false |
|---|---|---|---|
| `AMTPolicy` | `income_tax` | ordinary rate change, ±14.8% | No Tier 1 row scores an AMT reform |
| `InternationalTaxPolicy` | `corporate_tax` | corporate, ±44.5% | The one corporate row is a **statutory rate** change, not GILTI/FDII |
| `IRSEnforcementPolicy` | `income_tax` | ordinary rate change | No Tier 1 row scores an enforcement appropriation |
| `TCJAExtensionPolicy` | `income_tax` | ordinary rate change | A bundle of rates, brackets, standard deduction, CTC, AMT and QBI is not a single-rate change |

So the route is an explicit **allowlist keyed on the policy class**, with "no band" as the default:

| Policy class | Tier 1 class | Note |
|---|---|---|
| `CorporateTaxPolicy` | corporate | |
| `PayrollTaxPolicy` | payroll | |
| `CapitalGainsPolicy` | capital gains | |
| `TaxExpenditurePolicy` | tax expenditure | |
| `SpendingPolicy`, `policy_type` `discretionary_*` | discretionary spending | mandatory / transfer types get **no** band |
| `TaxPolicy` **exactly** (`type(policy) is TaxPolicy`) | ordinary rate change / AGI-inclusive surtax, on `ordinary_income_base` | the shared default from PR #142 |
| everything else | **none** | with a reason |

`type(policy) is TaxPolicy` is load-bearing: every module above subclasses `TaxPolicy` directly
(verified across all 17 `Policy` subclasses in the tree), so an `isinstance` test would hand
`TariffPolicy` the ordinary-rate band.

**A coverage test in PR #119's shape.** Every `Policy` subclass in the tree must appear either in the
route map or in an explicit `NO_TIER1_CLASS` set carrying a one-line reason, and the test fails on any
class that is in neither — because "a module nobody swept" is how four offset-sign defects got in.

### 1.3 What prints when there is no band

A policy whose class has no Tier 1 row prints **no empirical band** and says which class it is and
that the battery contains no row for it. Beside it, where the policy has a scorecard row of any tier,
that row's **own** error and tier print — read from `preset_validation.get_validation_badge`, which
already knows them and shares the one `cached_default_scorecard` materialisation. Nothing here
recomputes the scorecard.

### 1.4 The second, estimator-disagreement band

Wherever the benchmark's target is a **published range**, the range prints beside the model's figure
with containment and distance to the nearer bound — the rule H9 wrote into `docs/VALIDATION.md`.
`estimator_ranges.published_range_for` is already policy-agnostic and already tested on Pillar Two and
reciprocal tariffs; H3a renders it for corporate policies only. Four targets are live ranges:

| id | range (\$B) | shipped preset | covered today |
|---|---|---|---|
| `trump_corporate_15` | [+595.0, +673.1] | 🏢 Trump Corporate 15% | yes, by H3a |
| `pillar_two_adoption` | [−102.6, +56.5] | 🌍 Pillar Two Adoption | **no** |
| `reciprocal_tariffs` | [−1,800.0, −1,400.0] | 🏭 Reciprocal Tariffs | **no** |
| `eliminate_mortgage` | [−495.0, −367.9] | — (no shipped preset) | n/a |

H3a's corporate per-point band (55.1 / 55.9 / 64.4 / 79.5% of the vintage's average base) is
**unchanged and not re-rendered**; the general path yields to it so no corporate run prints the range
twice.

---

## 2. Files

**Owned and edited.** `fiscal_model/validation/policy_classes.py` (new), `fiscal_model/validation/credibility.py`,
`fiscal_model/validation/__init__.py` (exports), `fiscal_model/ui/confidence_band.py` (the shim),
`fiscal_model/ui/tabs/results_summary.py`, `fiscal_model/ui/tabs/bill_tracker.py` (the one caller of
the category band outside the result surfaces), `scripts/cold_holdout.py` (import only), `tests/`,
and this document.

**Not opened.** No module, no scoring path, no `app_data.py`, no `preset_ids.py`, no
`validation/scenarios.py`, no `data/capital_gains.py`, no `policies_core.py`, no `trade.py` — the
files Wave C's siblings and the label lane own. `fiscal_model/ui/estimator_ranges.py` is read and
reused; it needs no edit, and if it gets one it is additive.

---

## 3. Expected outcome — stated before the first edit

**Zero scored numbers move.** `cold_holdout.py --json`, the dashboard, the 53-preset × 2-mode sweep
with per-year paths, `check_readiness.py --strict` and both CI gate commands must be byte-identical.
Nothing this lane touches is on a scoring path.

**Every headline caption changes**, which is the deliverable. The band table after must differ from
the band table before on all 56 rows.

### 3.1 The eight bands, computed in advance

| class | n | inner ± (mean) | median | outer ± (max) | rows inside the inner band |
|---|--:|--:|--:|--:|:--|
| AGI-inclusive surtax | 6 | **17.6%** | 19.2% | **31.8%** | **2 of 6** |
| capital gains | 4 | **20.5%** | 19.4% | **32.8%** | **3 of 4** |
| ordinary rate change | 4 | **14.8%** | 16.4% | **24.5%** | **1 of 4** |
| corporate | 1 | **44.5%** | 44.5% | **44.5%** | 1 of 1 (n=1) |
| enacted-law spending | 3 | **13.4%** | 12.2% | **18.2%** | **2 of 3** |
| discretionary spending | 5 | **4.6%** | 2.6% | **10.8%** | **3 of 5** |
| payroll | 2 | **7.8%** | 7.8% | **8.1%** | **1 of 2** |
| tax expenditure | 1 | **13.1%** | 13.1% | **13.1%** | 1 of 1 (n=1) |

### 3.2 The four headlines the brief names

| Run | Today | After |
|---|---|---|
| **🏢 Biden Corporate 28%**, −\$1,397.2B | "Model accuracy in Corporate category: ±62.8% mean error across 3 calibrated runs (Approximate)"; sensitivity −\$1,477.0B to −\$1,317.4B (ETI 0.15–0.35) | band **±44.5%** → −\$2,018.9B to −\$775.5B, n=**1**, "one observation, not a distribution"; beside it the row: **calibrated reference**, 3.7% from −\$1.35T, agreement by construction; H3a's estimator range unchanged |
| **🏛️ TCJA Full Extension**, +\$4,581.9B | "±19.5% across 3 calibrated runs (Acceptable)"; sensitivity +\$3,509.7B to +\$5,654.1B ("model uncertainty band", a flat 46.8%) | **no empirical band** — the 26 Tier 1 rows contain none scoring a TCJA-style bundle — plus the row: **calibrated reference**, 0.4% from \$4,600B |
| **Warren Ultra-Millionaire Surtax**, −\$456.0B | "±14.7% across 26 calibrated runs (Limited)"; sensitivity −\$482.1B to −\$429.9B (11.43%) | band **±17.6%** → −\$536.3B to −\$375.7B, outer ±31.8% → −\$601.0B to −\$311.0B, **2 of 6** inside; row: **out-of-sample**, 24.8% from −\$350.0B |
| **Tailor, 1pp all brackets**, −\$1,195.3B | "±14.7% across 26 calibrated runs"; sensitivity −\$1,263.6B to −\$1,127.0B (11.43%) | band **±14.8%** → −\$1,372.2B to −\$1,018.4B, outer ±24.5% → −\$1,488.2B to −\$902.5B, **1 of 4** inside, median 16.4% |

### 3.3 Coverage of the new band across the app

Predicted from the routing in §1.2 against the measured preset → policy-class map, stated precisely
so it can be wrong: bands go to the **8** plain-`TaxPolicy` presets (5 on the ordinary-rate band, 3 on
the AGI-surtax band), the **4** `PayrollTaxPolicy` presets, the **4** `TaxExpenditurePolicy` presets
and the **2** `CorporateTaxPolicy` presets — **18 of 53**. The other **35** print no band and say why,
and they include every preset a journalist is most likely to quote: TCJA, the estate presets, the
credits, every tariff, every pharma row. All **3** generic shapes get a band.

That 18-of-53 is not a shortfall to be closed by widening the routing. It is the measurement: **two
thirds of the shipped catalog prices a reform this repository has never scored out of sample**, and
the plan's §2 says the same thing one tier up.

---

## 4. Falsification

1. **Containment, the brief's own test.** For every class, recomputed from the live scorecard rather
   than from a constant: **every** row of the class is inside the shipped outer half-width, and
   **exactly** the declared number of rows is inside the shipped inner half-width. A hard-coded band,
   a drifted statistic, or a band computed over a different population all fail it.
2. **Routing identity.** The band's class routing is the *same function object* the CI gate uses —
   asserted by import, not by duplication — and `classify_policy` still returns what it returned on
   `2d13e60` for all 26 Tier 1 ids.
3. **No number moves.** `cold_holdout.py --json`, the dashboard, the 53 × 2 preset sweep with per-year
   paths, `build_validation_headline.py --check` and both gate commands byte-identical. **If any
   scored figure moves, this lane has failed** — it may not open a scoring path.
4. **No band where no row.** A policy whose class has no Tier 1 row must print no band. Asserted
   directly on `TCJAExtensionPolicy`, `AMTPolicy`, `InternationalTaxPolicy`, `IRSEnforcementPolicy`,
   `TariffPolicy`, `EstateTaxPolicy`, `TaxCreditPolicy`, `DrugPricingPolicy`, `ClimateEnergyPolicy`
   and `PremiumTaxCreditPolicy` — the ten the §1.2 table sends nowhere.
5. **Coverage.** Every `Policy` subclass is named in the route map or in `NO_TIER1_CLASS`.
6. **Predicted figures.** The §3.1 and §3.2 tables are checked against the after-run. A miss is
   reported, not smoothed.

---

## 5. Out of scope

* **Any change to a scored number.** Wave C's H5 owns capital gains and H8 owns tariffs; this lane
  does not open a module.
* **Retuning a class's ceiling in `validation-dashboard.yml`.** The gate is re-derived by the
  workflow's own rule, downward only, after a wave that moves the tier. This lane moves nothing.
* **New Tier 1 rows.** Eight classes with n = 1, 1, 2, 3, 4, 4, 5, 6 is a thin basis for a band and
  saying so is the honest presentation; **widening the battery is H10**, and registering a row here to
  fatten a class would be selecting a target after seeing what the band needs.
* **The `Generic`/category vocabulary in `PRESET_AREA_TO_SCORECARD_CATEGORY`.** It still routes the
  *limitations* list and the holdout status, which are per-category facts; only the **accuracy claim**
  moves onto the Tier 1 classes.
* **`_scorecard_index`'s ~6.5 s on scored routes** (§6.2 item 39). This lane adds no second
  materialisation and removes none.

---

## 6. Outturn

*Appended after the run; see §7.*
