# HSB-H2 — Grow the generic base on the scored vintage

*Lane of `planning/HIGH_STAKES_ACCURACY.md` §3 H2, Wave B. Branch
`model/hs-b-h2-base-growth`, cut from `origin/model/hs-a-h1-base-rule` @ `fdb9f8b` (H1,
PR #142, CI green and awaiting the owner's merge), which is `main` @ `8964cb1` plus H1's
seven commits.*

*Pre-registration written 2026-09-09, **before** any model file was opened. Every "before"
figure in §0 and §3 was measured on the branch point by the four runs named in §0 and is
reproduced from a saved artifact, not recalled.*

Sibling lanes in this wave, on disjoint files: **H3a** owns `components/results.py` and the
corporate-range block in `fiscal_model/ui/tabs/results_summary.py`; **H9** owns
`fiscal_model/validation/{benchmark_sources,scenarios,cbo_scores,target_revisions}.py`,
`docs/VALIDATION.md` and the preset-description / `CBO_SCORE_MAP` target text in
`fiscal_model/app_data.py`.

---

## 0. The yardstick, frozen before anything moved

| Run | Command | Artifact |
|---|---|---|
| Tier 1 | `python scripts/cold_holdout.py --json` | `before_holdout.json` |
| Dashboard | `python scripts/run_validation_dashboard.py` | `before_dashboard.txt` |
| Leave-one-out | `python scripts/run_loo.py --donor-matrix` | `before_loo.txt` |
| Preset + generic sweep | 52 presets × static/dynamic through `composer._build_preset_policy` → `_scorer_for`; three generic shapes × three base settings | `before_sweep.json` |

`run_validation_dashboard.py` exits **1 on the branch point already** (`runtime [degraded]
Python 3.14.0`, `microdata [warn] SOI 2023`). Both are pre-existing; the printed blocks are
the signal, not the exit code.

**Tier 1 before: 26 rows, mean 15.03%, median 10.65%, 17 within 15%, 22 within 25%, mass
390.7.**

**The condition this lane was told to confirm first holds: the generic path is flat.**
`yr1 == yr10` to the cent on all three shapes and all three base settings, and on all seven
generic presets:

| Shape | ordinary base | AGI-inclusive base | yr1 | yr10 | flat |
|---|--:|--:|--:|--:|:-:|
| 1pp all brackets | −920.291193 | −1,017.211911 | −92.0291 | −92.0291 | ✓ |
| 2pp above \$400K | −166.503232 | −314.632045 | −16.6503 | −16.6503 | ✓ |
| 3pp above \$2M | −134.612557 | −283.469479 | −13.4613 | −13.4613 | ✓ |

---

## 1. Mechanism

### 1.1 What is wrong

`TaxPolicy._estimate_from_irs_data` reads IRS SOI Table 1.1 for **tax year 2023** — filer
counts and average taxable income by AGI class — and returns one annual figure. The engine
then stamps that same figure on all ten scored years:
`_score_tax_policy`'s generic branch calls `estimate_static_revenue_effect(base_rev,
use_real_data)` with **no year**, where `CapitalGainsPolicy`, `TaxExpenditurePolicy`,
`PayrollTaxPolicy`, `PremiumTaxCreditPolicy` and `CorporateTaxPolicy` all take one. So a
2026-2035 question is answered with a 2023 base, and the app's own default vintage projects
nominal GDP **35.6% higher** across that window than the year the base is measured in.

Nothing is fitted here and nothing is a judgement call: it is a stale input, on the surface
the plan's §1.2 ranks 14th and 15th by who reads the number (Tailor, Ask, Build, and seven
shipped presets including the largest unvalidated figure in the app).

### 1.2 The fix — one index, read off the vintage the run is scored on

The precedent is W5-A's payroll base ("CBO's own February 2024 wage path times one
covered-earnings ratio measured on completed history") and W5-C's realizations base
(`R(t) = h · A(t)`, projected off the stock it is a flow from, no new constant). The shape
here is the simpler of the two, because only a **ratio** is needed:

```
base(t) = base(SOI tax year) × L(t) / L(SOI tax year)
```

where `L` is the **nominal income index of the baseline the run is scored on**:

* `L(start_year − 1) = base_gdp` — the level that vintage's own Table B-1 publishes for the
  year before the window opens, and the level `CBOBaseline._project_gdp` already compounds
  from;
* `L(start_year + i) = nominal_gdp[i]` — that vintage's own projected path, which is
  `real_gdp_growth[i] + inflation[i]` compounded, both transcribed from the vintage's own
  supplemental economic projections file (`VINTAGE_SOURCING` grades all three `sourced`);
* years before `start_year − 1` continue the **earliest assumed growth rate** — the rule
  `payroll.covered_earnings` and `baseline._published_corporate_receipts` already use at
  both ends of their tables, applied here to at most **two** years (TY2023 → FY2025 for the
  validation window, TY2023 → FY2025 → FY2026 for the app's).

Only ratios are used, so the FRED-anchored *level* of `base_gdp` cancels: the index is a
pure function of the vintage's own transcribed growth assumptions. **No constant is
introduced, no data file is added, and nothing fitted is read.**

The resulting index, per (vintage, window) pair actually in use:

| Vintage @ window | FY+0 | … | FY+9 | window mean |
|---|--:|--:|--:|--:|
| `cbo_feb_2024` @ 2025 (the CBO Options battery) | 1.0962 | … | 1.5438 | **1.311824** |
| `cbo_feb_2026` @ 2025 (Tier 1 rows naming no vintage) | 1.0899 | … | 1.5276 | **1.298805** |
| `cbo_feb_2026` @ 2026 (**the app**) | 1.1379 | … | 1.5948 | **1.355952** |
| `cbo_jan_2025` @ 2026 | 1.1350 | … | 1.5872 | 1.350588 |

### 1.3 Why nominal GDP and not the wage path — and why it barely matters

The quantity being projected is **taxable income reported on individual returns**, which is
wages plus proprietors' income, interest, dividends and realized gains, less deductions.
Neither candidate *is* that series. Two things decide it:

1. **Only one is available for all three vintages.** CBO's fiscal-year wages-and-salaries
   path is transcribed for **February 2024 only**
   (`data_files/payroll/covered_earnings_base.csv`), and the repository records that
   cbo.gov returns HTTP 403 to this environment and the Wayback Machine holds no snapshot
   of the January 2025 or February 2026 workbooks. Every vintage's real-GDP-growth and PCE
   inflation arrays *are* transcribed and graded `sourced`. A lane required to be
   vintage-aware has one option that does not manufacture two vintages.
2. **Substantively, wages are the narrower quantity and the base is top-weighted.** Wages
   are about 62% of AGI in aggregate and a much smaller share above \$400,000 or \$2M,
   where realized gains and business income dominate. Growing a \$2M-threshold base at the
   wage path would understate it.

**Measured, the choice is worth 0.35%.** On February 2024 / FY2025-2034, anchored on the
same CY2023 the SOI base is measured in (`NIPA_WAGES_CY2023_BILLIONS = 11,807.6`, from the
same CBO file):

| Path | first | last | window mean |
|---|--:|--:|--:|
| wages and salaries | 1.08474 | 1.54284 | **1.30719** |
| nominal GDP | 1.09621 | 1.54381 | **1.31182** |

Ratio of window means **0.99647**. The mechanism is insensitive to the fork, which is the
sensitivity §4 asks for and is reported rather than asserted.

### 1.4 What the projection implicitly does to the threshold, stated in advance

Scaling the *aggregate marginal income above a fixed nominal threshold* by an index `f` is
arithmetically identical to indexing the threshold by `f` too: if every income grows by `f`
then `Σ max(0, f·y − T) ≥ f · Σ max(0, y − T)`, with equality only when `T = 0`. So this
mechanism is the **conservative** one — it under-states the base of an *unindexed*-threshold
reform, and the gap widens with the threshold. Naming it in advance keeps "real bracket
creep above a fixed threshold" a separate, measurable carry-over rather than something this
lane silently half-did. It is **not** in scope here; closing it needs a distributional
projection of the tail, not an index.

### 1.5 The filing-status split, held still

PR #127 apportions Table **1.2**'s composition onto Table **1.1**'s totals, so a uniform
threshold is byte-identical to the pooled path. This lane grows the **totals** and touches
no composition: the index multiplies the finished annual, after
`_estimate_from_irs_data_by_status` has done its apportionment and after
`preferential_income_share` has been measured at the pooled threshold. §4 test 6 asserts
the byte-identity survives.

---

## 2. Files owned

| File | Change |
|---|---|
| `fiscal_model/baseline.py` | `BaselineProjection.base_nominal_gdp` (the level for `start_year − 1`) + read-only `nominal_income_index(year)`; `CBOBaseline.generate()` populates it |
| `fiscal_model/policies_core.py` | `TaxPolicy._soi_base_tax_year` (non-init) set where the SOI base is read; read-only `soi_base_tax_year` property |
| `fiscal_model/scoring_engine.py` | the generic `TaxPolicy` branch multiplies by the index ratio |
| `fiscal_model/ui/tabs/results_summary.py` | **one** additive caption function + one call line (Decision 6) |
| `tests/test_generic_base_growth.py` | new |

**Not touched, each for a reason:** `fiscal_model/validation/*` (H9's, and the rows must
move through the model rather than through a target), `components/results.py` and the
corporate block of `results_summary.py` (H3a), `fiscal_model/app_data.py` (H9), the
capital-gains / payroll / corporate / credits / estate / AMT / PTC / expenditure modules
(each already projects its own base; touching one would double-count), `CLAUDE.md` /
`README.md` / `planning/NEXT_STEPS.md` / `planning/MODELING_IMPROVEMENT.md` /
`docs/CHANGELOG.md`.

**On the Decision 6 caption's placement.** The brief offered attaching the caption to the
scored result so the surface renders it without editing H3a's file. There is no render path
that picks up a free-form field on `ScoringResult`, so taking that option would mean editing
`scoring_result.py` **and** `components/results.py` **and** `results_summary.py` — more
surface, not less. This lane instead adds **one new function plus one call line** in
`results_summary.py`, the identical shape H1's `agi_inclusive_base_caption` already uses in
the same file two lines above. H3a's block is a different function and a different call
line; the merge is a two-hunk append.

---

## 3. Pre-registered movements

### 3.1 The plan's two endpoints are wrong, and the reason is measured

`HIGH_STAKES_ACCURACY.md` §3 H2 pre-registers `cbo_opt46_agi_surtax_1pp_20k` **49.8% →
~9.1%** and `cbo_opt46_agi_surtax_2pp_100k` **37.4% → ~1.0%**, citing
`W7_filing_status_split.md` finding 1, and §1.3(c) attributes those endpoints to "the joint
effect of (b) and (c)" where (b) is §1.3(b), *"no preset carries `agi_inclusive_base`"*.

**That attribution does not survive reading finding 1.** W7's decomposition is three steps,
not two:

> 44.7% → 49.8% [filing-status split] → 29.4% [an AGI base where the option says AGI] →
> **9.1%** [growth]

and W7's middle step is **not** the `agi_inclusive_base` flag. That flag is already `True`
on both Option 46 records and `validation/core.py:937` has always read it. W7's middle step
is a **base definition**: SOI Table 1.1's **AGI** column in place of its **taxable income**
column. W7 says so itself, in its own "what this lane did not do":

> It did not switch the AGI-inclusive rows to an AGI base … It is a lane of its own, with
> its own pre-registration.

H1 implemented §1.3(b) — three *preset* flags — and its own falsification test was that
**zero Tier 1 rows move**, which held: `cold_holdout.py --json` is byte-identical across
H1. So the AGI-column step is in neither lane, and the plan's endpoints embed it.

The step's size is measured here so the owner can see what is left. Marginal AGI over
marginal taxable income, IRS SOI TY2023, at each row's own threshold:

| threshold | filers | avg taxable | avg AGI | marginal AGI / marginal taxable |
|--:|--:|--:|--:|--:|
| \$20,000 | 125.298M | 92,658 | 120,414 | **1.3820** |
| \$100,000 | 41.137M | 222,469 | 260,361 | **1.3094** |
| \$400,000 | 6.231M | 688,552 | 768,716 | 1.2778 |
| \$2,000,000 | 0.283M | 5,817,557 | 6,529,039 | 1.1864 |

Composing the two published steps reproduces W7's figures to a point:
`0.502 × 1.3820 × 1.3118 = 0.910` → **9.0% under** against W7's 9.1%. **Growth alone gives
34.1%.** This lane therefore pre-registers what growth alone does, and §4 restates the
falsification condition on the corrected premise.

### 3.2 The ten Tier 1 rows on the generic path

Every generic row's ten-year total is one annual times the sum of its phase factors, so the
prediction is exact: **new = old × the window mean of that row's own (vintage, window)
index**. Signed error is `(model − official)/|official|`; a positive sign is an
under-prediction of a revenue raiser.

| Row | index | model before | model after | official | before | after |
|---|--:|--:|--:|--:|--:|--:|
| `cbo_opt46_agi_surtax_1pp_20k` | 1.3118 | −723.1 | **−948.6** | −1,440.1 | +49.8% | **+34.1%** |
| `cbo_opt46_agi_surtax_2pp_100k` | 1.3118 | −657.5 | **−862.5** | −1,051.0 | +37.4% | **+17.9%** |
| `cbo_opt45_all_rates_1pp` | 1.3118 | −920.3 | **−1,207.3** | −1,185.3 | +22.4% | **−1.9%** |
| `warren_ultramillionaire_surtax_3pp` | 1.2988 | −283.5 | **−368.2** | −350.0 | +19.0% | **−5.2%** |
| `cbo_opt45_top4_brackets_2pp` | 1.3118 | −498.7 | **−654.2** | −569.5 | +12.4% | **−14.9%** ⚠ |
| `biden_high_income_tax` | 1.2988 | −223.3 | **−290.0** | −245.9 | +9.2% | **−17.9%** ⚠ |
| `illustrative_500k_2pp` | 1.2988 | +364.4 | **+473.3** | +400.0 | −8.9% | **+18.3%** ⚠ |
| `illustrative_top_rate_5pp` | 1.2988 | −648.1 | **−841.8** | −700.0 | +7.4% | **−20.3%** ⚠ |
| `illustrative_1pp_all` | 1.2988 | −920.3 | **−1,195.3** | −960.0 | +4.1% | **−24.5%** ⚠ |
| `medicare_surcharge_2pp` | 1.2988 | −314.6 | **−408.6** | −310.0 | −1.5% | **−31.8%** ⚠ |

⚠ = a **registered regression**. The plan named three (`medicare_surcharge_2pp`,
`illustrative_top_rate_5pp`, `illustrative_500k_2pp`); measured, there are **six**, and the
two the plan missed are `biden_high_income_tax` and `cbo_opt45_top4_brackets_2pp`. The
mechanism is the one the plan named — each of the six currently under-predicts by *less*
than the growth term is worth, so growth carries it across its target — and the plan simply
did not enumerate them. `illustrative_1pp_all` is the sixth and is a special case; see §3.3.

**Tier 1 after, predicted: mean 15.59%, median 14.00%, 14 within 15%, 22 within 25%,
mass 405.4.** The CI gate (`--max-mean-error 20 --min-within-25pct 21`) still passes, with
15.59 < 20 and 22 ≥ 21. **The tier mean rises by 0.56pp**, which is the plan's own
falsification condition; §4 says what to do about it.

Per class, on the plan's §2 eight-row table:

| Class | n | before | after |
|---|--:|--:|--:|
| AGI-inclusive surtax | 6 | 20.67% | **21.27%** |
| ordinary rate change | 4 | 12.03% | **14.80%** |
| capital gains | 4 | 20.5% | 20.5% (unchanged) |
| corporate | 1 | 44.5% | 44.5% |
| enacted-law spending | 3 | 13.4% | 13.4% |
| discretionary spending | 5 | 4.6% | 4.6% |
| payroll | 2 | 7.8% | 7.8% |
| tax expenditure | 1 | 13.1% | 13.1% |

### 3.3 One reform, two published targets, 23.5% apart

`illustrative_1pp_all` and `cbo_opt45_all_rates_1pp` are **the same reform** — a 1pp
increase in every ordinary bracket — and the model scores both at exactly **−920.3** today.
Their targets are **−960.0** and **−1,185.3**. After the change the model scores −1,195.3
and −1,207.3 (the small gap is the vintage: the first names none and takes February 2026,
the second names February 2024).

So the model cannot be right about both, before or after, and the change swaps which one it
agrees with. What decides it is provenance, and it is not close: `cbo_opt45_all_rates_1pp`
is CBO's own *Options for Reducing the Deficit: 2025-2034* line item on the FY2025-2034
window being scored. `illustrative_1pp_all`'s record carries **no source URL** and the note
*"Rule of thumb: 1pp ≈ \$85-100B/year"*. Three more of the ten rows are labelled
"Illustrative estimate" with no URL (`illustrative_500k_2pp`, `illustrative_top_rate_5pp`)
or a bare domain and a "secondhand provenance" note (`warren_ultramillionaire_surtax_3pp`).
**Four of the six registered regressions are rows whose targets are rules of thumb.** This
lane does not touch a target — that is H9's ledger and this lane may not open it — but the
outturn will name which rows they are, because "the tier mean rose" reads differently once
it is known that half the movement is against figures nobody published.

### 3.4 Shipped presets — every generic one moves by +35.6%

All seven route through `composer._build_preset_policy`'s plain `TaxPolicy` branch at
`DEFAULT_SCORER_START_YEAR = APP_DEFAULT_START_YEAR = 2026` on the default February 2026
vintage, so all seven take the same window-mean index **1.355952**. Static ten-year totals:

| Preset | before | after |
|---|--:|--:|
| Flat Tax Reform | +4,601.4560 | **+6,239.3537** |
| Middle Class Tax Cut | +1,029.4398 | **+1,395.8710** |
| Progressive Millionaire Tax | −648.0920 | **−878.7817** |
| Top Rate to 45% | −724.3910 | **−982.2395** |
| High-Earner Medicare Surcharge 2pp | −314.6320 | **−426.6259** |
| Warren Ultra-Millionaire Surtax | −283.4695 | **−384.3710** |
| Biden 2025 Proposal | −216.4542 | **−293.5015** |

Dynamic totals move in the same direction and are **not** predicted to scale exactly: the
revenue-feedback and crowding-out terms are functions of the deficit path's level.

**The other 45 presets are predicted byte-identical**, static and dynamic, because every one
of them is a module class that returns from `_score_growth_tax_policy_year` or from the
`TCJAExtensionPolicy` / `CapitalGainsPolicy` branches before the generic branch is reached.

### 3.5 The three generic shapes, on the app's own scorer

| Shape | before | after |
|---|--:|--:|
| 1pp all brackets | −920.291193 | **−1,247.8707** |
| 2pp above \$400K | −166.503232 | **−225.7704** |
| 3pp above \$2M | −134.612557 | **−182.5282** |

Tailor, Ask, Explore and Build return the same figure for the same specification after H1;
they move together here, which is the property H1 bought and this lane must not spend.

### 3.6 No calibrated benchmark and no LOO row moves — verified, not assumed

`validation_shape` returns `ordinary_rate` for exactly **eleven** `KNOWN_SCORES` records.
Ten are the Tier 1 rows of §3.2; the eleventh is `top_rate_45`, retired in Phase E and not a
validation target. `grep -c "TaxPolicy(" fiscal_model/validation/scenarios.py` returns
**0**, and so does the same grep on `validation/loo.py`: every calibrated scenario and every
leave-one-out derivation builds a module class. So the fitted tier (21 @ 1.7%), the
reconstruction tier (34 @ 57.9%), the held-in-place readings (23 @ 7.7%, 27 @ 5.6%) and the
LOO suite (18 @ 30.1%, and its donor matrix) are all predicted **byte-identical**.

---

## 4. Falsification

The lane is **falsified** if any of these fails:

1. Any of the ten rows in §3.2 misses its pre-registered ten-year total by more than \$0.5B.
2. `run_loo.py --donor-matrix` differs from `before_loo.txt` by a single byte.
3. The calibrated block of `run_validation_dashboard.py` — fitted, held-in-place,
   reconstruction, and all twelve sub-populations — differs from `before_dashboard.txt`.
4. Any preset outside §3.4's seven changes its static or dynamic ten-year total.
5. Any of the seven in §3.4 misses its pre-registered static total by more than \$0.05B.
6. A policy carrying `threshold_by_filing_status` whose declared thresholds are all equal to
   `affected_income_threshold` stops being byte-identical to the pooled path.
7. A `TaxPolicy` whose base was **not** read from SOI — one built with an explicit
   `annual_revenue_change_billions`, or with a caller-supplied
   `affected_taxpayers_millions`/`avg_taxable_income_in_bracket` — moves at all.
8. `cold_holdout.py --max-mean-error 20 --min-within-25pct 21` exits non-zero.
9. `tests/test_cold_holdout.py`'s anti-leakage invariant (out-of-sample error > calibrated
   error) flips.

**The plan's own tenth condition — "falsified if the tier mean rises" — will fire, and the
lane reports rather than evades it.** Its premise is §3.1's: the plan expected H1 to have
delivered the AGI-column step, and no lane did. Growth alone raises the mean 15.03% →
15.59% while taking the one row whose target is CBO's own published option on the scored
window from **+22.4% to −1.9%**. The lane therefore ships the mechanism, records the
regression row by row, and puts the merge decision to the owner in §7 rather than choosing
for them. It does **not** withhold the change and it does **not** tune anything to make the
mean fall.

---

## 5. Explicitly out of scope

- **The AGI-column base** (§3.1). It is W7's own "lane of its own", it moves six rows this
  lane has not sourced, and taking it here would make it impossible to say which of the two
  steps moved which row — the "two errors cancelling" hazard this repository keeps finding.
  Its size is measured in §3.1 so the owner can sequence it.
- **The year-indexed threshold.** Option 45's own text reverts the bracket schedule in 2026
  and a plain `TaxPolicy` scores one number ten times. Rejected by the plan; the direction
  is known (further under) and it is §6.2 item 27's third `isinstance` branch. Note that
  §1.4's real-bracket-creep term points the *other* way, so the two are not a wash and
  neither may be used to excuse the other.
- **Real bracket creep above a fixed nominal threshold** (§1.4). Named, sized in direction
  only, carried over.
- **Every module path.** Capital gains (Decision 3 untouched), payroll, corporate, credits,
  estate, AMT, PTC, expenditures, tariffs, international, pharma, enforcement, climate and
  TCJA each already project their own base; this lane's factor is applied only where
  `soi_base_tax_year` is set, which is only the generic SOI read.
- **Any target.** H9's ledger. §3.3's finding is reported, not acted on.
- **The CI gate thresholds.** Re-derivation is a separate PR by the workflow's own rule,
  downward only.

---

## 6. Outturn

**Every pre-registered figure landed, and the largest miss on any of them is
\$0.08B.** The mechanism is exactly what §1.2 describes and the prediction that
a ten-year total is one annual times the window mean of its own index held on
all twenty checked quantities.

### 6.1 The ten Tier 1 rows, pre-registered against measured

| Row | pre-registered | measured | Δ | before | after |
|---|--:|--:|--:|--:|--:|
| `cbo_opt46_agi_surtax_1pp_20k` | −948.6 | **−948.6** | 0.02 | +49.8% | **+34.1%** |
| `cbo_opt46_agi_surtax_2pp_100k` | −862.5 | **−862.6** | 0.08 | +37.4% | **+17.9%** |
| `cbo_opt45_all_rates_1pp` | −1,207.3 | **−1,207.3** | 0.03 | +22.4% | **−1.9%** |
| `warren_ultramillionaire_surtax_3pp` | −368.2 | **−368.2** | 0.01 | +19.0% | **−5.2%** |
| `cbo_opt45_top4_brackets_2pp` | −654.2 | **−654.2** | 0.01 | +12.4% | **−14.9%** ⚠ |
| `biden_high_income_tax` | −290.0 | **−290.0** | 0.02 | +9.2% | **−17.9%** ⚠ |
| `illustrative_500k_2pp` | +473.3 | **+473.2** | 0.08 | −8.9% | **+18.3%** ⚠ |
| `illustrative_top_rate_5pp` | −841.8 | **−841.7** | 0.06 | +7.4% | **−20.2%** ⚠ |
| `illustrative_1pp_all` | −1,195.3 | **−1,195.3** | 0.01 | +4.1% | **−24.5%** ⚠ |
| `medicare_surcharge_2pp` | −408.6 | **−408.6** | 0.00 | −1.5% | **−31.8%** ⚠ |

Six registered regressions, as §3.2 predicted — the plan named three of them.
**No row outside these ten moved**, and none of these ten failed to move.

### 6.2 The tier

| | before | after |
|---|--:|--:|
| n | 26 | 26 |
| mean | 15.0% | **15.6%** |
| median | 10.6% | **14.0%** |
| within 15% | 17 | **14** |
| within 25% | 22 | **22** |
| error mass | 390.7 | **405.4** |

Per class, on the plan's §2 table, measured:

| Class | n | mean before | mean after | median before | median after | mass before | mass after |
|---|--:|--:|--:|--:|--:|--:|--:|
| AGI-inclusive surtax | 6 | 20.7% | **21.2%** | 13.9% | **19.2%** | 124.0 | **127.5** |
| ordinary rate change | 4 | 12.0% | **14.8%** | 10.8% | **16.4%** | 48.1 | **59.3** |
| capital gains | 4 | 20.5% | 20.5% | 19.4% | 19.4% | 82.0 | 82.0 |
| corporate | 1 | 44.5% | 44.5% | — | — | 44.5 | 44.5 |
| enacted-law spending | 3 | 13.4% | 13.4% | 12.2% | 12.2% | 40.2 | 40.2 |
| discretionary spending | 5 | 4.6% | 4.6% | 2.6% | 2.6% | 23.2 | 23.2 |
| payroll | 2 | 7.8% | 7.8% | 7.8% | 7.8% | 15.6 | 15.6 |
| tax expenditure | 1 | 13.1% | 13.1% | — | — | 13.1 | 13.1 |

The eight largest rows are now `cbo_opt64_corporate_rate_1pp` **44.5%**,
`cbo_opt46_agi_surtax_1pp_20k` **34.1%**, `biden_capital_gains_39` **32.8%**,
`medicare_surcharge_2pp` **31.8%**, `illustrative_1pp_all` **24.5%**,
`cbo_opt51_gains_at_death` **20.3%**, `illustrative_top_rate_5pp` **20.2%** and
`treasury_capgains_39_plus_stepup_elim` **18.4%**. Corporate is the tail now;
`cbo_opt46_agi_surtax_2pp_100k` left the top eight.

### 6.3 Everything else held

| Falsification test | result |
|---|---|
| 1. Ten rows on their pre-registered totals | **pass**, worst Δ \$0.08B |
| 2. `run_loo.py --donor-matrix` byte-identical | **pass**, `diff` empty |
| 3. Dashboard's calibrated block and twelve sub-populations identical | **pass** — the whole dashboard diff is **two lines**: the health tripwire `test_score=-8.3 → -9.1` and the Tier 1 summary |
| 4. No preset outside the seven moves | **pass**, 45 of 52 byte-identical static **and** dynamic |
| 5. The seven on their pre-registered totals | **pass**, all seven at exactly ×1.355952 |
| 6. Uniform per-status thresholds byte-identical to pooled | **pass** (test) |
| 7. A caller-supplied base does not move | **pass** (two tests) |
| 8. CI gate `--max-mean-error 20 --min-within-25pct 21` | **exit 0** (15.6 < 20; 22 ≥ 21) |
| 9. Anti-leakage invariant | **pass**, out-of-sample 15.6% against fitted 1.7% |

The health tripwire is allowed to move for the same reason H1 recorded: its own
comment reserves it against a *window* change, and it is the shipped default
generic probe, which is exactly what this lane changes. Nothing asserts its
value.

Presets: the seven generic ones at **+35.60%** static apiece, every figure on
its pre-registration to four decimals (Flat Tax Reform +4,601.4560 →
**+6,239.3536**, Middle Class Tax Cut +1,029.4398 → **+1,395.8710**,
Progressive Millionaire −648.0920 → **−878.7817**, Top Rate to 45% −724.3910 →
**−982.2394**, Medicare Surcharge −314.6320 → **−426.6260**, Warren −283.4695 →
**−384.3710**, Biden 2025 −216.4542 → **−293.5015**). Dynamic totals moved
further, as predicted and not proportionally. Generic shapes on the app's own
scorer: 1pp all brackets −920.2912 → **−1,247.8707**, 2pp above \$400K
−166.5032 → **−225.7704**, 3pp above \$2M −134.6126 → **−182.5282**.

### 6.4 Findings the plan did not name

**1 — the plan's endpoints need a third step, and it is a different step from
the one the plan names.** §3.1 above, established before any file was opened
and confirmed by the outturn: 49.8% → 34.1% and 37.4% → 17.9%, not 9.1% and
1.0%. `HIGH_STAKES_ACCURACY.md` §1.3(c) attributes W7's endpoints to "(b) and
(c)", where (b) is *"no preset carries `agi_inclusive_base`"* — a preset flag
that cannot move a validation row, and H1's own falsification test was that it
did not. W7's middle step is SOI's **AGI column** in place of its
**taxable-income** column, and W7 scoped it as "a lane of its own". Its size is
measured here: marginal AGI over marginal taxable income is **1.3820** at
\$20,000 and **1.3094** at \$100,000, and carrying W7's own AGI-base figures
through this lane's index gives about **7.4%** and **2.9%** on the two rows.

**2 — the tier mean rises, which fires the plan's own falsification condition,
and the lane reports rather than evades it.** 15.03% → 15.59%. Six rows crossed
their targets because each was under-predicting by *less* than a decade of the
baseline's own nominal growth is worth. The plan named three of the six; the two
it missed are `biden_high_income_tax` and `cbo_opt45_top4_brackets_2pp`. Whether
that is a reason to hold the change is §7's owner item, not this lane's call —
what the lane may not do is tune anything to make the mean fall, and it did not.

**3 — four of the six regressions are rows whose targets are rules of thumb,
and one of them scores the same reform as a row that improved by 20 points.**
`illustrative_1pp_all` and `cbo_opt45_all_rates_1pp` are both "1pp on every
ordinary bracket" and the model scores them at −\$1,195.3B and −\$1,207.3B (the
gap is the vintage). Their targets are **−\$960.0B** and **−\$1,185.3B**, 23.5%
apart. The first record carries no source URL and the note *"Rule of thumb: 1pp
≈ \$85-100B/year"*; the second is CBO's own *Options* line item on the
FY2025-2034 window being scored. The model cannot agree with both, and the
change swaps which one it agrees with: **+4.1% → −24.5%** on the rule of thumb,
**+22.4% → −1.9%** on the published option. `illustrative_top_rate_5pp` and
`illustrative_500k_2pp` are also "Illustrative estimate" with no URL, and
`warren_ultramillionaire_surtax_3pp` carries a "secondhand provenance" note and
a bare domain. That is four of the six. It is H9's ledger to act on, not this
lane's, but "the tier mean rose" reads differently once it is known that most of
the movement is against figures nobody published.

**4 — `medicare_surcharge_2pp`'s 1.5% was measuring a cancellation.** A row
cannot be within 1.5% of a published figure on a base held three years stale for
a ten-year window unless something else is over-stating by about the same
amount. The model prices 2pp on **all** income above \$400,000 where the Green
Book's surcharge reaches the NIIT/Medicare base, and the published row is a net
of interactions the model does not build. The 31.8% is the honest reading of a
model that now prices the right decade with the wrong base definition; the 1.5%
was the two errors meeting. This is `fra_2023_discretionary_caps` and the
Option 46 2pp row again, for the third time in the battery.

**5 — the choice between CBO's wage path and nominal GDP is worth 0.35%, so the
fork the brief posed does not decide anything.** §1.3: window means 1.30719
against 1.31182 on the one vintage where both are transcribed. The reason to
choose is availability and base definition, not fit — which is the answer the
brief asked for, arrived at by measurement rather than by argument.

**6 — the projection implicitly indexes the threshold, so it is a lower bound.**
§1.4, named in advance and confirmed by the direction of the two Option 46 rows,
which stay under. Scaling the aggregate above a fixed nominal floor by `f` is
identical to indexing that floor by `f`; the real base of an unindexed-threshold
reform grows faster. Carried over.

**7 — three rows crossed into "Poor" without a `known_limitations` note and
strict readiness blocks on exactly that.** `illustrative_1pp_all`,
`illustrative_top_rate_5pp` and `medicare_surcharge_2pp`. The gate's own text
says a documented Poor entry is a *warning* — "how a documented out-of-sample
miss (kept, not tuned away) is recorded" — so the fix is the note, not an
exemption and not a retune. Readiness went `not_ready` (1 fail) →
`ready_with_warnings` (0 fail). Four rows' notes were also **stale**: two
Option 46 and two Option 45 bullets described a base "held flat at its tax
year", which this lane makes false.

**8 — one test was pinning the defect rather than the property.**
`test_split_policy_is_flat_across_the_window` asserted the path was flat, while
its own docstring said what it was for: catching a silent revert to the pooled
formula after year one. It now divides each year's factor back out and asserts
ten identical annuals remain, which fails the same way and no longer asserts
that a ten-year score must repeat one year's answer.

### 6.4b The caption was wrong on dynamic runs, in both halves (review finding)

Copilot's review of PR #144 caught a real defect and the lane had it in the
**premise**, not the arithmetic. `income_base_projection_caption` read
`result.final_deficit_effect`, which on a **dynamic** run also carries
`revenue_feedback` — a function of the deficit path's *level*, not of the static
base. The projection multiplies the static base and nothing else, so:

- the reconstruction (`Σ path / factor`) divided a quantity the factor is not
  linear in, and returned a "before" figure the policy never printed; **and**
- the "now" figure was `final_deficit_effect` while the **headline directly
  above it** is the conventional score, so the caption disagreed with the
  number it was explaining.

The second half is the worse one and neither the lane nor its tests caught it,
because every caption test ran `dynamic=False`, where the two arrays are equal
to the cent. Measured on two shipped presets:

| Preset (dynamic) | headline above | caption's "now" | caption's "before" | correct "before" |
|---|--:|--:|--:|--:|
| Warren Ultra-Millionaire Surtax | −384.37 | −118.91 | −96.42 | **−283.47** |
| Flat Tax Reform | +6,239.35 | +5,036.39 | +3,714.19 | **+4,601.46** |

So on Warren's dynamic run the caption's own headline figure was **$265.5B out,
69.1%**. Both halves now read `static_deficit_effect + behavioral_offset`. On a
static run that array **is** `final_deficit_effect`, so **no static figure moved
and no scorecard row moved** — the fix is invisible to §6.1–§6.3 and its own
test asserts that.

Three tests were added and the load-bearing one asserts its own premise first
(that the two paths genuinely differ on a dynamic run) before asserting the
caption quotes the conventional pair, and separately that the *final*-path
figure does **not** appear in the caption. A fourth property falls out and is
pinned: the caption now reads **identically static and dynamic**, which is
correct — the projection is a property of the base, not of the engine mode.

The general lesson is the one worth carrying: **a caption that explains a
headline must be computed from the same quantity as that headline**, and a
caption tested only on the default engine mode is untested on the other one.

### 6.4c The two captions are a 2×2, not a chain — and it closes to the cent

H1's caption fix landed at `3cb84a2` and both now run on the same page. It is
worth writing down what they say together, because the natural reading of the
wave — "−134.6 → −283.5 → −384.4" — is the **history**, and neither caption
prints the first figure. Each holds the *other* attribute at today's value,
which is what a counterfactual caption should do. On Warren Ultra-Millionaire
Surtax:

| | flat (TY2023) | projected |
|---|--:|--:|
| **ordinary base** | −134.6126 | **−182.5282** ← H1's counterfactual |
| **AGI-inclusive base** | **−283.4695** ← H2's counterfactual | −384.3710 ← shipped |

The wave's history is the diagonal — **−134.6126 → −283.4695 → −384.3710** —
and it is reproduced to the cent from the shipped number by two independent
quantities the two lanes own separately: `preferential_share_of_base()` =
**52.5125%** and this lane's window-mean index = **1.355952** (the flat/projected
ratio prints as its exact reciprocal, 0.737489). So H1's caption reads
**−182.5** and not −134.6, correctly: −134.6 is the pre-wave number, which is
*two* changes away from what the app prints and is therefore not the
counterfactual for either caption alone.

Both captions are byte-identical static and dynamic, and both quote the same
headline (−384.4). That is the property the review finding was about, and it
now holds on both of them.

### 6.5 Gates

| Gate | Result |
|---|---|
| `ANTHROPIC_API_KEY= python -m pytest tests/ -q` | **3779 passed, 7 skipped** (3758 + this lane's 21) |
| `ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py` (CI's own scope) | **All checks passed** |
| `ruff check .` | 9 pre-existing `api.py` findings, **identical on `origin/main`** and outside CI's linted scope; none introduced here |
| `scripts/check_readiness.py --strict` | `ready_with_warnings`, **6 pass / 4 warn / 0 fail** (was 1 fail before §6.4 finding 7's notes). Read past the Python 3.14 runtime warning, which fails first locally and is pre-existing |
| `scripts/build_validation_headline.py --check` | **OK** — 75 published of 81, unchanged |
| `scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | **exit 0** |
| `scripts/run_loo.py --donor-matrix` | **byte-identical** to the branch point |
| `cold_holdout.py --json`, re-run after §6.4b's caption fix | **every numeric and structural field identical** to this lane's own outturn; the only diff is the `known_limitations` prose §6.4 finding 7 added, and no row's `model_10yr_billions` moved |
| `scripts/smoke_ask_assistant.py` | **3/3 PASS**, \$0.0323 |

The smoke test's output, pasted rather than summarised:

```
  PASS 1. CBO baseline (forces get_cbo_baseline)  (7.6s, tools: ['get_cbo_baseline'])
  PASS 2. Hypothetical scoring (forces score_hypothetical_policy)  (7.7s, tools: ['score_hypothetical_policy'])
  PASS 3. Knowledge corpus (forces search_knowledge)  (5.2s, tools: ['search_knowledge'])
Total cost across 3 call(s): $0.0323
Session summary: 6 turn(s) · $0.0323 · 26,499 tokens · cache-hit 80%
```

Its three figures are all unmoved by this lane and that is worth stating rather
than leaving implied: scenario 1 reads the baseline (\$29.5T cumulative deficit,
103.8% debt/GDP — PR #130's figures, not this lane's), scenario 2 scores a
**corporate** rate change, which routes to `CorporateTaxPolicy` and never
reaches the generic branch, and scenario 3 is the knowledge corpus. **So the
smoke test does not cover the path this lane changed** — the generic
`score_hypothetical_policy` income-tax route is covered by §3.5's sweep instead,
and adding a fourth scenario is a blue-tier carry-over rather than something to
slip into a green-tier lane's PR.

**One file outside §2 was touched and it is `scripts/smoke_ask_assistant.py`.**
The script crashed on Windows with `UnicodeEncodeError` printing its own
`cost ≈ $x` line — *after* the billed API call, so a paid run failed on a
`print`. `sys.stdout`/`sys.stderr` are now reconfigured to UTF-8 with
`errors="replace"`. No assistant behaviour changed and the file is nobody's
lane.

### 6.6 Carry-overs

- **The AGI-column base** (finding 1). Sized here; W7's lane, still unopened.
- **Real bracket creep above a fixed nominal threshold** (finding 6).
- **Option 45's 2026 bracket revert.** Rejected by the plan, unchanged by this
  lane, and now pointing the *opposite* way to finding 6 on the same row.
- **The four rule-of-thumb targets** (finding 3) — H9.
- **`medicare_surcharge_2pp`'s base definition** (finding 4): the surcharge's
  own statutory base against "all income above \$400,000".
- **The CI gate.** Re-derived by the workflow's rule on 15.6% / 22 the ceiling
  is `ceil(15.6 × 1.25) = 20 →` nearest 5 `= 20` and the floor `22 − 1 = 21` —
  the gate it already carries. Nothing to move, and moving it is not a lane's.

---

## 7. Owner items

1. **Merge now, or hold for the AGI-column lane?** This lane ships a mechanism
   that is right on its own terms — a 2023 base was answering a 2026-2035
   question on Tailor, Ask, Build and seven presets — and it raises the tier
   mean 15.0% → 15.6% because six rows were under-predicting by less than the
   growth term is worth. The plan's own falsification condition fires, on a
   premise (§3.1) that is documented-false. The repository's precedent is to
   ship (PRs #127, #128, #131 each made rows worse by design), and the CI gate
   passes either way. **The decision is whether the two steps should land
   together**, since the AGI-column step moves the same rows the other way and
   would land the two Option 46 rows near the plan's stated endpoints.
2. **The four rule-of-thumb targets** (finding 3). `illustrative_1pp_all`,
   `illustrative_top_rate_5pp`, `illustrative_500k_2pp` and
   `warren_ultramillionaire_surtax_3pp` are Tier 1 rows whose targets carry no
   document. H9 is in this wave and owns the ledger; whether these four are
   revised, examined-and-left or retired is a target decision, and this lane
   deliberately took none of it.
3. **Three Tier 1 rows are now documented Poor outliers**, so strict readiness
   reports `ready_with_warnings` rather than `ready`. That is the gate's
   intended state for a kept out-of-sample miss, but it is a visible change in
   the readiness verdict and is flagged rather than absorbed.
4. **The Ask smoke test does not cover the generic income path** (§6.5). Its
   scoring scenario is corporate. A fourth scenario would have caught this
   lane's movement; adding one is a blue-tier change and was not made here.
