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

*(appended after implementation)*

---

## 7. Owner items

*(appended after implementation)*
