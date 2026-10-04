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

*(appended after implementation — see below)*
