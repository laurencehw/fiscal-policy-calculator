# R4 — The statutory parameter schedule

*Lane of `planning/ROUTE_TO_8_5.md` §1 R4 (Wave F). Branch `model/r4-parameter-schedule`,
cut from `main` @ `f6a9b28` (R1 merged). Sibling lanes on disjoint files: **R5** owns
`fiscal_model/corporate.py`, **R8** owns `fiscal_model/trade.py`, a docs-sync lane owns every
`planning/` and `docs/` file this one does not create and the workflow gate values.*

*Pre-registration written 2026-09-11, **before** any model file was opened. Every "before"
figure in §0 and §3 was measured on the branch point by the four runs named in §0 and is
read back from a saved artifact, not recalled. The §3 "after" figures were produced by a
scratch prototype that reproduces the engine's generic path by hand — it reproduces today's
`cbo_opt45_top4_brackets_2pp` to the cent (−650.97 against the engine's −650.97), which is
what makes its counterfactuals predictions rather than guesses.*

---

## 0. The yardstick, frozen before anything moved

| Run | Command | Artifact |
|---|---|---|
| Tier 1 | `python scripts/cold_holdout.py --json` | `before_holdout.json` |
| Dashboard | `python scripts/run_validation_dashboard.py` | `before_dashboard.txt` |
| Leave-one-out | `python scripts/run_loo.py --donor-matrix` | `before_loo.txt` |
| Preset + generic sweep | 53 presets × static/dynamic by stable id; 11 generic `KNOWN_SCORES` rows year by year; 12 Tailor shapes | `before_sweep.json` |

**Tier 1 before: 22 rows, mean 11.6%, median 8.9%, 18 within 15%, 19 within 25%, mass 255.2.**
Class means: `discretionary_spending` 4.6 (n=5), `agi_inclusive_surtax` 5.2 (2),
`enacted_law_spending` 7.4 (3), `payroll` 7.8 (2), `ordinary_rate_change` 12.9 (4),
`tax_expenditure` 12.8 (1), `capital_gains` 18.7 (4), `corporate` 44.5 (1).

`run_validation_dashboard.py` exits **1 on the branch point already** (`runtime [degraded]
Python 3.14.0`, `microdata [warn] SOI 2023`). Both are pre-existing; the printed blocks are
the signal, not the exit code.

---

## 1. Mechanism

### 1.1 What is wrong, and the sentence that says so

`cbo_opt45_top4_brackets_2pp`'s own pre-registered note has said it since Phase B:

> *"The bracket boundary is filing-status specific and moves in 2026 when the pre-2018 rate
> schedule returns; the model holds one fixed threshold."*

PR #127 closed the first half — `threshold_by_filing_status` is built, off IRS SOI Table 1.2.
The second half stayed open because `cbo_scores.py`'s `known_limitations` said the data does
not exist: *a published post-2025 rate table*. `HIGH_STAKES_ACCURACY.md`'s rejection table
carries the same verdict, and H2 §5 lists the year-indexed threshold as out of scope for it.

**It exists.** `US-CBO/cbo-data`, `data/budget/tax_parameters/annual_cy_{2024-06,2025-01,2026-02}.csv`
(CBO publication 53724, *Tax Parameters and Effective Marginal Tax Rates*): 130/134/150
variables × CY2021–CY2036, in long format, public domain. All seven statutory rates
(`tp_rate_1..7`) and all seven bracket floors in four filing statuses
(`tp_bracket_1..7_{single,mfj,mfs,hoh}`), plus AMT exemptions and phase-outs, sixteen EITC
parameters, five CTC parameters, SALT limits, standard deductions, `tp_ss_max_earnings` and
both price indices.

And the **June 2024 vintage carries the 2026 revert in full**, which is the table the app was
told did not exist:

| CY | 2024 | 2025 | 2026 | 2027 | … | 2034 |
|---|--:|--:|--:|--:|--:|--:|
| `tp_rate_2..7` | 12/22/24/32/35/37 | 12/22/24/32/35/37 | **15/25/28/33/35/39.6** | 15/25/28/33/35/39.6 | | 15/25/28/33/35/39.6 |
| `tp_bracket_4_mfj` | 201,050 | 207,300 | **200,100** | 204,100 | | 233,950 |
| `tp_bracket_4_single` | 100,525 | 103,650 | **120,100** | 122,500 | | 140,400 |
| `tp_bracket_4_hoh` | 100,500 | 103,650 | **171,500** | 174,900 | | 200,500 |

The revert is not a uniform shift: joint floors fall 3.5% while single floors rise 15.9% and
head-of-household floors rise 65.5%, because the pre-TCJA 28% bracket sits differently against
TCJA's 24% bracket in each status. **A scalar threshold cannot express that and neither can a
scalar plus one joint amount** — which is why this lane needs PR #127's split to exist first.

### 1.2 The mechanism: `Policy.scores_by_year()`, and one unit conversion

This is §6.2 item 27's third case, and the item names the remedy: *"A third will make it a
pattern worth naming — `Policy.scores_by_year()`, say — rather than a third special case."*
So the lane builds the concept rather than a fourth `isinstance` branch:

* `Policy.scores_by_year()` on the base class, `False`;
* `TaxPolicy.scores_by_year()` → `True` when the threshold is not income-indexed;
* `CapitalGainsPolicy.scores_by_year()` → `True` **always**, converting the existing
  `isinstance(policy, CapitalGainsPolicy)` branch in `_score_tax_policy` to the general hook.
  Two implementers is what makes it a pattern; the five `isinstance` branches in
  `_score_growth_tax_policy_year` live in five modules this lane does not own and are named
  as a carry-over rather than half-converted.

**The threshold is read per year per filing status from the schedule, and then deflated into
the SOI base year's dollars.** The deflation is not a choice — it is the unit conversion the
projection H2 shipped already implies. H2 §1.4 states the identity: scaling the aggregate
marginal income above a fixed nominal threshold by an index `g` is arithmetically identical to
indexing the threshold by `g` too. So under H2 the effective year-`t` threshold is
`T_fixed · g(t)`, in year-`t` dollars. To apply a **statutory** threshold `T(t)`, also in
year-`t` dollars, against a base measured in SOI tax-year dollars:

```
base(t) = g(t) · Σ_status Σ_returns max(0, y_i − T_status(t) / g(t)) · n_i
```

with `g(t) = nominal_income_index(t) / nominal_income_index(SOI tax year)` — H2's index,
unchanged, read from the **scored vintage's own** transcribed path, and applied exactly once.
No constant is introduced and nothing fitted is read: the schedule is law and a projection of
the price index that indexes it, both published, and the index is H2's.

**The wrong variant scores better and is not taken, and this is the lane's sharpest finding.**
Applying `T(t)` directly to SOI-year incomes — a year-2031 threshold against a 2023 income —
takes `cbo_opt45_top4_brackets_2pp` to **3.61%**. The correct one takes it to **17.86%**,
worse than today's 14.31%. Measured, on the branch point:

| variant | 10-year | error |
|---|--:|--:|
| **A.** today: record floors, no schedule, no deflation | −650.97 | 14.31% |
| **B.** record floors, deflated (real bracket creep alone) | −719.35 | 26.31% |
| **C.** schedule, **not** deflated — the unit error | −590.05 | **3.61%** |
| **D.** schedule + deflated — **the mechanism** | **−671.21** | **17.86%** |

C is the shape this repository keeps finding and naming: a number that looks right because two
things are wrong. It is recorded here so that choosing D is visible as a choice.

### 1.3 What is a statutory boundary — the rule, fixed before any record was edited

```
STATUTORY_BRACKET_SCHEDULE_RULE
A record's threshold is read from CBO's tax-parameter schedule if and only if its own source
describes the boundary as a statutory ordinary-income bracket. The bracket's INDEX (1-7) is
what the record declares; the four dollar amounts per year are the schedule's. An amount the
source states in its own words - an option's "$20,000 for single filers", a Green Book's
"$400,000" - is the source's own number and stays where the source put it, however closely it
happens to sit to a bracket floor. Numeric coincidence is not evidence: $20,000 IS
tp_bracket_2_hoh in CY2033 on the June 2024 vintage, and CBO's Option 46 still means $20,000.
```

Applied, from each source's own words:

| row | source's words | verdict |
|---|---|---|
| `cbo_opt45_all_rates_1pp` | "Raise **all** tax rates on ordinary income by 1 pp" | **bracket 1** (floor $0 in every year of every vintage) |
| `cbo_opt45_top4_brackets_2pp` | "in the **four highest brackets**" | **bracket 4** (of seven) |
| `illustrative_1pp_all` | "Raise **all** tax rates on ordinary income by 1 pp" (pub. 58164, Option 13) | **bracket 1** |
| `cbo_opt46_agi_surtax_1pp_20k` | "AGI above **$20,000** for single filers and **$40,000** for joint filers" | not statutory — **unmoved** |
| `cbo_opt46_agi_surtax_2pp_100k` | "AGI above **$100,000** … **$200,000**" | not statutory — **unmoved** |
| `biden_high_income_tax` | Green Book's **$400,000 / $450,000 / $425,000 / $225,000** | not statutory — **unmoved** |

### 1.4 Which schedule vintage, and the one substitution

The schedule vintage is matched to the **scored baseline vintage**, the same discipline
`build_scorer_for_vintage()` already imposes:

| baseline vintage | schedule file | grade |
|---|---|---|
| `cbo_jan_2025` | `annual_cy_2025-01.csv` | `exact` |
| `cbo_feb_2026` (app default) | `annual_cy_2026-02.csv` | `exact` |
| `cbo_feb_2024` (the Options battery) | `annual_cy_2024-06.csv` | **`nearest_vintage`** |

`cbo-data`'s oldest `tax_parameters` vintage is June 2024; February 2024 is not among them.
R1 declined exactly this substitution for the **budget** table — *"June 2024 is a different
publication with different numbers"* — and that reasoning is kept, not overridden: what is
substituted here is a different kind of object. The **structure** (seven rates, 15/25/28/33/35/39.6
from 2026) is statute and was identical in February and June 2024; only the **indexed dollar
boundaries** are a projection, and they differ by the price index CBO assumed four months apart.

**Sized, not asserted.** The largest such gap on this lane's one moving row is CY2025, where
June 2024 projects `tp_bracket_4_mfj` = 207,300 against the IRS's later actual of 206,700
(Rev. Proc. 2024-40 §2.01), **+0.29%**. Re-scoring the whole row with CY2025 forced to the
Revenue Procedure actuals gives **−671.20 against −671.21 — one cent**. The substitution is
graded in the data rather than hidden, and it is worth $0.01B.

### 1.5 The custom threshold — and what "nominal" turns out to mean

`threshold_indexation` is a three-valued enum on `TaxPolicy`, and writing it down is half the
value of this lane, because **today's behaviour is an unnamed assumption nobody could read off
the code**:

| value | meaning | who gets it |
|---|---|---|
| `"income"` | the threshold rides the nominal-income index — today's behaviour, exactly | **default**, so every preset, every Tailor row and every unmoved validation row is byte-identical |
| `"statutory"` | the boundary is read from the schedule per year per status | the three rows §1.3 names |
| `"nominal"` | the amount is fixed in year-`t` dollars, i.e. deflated by `g(t)` | nobody today; available |

A user who types `$400,000` into Tailor is currently told a story about a threshold that
reaches **$617,000** by FY2035, because `"income"` is what the engine does and nothing said so.
`"nominal"` is the literal reading of a typed amount and is the closed form of H2 §1.4's
carry-over ("real bracket creep above a fixed nominal threshold") — worth 10.5% on
`cbo_opt45_top4_brackets_2pp` (variant B above). **The default is `"income"` and not
`"nominal"`**, deliberately: switching it would move every shipped generic preset and the whole
Tailor surface on a lane whose stated gain is expressiveness, and H2 carried that term over on
the ground that closing it properly "needs a distributional projection of the tail, not an
index". This lane makes it *reachable and measured*; it does not make it the default.

**The Tailor control is out of scope and this is a deviation from the brief, stated as one.**
`app_pages/tailor.py` and `fiscal_model/ui/share_links.py` are not among this lane's files;
adding the option to the URL contract touches the table in `CLAUDE.md` that the docs-sync lane
owns, in a wave with three parallel model lanes. The model-level option ships; the widget, the
`&index=` parameter and its `share_links` round-trip are an owner item with their shape named
in §7.

### 1.6 Held still, each for a reason

* **The preferential-income share.** Measured on the **pooled** base at the record's own
  `affected_income_threshold`, once, exactly as PR #127 left it (§2.3 of that lane: the
  capital-gains series has no filing-status dimension). Re-measuring it per year against a
  moving threshold is a second change on the same row and would make this one unreadable.
  Variant D's prototype holds it at 0.78413 for all ten years and reproduces the engine to the
  cent, which is the check that nothing else moved.
* **The record's scalar `income_threshold`.** Unchanged on all three scheduled rows. It stays
  the preferential-share anchor and the fallback, so a schedule that fails to load degrades to
  today's number rather than to zero.
* **Every target.** No `CBOScore.ten_year_cost` moves, no `preregistered.py` row is added.
* **Every module.** AMT, credits, tax expenditures and the SS wage cap all have parameters in
  this schedule; none is wired here (§5).

---

## 2. Files owned

| File | Change |
|---|---|
| `scripts/fetch_cbo_tax_parameters.py` | **new** — R1's pattern: pinned commit SHA, SHA-256 per file, `--check`, `--source-dir` |
| `fiscal_model/data_files/cbo_tax_parameters/cbo_tax_parameters.csv` | **new** — three vintages, long format, verbatim |
| `fiscal_model/data_files/cbo_tax_parameters/PROVENANCE.csv` | **new** — repo, path, SHA, SHA-256, date, row count, grade per vintage |
| `fiscal_model/cbo_tax_parameters.py` | **new** — one reader, cached, read-only |
| `fiscal_model/policies_core.py` | `Policy.scores_by_year()`; `TaxPolicy.threshold_indexation` / `threshold_bracket_index` / `threshold_schedule_vintage`; the per-year threshold path; `CapitalGainsPolicy.scores_by_year()` |
| `fiscal_model/scoring_engine.py` | the generic branch consults `scores_by_year()` and passes the deflator; the `CapitalGainsPolicy` `isinstance` for the static call is replaced by it |
| `fiscal_model/validation/core.py` | `STATUTORY_BRACKET_SCHEDULE_RULE`; `create_policy_from_score` sets the bracket index and the schedule vintage |
| `fiscal_model/validation/cbo_scores.py` | `CBOScore.statutory_bracket_index`; the three records declare it; Option 45's `known_limitations` and notes stop asserting the table does not exist |
| `fiscal_model/ui/tabs/results_summary.py` | **one** additive caption function + one call line (Decision 6) |
| `tests/test_parameter_schedule.py` | new |

**On `cbo_scores.py`.** The brief grants `fiscal_model/validation/core.py` "only for the Tier 1
rows' shape inputs and `known_limitations`". Neither lives in `core.py` — both are fields on
`CBOScore` records in `cbo_scores.py` — so the grant is read as *the validation package,
limited to those two things*, and the edit is confined to them. Reported as a clarification.

**No `.v2` preregistered row, and the precedent is PR #127's, not PR #126's.** PR #126 gave a
row a new `.v2` because a *window* changes which ten years the model's total covers — the
quantity being compared to the target. PR #127 added `income_threshold_by_filing_status` to
four existing records under a rule stated in `core.py` and created **no** new row, because a
shape refinement governed by a written rule changes how the model computes inside an unchanged
window against an unchanged target. This lane is #127's case exactly, down to the same field on
the same records, so it follows #127 and states the judgement here so an owner can overturn it.

**Not touched, each for a reason:** `fiscal_model/corporate.py` and its data (R5),
`fiscal_model/trade.py` and its data (R8), every `planning/` and `docs/` file this lane does
not create and the workflow gate values (docs-sync), `fiscal_model/baseline.py` (R1's, merged;
the schedule is reached from the policy rather than from `BaselineProjection`, so no field is
added there), `fiscal_model/app_data.py` (a preset threshold is a shipped number — see §7),
`app_pages/` and `fiscal_model/ui/share_links.py` (§1.5), `fiscal_model/amt.py`,
`credits.py`, `tax_expenditures_core.py`, `payroll.py` (§5).

---

## 3. Pre-registered movements

Every figure below is the prototype's, computed on the branch point before any model file was
opened. A band is given where the implementation could legitimately differ from the prototype
in rounding; "to the cent" is asserted where it must not differ at all.

### 3.1 The three scheduled rows

| row | bracket | before | **predicted after** | band | before err | **predicted err** |
|---|--:|--:|--:|---|--:|--:|
| `cbo_opt45_top4_brackets_2pp` | 4 | −651.0 | **−671.2** | −671.2 ± 0.5 | 14.31% | **17.86% ± 0.1** |
| `cbo_opt45_all_rates_1pp` | 1 | −1201.2 | **−1201.2** | **to the cent** | 1.35% | **1.35%** |
| `illustrative_1pp_all` | 1 | −1235.7 | **−1235.7** | **to the cent** | 14.28% | **14.28%** |

`cbo_opt45_top4_brackets_2pp` is a **registered regression** — the lane predicts the movement,
not the attainment. The plan's stated direction ("further under") is **wrong on this tree and
is corrected here**: the row over-predicts today (−651.0 against −569.5) and the mechanism
takes it *further over*, because H2 shipped the base projection after that direction was
written. The two terms point opposite ways and neither excuses the other — deflating the
threshold is worth **−68.4B** (more base, B above) and the 2026 revert is worth **+48.1B**
(less base on balance, since single floors rise 15.9% and head-of-household floors 65.5% while
joint floors fall 3.5%) — and the net is **−20.2B**, 3.55 points of error.

The two bracket-1 rows are the lane's **falsification anchor**, not filler: they take the new
code path end to end — schedule read, four per-status floors, deflation, the split base — and a
floor of $0 in every year must return today's number **to the cent**. The prototype already
returns −1201.24 against the engine's −1201.2. If either moves by a cent, the mechanism is
perturbing something it was not asked to touch.

### 3.2 The three unmoved rows, and what "unmoved" is evidence of

`cbo_opt46_agi_surtax_1pp_20k` (−1326.3), `cbo_opt46_agi_surtax_2pp_100k` (−1075.8) and
`biden_high_income_tax` (−299.8) are predicted **byte-identical**. They are the rows most
likely to be quietly swept into a schedule by an implementation that tests numeric proximity
instead of reading the source, and `$20,000 == tp_bracket_2_hoh(CY2033)` is the trap sitting
in the data waiting for it.

### 3.3 The tier

| | before | **predicted after** |
|---|--:|--:|
| n | 22 | 22 |
| mean | 11.6% | **11.8%** |
| median | 8.9% | **8.9%** |
| within 15% | 18 | **17** |
| within 25% | 19 | **19** |
| mass | 255.2 | **258.8** |
| `ordinary_rate_change` (n=4) | 12.9% | **13.8%** |

Every other class byte-identical. **The gates hold with headroom and the arithmetic is stated
so the claim is checkable**: pooled `--max-mean-error 15` against 11.8, `--min-within-25pct 19`
against 19 (17.86% is nowhere near the 25% bound), and the per-class ceiling
`ordinary_rate_change=15` against 55.36/4 = **13.84**, 1.16 points of headroom. No row crosses
into Poor — 17.86% is *Acceptable* (the band is ≤20%) — so `check_readiness.py --strict` should
not change its verdict.

### 3.4 Presets, Tailor and the calibrated tiers

**Zero presets move. Zero Tailor rows move. No Decision 6 caption is owed.** The default is
`"income"`, which is today's arithmetic, so all 53 presets × 2 modes and all 12 Tailor shapes
are predicted byte-identical. The caption function ships anyway, dormant, because the option
exists and a scored result that used it must be able to say so.

**The fitted tier (21 rows), the reconstruction tier (34) and `run_loo.py --donor-matrix` are
predicted byte-identical, and this is verified rather than assumed.** No calibrated benchmark
routes through the generic `TaxPolicy` path — every one of them is a module class — and none
declares a statutory bracket. A moved calibrated row is a §4 falsification.

**One shipped preset is a statutory boundary and is deliberately left alone**: `Top Rate to 45%`
carries $609,350, which is `tp_bracket_7_single` for CY2024 exactly. Declaring it would move a
shipped number through `fiscal_model/app_data.py`, which is not this lane's file, and its
validation row `top_rate_45` was **retired** by R2 for want of a target — so the movement could
not be scored against anything. §7 carries it.

---

## 4. Falsification

The lane is falsified, and the branch is not opened as a PR, if any of:

1. **Either bracket-1 row moves by a cent.** A $0 floor read through the schedule must be the
   $0 floor read today.
2. **`cbo_opt45_top4_brackets_2pp` lands outside −671.2 ± 0.5**, or its error outside 17.86 ± 0.1.
3. **Any of the three unmoved generic rows moves.**
4. **Any non-generic Tier 1 row moves** — the eight spending rows, four capital-gains rows, two
   payroll, one corporate, one tax expenditure.
5. **Any calibrated row, either tier, or any `run_loo.py --donor-matrix` line moves.**
6. **Any preset or Tailor row moves** while `threshold_indexation` defaults to `"income"`.
7. **A gate is passed by moving it.** The per-class ceiling, the pooled gate, the LOO ceiling
   and the anti-leakage invariant are not this lane's to touch; if `ordinary_rate_change=15`
   fails, it is reported and the sync lane re-derives it by the workflow's own rule.
8. **Any constant is fitted.** The schedule is transcribed verbatim and verified by SHA-256
   against the upstream file; if `--check` cannot reproduce the hashes, the data does not ship.

A fixed threshold and a schedule read at the same year must agree, which is test 1's general
form and is the property the implementation is built around.

---

## 5. Explicitly out of scope

* **Every other parameter in the file.** AMT exemptions and phase-outs (`amt.py` carries eleven
  Revenue Procedures from PR #106), sixteen EITC and five CTC parameters (`credits.py`), SALT
  limits by status (`tax_expenditures_core.py`), `tp_ss_max_earnings` (`payroll.py`) and CBO's
  own EMTRs are **transcribed and reachable and wired to nothing**. Each is a module this lane
  does not own, each would move rows in the calibrated tier, and taking any of them here would
  make it impossible to say which step moved which row.
* **The AGI and taxable-income path** (`revenue_detail/annual_cy_iit_*.csv`). That is R7 and it
  moves the same rows this lane touches, in both directions.
* **Real bracket creep as a default** (§1.5). Built, measured at 10.5% on the one moving row,
  not switched on.
* **Converting the five `isinstance` branches in `_score_growth_tax_policy_year`** to
  `scores_by_year()`. Item 27 asks for the concept; the concept ships with two implementers in
  the one file this lane owns. Each remaining conversion needs its module opened.
* **Any target, and the `.v2` machinery.** §2.
* **The CI gate thresholds.** Re-derivation is a separate PR by the workflow's own rule.

---

## 6. Outturn

**Every pre-registered figure landed, and the two that had to land to the cent did.**
The hand prototype reproduced the engine exactly in both directions: it matched the *before*
path to the cent before anything was written, and the engine then reproduced the prototype's
predicted *after* path to the cent, year by year, across all ten years.

### 6.1 The six generic rows, pre-registered against measured

| Row | before | predicted | **measured** | Δ | before err | predicted err | **measured err** |
|---|--:|--:|--:|--:|--:|--:|--:|
| `cbo_opt45_top4_brackets_2pp` | −650.97 | −671.2 ± 0.5 | **−671.21** | −20.24 | 14.31% | 17.86 ± 0.1 | **17.86%** |
| `cbo_opt45_all_rates_1pp` | −1201.24 | to the cent | **−1201.24** | **0.0000** | 1.35% | 1.35% | **1.35%** |
| `illustrative_1pp_all` | −1235.67 | to the cent | **−1235.67** | **0.0000** | 14.28% | 14.28% | **14.28%** |
| `cbo_opt46_agi_surtax_1pp_20k` | −1326.31 | unmoved | **−1326.31** | **0.0000** | 7.90% | — | **7.90%** |
| `cbo_opt46_agi_surtax_2pp_100k` | −1075.85 | unmoved | **−1075.85** | **0.0000** | 2.36% | — | **2.36%** |
| `biden_high_income_tax` | −299.84 | unmoved | **−299.84** | **0.0000** | 21.94% | — | **21.94%** |

The five retired or non-battery generic records in `KNOWN_SCORES` — `illustrative_500k_2pp`,
`illustrative_top_rate_5pp`, `medicare_surcharge_2pp`, `top_rate_45`,
`warren_ultramillionaire_surtax_3pp` — are byte-identical too, checked because a rule that
swept on numeric proximity would have caught `top_rate_45`'s $609,350 (see §6.4).

### 6.2 The tier

| | before | predicted | **measured** |
|---|--:|--:|--:|
| n | 22 | 22 | **22** |
| mean | 11.6% | 11.8% | **11.8%** |
| median | 8.9% | 8.9% | **8.9%** |
| within 15% | 18 | 17 | **17** |
| within 25% | 19 | 19 | **19** |
| `ordinary_rate_change` mean | 12.9% | 13.8% | **13.8%** |
| `ordinary_rate_change` mass | 51.8 | 55.36 | **55.4** |

The other seven classes are byte-identical: `capital_gains` 18.7 (n=4), `agi_inclusive_surtax`
5.2 (2), `payroll` 7.8 (2), `corporate` 44.5 (1), `discretionary_spending` 4.6 (5),
`tax_expenditure` 12.8 (1), `enacted_law_spending` 7.4 (3).

### 6.3 Everything else held

* **Presets: 0 of 53 moved**, in either engine mode, across 106 scored runs.
* **Tailor: 0 of 12 shapes moved**, including the two at bracket-boundary amounts.
* **Fitted tier: 0 of 15 rows moved.** **Reconstruction tier: 0 of 38 rows moved.**
* **`run_loo.py --donor-matrix` is byte-identical** — `diff` returns nothing.
* **`run_validation_dashboard.py` differs in exactly one line**, the Tier 1 summary.
* **No Decision 6 caption is owed**, because no shipped score moved. The caption function
  ships dormant and is tested in both engine modes, because the thing it explains is
  reachable from the model API today and from Tailor the moment §7's item 1 lands.

### 6.4 Findings the pre-registration did not name

**1. The plan's stated direction for the registered regression was backwards, and the reason
is datable.** `ROUTE_TO_8_5.md` §1 R4 and `HSB_h2_base_growth.md` §5 both say the year-indexed
threshold takes `cbo_opt45_top4_brackets_2pp` *further under*. It takes it further **over**,
because H2 shipped the base projection after that direction was written and the row crossed
its target on that step: 12.4% under became 14.9% over, and this lane takes it to 17.9% over.
The direction was true of the tree it was written about and false of the tree it was executed
on — which is an argument for measuring a band in the pre-registration rather than inheriting
one.

**2. The row moves by the *difference* of two terms the base projection created, and neither
excuses the other.** Deflating the boundary is worth **−$68.4B** and the CY2026 reversion
**+$48.1B**; the net is −$20.2B, 3.6 points. H2's §6.6 carry-over said these two point
opposite ways and that is confirmed to the dollar. What it could not say is which is larger:
deflation wins, so the schedule makes the row worse even though the reversion alone would have
improved it.

**3. The arithmetically wrong variant scores 3.61%, four times better than the correct one.**
Applying a year-`t` nominal floor to a TY2023 income — the unit error — reads 3.61% against
17.86%. It is written into the row's `known_limitations` and into `TaxPolicy`'s docstring,
because a repository that keeps finding two-errors-cancelling should record the one it
declined to introduce, and a future lane looking for three points of improvement on this row
will find this note before it finds the shortcut.

**4. The CY2025 vintage substitution is worth one cent.** Re-scoring the whole row with CY2025
forced to the Revenue Procedure's actual floors (206,700/103,350) rather than June 2024's
projection (207,300/103,650) gives **−671.20 against −671.21**. The `nearest_vintage` grade is
still carried and still printed, because the grade is about what was read and not about
whether it mattered.

**5. One shipped preset's threshold *is* a statutory boundary, and it was left alone.**
`Top Rate to 45%` carries $609,350, which is `tp_bracket_7_single` for CY2024 exactly. It is
not declared: `fiscal_model/app_data.py` is not this lane's file, declaring it would move a
shipped number, and its validation row `top_rate_45` was **retired by R2 for want of a
target**, so the movement could not be scored against anything. §7 carries it.

**6. The trap the rule exists for is real and is now a test.** `$20,000` is
`tp_bracket_2_hoh` in CY2033 on the February 2024 vintage — the exact threshold of CBO's
Option 46 alternative 1, the row a proximity rule would have swept onto a schedule its own
text never mentions. `tests/test_parameter_schedule.py::test_numeric_coincidence_is_not_evidence`
asserts the coincidence, the record's `None`, and the rule's own sentence together, so the
three cannot drift apart.

**7. The unnamed default is worth a third of the answer on an ordinary Tailor shape.** A
+2pp rate above \$400,000 on the app's own vintage and window (FY2026–2035, February 2026)
scores **−\$232.49B** under `"income"`, the default; **−\$309.86B** under `"nominal"`, which is
what a user typing "\$400,000" most plausibly means; and **−\$266.88B** under `"statutory"` at
bracket 6, whose joint floor runs \$512,450 → \$617,650 across that window. The gap between
the first two is **33.3%**, larger than every band the app prints for this class, and until
this lane nothing on the surface or in the code said which of the three was being answered.
That is the argument for the enum independently of the schedule.

**8. The SHA-256 pin was a property of the checkout, not of CBO's file, and it took a
network round-trip to find out.** The digests were first recorded from the local clone, which
`git` had checked out with Windows line endings under `core.autocrlf`. `--check --source-dir`
passed; `--check` over HTTPS **failed on all three files** with a mismatch indistinguishable
from tampering. The fix is one line — normalise CRLF to LF before hashing, on both paths — and
the lesson is the general one: *a verification that only ever runs one way has not been
verified*. Both invocations now agree on the same commit, the recorded digests are the bytes
`raw.githubusercontent.com` serves, and `test_provenance_digests_match_the_scripts_pins`
pins the data directory to the script's constants offline so the two cannot drift. The
vendored parameter CSV was **byte-identical** before and after, which is the evidence that
nothing read was ever wrong — only what was claimed about it.

**9. `estimate_static_revenue_effect` is an eleven-way override point, and the lane broke six
of them by adding one keyword-only parameter.** The first implementation carried `year` and
`threshold_deflator` on the **base** method. Every local gate this lane ran was green and CI
failed on **all four test jobs**, at the *Type-check gate (blocking) — green-core allowlist*
step (`mypy $(grep -v '^#' mypy.gate.txt …)`), which no instruction in the lane's brief named
and which this lane therefore never ran:

```
fiscal_model/tax_expenditures_core.py:1187  Signature of "estimate_static_revenue_effect"
fiscal_model/ptc.py:1055                     incompatible with supertype
fiscal_model/tcja.py:298                     "fiscal_model.policies_core.TaxPolicy"  [override]
fiscal_model/enforcement.py:91
fiscal_model/international.py:443
fiscal_model/policies_core.py:758            Argument 1 to "int": "int | None"  [arg-type]
```

Five of the six are in modules belonging to other lanes, and all six are inside
`mypy.gate.txt`'s **blocking** allowlist — so the cheap fix (widen the five overrides) was
also the one that reaches furthest into other people's files. The base signature is now
**exactly `main`'s** and the per-year entry point is a separate method beside it,
`estimate_static_revenue_effect_for_year`, which every subclass inherits and only
`CapitalGainsPolicy` overrides; both public methods delegate to a private `_estimate_static`,
so a future parameter can never change a signature anything else has to match. **None of the
five modules was opened**, and every measured figure in §6.1–§6.3 is byte-identical across
the refactor — the preset/Tailor/Tier 1 sweep, `cold_holdout --json` and the donor matrix all
compare equal.

Three tests so it cannot recur: the base signature is pinned parameter by parameter with a
message saying where to put the next one; **every `TaxPolicy` subclass in the tree is walked
and its override bound to the engine's own call**, which is PR #119's coverage-grep shape
applied to signatures rather than to methods; and the per-year method is asserted *inherited*
where it should be. The lesson generalises past this lane: **a repository whose CI has a
blocking step no lane brief mentions will keep discovering it the same way**, and the local
gate list in a lane brief should name `mypy.gate.txt` beside `ruff` and `pytest`.

**10. The schedule contains far more than this lane wired, and the count is the point.**
130–150 variables per vintage: AMT exemptions and phase-outs by status (which `amt.py`
transcribes from eleven Revenue Procedures by hand), sixteen EITC parameters, five CTC
parameters, SALT limits by status, standard deductions, `tp_ss_max_earnings`, both price
indices, and CBO's own EMTRs on labour and capital. **Two variables out of 150 are read.**
Each of the others belongs to a module with calibrated benchmarks, and wiring one here would
have made it impossible to say which step moved which row.

### 6.5 Gates

| Gate | Result |
|---|---|
| `pytest tests/ -q` | **4,176 passed, 7 skipped** on the merged tree (this lane adds 43) |
| `ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py` | **All checks passed** |
| `cold_holdout.py --max-mean-error 15 --min-within-25pct 19` | **exit 0** (11.8 against 15; 19 against 19) |
| `cold_holdout.py --max-class-mean-error …` | **exit 0** — `ordinary_rate_change` **13.84 against a ceiling of 15**, 1.16 points of headroom; the other seven unmoved |
| `check_readiness.py --strict` | **`ready_with_warnings`, 5 pass / 5 warn / 0 fail** — the same three documented Poor outliers as `main` (`repeal_ptc`, `pwbm_39_with_stepup`, `eliminate_mortgage`). 17.86% is *Acceptable*; no row crossed into Poor and no exemption was added |
| `build_validation_headline.py --check` | **exit 0** — 73 published of 77, unchanged |
| `fetch_cbo_tax_parameters.py --check` | **exit 0** over HTTPS **and** `--source-dir`, which is finding 8 — three SHA-256s verified, all statutory identities hold |
| **`mypy $(grep -v '^#' mypy.gate.txt …)`** (blocking, green-core allowlist) | **`Success: no issues found in 18 source files`** — and it is finding 9: this lane failed it on four CI jobs before the fix, having never run it |
| `mypy fiscal_model` (non-blocking) | 241 errors in 38 files, **none of them in this lane's files**; 242/39 before, the one that left being this lane's own |
| `smoke_ask_assistant.py` | see §6.6 |

**No gate value was touched.** The registered regression did not break the per-class ceiling,
so there is nothing for the sync lane to re-derive; had it, the instruction was to report it
rather than move it.

## 7. Owner items

1. **The Tailor control, which is this lane's one declared deviation from its brief.** The
   brief asked for the option on Tailor; the model-level option ships and the widget does not,
   because `app_pages/tailor.py` and `fiscal_model/ui/share_links.py` are not among this
   lane's files and the URL contract's table lives in a file the docs-sync lane owns, in a
   wave with three parallel model lanes. The shape is: one `st.radio` or `st.selectbox` over
   `THRESHOLD_INDEXATIONS` defaulting to `"income"`, one `&index=` parameter in
   `share_links.encode_tailor_params` / `decode_tailor_params`, one row in `CLAUDE.md`'s URL
   table, and the frozen-link proxy picks it up for free because it renders every input.
   **Nothing shipped moves until it lands**, so it is additive.
2. **`Top Rate to 45%`'s threshold** (finding 5). $609,350 is a statutory boundary and the
   preset does not say so. Declaring it is an `app_data.py` edit that moves a shipped number
   with no scorecard row to check it, since `top_rate_45` is retired. Both halves are the
   owner's.
3. **The other 148 variables** (finding 10). AMT's eleven hand-transcribed Revenue Procedures
   are the sharpest candidate — the same statute, published by CBO, on three vintages, in one
   file — but `amt.py`'s benchmarks are calibrated and a rewiring there is a lane with its own
   pre-registration.
4. **Converting the five remaining `isinstance` branches** in `_score_growth_tax_policy_year`
   to `scores_by_year()`. The concept exists with two implementers; the rest is mechanical and
   needs five modules opened. It changes no number by construction, which makes it a good
   candidate for a lane that wants a falsification test it can actually fail.
5. **Real bracket creep as a default** (§1.5). `"nominal"` is built and measured at 10.5% on
   the one moving row. Making it the default is a defensible reading of what a typed threshold
   means and would move every generic preset and the whole Tailor surface, so it is a
   deliberate product decision with a Decision 6 caption attached, not a tidy-up.
