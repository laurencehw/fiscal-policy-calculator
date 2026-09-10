# HSB-H2b — AGI-surtax rows score on SOI's AGI column

*Follow-on lane to `planning/HIGH_STAKES_ACCURACY.md` §3 H2, Wave B. Branch
`model/hs-b-h2b-agi-column`, cut from `origin/model/hs-b-h2-base-growth` @ `fb5bbe0`
(H2, PR #144, awaiting merge), which is H1's branch (PR #142) plus H2's five commits.*

*Pre-registration written 2026-09-10, **before** any model file was opened. Every
"before" figure in §0 and §3 was measured on the branch point by the six runs named in
§0 and is reproduced from a saved artifact, not recalled.*

Sibling lanes in this wave, on disjoint files: **H3a** owns `components/results.py` and
the corporate-range block in `fiscal_model/ui/tabs/results_summary.py`; **H9** owns
`fiscal_model/validation/{benchmark_sources,scenarios,cbo_scores,target_revisions,preregistered}.py`,
`docs/VALIDATION.md` and the preset-description / `CBO_SCORE_MAP` **target text** in
`fiscal_model/app_data.py`.

---

## 0. The yardstick, frozen before anything moved

| Run | Command | Artifact |
|---|---|---|
| Tier 1 | `python scripts/cold_holdout.py --json` | `before_holdout.json` |
| The tell | `python scripts/cold_holdout.py --ordinary-base` | `before_ordinary_base.txt` |
| Dashboard | `python scripts/run_validation_dashboard.py` | `before_dashboard.txt` |
| Leave-one-out | `python scripts/run_loo.py --donor-matrix` | `before_loo.txt` |
| Preset + generic sweep | 52 presets × static/dynamic through `composer._build_preset_policy` → `_scorer_for`; three generic shapes × two base settings | `before_sweep.json` |
| The ten generic rows | each `ordinary_rate` record scored on its own vintage and window | `before_rows.json` |

`run_validation_dashboard.py` exits **1 on the branch point already** (`runtime
[degraded] Python 3.14.0`, `microdata [warn] SOI 2023`). Both are pre-existing; the
printed blocks are the signal, not the exit code.

**Tier 1 before: 26 rows, mean 15.6%, median 14.0%, 14 within 15%, 22 within 25%,
mass 405.4.** That is H2's outturn reproduced to the decimal on this branch point.

---

## 1. Mechanism

### 1.1 What is wrong, and it is a unit mismatch rather than a level

`TaxPolicy._estimate_from_irs_data` reads IRS SOI Table 1.1, whose rows are **AGI size
classes** and whose columns include **both** total AGI and total taxable income. It
selects returns by the class boundary — an **AGI** boundary — and then prices the reform
as

```
Σ  max(0, avg_TAXABLE_income(above the AGI floor) − T) × N
```

subtracting a threshold `T` from an average of a *different* quantity than the one the
threshold was applied to. On `cbo_opt46_agi_surtax_1pp_20k` that is
`$92,658 − $20,000`, where CBO's option says *"a surtax of 1 percentage point would be
imposed on **AGI** above $20,000 for single filers and $40,000 for joint filers"*
(publication 60557, report p. 56). The single-filer AGI average above that floor is
`$120,414`. Same returns, same floor, a base **1.4052×** larger.

The two columns are already both loaded — `IRSSOIData.get_filers_by_bracket` has
returned `avg_agi` and `total_agi_billions` alongside the taxable ones since before any
of these lanes — so nothing is being sourced here that was not already in the tree. What
is being fixed is which column a row reads, and the answer is transcribed from each
row's own source sentence.

### 1.2 Which rows read AGI, from each source's own words

`CBOScore.agi_inclusive_base` is `True` on **six** records. It has one meaning today:
*do not apply the ordinary-income (preferential LTCG/QDIV) correction*, which is right
for all six — every one of them reaches capital gains. It does **not** say which SOI
column supplies the base, and the six do not agree about that. Read one at a time:

| Record | Its own words | Reads |
|---|---|---|
| `cbo_opt46_agi_surtax_1pp_20k` | *"a surtax of 1 percentage point would be imposed on **AGI** above $20,000 for single filers and $40,000 for joint filers"* (CBO 60557, report p. 56) | **AGI** |
| `cbo_opt46_agi_surtax_2pp_100k` | *"a surtax of 2 percentage points would be imposed on **AGI** above $100,000 for single filers and $200,000 for joint filers"* (CBO 60557, report p. 56) | **AGI** |
| `warren_ultramillionaire_surtax_3pp` | record description: *"3 percentage point surtax on **AGI** above $2 million"*; its note: *"the surtax applies to **AGI**, which contains the preferential LTCG/QDIV portion"* | **AGI** |
| `illustrative_top_rate_5pp` | its note: *"TPC scores this on **taxable income** that includes the preferential (LTCG/QDIV) portion"* | taxable income |
| `illustrative_500k_2pp` | its note: *"TPC scores this on **taxable income** that includes the preferential (LTCG/QDIV) portion"* | taxable income |
| `medicare_surcharge_2pp` | record description: *"2 percentage point Medicare surcharge on **wage and investment income** above $400,000"*; its note: *"investment income is explicitly in the surcharge base"* | **neither** |

Three read AGI. Two state **taxable income** in as many words, and taxable income is
what they already get, so they do not move. The sixth states a base that is **neither
SOI column** — wages plus net investment income is not AGI (which also carries
proprietors' income, pensions and IRA distributions, less above-the-line deductions) and
is not taxable income (which is net of the standard or itemised deduction and of the
QBI deduction). Under this lane's binding rule — *if a source is ambiguous about AGI vs
taxable income, record the ambiguity and leave the row where it is* — it does not move.
H2's finding 4 already carried its base definition over, and this lane carries it
further rather than closing it with the nearer-looking column.

**One row's own record contradicts itself and that is recorded rather than resolved.**
`illustrative_top_rate_5pp` carries "TPC scores this on taxable income" in
`cbo_scores.py` and, since H2, "the base is also taxable income **where the surtax is
stated on AGI**" in `core.py`'s `known_limitations`. Both are repository prose about a
row whose target has **no source URL** and is labelled "Illustrative estimate", so
neither can be checked against a document. Two statements that disagree are not a
source; the row stays where it is, `core.py`'s bullet is corrected to say so, and the
row joins H2 finding 3's list of four rule-of-thumb targets that are H9's to rule on.

### 1.3 What the classification costs, stated before it is applied

The rule is not the flattering one and the arithmetic says so in two directions.

**It makes the best-scoring AGI-inclusive row five times worse.**
`warren_ultramillionaire_surtax_3pp` is at **5.2%** today and the AGI column takes it to
**24.8% over** — the single largest deterioration this lane produces, on the one row of
the three that moves whose source is a bare `taxpolicycenter.org` domain. It is moved
anyway, because its own description says AGI.

**And the three rows it leaves alone would all get worse if it moved them**, which is a
conflict of interest this lane declares rather than leaves for a reader to find:

| Left where it is | now | AGI ratio | would score | would read |
|---|--:|--:|--:|--:|
| `medicare_surcharge_2pp` | 31.8% | 1.2778 | −$522.2B | **68.4%** |
| `illustrative_top_rate_5pp` | 20.2% | 1.1775 | −$991.2B | **41.6%** |
| `illustrative_500k_2pp` | 18.3% | 1.1762 | +$556.6B | **39.2%** |

Moving all six would put the tier at **17.8% mean** against the **14.7%** §3 predicts
for moving three. The three are held on their sources' words, and the fact that holding
them is also the lower number is stated here so that the *reason* is visible and can be
overturned by a document rather than by a preference. If a page reference turns up
saying TPC's illustrative rows are AGI, or that Treasury's surcharge base is nearer AGI
than taxable income, those rows move and the tier mean rises.

### 1.4 What "AGI-inclusive" meant before, and what it means after

Before: one boolean, `TaxPolicy.ordinary_income_base`, doing one job — *is the
preferential (LTCG/QDIV) share removed from the base?* H1 made its default and its four
surfaces agree; H2 projected whatever base it produced onto the scored years.

After: that boolean is **unchanged in meaning, default and behaviour**, and a second,
orthogonal fact rides beside it — `TaxPolicy.income_measure`, `"taxable_income"`
(default, and every policy's behaviour today) or `"agi"`. The two are related by one
invariant, enforced in `__post_init__`: **`income_measure="agi"` requires
`ordinary_income_base=False`**, because AGI contains realized gains and qualified
dividends by construction, so removing the preferential share from an AGI base would
subtract income the surtax demonstrably reaches. The reverse is not an invariant:
`ordinary_income_base=False` with a taxable-income base is exactly what the two TPC
illustrative rows are, and is now sayable instead of being collapsed into the same flag.

### 1.5 The split path, and why the pooled ratio is not the answer

The two Option 46 rows carry `threshold_by_filing_status` (W7), so their base is
apportioned four ways and each status faces its own floor. The AGI switch is applied
**inside** that split — each status's own marginal AGI above its own floor — not to the
pooled aggregate afterwards. It matters, and it is why this lane measures its own
ratios rather than reusing H2 §3.1's:

| threshold | pooled ratio (H2 §3.1) | **split ratio (this lane)** |
|---|--:|--:|
| \$20,000 single / \$40,000 joint | 1.3820 | **1.4052** |
| \$100,000 single / \$200,000 joint | 1.3094 | **1.2535** |
| \$2,000,000 (no split) | 1.1864 | 1.1864 |

The two move in opposite directions, so composing published pooled ratios would have
missed both rows — the 1pp row by 1.7% and the 2pp row by 4.5%. W7's own arithmetic in
`core.py`'s `known_limitations` was on the split and lands where this lane does; H2's
§3.1 table is pooled and is a sizing, not a prediction. Neither is wrong; they answer
different questions, and this note exists so the next reader does not multiply the wrong
one.

**Table 1.1's level, Table 1.2's composition, unchanged.** W7's apportionment rule is
untouched: `get_bracket_distribution_by_status` already apportions Table 1.1's `total_agi`
by Table 1.2's AGI composition exactly as it does taxable income, and Table 1.2's AGI
column agrees with Table 1.1's *to the unit* on 18 of 19 classes (W7 finding 4), so the
AGI path inherits none of the taxable-income discrepancy that made the apportionment
necessary. A uniform per-status threshold stays byte-identical to the pooled path on the
AGI measure too, and §4 test 6 asserts it.

### 1.6 Where the classification lives, and why not on the record

The honest home for "which income measure does this record's source state" is a field on
`CBOScore` beside `agi_inclusive_base`. **`cbo_scores.py` is H9's file this wave**, so
the classification goes into `fiscal_model/validation/core.py` as `AGI_BASE_RULE` plus
`_AGI_BASE_POLICY_IDS`, each entry carrying its own source sentence — the same shape
`FILING_STATUS_THRESHOLD_RULE`, `GREEN_BOOK_DEATH_DESIGN_RULE` and
`_SPENDING_OUTLAY_CLASS` already use in that file, and the same discipline: fixed before
the code that reads it, one rule for every row, never a per-row knob. Migrating it onto
`CBOScore` when H9's file is free is an owner item in §7, not a modelling change: the
mapping and the field would carry the identical three ids.

---

## 2. Files owned

| File | Change |
|---|---|
| `fiscal_model/data/irs_soi.py` | `get_filers_by_status_thresholds(..., income_measure=)`; the pooled reader already returns both columns |
| `fiscal_model/policies_core.py` | `INCOME_MEASURE_*` constants, `TaxPolicy.income_measure` + its invariant, the AGI branch in both SOI readers, its years-2-10 cache, `income_measure_for_preset()` |
| `fiscal_model/validation/core.py` | `AGI_BASE_RULE` + `_AGI_BASE_POLICY_IDS` (with source sentences); `create_policy_from_score` sets the measure; `known_limitations` prose for the rows that move and the rows that do not |
| `fiscal_model/app_data.py` | **one key** on the Warren preset (`"income_measure": "agi"`) + its comment. **Not target text** — no description, no `CBO_SCORE_MAP` figure, no preset label is touched |
| `fiscal_model/composer/composer.py`, `api.py`, `fiscal_model/ui/policy_input_tax.py`, `ui/calculation_controller.py`, `ui/policy_execution.py`, `ui/tabs/{multi_model,policy_comparison,side_by_side}.py` | one line each, beside the existing `ordinary_income_base=` — the preset-construction sites H1 already enumerated |
| `fiscal_model/ui/tabs/results_summary.py` | **one** additive caption function + one call line (Decision 6), H2's shape |
| `tests/test_agi_income_measure.py` | new |

**Not touched, each for a reason:** `validation/{cbo_scores,scenarios,benchmark_sources,target_revisions,preregistered}.py` and `docs/VALIDATION.md` (H9's; and a row must move through the model, never through a target), `components/results.py` and H3a's corporate block in `results_summary.py`, every module policy class (none reads the generic SOI branch), `CLAUDE.md` / `README.md` / `planning/{NEXT_STEPS,MODELING_IMPROVEMENT}.md` / `docs/CHANGELOG.md`.

**The line drawn on surfaces.** A surface that reads a **source** gets the measure — the
validation manifest, the preset catalog, and Tailor's preset seed. A surface where the
**user** states the policy keeps the taxable-income base and the existing
`ordinary_income_base` control: Ask's `score_hypothetical_policy`, the API's `ScoreRequest`
and Tailor's manual form. Neither has a document to transcribe, and widening their
schemas is a UX change, not a modelling one. It is §7's carry-over, and the consequence
is stated rather than hidden: a user who types "a surtax on AGI above \$2M" into Ask
still gets a taxable-income base, exactly as today.

---

## 3. Pre-registered movements

Signed error is `(model − official)/|official|`; a positive sign is an under-prediction
of a revenue raiser. Each prediction is `before × the row's own ratio`, exact because a
ten-year total is one annual times the sum of its phase and index factors and this lane
multiplies the annual.

### 3.1 The three Tier 1 rows that move

| Row | ratio | model before | model after | official | before | after |
|---|--:|--:|--:|--:|--:|--:|
| `cbo_opt46_agi_surtax_1pp_20k` | 1.40519 | −948.591 | **−1,332.951** | −1,440.1 | +34.1% | **+7.4%** |
| `cbo_opt46_agi_surtax_2pp_100k` | 1.25352 | −862.557 | **−1,081.235** | −1,051.0 | +17.9% | **−2.9%** |
| `warren_ultramillionaire_surtax_3pp` | 1.18637 | −368.171 | **−436.788** | −350.0 | −5.2% | **−24.8%** ⚠ |

⚠ = a **registered regression**, and the only one this lane has. The 2pp row crosses its
target from under to over; the 1pp row stays under.

**The two Option 46 endpoints land at 7.4% and 2.9%, not the plan's 9.1% and 1.0%.**
Those two figures are W7 finding 1's, computed on the pre-H2 tree with W7's own hand
arithmetic; H2 rebuilt the growth term as the *scored vintage's* index rather than a
single 28.8% average, and this lane rebuilds the AGI term inside the filing-status split
rather than as a pooled ratio. Both differences are small and both are mechanism. §4
restates the falsification band on the computed endpoints.

### 3.2 The seven Tier 1 rows on the generic path that do **not** move

`cbo_opt45_all_rates_1pp` (1.9%), `cbo_opt45_top4_brackets_2pp` (14.9%),
`biden_high_income_tax` (18.0%) and `illustrative_1pp_all` (24.5%) are ordinary-bracket
rate changes and read the ordinary base; `medicare_surcharge_2pp` (31.8%),
`illustrative_top_rate_5pp` (20.2%) and `illustrative_500k_2pp` (18.3%) are §1.2's three
non-AGI AGI-inclusive rows. **All seven are predicted byte-identical**, and so are all
sixteen non-generic Tier 1 rows (capital gains, corporate, payroll, spending, Option 56).

### 3.3 The tier

| | before | predicted after |
|---|--:|--:|
| n | 26 | 26 |
| mean | 15.6% | **14.7%** |
| median | 14.0% | **12.7%** |
| within 15% | 14 | **15** |
| within 25% | 22 | **23** |
| error mass | 405.4 | **383.3** |

The CI gate (`--max-mean-error 20 --min-within-25pct 21`) passes: 14.7 < 20 and 23 ≥ 21.
`warren_ultramillionaire_surtax_3pp` at 24.8% stays inside the within-25 band by 0.2pp,
and §4 test 8 is the gate rather than that margin.

Per class, on the plan's §2 eight-row table:

| Class | n | before | predicted after |
|---|--:|--:|--:|
| AGI-inclusive surtax | 6 | 21.2% | **17.6%** |
| ordinary rate change | 4 | 14.8% | 14.8% |
| capital gains | 4 | 20.5% | 20.5% |
| corporate | 1 | 44.5% | 44.5% |
| enacted-law spending | 3 | 13.4% | 13.4% |
| discretionary spending | 5 | 4.6% | 4.6% |
| payroll | 2 | 7.8% | 7.8% |
| tax expenditure | 1 | 13.1% | 13.1% |

**The plan's §5 target for this class is ≤ 10% and this lane does not reach it**, which
is stated now rather than discovered later. Three of the six rows are held on their
sources' words (§1.2) and carry 70.3 of the class's predicted 105.4 points of mass on
their own. What is left in the class after this lane is a **base definition**
(`medicare_surcharge_2pp`, whose statutory base is neither SOI column) and **two
unsourced targets**, not a missing mechanism.

### 3.4 Shipped presets — exactly one moves

| Preset | before (static) | predicted after | Δ |
|---|--:|--:|--:|
| **Warren Ultra-Millionaire Surtax** | −384.371018 | **−456.007** | **+18.64%** |

A Decision 6 caption ships with it in this PR. Its dynamic total moves in the same
direction and is **not** predicted to scale exactly, because the revenue-feedback and
crowding-out terms are functions of the deficit path's level.

**The other 51 presets are predicted byte-identical**, static and dynamic. The two other
presets carrying `agi_inclusive_base: True` stay where they are, for reasons that are
*different from each other* and both recorded in the catalog already:

* **High-Earner Medicare Surcharge 2pp** — its own comment cites Treasury's row applying
  the surcharge to *"investment + wage income"*. §1.2: neither column.
* **Progressive Millionaire Tax** — its own comment says there is **no source document**
  and that the AGI-inclusive base is *"a design choice of the preset"* by analogy. A
  design choice by analogy with two presets that now differ from each other cannot
  select a column, and inventing one would be the tuning this lane is forbidden.

### 3.5 The three generic shapes, on the app's own scorer

Predicted **byte-identical** on both base settings — `−1,247.871 / −1,379.291` (1pp all
brackets), `−225.770 / −426.626` (2pp above \$400K), `−182.528 / −384.371` (3pp above
\$2M) — because a shape typed into Tailor's manual form, Ask or the API carries no
source and therefore no measure (§2). The Warren *preset* moves; the Warren-shaped
*hand-typed* policy does not, and that asymmetry is deliberate and is §7's carry-over.

### 3.6 No calibrated benchmark and no LOO row moves — to be verified, not assumed

`validation_shape` returns `ordinary_rate` for eleven `KNOWN_SCORES` records (H2 §3.6):
the ten of §3.1–3.2 plus the retired `top_rate_45`. Three of the eleven are in
`_AGI_BASE_POLICY_IDS`, all Tier 1. `grep -c "TaxPolicy(" fiscal_model/validation/scenarios.py`
returns **0** and so does the same grep on `validation/loo.py`. So the fitted tier
(21 @ 1.7%), the reconstruction tier (34 @ 57.9%), the held-in-place readings
(23 @ 7.7%, 27 @ 5.6%), the twelve dashboard sub-populations and the LOO suite
(18 @ 30.1%, and its donor matrix) are all predicted **byte-identical**.

The dashboard's health tripwire (`test_score`) is the shipped **default** generic probe
— `ordinary_income_base=True`, therefore taxable income — so unlike H2, this lane
predicts it **does not move**, and the whole dashboard diff is the Tier 1 summary block.

---

## 4. Falsification

The lane is **falsified** if any of these fails:

1. Either Option 46 row lands outside **±3pp** of §3.1's computed endpoints (+7.4% and
   −2.9%), or `warren_ultramillionaire_surtax_3pp` misses −24.8% by more than 3pp.
2. Any of the three rows in §3.1 misses its pre-registered ten-year total by more than
   \$0.5B.
3. **Any ordinary-base row moves at all** — `cbo_opt45_all_rates_1pp`,
   `cbo_opt45_top4_brackets_2pp`, `biden_high_income_tax`, `illustrative_1pp_all` — or
   any of §1.2's three held AGI-inclusive rows moves.
4. Any Tier 1 row outside the generic path (capital gains, corporate, payroll, spending,
   Option 56) moves by a cent.
5. `run_loo.py --donor-matrix` differs from `before_loo.txt` by a single byte, or the
   dashboard's calibrated block and twelve sub-populations differ from
   `before_dashboard.txt`.
6. A policy carrying `threshold_by_filing_status` whose declared thresholds are all equal
   to `affected_income_threshold` stops being byte-identical to the pooled path **on the
   AGI measure**.
7. Any preset outside Warren changes its static or dynamic ten-year total; or Warren
   misses −456.007 by more than \$0.05B; or any of the six generic-shape figures in §3.5
   moves.
8. `cold_holdout.py --max-mean-error 20 --min-within-25pct 21` exits non-zero.
9. `tests/test_cold_holdout.py`'s anti-leakage invariant (out-of-sample error >
   calibrated error) flips.
10. A `TaxPolicy` built with `income_measure="agi"` and `ordinary_income_base=True` is
    accepted rather than refused (§1.4's invariant), or `income_measure` defaults to
    anything but `"taxable_income"`.

**The plan's H2 condition "falsified if the tier mean rises" does not fire here** — the
mean is predicted to fall 15.6% → 14.7%. That is not this lane vindicating H2's
regression: H2's six regressions are all still on the board, and four of them are
against targets nobody published (H2 finding 3). This lane moves three rows and one of
them gets worse.

---

## 5. Explicitly out of scope

- **The three rows §1.2 holds.** `medicare_surcharge_2pp`'s statutory base (H2's own
  carry-over), and the two TPC illustrative rows whose targets carry no URL. Their
  would-be scores are published in §1.3 so the owner can see exactly what a document
  would buy.
- **Every target.** H9's ledger. §1.2's contradiction inside `illustrative_top_rate_5pp`'s
  own record is reported, not acted on.
- **Ask, the API's `ScoreRequest` and Tailor's manual form** (§2). No document to
  transcribe; widening their schemas is blue-tier.
- **Real bracket creep above a fixed nominal threshold**, and **Option 45's 2026 bracket
  revert.** Both are H2 §5's carry-overs, both untouched, and they still point in
  opposite directions on the same row.
- **The `CBOScore` field migration** (§1.6). H9's file.
- **The CI gate thresholds.** Re-derivation is a separate PR by the workflow's own rule,
  downward only.
- **Any constant.** None is introduced, none is fitted, no data file is added, and no
  SOI column is read that the loader did not already return.

---

## 6. Outturn

**Every pre-registered figure landed to the cent, and exactly three rows and one
preset moved.** The mechanism is what §1 describes; the largest miss on any
prediction is **\$0.0004B**, on the Warren preset.

### 6.1 The three Tier 1 rows, pre-registered against measured

| Row | pre-registered | measured | Δ | before | after |
|---|--:|--:|--:|--:|--:|
| `cbo_opt46_agi_surtax_1pp_20k` | −1,332.951 | **−1,332.951** | 0.000 | +34.1% | **+7.4%** |
| `cbo_opt46_agi_surtax_2pp_100k` | −1,081.235 | **−1,081.235** | 0.000 | +17.9% | **−2.9%** |
| `warren_ultramillionaire_surtax_3pp` | −436.788 | **−436.788** | 0.000 | −5.2% | **−24.8%** ⚠ |

⚠ = the lane's one registered regression, and it is the row that had the second
best error of the six AGI-inclusive cases. **No row outside these three moved**,
and none of the three failed to move. The seven other rows on the generic path
and all sixteen non-generic rows are byte-identical.

### 6.2 The tier

| | before | predicted | **measured** |
|---|--:|--:|--:|
| n | 26 | 26 | 26 |
| mean | 15.6% | 14.7% | **14.7%** |
| median | 14.0% | 12.7% | **12.6%** |
| within 15% | 14 | 15 | **15** |
| within 25% | 22 | 23 | **23** |
| error mass | 405.4 | 383.3 | **383.3** |

Per class, on the plan's §2 table, measured:

| Class | n | mean before | mean after | median before | median after | mass before | mass after |
|---|--:|--:|--:|--:|--:|--:|--:|
| AGI-inclusive surtax | 6 | 21.2% | **17.6%** | 19.2 | 19.2 | 127.5 | **105.4** |
| ordinary rate change | 4 | 14.8% | 14.8% | 16.4 | 16.4 | 59.3 | 59.3 |
| capital gains | 4 | 20.5% | 20.5% | 19.4 | 19.4 | 82.0 | 82.0 |
| corporate | 1 | 44.5% | 44.5% | — | — | 44.5 | 44.5 |
| enacted-law spending | 3 | 13.4% | 13.4% | 12.2 | 12.2 | 40.2 | 40.2 |
| discretionary spending | 5 | 4.6% | 4.6% | 2.6 | 2.6 | 23.2 | 23.2 |
| payroll | 2 | 7.8% | 7.8% | 7.8 | 7.8 | 15.6 | 15.6 |
| tax expenditure | 1 | 13.1% | 13.1% | — | — | 13.1 | 13.1 |

**The AGI-inclusive class's median did not move at all** (19.2 before and
after), which is the shape of a lane that moved three of six rows a long way in
two directions. The plan's §5 target for this class is **≤ 10%** and the
measured **17.6%** does not reach it; §6.4 finding 2 says what is left and why
none of it is a missing mechanism.

The eight largest rows are now `cbo_opt64_corporate_rate_1pp` **44.5%**,
`biden_capital_gains_39` **32.8%**, `medicare_surcharge_2pp` **31.8%**,
`warren_ultramillionaire_surtax_3pp` **24.8%**, `illustrative_1pp_all` **24.5%**,
`cbo_opt51_gains_at_death` **20.3%**, `illustrative_top_rate_5pp` **20.2%** and
`treasury_capgains_39_plus_stepup_elim` **18.4%**. **Both Option 46 rows have
left the tail** — they were its first and third rows before this lane — and the
row that replaced one of them is the one this lane moved the other way.

### 6.3 Every falsification test, and what it returned

| Test | result |
|---|---|
| 1. Both Option 46 rows within ±3pp of +7.4% / −2.9%; Warren within 3pp of −24.8% | **pass**, all three exact |
| 2. The three rows on their pre-registered totals within \$0.5B | **pass**, worst Δ \$0.000B |
| 3. No ordinary-base row moves; no held AGI-inclusive row moves | **pass**, all seven byte-identical |
| 4. No Tier 1 row outside the generic path moves | **pass**, all sixteen byte-identical |
| 5. `run_loo.py --donor-matrix` byte-identical; dashboard's calibrated block identical | **pass** — `diff` on the LOO output is **empty**, and the whole dashboard diff is **one line**, the Tier 1 summary |
| 6. A uniform per-status threshold reproduces the pooled path on the AGI measure | **pass** (test, both measures parametrised) |
| 7. No preset outside Warren moves; Warren within \$0.05B; the six generic-shape figures unmoved | **pass** — 51 of 52 byte-identical static **and** dynamic, Warren \$0.0004B from prediction, all six shapes identical |
| 8. CI gate `--max-mean-error 20 --min-within-25pct 21` | **exit 0** (14.7 < 20; 23 ≥ 21) |
| 9. Anti-leakage invariant | **pass**, out-of-sample 14.7% against fitted 1.7% |
| 10. The `income_measure` invariant and default | **pass** (three tests) |

**The dashboard's health tripwire did not move**, unlike H2's — its `test_score`
probe is the shipped default (`ordinary_income_base=True`, therefore taxable
income), so this lane cannot reach it. That was predicted in §3.6.

**Presets:** `Warren Ultra-Millionaire Surtax` **−384.371018 → −456.006646**
(+18.64% static), dynamic **−118.913564 → −180.818233**. The other 51 score to
the cent what they scored before, static and dynamic. Generic shapes on the
app's own scorer, all six unchanged: 1pp all brackets −1,247.8707 / −1,379.2906,
2pp above \$400K −225.7704 / −426.6260, 3pp above \$2M −182.5282 / −384.3710.

### 6.4 Findings

**1 — the ordinary-base tell got sharper, and its "corrected" column could not
have moved.** `cold_holdout.py --ordinary-base` reads **34.6% → 32.3%** on the
legacy (AGI-inclusive) column and **27.6% → 27.6%** on the corrected one, every
corrected figure byte-identical. That is structural rather than lucky: forcing
`ordinary_income_base=True` also forces the taxable column (§2), so the
diagnostic's corrected branch is the one place this lane provably cannot reach.
What it now shows is a *wider* gap on the three rows that moved — 8%→43%,
2%→36% and 25%→50% legacy-to-corrected — which is the tell doing its job: the
correction removes preferential income from a base that is now, explicitly, AGI.

**2 — the class target is missed by 7.6 points and none of it is a missing
mechanism.** The plan asks the AGI-inclusive class for ≤ 10% and it reads 17.6%.
Of the 105.4 points of mass left, **70.3 sit on the three rows §1.2 holds**:
`medicare_surcharge_2pp` (31.8%), whose statutory base is neither SOI column;
and `illustrative_top_rate_5pp` (20.2%) and `illustrative_500k_2pp` (18.3%),
whose targets carry no source URL. The two rows with a published option and a
transcribed base read **7.4% and 2.9%**. The class figure is now dominated by
target provenance and by one base definition, and moving the three anyway would
read **17.8% for the tier** against the measured 14.7% — the number §1.3
declared in advance.

**3 — the repository contradicted itself about `illustrative_top_rate_5pp`'s
base, and both statements are unsourced.** `cbo_scores.py` says *"TPC scores
this on taxable income that includes the preferential (LTCG/QDIV) portion"*;
`core.py`'s `known_limitations` said, since H2, *"the base is also taxable income
where the surtax is stated on AGI"*. They cannot both be right, the target has
no URL, and neither can be checked. The row is left on the taxable column and
`core.py`'s bullet now records the contradiction instead of asserting one side.
This is the fourth of H2 finding 3's four rule-of-thumb targets to turn out to
have a second problem behind the first.

**4 — composing published pooled ratios would have missed both Option 46 rows,
in opposite directions.** H2 §3.1 sized the step with pooled marginal ratios
(1.3820 at \$20,000, 1.3094 at \$100,000). Inside the filing-status split the
same quantities are **1.4052** and **1.2535** — one higher, one lower, because
the joint floor is twice the single floor and joint returns are a different
share of the two populations. Applying the pooled ratios would have put the rows
at about 9.0% and 1.5% instead of 7.4% and 2.9%. Both W7's own
`known_limitations` arithmetic and this lane are on the split; H2's table is a
sizing and says so. The general rule is the one W7 finding 3 already stated in a
different form: a ratio measured on a pooled base is not the ratio that applies
to a split one.

**5 — three captions on one preset needed a convention, and the file already
had one implicitly.** The Warren surtax now carries H1's base-flag caption, this
lane's column caption and H2's projection caption. Each reconstructs **only its
own change**, so none of the three figures is what the app printed a month ago —
and that was already true before this lane: H2 set H1's pinned "before" to
−\$182.5B, a figure the app never printed (it printed −\$134.6B pre-H2). Left
alone, H1's caption would have computed its counterfactual from an AGI total and
printed −\$216.5B, a hybrid quantity that is neither. It now divides the column
ratio out, so the two captions read as a **chain** — −\$182.5B → −\$384.4B (the
base flag) → −\$456.0B (the column) — and every figure in it is a total this
tree produces. That cost one shared helper and three lines inside H1's function;
§6.5 records it as a deviation.

**6 — the defect is a unit mismatch, and naming it that way is what made the
classification tractable.** The old branch selected returns by their **AGI** (SOI
publishes size classes on AGI) and then subtracted the threshold from an average
of **taxable income**. Read as "the base is a bit low" it invites a fudge factor;
read as "these are two different quantities" it has exactly one fix, and the fix
is per-source — which is how three of six rows moved and three did not.

**7 — the invariant found nothing, which is the outcome to want.** No shipped
surface, preset or validation record could construct `income_measure="agi"` with
`ordinary_income_base=True`. The one caller that comes close is
`cold_holdout.py --ordinary-base`, which forces the flag on every generic row in
both directions; `create_policy_from_score` therefore ties the column to the
*effective* flag rather than to the record alone, and the diagnostic keeps
working unchanged. Had the invariant been written as a silent normalisation
instead of a refusal, that interaction would have been invisible.

### 6.5 Gates

| Gate | Result |
|---|---|
| `ANTHROPIC_API_KEY= python -m pytest tests/ -q` | **3813 passed, 7 skipped** (3791 + this lane's 22) |
| `python -m ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py` (CI's own scope) | **All checks passed** |
| `python -m ruff check .` | 9 pre-existing `api.py` findings, the same nine H2 recorded as identical on `origin/main`; none introduced here and none in CI's linted scope |
| `scripts/check_readiness.py --strict` | `ready_with_warnings`, **5 pass / 5 warn / 0 fail**. Read past the Python 3.14 runtime warning, which fails first locally and is pre-existing; the assistant warn is `ANTHROPIC_API_KEY` unset in this invocation |
| `scripts/build_validation_headline.py --check` | **OK** — 75 published of 81, unchanged |
| `scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | **exit 0** |
| `scripts/run_loo.py --donor-matrix` | **byte-identical** to the branch point |
| `scripts/smoke_ask_assistant.py` | **3/3 PASS**, output pasted in §6.6 |

**Three tests outside this lane needed updating and none of them was weakened.**

1. `test_base_rule_contract.py::test_no_constructor_carries_its_own_literal_default`
   is a grep gate over the whole tree for a hard-coded base default, and it
   fired on the **text of this lane's error message**, which contained
   `ordinary_income_base=False`. The message was reworded to name the flag
   without a literal beside it. **The gate was not exempted** — carving an
   exemption into the one test that would have caught H1's original defect, to
   accommodate a string, is exactly the wrong trade.
2. `test_package_integrity.py::test_calculate_tax_policy_result_simple_mapping`
   failed because the new keyword argument was required. It now defaults to
   `DEFAULT_INCOME_MEASURE`, so a caller predating the column gets the column
   every policy used before it existed rather than a `TypeError`.
3. `test_base_rule_contract.py::test_the_caption_states_the_move_it_explains`
   pinned the Warren preset's scored total at H1's −\$384.371018B. The pinned
   *caption* figures are unchanged; a separate `SCORED_TOTALS` map now carries
   what each preset actually scores, and its comment explains the chain (finding
   5). Nothing about H1's contract was relaxed: the three constructors still
   have to agree, and they do.

**One test failure fixed itself and is worth recording.**
`test_offset_sign_contract.py::test_strict_readiness_reports_no_fitted_tier_regression`
failed in the first full run and passes now, with no change to it: at 24.8% the
Warren row crosses into **Poor**, and an *undocumented* Poor row is
strict-blocking. Adding its `known_limitations` entry — which this lane owed
anyway — cleared it. The gate behaved exactly as designed: a row may get worse,
but not silently.

The smoke test's output, pasted rather than summarised:

```
  PASS 1. CBO baseline (forces get_cbo_baseline)  (8.0s, tools: ['get_cbo_baseline'])
  PASS 2. Hypothetical scoring (forces score_hypothetical_policy)  (7.0s, tools: ['score_hypothetical_policy'])
  PASS 3. Knowledge corpus (forces search_knowledge)  (5.4s, tools: ['search_knowledge'])
Total cost across 3 call(s): $0.0434
Session summary: 6 turn(s) · $0.0434 · 26,448 tokens · cache-hit 67%
```

It was run because a shipped preset moved, and its three figures are unmoved by
this lane, which is worth stating rather than leaving implied: scenario 1 reads
the baseline, scenario 2 scores a **corporate** rate change and never reaches
the generic branch, and scenario 3 is the knowledge corpus. **The smoke test
does not cover the path this lane changed** — H2 recorded the same gap and
carried a fourth scenario over; the generic and preset paths are covered by
§6.2's sweep instead.

### 6.6 Deviations from §2

**One file outside §2's list was touched, and one function inside it was edited
beyond the "one function plus one call line" allowance.**

* `fiscal_model/ui/policy_execution.py`'s new keyword argument was made
  defaulted rather than required, after a package-integrity test showed the
  required form breaks a caller that has no opinion about the column.
* `agi_inclusive_base_caption` (H1's, in `results_summary.py`) gained three
  lines and shares a new module-level ratio helper with this lane's caption.
  Finding 5 says why: left alone it would have printed a hybrid figure that is
  neither of the two totals this tree produces. H3a's corporate-range block is a
  different function and a different call line; the merge is still an append.

Everything else in §2 was touched as planned, and H9's five validation modules,
`docs/VALIDATION.md`, `components/results.py`, `CLAUDE.md`, `README.md` and the
three planning docs were not opened.

### 6.7 Carry-overs

- **`medicare_surcharge_2pp`'s statutory base** (finding 2). Neither SOI column
  is right for wages plus net investment income, and the AGI column would take
  it to 68.4%. H2 carried this; it is still open and now sized.
- **The two TPC illustrative targets** (finding 3), plus the two other
  rule-of-thumb rows H2 finding 3 named. H9's ledger.
- **`AGI_BASE_RULE` onto `CBOScore`** (§1.6). A field beside
  `agi_inclusive_base` with the same three ids, once `cbo_scores.py` is free.
- **Ask, the API's `ScoreRequest` and Tailor's manual form** cannot express an
  AGI-stated surtax (§2). A user who types one still gets a taxable-income base.
- **Real bracket creep** and **Option 45's 2026 bracket revert**, both H2's,
  both untouched, both still pointing opposite ways on the same row.
- **The CI gate.** Re-derived by the workflow's rule on 14.7% / 23 the ceiling is
  `ceil(14.7 × 1.25) = 19 →` nearest 5 `= 20` and the floor `23 − 1 = 22`, so
  the floor could tighten 21 → 22. That is a separate PR by the workflow's own
  rule and not a lane's to take.

---

## 7. Owner items

1. **The AGI-inclusive class does not reach the plan's ≤ 10%, and the remaining
   distance is not modelling.** 70.3 of its 105.4 points sit on three rows this
   lane holds on their own sources' words: one whose statutory base is neither
   SOI column, and two whose targets have no document. The two rows with a
   published option and a transcribed base read 7.4% and 2.9%. Whether the class
   target is met by finding documents (H9) or by re-scoping it is an owner call.
2. **`warren_ultramillionaire_surtax_3pp` at 24.8%** is a registered regression
   against a secondhand TPC-range figure on a FY2021-2030 window scored here on
   FY2025-2034. It is 0.2pp inside the within-25 band. Its target is one of the
   four H2 finding 3 named; this lane took no target decision.
3. **H2 and H2b together, or separately?** H2 raised the tier mean 15.0% → 15.6%
   and this lane takes it to 14.7% — below where H2 found it — with 15 within 15%
   and 23 within 25%, both better than either branch point. The plan's H2
   falsification condition ("the tier mean rises") is satisfied by the pair and
   not by H2 alone, which is the sequencing question H2's own §7 item 1 put to
   the owner.
4. **Three rows would move if a document turned up**, and their figures are
   published in `core.py`'s `known_limitations` so the decision is legible:
   68.4%, 41.6% and 39.2%. If any of those documents is found and says AGI, the
   tier mean rises and the classification was still right.
