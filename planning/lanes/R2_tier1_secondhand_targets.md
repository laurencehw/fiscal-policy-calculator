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

---

## §6 — Outturn (appended 2026-09-11, after the work)

### The five verdicts

| row | verdict | the document, and the figure |
|---|---|---|
| `illustrative_1pp_all` | **superseded** `.v1` → `.v2` | CBO pub. **58164**, *Options for Reducing the Deficit: 2023 to 2032, Vol. I* (Dec 2022), Option 13 alt 1, "Raise all tax rates on ordinary income by 1 percentage point", **−$1,081.3B** FY2023–2032, report p. 72; *"Data source: Staff of the Joint Committee on Taxation"*. −$960B → −$1,081.3B; **24.5% → 10.5%**, prediction unmoved |
| `warren_ultramillionaire_surtax_3pp` | **retired** | TPC *AGI Surtax Options* = 13 tables, **all 10 percent**; sole revenue table **T19-0037** (23 Sep 2019) prices $2M at **$585.325B**, $2.5M at $500.635B, $2M-MFJ/$1M-other at $633.897B. No 3pp figure anywhere; and Warren's own Act is a **wealth** tax, so the shape matches no scored proposal |
| `medicare_surcharge_2pp` | **retired** | Treasury FY2025 Green Book: the proposal is **1.2pp** (report pp. 76–77) and prints **$403,790M** (report p. 242); FY2024 prints **$344,371M**; FY2023 has none. −$310.0B is none of them. Restated on Treasury's own rate the model is **39.3% under** |
| `illustrative_top_rate_5pp` | **retired** | No +5pp at $1,000,000 exists. TPC sitemap (Phase E) plus the individual-rate option of **all four** *Options* volumes (2018 #1, 2020 #1, 2022 #13, 2024 #45): every alternative is a uniform change at a bracket boundary or an AGI surtax at a statutory floor |
| `illustrative_500k_2pp` | **retired** | No 2pp **cut** at $500,000 exists, and the *Options* volumes are deficit-**reduction** menus carrying no cut at all. This was the battery's only rate cut and only positive target |

### Tier 1, both trees

| | this tree before | this tree after | + R1 before | + R1 after |
|---|--:|--:|--:|--:|
| n | 26 | **22** | 26 | **22** |
| mean | 13.8% | **11.3%** | 14.7% | **11.6%** |
| median | 10.6% | **8.9%** | 10.6% | **8.9%** |
| within 15% | 17 | **18** | 17 | **18** |
| within 25% | 22 | **19** | 20 | **19** |
| within-25 **share** | 84.6% | **86.4%** | 76.9% | **86.4%** |
| error mass | 358.2 | **249.1** | 381.6 | **255.3** |
| `secondhand` | 5 | **0** | 5 | **0** |

**Every figure landed on its §5 prediction.** Every surviving row's `model_10yr_billions` is byte-identical (checked row by row), `run_loo.py --donor-matrix` is byte-identical, and all four calibrated summaries — `calibrated_reference`, `uncalibrated_reconstruction`, `retired_targets` and the retired-held-in-place block — compare `SAME`.

**The pooled gate passes on both trees at the same numbers** (`--max-mean-error 15 --min-within-25pct 19`, exit 0 here; on the R1-merged scratch tree the tier reads 11.6% / 19, inside both). That is the result R1 needs: the two rows R1 pushed across 25% (`warren` 24.8% → 29.0% and `illustrative_1pp_all` 24.5% → 28.7%) are the one this lane retired for want of a document and the one it moved onto CBO's own option, so R1 no longer has a Tier 1 gate problem to solve.

### The gate, and why none of it is discretionary

| threshold | before | after | forced by |
|---|--:|--:|---|
| pooled ceiling | 20 | **15** | `test_no_gate_is_looser_than_the_workflow_rule_derives`: `max_mean <= ceil(11.3 × 1.25) → 15` |
| pooled floor | 22 | **19** | the same test: `min_within <= within_25pct`, live count 19 |
| `agi_inclusive_surtax` | 22 | **7** | both one-sided invariants, at a class mean of 5.15% (n 6 → 2) |
| `ordinary_rate_change` | 19 | **15** | `ceilings[slug] <= ceil(11.32 × 1.25)` |

The other six re-derive to themselves. On the R1-merged tree `ordinary_rate_change` derives to 17 and `tax_expenditure` to 16; 15 is tighter than the first and passes, and the second is **R1's** re-derivation to make, on the row R1 moves (`cbo_opt56` 13.1% → 12.8%).

### Findings the pre-registration did not predict

1. **`medicare_surcharge_2pp`'s target matches the FY2025 Green Book's *child-credit* row to 0.008%** (−$310,024M against −$310.0B) — a cost, the opposite sign to the raiser it was scoring. The coincidence is recorded and explicitly **not** claimed as provenance; what it establishes is that the figure is not the proposal's.
2. **The 1.2pp/2pp mismatch makes this row's reported accuracy better than its real accuracy, not worse.** On Treasury's own rate the model reads −$245.2B against −$403.8B, **39.3% under**, where the row had been reporting 31.8%. A retirement that *raises* the honest error is the cleanest possible demonstration that the rule is about documents and not about means.
3. **CBO prices the same 1pp reform three times and gets three numbers**: −$884.0B (2020 volume, FY2021–2030), −$1,081.3B (2022, FY2023–2032), −$1,185.3B (2024, FY2025–2034). The model gives −$1,195.3B and −$1,207.3B for two of them, **1.0% apart**, where CBO's own figures are 9.6% apart — so the pair `illustrative_1pp_all` / `cbo_opt45_all_rates_1pp` measures the model's **insensitivity to the decade**, not two independent predictions. Read it that way, and R3 should read the other two vintages the same way before registering them.
4. **The Warren row's name was wrong, not just its number.** The Ultra-Millionaire Tax Act is a wealth tax on net worth (2% above $50M, 3% above $1B); the "3pp" is the billionaire *wealth* rate transplanted onto an income base and the "$2M" comes from a different proposal. No search could have found this target, because the reform does not exist.
5. **The `sourced` branch of `agi_inclusive_base_caption` now has no live preset.** All three AGI-inclusive presets take the "design choice — no published score of this reform exists" branch, which is **more** accurate after R2 than before it, and the branch is kept covered by a monkeypatched test rather than left to rot.
6. **A gate stated as a count cannot survive a shrinking battery, and the repository already knew.** `test_no_gate_is_looser_than_the_workflow_rule_derives` asserts `min_within <= within_25pct`, so the floor was a *test failure* at 22 before it was a CI failure — which is why lowering it is bookkeeping rather than a relaxation. The invariant worth carrying: **quote the within-25 share beside the count**, because only one of the two is comparable across a battery that changes size.

### What moved that a user can see

Two shipped presets lost their `official_score` and their validation badge — **Warren Ultra-Millionaire Surtax** and **High-Earner Medicare Surcharge 2pp** — following `top_rate_45`'s Phase E precedent exactly. Both still score and still show the model's own estimate; neither prints a dollar figure in its label. The Build card copy moved **"45+ scored policies" → "40+"**, because the catalog is 44 and a promise the catalog cannot meet is the defect H6 exists to prevent. **No `rate_change`, `threshold`, `agi_inclusive_base` or `income_measure` moved, so no app number moved and no Decision 6 caption is owed.**

### Carry-overs

- A `medicare_surcharge_2pp.v2` at **−$403.8B** on a `rate_change=0.012` shape. Its base question comes with it: wages plus net investment income is neither SOI column.
- A new TPC case scoring a **10pp** surtax on AGI above $2M against T19-0037's **$585.325B** — the withdrawn row's own base and threshold at a rate somebody priced.
- An `illustrative_1pp_all.v3` with `scoring_window_first_year=2023`, worth most of the row's remaining 10.5%.
- **Tier 1 now contains no rate cut and no positive target.** R3's `leg_rev_*` series is where a scored cut with a document comes from.
- Tier 1 is 22 rows against criterion ①'s 40, and `agi_inclusive_surtax` is down to **n=2**. R3 owes this tier four rows before the per-class bands mean anything again.
