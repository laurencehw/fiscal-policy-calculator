# R2 — the five Tier 1 targets without a document

*Pre-registered 2026-09-11 on `provenance/r2-tier1-secondhand`, branched from `main` @ `143629d`
(PR #160). Lane R2 of `planning/ROUTE_TO_8_5.md` §1, criteria ① and ③. Every figure below is from
one of three runs on **this** tree — `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json`,
`scripts/run_validation_dashboard.py`, `scripts/run_loo.py --donor-matrix` — from a fourth on a
scratch merge of `origin/model/r1-baseline-transcription` (PR #159, open and held) into this
branch, or from a document this lane opened and cites by page. Nothing is recalled.*

---

## §1 — What this lane is, and what it may not do

Tier 1 is the only tier in this repository that claims **predictive skill**, and
`preregistered.py` states the condition that claim rests on: *"a predictive claim is worth nothing
unless the target was fixed before the model was allowed to move."* A target nobody published was
not fixed before the model moved — it was written down by this repository, and a row scored against
it measures nothing at all. That is why `top_rate_45` was retired in Phase E rather than corrected:
*"There is no figure to correct it to."*

Five of the battery's 26 rows are `secondhand`. Split by provenance on this tree
(`cold_holdout.py --json`, 2026-09-11):

| provenance | n | mean | error mass | within 25% |
|---|--:|--:|--:|--:|
| `line_item` | 21 | **11.36%** | 238.6 | 18/21 |
| `secondhand` | 5 | **23.92%** | 119.6 | 4/5 |

**Nineteen percent of the battery carries 33.4% of its error mass**, and it is the 19% whose
targets nobody can open.

### The rule this lane binds itself to, before opening a document

1. **A retirement must be justified by the absence of a document, never by the row's error.**
   Each verdict below states this in as many words. If the same row had scored 1%, the same
   verdict would follow — and §4's `medicare_surcharge_2pp` is exactly that case, which is why it
   is the sharpest test of the rule rather than the easiest application of it.
2. **No module may be opened, and no `model_10yr_billions` may move.** This is a provenance lane.
   Every prediction in §5 is arithmetic on the BEFORE file, and the outturn must reproduce it to
   the cent. A shape re-read (`rate_change`, `income_threshold`, `scoring_window_first_year`) would
   move a model figure; where a document argues for one, the lane **publishes the number and hands
   the decision to the owner**, exactly as PR #126 published IIJA's 18.2% → 0.3% and declined to
   take it.
3. **The manifest's supersede rule.** A target that moves gets a **new row** with a new `case_id`
   and `superseded_by` on the old one, entered in a commit *before* the commit that first scores
   it. A target that cannot be sourced gets `retired=True` with the search recorded.
4. **Four end states, one per row, all written down**: superseded onto a document; retired with the
   search recorded; examined-and-left with a verdict; range-revised. ROUTE §0 criterion ③ asks for
   the `retire` state *"either applied or declined in writing, per row"*.

### What would falsify this lane

Any `model_10yr_billions` moving; any row retired whose target this lane could in fact open; any CI
threshold **loosened** beyond what `tests/test_ci_workflow.py` already forces.

---

## §2 — The five rows, and the search each will run

| row | target | claimed source | model (this tree) | error | search |
|---|--:|---|--:|--:|---|
| `medicare_surcharge_2pp` | −$310.0B | Treasury FY2025 Green Book | −$408.6B | 31.8% | the FY2023/FY2024/FY2025 Green Book revenue tables, row by row |
| `warren_ultramillionaire_surtax_3pp` | −$350.0B | TPC (bare homepage URL) | −$436.8B | 24.8% | TPC's *AGI Surtax Options* simulation and every revenue table in it |
| `illustrative_1pp_all` | −$960.0B | JCT "rule of thumb" | −$1,195.3B | 24.5% | the four CBO *Options* volumes (2018, 2020, 2022, 2024), whose individual-rate option is a JCT estimate |
| `illustrative_top_rate_5pp` | −$700.0B | TPC (bare homepage URL) | −$841.7B | 20.2% | the same four volumes for a $1,000,000 threshold; PWBM's nearest published bracket change |
| `illustrative_500k_2pp` | +$400.0B | TPC (bare homepage URL) | +$473.2B | 18.3% | the same four volumes for a rate **cut**; TPC's model-estimate catalogue |

Phase E already enumerated TPC's full sitemap (11 sub-sitemaps, ~20,600 URLs, ~6,500 model-estimate
pages) for three of these and recorded the result in `benchmark_sources.py`. **This lane's addition
is the decision**, which is what ROUTE §0 criterion ③ says is missing: *"H9 built it and applied it
to nothing, which is correct only while ④ is open."*

---

## §3 — Why this lane is urgent, and the tree its outcome must pass on

R1 (PR #159, held) grows the generic base at CBO's own FY2023→FY2025 nominal rate, 10.70% against
the hand-entered 8.99%. Measured on a scratch merge of R1 into this branch (never pushed):

| | main @ `143629d` | + R1 |
|---|--:|--:|
| n | 26 | 26 |
| mean | 13.8% | **14.7%** |
| within 15% | 17 | 17 |
| within 25% | **22** | **20** |
| `secondhand` mean | 23.92% | **28.12%** |
| `line_item` mean | 11.36% | 11.48% |

Eleven rows move and **two cross 25%**: `warren_ultramillionaire_surtax_3pp` 24.8% → **29.0%** and
`illustrative_1pp_all` 24.5% → **28.7%**. Both are `secondhand`. The pooled floor is
`--min-within-25pct 22`, met on main with no slack, so on the merged tree the gate fails at 20.
Note that the workflow's own meta-test already forbids a floor above the live count
(`tests/test_ci_workflow.py::test_no_gate_is_looser_than_the_workflow_rule_derives`:
`assert min_within <= summary["within_25pct"]`), so **the floor is not a free parameter on either
tree** — it is pinned to the battery the repository actually has.

---

## §4 — The four possible end states, per row, and what this lane predicts

Written before the verdicts are taken. Each row's verdict is settled by the document, not by the
prediction.

- **`medicare_surcharge_2pp`** — expected **retired**. Treasury's proposal is a **1.2 percentage
  point** increase in each of two rates, not 2pp, and no volume prints −$310B for it. The trap to
  avoid is named in advance: the FY2025 volume's own figure sits close to this row's *2pp* model
  output, so adopting it would buy a small error with a 1.67× rate mismatch — two errors
  cancelling, and the flattering option. If the document is adopted the row must be re-shaped, and
  re-shaping moves a model figure, which rule 2 forbids here.
- **`warren_ultramillionaire_surtax_3pp`** — expected **retired**. TPC's AGI-surtax work is at
  10 percent. A 3pp figure derived by scaling it would be *constructing* a target, which
  `PROVENANCE_corporate_ptc.md` already refused (*"summing two rows of PWBM's table would be
  constructing a target rather than reading one"*).
- **`illustrative_1pp_all`** — expected **superseded**. This is the one row whose reform, source
  (JCT), window (FY2023–2032) and vintage all point at a real published line. If it does, the row
  becomes `line_item` and the **window mismatch must be published** rather than closed, because
  closing it moves a model figure.
- **`illustrative_top_rate_5pp`**, **`illustrative_500k_2pp`** — expected **retired**. Both call
  themselves "Illustrative" in their own records.

**Direction of the tier mean is genuinely unknown and is not the objective.** H9's outturn was that
five of six revisions made their row *worse*, and that is the shape a correct provenance pass has.
What this lane registers is the **count**: Tier 1 `secondhand` **5 → ≤ 2**.

---

## §5 — Pre-registered arithmetic

Computed from the BEFORE files before any file was edited
(`scratchpad/r2/predict.py`, retiring four rows and moving one target to −$1,081.3B). **If the
outturn differs from any figure below by more than $0.1B or 0.1pp, something moved that should not
have.**

| | this tree, before | this tree, after | + R1, before | + R1, after |
|---|--:|--:|--:|--:|
| n | 26 | **22** | 26 | **22** |
| mean | 13.8% | **11.3%** | 14.7% | **11.6%** |
| median | 10.7% | **8.9%** | 10.7% | **8.9%** |
| within 15% | 17 | **18** | 17 | **18** |
| within 25% | 22 | **19** | 20 | **19** |
| within 25%, as a **share** | 84.6% | **86.4%** | 76.9% | **86.4%** |
| error mass | 358.2 | **249.1** | 381.6 | **255.3** |
| `secondhand` rows | 5 | **0** | 5 | **0** |

`illustrative_1pp_all` is predicted at **10.5%** on this tree and **14.3%** with R1, against
24.5% / 28.7% today. Every other surviving row is predicted **byte-identical**.

### The gate, re-derived by the workflow's own rule

The count within 25% falls because the **denominator** falls; the share rises. Every move below is
**forced** by `tests/test_ci_workflow.py`, not chosen:

| threshold | now | derived after | why it is not discretionary |
|---|--:|--:|---|
| pooled ceiling | 20 | **15** | `ceil(11.3 × 1.25) → 15`; `max_mean <= derived_ceiling` fails at 20 |
| pooled floor | 22 | **19** | `min_within <= summary["within_25pct"]` fails at 22 against a live count of 19 |
| `agi_inclusive_surtax` | 22 | **7** | class n 6 → 2, mean 17.6% → 5.15%; both one-sided invariants fail at 22 |
| `ordinary_rate_change` | 19 | **15** | class mean 14.8% → 11.32%; `ceilings[slug] <= derived` fails at 19 |

The other six ceilings re-derive to themselves. Both derivations **tighten**, and the floor is
pinned by an existing assertion rather than relaxed by this lane. On the R1-merged tree the same
four values hold (`ordinary_rate_change` derives to 17 there, so 15 is tighter and still passes;
`tax_expenditure` derives to 16 against a ceiling of 17, which is **R1's** re-derivation to make,
on the row R1 moves).

### What must not move

`run_loo.py --donor-matrix` byte-identical; all 55 calibrated rows byte-identical; every surviving
Tier 1 `model_10yr_billions` byte-identical; `build_validation_headline.py --check` green after
regeneration; `check_readiness.py --strict` exit 0.

### What the app loses, and why that is the point

Two shipped presets quote one of these targets as an `official_score`: **Warren Ultra-Millionaire
Surtax** (−$350.0B) and **High-Earner Medicare Surcharge 2pp** (−$310.0B). Phase E's precedent is
exact — *"An official score nobody published should not be quoted in the app, so the entry was
removed; the preset itself is unchanged and still scoreable, it simply shows the model's own
estimate with no official comparison."* Both presets keep their model output; both lose the
comparison. This is ROUTE §0 criterion ④ moving in the same direction: 13 Build options quoting a
`secondhand` or `model_estimate` target, against a destination of ≤ 6. **No `rate_change`,
`threshold`, `agi_inclusive_base` or `income_measure` is touched**, so no app number moves and no
Decision 6 caption is owed.
