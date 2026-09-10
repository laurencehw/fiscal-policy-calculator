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
