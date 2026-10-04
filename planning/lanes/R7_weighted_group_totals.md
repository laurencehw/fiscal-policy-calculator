# R7 — Weighted group totals on the tax-unit microsim path

**Lane** R7. **Owns** `fiscal_model/distribution_grouping.py`,
`fiscal_model/distribution_engine.py`, `fiscal_model/validation/distributional_validation.py`
(§6), their tests, and this file. **Not opened for editing:** `ui/**`, `assistant/**`,
`multi_model.py`, `distribution_households.py`, `distribution_effects.py`,
`validation/cbo_distributions.py`.

Sections 0–4 were written **before** any shipped file was edited. Every "after" figure in §3
comes from `scratchpad/r7_sweep.py predicted`, which monkeypatches the two functions this lane
changes with weighted reimplementations defined in the scratch script and runs every microsim
distributional surface; `r7_sweep.py current` is the same sweep on the unmodified tree. The
outturn (§5) is the same sweep re-run on the edited tree with no patches, so a prediction that
matches is a prediction, not a reading.

---

## 0. The defect, reproduced

`create_groups_from_microdata` (`distribution_grouping.py:216-260`) weights the return count
and sums the money **unweighted**:

```python
num_returns = int(group_weights.sum())                       # weighted
total_agi=group_data["agi"].sum() / 1e9                      # unweighted
total_taxable_income=group_data["taxable_income"].sum() / 1e9
baseline_tax=group_data["final_tax"].sum() / 1e9
```

Two tax units, AGI $200,000 and $250,000, weights 1 and 1,000:

| | Shipped | Correct (weighted) |
|---|---:|---:|
| `num_returns` | 1,001 | 1,001 |
| `total_agi` ($B) | **0.00045** | 0.25020 |
| `avg_agi` ($) | **449.55** | 249,950.05 |
| `effective_tax_rate` | 0.1667 | 0.1800 |

On the shipped microdata (78,727 CPS units, mean weight 2,427.6) the error is a factor of
roughly the mean weight: the "Top Quintile" reports an average AGI of **$132** where the
weighted figure is **$309,920**.

The same branch of `DistributionalEngine.analyze_policy_microsim` (the tax-unit path;
`distribution_engine.py:271-336`) weights the dollar change but not the rest:

| Field | Shipped computation | Defect |
|---|---|---|
| `tax_change_total`, `tax_change_avg` | `Σ w·Δ` | none — weighted |
| `tax_change_pct_income` | weighted avg ÷ **unweighted** `mean(agi − tax)` | denominator unweighted |
| `pct_with_increase` / `_decrease` / `_unchanged` | **row counts** | unweighted |
| `baseline_etr`, `new_etr`, `etr_change` | `Σ tax / Σ agi` over **rows** | unweighted |

**The brief's second claim is refuted as located**: `fiscal_model/microsim/engine.py` computes
no `pct_with_*` at all (it returns per-record tax). The unweighted `pct_with_*` is in
`distribution_engine.py`'s tax-unit branch. The household branch (`_analyze_households`) and
`build_household_groups` already weight everything by `household_weight`, and are the pattern
the fix copies.

## 1. Consumers, traced

Every reader of the six affected fields, found by grep over the tree and followed to a surface:

| Surface | Reads | Moves? |
|---|---|---|
| **7 CBO/JCT distributional benchmarks** (`compare_distribution`) — dashboard, `/benchmarks`, `/summary`, readiness | `share_of_total_change`, `tax_change_avg` only | **No.** Both are already weighted, and group *membership* is by AGI threshold, not by group totals. Only `jct_salt_repeal_2024` reaches the tax-unit microsim at all; ARP is household, the other five synthetic. |
| App Distribution tab (`ui/tabs/distribution_analysis.py`) via `format_distribution_table(style="tpc")` | `% of Income`, `% Tax Increase`, `% Tax Decrease`, `ETR Change (ppts)`; `Returns (M)` | Yes, the four named columns; returns no |
| Same tab, summary metrics via `generate_winners_losers_summary` | `num_returns × pct_with_*` | Yes (the per-group percentages are unweighted) |
| Same tab, `render_winners_losers_callout` → `build_winners_losers` | `tax_change_pct_income` (progressive/regressive headline) | Values yes; **headline direction predicted unchanged in all 45 tables** |
| `models/comparison.py` multi-model pilot (`analyze_policy_microsim(...).to_dataframe()`) | every `to_dataframe` column incl. `Avg AGI`, `Baseline ETR`, `New ETR` | Yes |
| `composer/progressivity.py` → policy tags, Build composer | `tax_change_total` only | **No** |
| `api.py` | no `analyze_policy` call; only benchmark comparisons | **No** |
| `IncomeGroup.avg_agi` / `effective_tax_rate` | group totals | Yes (synthetic path's groups are SOI aggregates, already weighted, untouched) |

Nothing in `cold_holdout.py`, `run_loo.py` or any revenue score reads a distributional table.

## 2. Mechanism

Weight every money total and every share by `weight`, exactly as the household branch already
weights by `household_weight`:

- group totals: `Σ w·agi`, `Σ w·taxable_income`, `Σ w·final_tax`;
- `tax_change_pct_income = (Σ w·Δ / Σ w) ÷ (Σ w·max(agi − tax, 1) / Σ w) × 100`;
- `pct_with_increase = Σ_{Δ>0.01} w / Σ w × 100` (likewise decrease, unchanged);
- `baseline_etr = Σ w·tax / Σ w·agi`, `new_etr = Σ w·reform_tax / Σ w·agi`.

No constant, threshold, target or benchmark is touched. A frame without a `weight` column
behaves as weight 1, which reproduces today's arithmetic exactly (tested).

## 3. Pre-registered predictions

**Sweep scope.** The 7 benchmarks through `run_full_cbo_jct_validation(default_model_runner)`;
every preset that reaches the microsim (9 of 52: Biden 2025 Proposal, Flat Tax Reform,
High-Earner Medicare Surcharge 2pp, Middle Class Tax Cut, Progressive Millionaire Tax, Top Rate
to 45%, Warren Ultra-Millionaire Surtax, EITC Childless Expansion, Repeal SALT Cap) and four
Tailor-shaped `TaxPolicy` runs (+2.6pp > $400K, ±1pp all, +5pp > $1M), each at quintile,
decile and JCT-dollar grouping — **45 tables, 401 group rows**, plus the SALT benchmark's own
table.

### 3.1 The seven distributional benchmarks — byte-identical

| Benchmark | Engine path | Before (pp) | Predicted after (pp) |
|---|---|---:|---:|
| `cbo_tcja_2018` | synthetic | 7.8e-17 (0.00) | identical |
| `jct_tcja_2019` | synthetic | 2.0986 | identical |
| `cbo_arp_2021` | microsim, household | 3.7211 | identical |
| `jct_salt_repeal_2024` | **microsim, tax unit** | 5.8607 | **identical** |
| `jct_corporate_28_2022` | synthetic | 2.5125 | identical |
| `cbo_tcja_extension_2026` | synthetic | 0.7400 | identical |
| `cbo_pl119_21_2026` | synthetic | 3.9600 | identical |

Every `per_group` dict (model share, model avg change, error) identical to the last bit.
**Falsification:** any benchmark error moving at all means a weighted quantity reached the
share metric, which the trace in §1 says it cannot.

### 3.2 What does move, cell counts over the 45 tables

| Field | Cells predicted to move / unchanged |
|---|---:|
| `num_returns`, `tax_change_total`, `tax_change_avg`, `share_of_total_change` | **0 / 401** each |
| `total_tax_change`, `total_affected_returns`, headline direction | **0 / 45** each |
| `total_agi`, `baseline_tax`, `avg_agi`, group ETR, `baseline_etr`, `new_etr` | 349 / 52 (the 52 are empty groups) |
| `total_taxable_income` | 322 / 79 |
| `tax_change_pct_income`, `pct_unchanged`, `etr_change` | 76 / 325 (rows with no change stay 0 / 100 / 0) |
| `pct_with_increase` / `pct_with_decrease` | 32 / 369 and 44 / 357 |
| summary `pct_with_increase` / `_decrease` | 24 / 16 of 45 |

### 3.3 Figures a user would see

`jct_salt_repeal_2024` (JCT dollar classes; shares and the 5.86pp unchanged):

| Class | % with cut | % of income | ETR change (pp) | Avg AGI |
|---|---|---|---|---|
| $100K–200K | 3.6 → **4.8** | −0.023 → −0.023 | −0.013 → **−0.021** | $60 → **$137,489** |
| $200K–500K | 29.5 → **30.6** | −0.250 → **−0.252** | −0.191 → **−0.210** | $120 → **$280,270** |
| $500K–1M | 82.6 → **78.9** | −1.583 → **−1.574** | −1.167 → **−1.187** | $279 → **$656,221** |
| $1M+ | 80.3 → **76.0** | −1.856 → **−1.843** | −1.389 → **−1.298** | $462 → **$1,221,475** |

Whole-table share with a cut: 3.05% → **3.24%**.

Tailor +2.6pp above $400K, quintiles: top quintile baseline ETR 18.45% → **18.78%**, ETR change
0.248 → **0.258**pp, % of income 0.320 → **0.317**, % with increase 11.9 → **11.9**; every
lower quintile's baseline ETR rises by 0.4–1.0pp (lowest −4.98% → **−3.95%**).

Preset summaries (quintile view, "% with tax cut / increase"): Repeal SALT Cap 3.00 → **3.24**%
with a cut; EITC Childless 7.37 → **7.64**%; Middle Class Tax Cut 28.75 → **28.87**%; Top Rate
to 45% 0.43 → **0.46**% with an increase; Progressive Millionaire 0.15 → **0.17**%; Warren
Surtax 0.00 → **0.01**%; Biden 2025 and the Medicare surcharge **1.11 → 1.11**.

**Falsification:** any of the "0 moved" rows in §3.2 moving, a headline direction flipping, or
any figure in §3.3 landing elsewhere than stated.

## 4. Must stay byte-identical

- `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json` — sha256 equal to `base2`.
- `python scripts/run_loo.py --donor-matrix` — `diff` empty against `base2`.
- `python scripts/run_validation_dashboard.py` text and `--json` `distributional_benchmarks`
  block — empty diff apart from timestamps.
- The household path (ARP) and the synthetic path — not opened.

---

## 5. Outturn

**Every prediction landed exactly.** `r7_sweep.py current` on the edited tree, with no patches,
produced a JSON file **byte-identical** (`cmp`) to the `predicted` run written before the edit:
all 45 tables, all 401 group rows, every field, and the seven benchmark comparisons.

| Check | Result |
|---|---|
| 7 distributional benchmarks | identical to the last bit (§3.1 table holds as written) |
| §3.2 cell counts | as predicted; 0 cells moved in `num_returns`, `tax_change_total`, `tax_change_avg`, `share_of_total_change`, totals, affected returns, headline direction |
| §3.3 figures | as predicted to the printed digit |
| `cold_holdout.py --json` sha256 | **69f52cf3…a37a9dd**, equal to `base2` |
| `run_loo.py --donor-matrix` | `diff` empty against `base2` |
| `run_validation_dashboard.py` | text `diff` empty; `--json` equal to `base2` after dropping `generated_at` |
| Composer progressivity / policy tags | unaffected (read `tax_change_total` only, 0 cells moved) |

**Shipped.** `create_groups_from_microdata` sums `weight × column` for AGI, taxable income and
tax (missing `weight` = 1, so unweighted frames reproduce the old arithmetic exactly); the
tax-unit branch of `analyze_policy_microsim` weights the after-tax-income denominator, the
increase / decrease / unchanged shares and both ETRs. Tests:
`tests/test_weighted_group_totals.py` (9): the two-row weights-1-and-1,000 frame for totals,
`avg_agi`, ETR, share with an increase, % of income and the winners/losers summary; the
no-weight frame; and the invariant that group totals sum to the weighted population total over
AGI ≥ 0, on random frames at all three groupings and on the shipped CPS file. **Eight of the nine
fail on the pre-R7 code** (the no-weight test is the one that must pass on both).

**No benchmark got worse, and none could have:** the seven tables score shares, and shares were
already weighted. What was wrong was every *other* column of the tax-unit microsim table, on the
one tab where the app calls it "the validated distributional tier": `% Tax Increase` and
`% Tax Decrease` were shares of CPS *rows*, `ETR Change` and the ETRs were row-sum ratios, and the
multi-model pilot's `Avg AGI` was off by roughly the mean weight (top quintile $132). The
headline progressive/regressive sentence did not flip in any of the 45 tables.

**Found while sweeping, not this lane's to fix** (`distribution_effects.py` is not owned): a
generic `TaxPolicy` with `affected_income_threshold=0` is mapped by
`policy_to_microsim_reforms` to `{"new_top_rate": 0.37 + rate_change}`, so a Tailor "+1pp on
every bracket" run's distribution table shows a top-bracket-only change ($1.87B in year one,
0.34% of returns affected) while its revenue score prices every bracket. The table and the
headline describe different reforms.

## 6. The `distributional_validation.py` "105.9%"

CLAUDE.md's command `python fiscal_model/validation/distributional_validation.py` prints
"Overall Score: NEEDS IMPROVEMENT / Average Share Error: 105.9%" while the dashboard reports the
seven CBO/JCT tables at 0.00–5.86pp. They measure different things:

| | `distributional_validation.py` | dashboard (`cbo_distributions.compare_distribution`) |
|---|---|---|
| Benchmark | TPC, *TCJA conference agreement, 2018* (Dec 2017) — not one of the seven | 7 CBO/JCT tables |
| Model policy | `create_tcja_extension(extend_all=True)`, analysis year 2026 | per benchmark |
| Path | synthetic bracket path (TCJA has no microsim reform): `calculate_tcja_effect`'s **tier table, calibrated to CBO's own decile tables** | same tier table for the three TCJA rows |
| Groups | engine "quintiles" = fixed AGI cut-offs $35K/65K/105K/170K over IRS filers, holding **38.9 / 22.0 / 16.1 / 10.4 / 12.6%** of returns | each benchmark's own grouping |
| Metric | **relative** error of the share, `|m − b| / b`, averaged | **absolute** error in percentage points, averaged |

**It is mostly a units issue, partly a definitional mismatch, and a little a real finding — not
stale code.** The path is live and current. In the dashboard's own metric the same comparison is
**6.94pp ("acceptable" on the dashboard's bands)**: 2.90, 5.81, 4.29, 4.35 and 17.35pp by group.
The 105.9% is dominated by dividing by small benchmark shares — the lowest group's 2.9pp miss on
a 1.0% share is "290%", the second's 5.8pp on 4.0% is "145%"; the top group's 17.35pp miss, the
one that matters, is only "25.5%". The remaining gap has two causes the script cannot separate:
the model's "Top Quintile" is the top **12.6%** of filers, not 20% of all tax units by expanded
cash income, and the policy is the 2026 individual extension, not the 2018 conference agreement
(which includes the corporate cut whose incidence lifts TPC's top quintile to 68%). What is real:
this is the **only independent check of the TCJA tier table** in the repository — the dashboard's
`cbo_tcja_2018` 0.00pp and `cbo_tcja_extension_2026` 0.74pp are that table read back against the
tables it was calibrated to (two of the "circular" rows) — and against TPC it misses the top by
17pp.

**Changed** (history kept): `validate_distribution` now also returns per-group `share_error_pp`,
`model_population_share`, `overall_share_error_pp` and `overall_rating_pp` (the dashboard's
<2 / <5 / <10pp bands, `rating_from_share_error_pp`). `print_validation_report` prints the legacy
line labelled as relative, the pp line beneath it, a pp column and a population-share column, and
a note that the "quintiles" are not fifths and that this comparison is not one of the seven
gated tables. `overall_score` and `overall_share_error` are unchanged. Tests in
`tests/test_distributional_validation.py` (`TestPercentagePointMetric`, 9 cases).

**Doc sentences that need changing** (not edited by this lane):

- `CLAUDE.md`, Commands: `# Run distributional validation` above
  `python fiscal_model/validation/distributional_validation.py` — should say it is a single TPC
  2018 TCJA comparison against the CBO-calibrated TCJA tier table, not the seven gated tables,
  and that its headline 105.9% is relative error (6.94pp in the dashboard's metric).
- `CLAUDE.md`, Module Structure: "`fiscal_model/validation/distributional_validation.py` | TPC
  distributional benchmark validation" — same qualification.
- `fiscal_model/ui/tabs/distribution_analysis.py`'s caption "the validated distributional tier,
  benchmarked against CBO/JCT tables within ≤3pp" (owned by the UI lane): the seven tables span
  0.00–5.86pp, five of them score the synthetic path rather than the microsim, and only one
  (`jct_salt_repeal_2024`, 5.86pp) scores the tax-unit microsim table the caption sits above.

---

## 7. R7b — An all-bracket rate change was mapped to the top bracket (pre-registration)

*Written before `distribution_effects.py` was edited. Predictions from
`scratchpad/r7b_patch.py`, which wraps `policy_to_microsim_reforms` with the proposed mapping, run
through the same `r7_sweep.py` (45 tables) and a Build interaction sweep (`r7b_build.py`, all 36
pairs of the nine microsim presets).*

### 7.1 Trace

`policy_to_microsim_reforms` (plain income-tax `TaxPolicy`, non-zero `rate_change`):

| `affected_income_threshold` | Reform emitted | What `MicroTaxCalculator.apply_reform` does |
|---|---|---|
| > 0 (mid or top: $50K, $400K, $609,350, $1M, $2M) | `income_rate_change=Δ`, `income_rate_change_threshold=T` | after `calculate`, adds `Δ × max(0, ordinary taxable income − T)` (`engine.py:763-788`) |
| **0** | **`new_top_rate = 0.37 + Δ`** | overwrites only `rates_single[-1]` / `rates_mfj[-1]` — the 37% bracket |

The revenue path prices a threshold-0 `TaxPolicy` against the whole base, so the distribution
table and the score describe different reforms: Tailor "+1pp, everyone" scores **+$122.5B** of
static revenue in year one and its distribution table shows **+$1.87B**, every dollar in the top
quintile, 0.34% of returns affected. The engine can already express the right reform: the same
adder with threshold 0 applies to all ordinary taxable income. `0.37` is also a hard-coded copy
of the engine's top rate.

### 7.2 Mechanism chosen, and the alternative measured

Map threshold 0 to `income_rate_change=Δ, income_rate_change_threshold=0.0`, exactly as every
threshold > 0 change is already mapped. One reform per policy, no change to `engine.py`.

The alternative — setting every bracket's rate through `rate_changes` / `rate_changes_mfj` — runs
the change through the regular-tax computation, so it sees the AMT. Measured on the shipped CPS
file, year 2026, year-one $B:

| Policy | Revenue score (static) | top-rate (now) | **adder at 0 (chosen)** | all brackets |
|---|---:|---:|---:|---:|
| +1pp all | +122.5 | +1.87 | **+92.23** | +90.72 |
| −1pp all | −122.5 | −1.87 | **−92.23** | −90.08 |
| −5pp all (Flat Tax Reform) | −612.3 | −9.37 | **−461.15** | −392.66 (top quintile −164.6 vs −232.3) |

The two agree within 2% at ±1pp; at −5pp the bracket route is 15% smaller because a large regular
rate cut pushes high earners into the AMT. Chosen anyway, for consistency: every other ordinary
rate change on every surface is the post-calculation adder, and `package_interactions.py`'s
`_STRUCTURALLY_ADDITIVE` table states as fact that "an ordinary-rate change is added after
`calculate`". The bracket route would make that statement false for one preset in a file this
lane does not own. **Carry-over:** the adder ignores AMT for *every* rate change, threshold or
not; that is a separate engine lane.

### 7.3 Predicted movements

- **7 distributional benchmarks: byte-identical.** None uses a plain threshold-0 `TaxPolicy`.
- **Revenue scores, `cold_holdout.py --json`, `run_loo.py`, dashboard text: byte-identical.**
  Neither scorer reads this mapping; the dashboard's distributional block scores the seven tables
  only.
- **Distribution tables:** exactly one preset — **Flat Tax Reform** (`across-the-board-rate-cut-5pp`,
  −5pp, threshold 0) — and threshold-0 Tailor runs. 9 of 45 swept tables move; every other
  preset's table byte-identical. Headline direction flips: 0 of 45. Group totals, ETR baselines and
  return counts: 0 cells move.

| Table (quintile view, year one) | Total now → predicted | % affected now → predicted |
|---|---|---|
| Flat Tax Reform | −$9.37B → **−$461.15B**; quintiles $0 / 0 / 0 / 0 / −9.37 → **−10.25 / −48.50 / −72.17 / −97.93 / −232.30** | 0.34% → **59.81%** |
| Tailor +1pp all | +$1.87B → **+$92.23B**; top-quintile share 100% → **50.4%** | 0.34% → **59.76%** |
| Tailor −1pp all | −$1.87B → **−$92.23B** | 0.34% → **59.76%** |

- **Build:** Build's catalog can measure only `top-rate-39-6`, `salt-cap-repeal` and
  `eitc-childless-expansion` (`MICROSIM_MEASURABLE_IDS`), none of them threshold-0, so **no Build
  surface moves**. Through `measured_interaction_share` directly (outside Build's catalog), 8 of
  36 pairs change and all involve `across-the-board-rate-cut-5pp`: its standalone microsim level
  −$9.37B → **−$500.62B** (2025, top-tail-augmented population); interaction with
  `salt-cap-repeal` +$1.90B → **+$9.82B** (share of SALT 7.5% → **38.6%**); the other seven pairs
  stay at zero (some switch the sign of zero).
- **Multi-model pilot** (`models/comparison.py`, not owned): its TPC-Microsim revenue for a
  threshold-0 rate policy moves by the same mechanism, and its note "Generic rate-change policies
  are approximated as top-rate reforms in the pilot microsim" becomes stale.
- **Tests:** `tests/test_policy_to_microsim_reforms.py::test_tax_policy_with_rate_change_produces_top_rate_reform`
  pins the defect (`new_top_rate == 0.37 + 0.026`) and is rewritten to the new mapping.

**Falsification:** any benchmark, revenue score, holdout hash or LOO line moving; any table other
than the threshold-0 ones moving; any figure above landing elsewhere.

### 7.4 Outturn

**Every prediction landed exactly.** On the edited tree, with no patches, `r7_sweep.py` and
`r7b_build.py` produced JSON **byte-identical** (`cmp`) to the predictions in §7.3: 9 of 45
tables moved (Flat Tax Reform and the two threshold-0 Tailor runs, each at three groupings),
0 headline flips, 0 group-total cells, all seven benchmarks bit-identical, Build's three
catalog-measurable pairs unchanged, and 8 off-catalog pairs moved as stated.

| Check | Result |
|---|---|
| `cold_holdout.py --json` sha256 | **69f52cf3…a37a9dd**, equal to `base2` |
| `run_loo.py --donor-matrix` | `diff` empty against `base2` |
| `run_validation_dashboard.py` text | `diff` empty against `base2` (exit 2, as before) |
| `pytest -k "distribution or microsim or package_interactions or tailor or build"` | 518 passed |
| pilot / capability tests (`test_model_comparison`, `test_model_capabilities`, `test_multi_model*`, `test_microsim`) | 77 passed |

**Shipped.** `policy_to_microsim_reforms` emits `income_rate_change` /
`income_rate_change_threshold` at every threshold, threshold 0 included; the hard-coded `0.37`
is gone. One existing test pinned the defect and was rewritten
(`test_tax_policy_with_no_threshold_changes_every_bracket`). New
`tests/test_all_bracket_distribution.py` (5): ±1pp all-bracket changes move every quintile in the
policy's direction with a non-zero affected share; the +1pp table total ($92.2B) agrees in sign
and order with the year-one static revenue score ($122.5B, ratio 0.75, was 0.015); one mapping
rule at five thresholds; and Top Rate to 45% (threshold $609,350) is pinned to its pre-R7b table
to the last bit. `package_interactions.py`'s tests all pass unchanged.

**Left for others.** `models/comparison.py`'s note "Generic rate-change policies are approximated
as top-rate reforms in the pilot microsim" is now false (that file is not this lane's). The AMT
blind spot of the post-calculation adder (§7.2: −$232.3B vs −$164.6B in the top quintile at −5pp)
applies to every ordinary-rate change and is an engine carry-over.
