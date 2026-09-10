# Lane H13 — Say what the two OCACT payroll targets are

*Pre-registered 2026-09-09 against `main` @ `8964cb1` (= `f3dc042` plus three
nightly bill-tracker commits), before any file in §2 was opened. Outturn
appended at the end of the lane, in the last commit.*

Scope: `planning/HIGH_STAKES_ACCURACY.md` §1.2 row 3 and §3 **H13**. **No model
change.** `ss_donut_250k` (−$2,700.0B) and `ss_eliminate_cap` (−$3,200.0B) are
two of the app's six largest headline figures; both print their target to the
cent because a constant was fitted to it, and both targets are `secondhand`.
The lane says out loud what the two numbers are, beside the held-out figures the
same machinery returns when the fitted constant is taken away.

This lane is **docs plus one caption**. It may not open `fiscal_model/payroll.py`,
`fiscal_model/validation/*` (Wave B's H9 owns provenance), or
`fiscal_model/app_data.py` (Wave A's H1 owns it).

---

## 1. Starting numbers

Measured on the branch point, `8964cb1`, from `python scripts/run_loo.py
--donor-matrix`, `python scripts/cold_holdout.py --json` and `python
scripts/run_validation_dashboard.py`. Nothing below is copied from the plan.

### 1.1 The two rows

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| Payroll | `ss_cap_90_pct` | −800.0 | −800.0 | −749.5 | **+6.3%** |
| Payroll | `ss_donut_250k` | −2,700.0 | −2,700.0 | **−2,664.0** | **+1.3%** |
| Payroll | `ss_eliminate_cap` | −3,200.0 | −3,200.0 | **−3,319.5** | **−3.7%** |
| Payroll | `expand_niit` | −250.0 | −250.0 | — | not cross-validatable |

Payroll module mean **3.8%** (n=3 derivable, 1 excluded). Suite aggregate: **18
derivable, 30.1% mean / 19.1% median, 8/18 within 15%**, 4 not cross-validatable.

The plan quoted −$2,664.0B (1.3%) and −$3,319.5B (3.7%); both re-measure to the
decimal, so the figures the caption pins are these.

### 1.2 Why the by-construction column is 0.0%

`payroll.py`'s `BASELINE_WAGE_DATA` carries its own arithmetic in the comment:

```
"wages_above_cap_billions": 2_581.0,   # 320 / 0.124
"wages_250k_plus_billions": 2_177.0,   # 270 / 0.124
```

and `create_ss_eliminate_cap` / `create_ss_donut_hole` stamp
`annual_revenue_change_billions = 320.0` and `270.0`, each documented as the
"window-average of Trustees $3.2T / $2.7T over 10yr". The target divided by ten,
divided by the statutory rate, is the base; the base times the rate, times ten,
is the score. **A 0.0% row here measures arithmetic, not agreement.**

`SSA_COVERED_WAGES_ABOVE_BILLIONS` reuses the same two numbers as the
$176,100 and $250,000 anchors of the interpolation table every other threshold
is read off, which is why `validation/cbo_options.py` excludes CBO Option 62
from the Tier 1 battery for **leakage** rather than for missing machinery.

### 1.3 What the leave-one-out figures are, and are not

`validation/loo.py`'s `derive_payroll_annual` holds out the case's own anchor
and refits the covered-wage level at its threshold from the **other two**
anchors' Pareto slope. So −$2,664.0B and −$3,319.5B are what the module returns
when it is not told the answer for that row — a real cross-validation of the
band table's *shape*, and still not an independent measurement of the reform,
because two of the three anchors are themselves fitted.

---

## 2. What the lane changes

Files, and nothing else:

1. `planning/lanes/HSA_h13_payroll_targets.md` — this doc.
2. `docs/VALIDATION.md` — one paragraph in the provenance section: what OCACT
   publishes for E2.1 and E2.5, where the two dollar figures actually come
   from, the held-out figures, and the rule that a `secondhand` target
   reproduced by a fitted constant is bookkeeping.
3. `docs/METHODOLOGY.md` — the **payroll section only**, where line 853 reads
   "vs Trustees $2,700B" and that attribution is wrong.
4. `fiscal_model/ui/tabs/results_summary.py` — **one additive caption block**
   (`payroll_fitted_target_caption`) plus one call site in
   `render_headline_block`, following `ptc_repeal_baseline_caption`'s pattern
   exactly. H1 adds its own separate block in the same file; both are additive
   and independent, so the merge is a two-hunk append.
5. `tests/test_payroll_target_caption.py` — the caption's tests, including the
   **drift test**.

### 2.1 The caption's held-out figures are pinned, not computed

`run_payroll_loo()` re-scores three benchmarks through the full runner. Running
that on a page render is the defect PR #129 measured and PR #135 closed — the
footer computing the entire 81-row scorecard to print one clause, 8.68s of a
9.38s first paint. So the caption reads **two module-level constants**, and
`tests/test_payroll_target_caption.py` calls `derive_payroll_annual` and
`run_payroll_loo` and fails if either constant drifts from what the suite
returns. A pinned constant with a drift test is the cheap half of PR #135's
answer, applied to a two-number artifact rather than a JSON file.

### 2.2 The caption fires on the two shipped designs only

Guarded on `(ss_eliminate_cap, ss_donut_hole_start,
annual_revenue_change_billions)` matching one of the two factory outputs, so a
Tailor-built payroll policy at a different threshold — which is **not** the
fitted design and does **not** print the target — gets no caption. The claim
"the shipped figure reproduces the carried target" must be true whenever the
caption is on screen.

---

## 3. The prediction

**Zero numbers move.** This lane changes no constant, no target, no shape and
no registry.

- `python scripts/cold_holdout.py --json` — **byte-identical**.
- `python scripts/run_loo.py --donor-matrix` — **byte-identical**.
- `python scripts/run_validation_dashboard.py` — **byte-identical**
  (it exits 1 on the branch point already; that must not change either).
- All 53 shipped presets score to the cent what they scored before.
- No Decision 6 caption is owed, because no headline number moves. The caption
  this lane adds is not a Decision 6 caption; it is a provenance statement about
  a number that has not changed and never should have been read as evidence.

**Registries the lane must not touch**: `fiscal_model/validation/target_revisions.py`,
`benchmark_sources.py`, `preregistered.py`, `cbo_scores.py`. Anything the
sourcing turns up is written down **for H9**, and registered by H9 or not at all.

---

## 4. Falsification

The lane is falsified if:

1. Any of the three measurement artifacts differs before and after (`cmp`).
2. The two pinned LOO constants do not equal what `run_payroll_loo()` returns.
3. The caption fires on a payroll policy that does not print its carried target.
4. Any file outside §2's list is modified.
5. The sourcing turns up a published ten-year dollar score and this lane
   registers it rather than handing it to H9.

---

## 5. What this lane will not do

- **Not revise either target.** Sixteen targets have moved through
  `target_revisions.py` and every one of them was a ledger commit followed by a
  scoring commit. A docs lane may not take a target decision by implication —
  the same rule PR #126 applied when it published IIJA's 18.2% → 0.3% number
  and left the `.v3` row to the owner.
- **Not retune anything to close the held-out gap.** 1.3% and 3.7% are the
  honest figures and they are good ones; the point of printing them is that
  0.0% is not.
- **Not convert OCACT's percent of payroll into dollars.** A conversion this
  repository performs is a target this repository constructed. The whole finding
  is that the conversion is unpublished.

---

## 6. Outturn

### 6.1 What OCACT publishes for E2.1 and E2.5

Both provisions are scored, on the intermediate assumptions of the **2025
Trustees Report**, in memoranda dated **6 January 2026**. The current
`ssa.gov/oact/solvency/provisions/payrolltax.html` says the category is being
moved to a 2026 Trustees basis and is "not yet available", and points at
`provisions_tr2025/`, which is where the live figures are.

| | `ss_eliminate_cap` | `ss_donut_250k` |
|---|---|---|
| Provision | **E2.1** — "Eliminate the taxable maximum in years 2026 and later, and apply full 12.4 percent payroll tax rate to all earnings. **Do not provide benefit credit** for earnings above the current-law taxable maximum." | **E2.5** — "Apply 12.4 percent payroll tax rate on earnings above $250,000 starting in 2026, and tax all earnings once the current-law taxable maximum exceeds $250,000. **Do not provide benefit credit** for additional earnings taxed." |
| Run | 415 | 418 |
| Δ long-range actuarial balance | **+2.55% of payroll** | **+2.50% of payroll** |
| Δ annual balance, 75th year | +2.60% of payroll | +2.60% of payroll |
| Shortfall eliminated | 67% long-range / 54% in the 75th year | 65% / 54% |
| Reserve depletion | 2034 → **2059** | 2034 → **2057** |
| Current law, for reference | −3.82 long-range / −4.84 in the 75th year | same |
| **Ten-year dollars** | **none, at any horizon** | **none, at any horizon** |

The last row is not an inference, and it is checkable three ways. OCACT's
*Detailed Single Year Tables* for runs 415 and 418 are cost rate, income rate,
annual balance and trust-fund ratio, every column stated as a percentage of
current-law taxable payroll, year by year to 2100. **The only `$` anywhere in
run 418's table is inside the words "$250,000" in the provision text.** And
across the **whole six-page category summary** — every E1, E2 and E3 provision,
not only these two — the words "billion" and "trillion" **do not appear once**,
and every `$` figure in it is a threshold inside a provision description. So the
repository's older claim that OCACT "publishes no ten-year dollar amount for any
payroll provision" is not a hedge: it is true of the whole category, and now
verified rather than asserted. Every figure in `benchmark_sources.py`'s two
`searched` records checks out against the transcription.

### 6.2 Where −$2.7T and −$3.2T actually come from

The Peter G. Peterson Foundation's *Social Security Reform: Options to Raise
Revenues* (last updated **7 March 2025**) is the source of one of them, verbatim:

> "According to the Trustees' projection, that option would raise **$2.7
> trillion over 10 years**."

No report year, no run number, no window. Two things the earlier note did not
have. **First, the same page's cap-elimination sentence is $3.4 trillion, not
$3.2 trillion** — "eliminating the Social Security tax cap while providing
benefit credit for those earnings would raise an additional $3.4 trillion over
10 years (2026 to 2035) — or close **48 percent** of the 75-year funding gap".
48% is not the 2025 basis (E2.1 is 67%, E2.2 lower), so PGPF's figures are keyed
to a Trustees edition it does not name, and **−$3.2T matches nothing PGPF or
OCACT prints. Its origin is still unlocated.** Second, both PGPF sentences
describe **benefit-crediting** variants, where E2.1 and E2.5 both say "Do not
provide benefit credit" — so even the figure that does trace traces to a
different provision from the one the repository cites.

### 6.3 Registrable by H9 — two published ten-year dollar scores, neither adopted

- **The $250,000 donut.** CBO, *Options for Reducing the Deficit: 2025 to 2034*
  (pub. 60557), **Option 62 alternative 2**, "Subject earnings greater than
  $250,000 to payroll taxes": **$1,426.8B over FY2025-2034**, report p. 73 /
  PDF p. 79 — **already in this repository**, transcribed with its annual path
  to `cbo_options_2025_2034_alternatives.csv`. Same design, this repository's own
  window, **47% below** the carried −$2.7T. If H9 moves the target here, the
  ledger's own rule applies: the constant fitted to $2.7T is not fitted to
  $1,426.8B, so the row leaves the fitted tier and reports as a reconstruction
  at roughly 89%. That is the mechanism working, not a regression.
- **Cap elimination.** Tax Foundation, Alex Durante, *Uncapping the Payroll Tax
  Would Be the Largest Tax Increase in Decades* (24 June 2026), on the
  Moreno-Warren proposal — "apply the payroll tax to all earnings above the cap,
  with no corresponding changes to benefits", which is E2.1 — **"$3.2 trillion
  from 2027 through 2036 on a conventional basis and $1.5 trillion after
  accounting for the negative economic effects."**

**The second one is a trap and the lane says so rather than banking it.** It
agrees with the carried figure at its one significant figure, and the carried
figure is a constant chosen to produce −$3.2T; registering it would manufacture
a ~0% row out of a coincidence of rounding — the same failure `repeal_individual_amt`
refuses TPC T25-0049 for and `repeal_ptc` refuses CBO 51298 Table 2 for. It also
post-dates the target by about a year, so it cannot be its provenance. If H9 takes
it, it should take it with the window stated rather than adjusted
(`biden_corporate_28_fy2022`'s precedent) and with the dynamic/conventional
distinction on the record, since $1.5T against $3.2T is a **53% erosion** and
`reciprocal_tariffs` is already on the books as a case of a dynamic score sitting
in a conventional column.

### 6.4 Unpredicted finding — both published paths ramp and the module's does not

Not part of the lane's scope and not sought; it fell out of the transcription.
**OCACT's own E2.5 income-rate path is not flat.** The change from current law
runs **1.85% of payroll in 2026 → 2.00, 2.06, 2.13, 2.20, 2.27, 2.34, 2.43, 2.50
by 2034**, because the taxable maximum grows toward $250,000 and the hole closes.
**CBO's annual path for the identical donut ramps the same way**: $122.0B in 2026
→ $192.0B in 2034, a 57% rise. `create_ss_donut_hole` stamps a flat **$270B a
year**, documented as a "window-average". E2.1's path *is* nearly flat (2.40% →
2.51%), so this belongs to the donut alone.

That is `create_repeal_ptc`'s defect in a second module (PR #131): **a fitted
annual that reproduces a ten-year total while being wrong in every year of it**.
Sized on CBO's own path — hold the ten-year total at $1,426.8B and a flat annual
is $142.68B — the flat shape is **17.0% high in FY2026 and 25.7% low in FY2034**.
The same measurement on the shipped $270B is a hand-off, not this lane's, because
it needs the target question answered first. It is a modelling finding, so this lane records it
and does not act on it; a shape fix here would move a shipped headline and needs
its own lane, its own pre-registration and a Decision 6 caption.

### 6.5 One deviation from §2.2, and it is a strengthening

§2.2 guarded the caption on the *design* and the fitted annual. That is not
enough: the caption's first sentence asserts something about the number printed
above it — "reproduced to the cent" — and a guard on the policy alone would let
that sentence survive a change to the scoring path. So the caption also sums the
run's own static and behavioural effects and returns `""` when they sit more
than $0.05B from the pinned target. Both presets score their target exactly
today (−$3,200.0B and −$2,700.0B through `FiscalPolicyScorer`), so nothing on
screen changed; what changed is that a future lane which moves either score
silences the claim rather than publishing a false one.

### 6.6 The falsification tests all fired the right way

| Test | Result |
|---|---|
| `scripts/cold_holdout.py --json` byte-identical | **identical** |
| `scripts/run_loo.py --donor-matrix` byte-identical | **identical** |
| `scripts/run_validation_dashboard.py` byte-identical | **identical**, and its exit code is 1 before and after, as it already was on the branch point |
| Pinned LOO constants equal what `run_payroll_loo()` returns | asserted by `test_pinned_held_out_figures_match_the_loo_suite`; also the target and the by-construction score, so the caption's first sentence is checked rather than claimed |
| Caption never fires on a policy that does not print its target | seven negative tests: a $400K donut, `ss_cap_90_pct`, `expand_niit`, the same design with a different annual, the same design with no annual, a non-payroll policy, and a run whose score is not the target (§6.5's guard) |
| No file outside §2 modified | the branch touches exactly §2's five paths — this doc, `docs/VALIDATION.md`, `docs/METHODOLOGY.md`, `fiscal_model/ui/tabs/results_summary.py`, `tests/test_payroll_target_caption.py` |
| Nothing registered that belongs to H9 | `fiscal_model/validation/` untouched |
| Suite green with the key unset | `ANTHROPIC_API_KEY= python -m pytest tests/ -q` — **3738 passed, 7 skipped**, exit 0, the lane's 15 among them |

Ruff over CI's own scope (`fiscal_model/ tests/ app.py app_pages/ components/
classroom_app.py`, ruff 0.15.8) passes. `ruff format --check .` fails on 318
files on the branch point too, `results_summary.py` among them, and CI does not
run it — so the new test file is formatted and the existing module is left in
its neighbours' style rather than reformatted under H1's feet.

### 6.7 What the lane did not do, and why

- **Did not convert OCACT's percent of payroll into dollars.** It is arithmetic
  anyone can do — the change in the income rate times the Trustees' own taxable
  payroll path — and doing it here would have produced a number this repository
  constructed and then scored itself against. The finding is that the conversion
  is unpublished; performing it privately would delete the finding.
- **Did not revise either target**, register the Tax Foundation figure, or open
  `fiscal_model/validation/`. §6.3 is a hand-off.
- **Did not touch the shape.** §6.4 is a hand-off too.
- **Did not correct `payroll.py`'s two factory docstrings**, which still read
  "SS Trustees estimate: ~$2.7T" and "~$3.2T". They are wrong in exactly the way
  this lane documents, and `payroll.py` is not this lane's file — it belongs with
  whoever next opens the module, or with H9's provenance pass.
- **Did not correct the in-app Methodology table.**
  `fiscal_model/ui/tabs/methodology.py`'s calibrated-reference table prints
  `SS Donut Hole $250K | -$2,700B | -$2,700B | 0.0% | **Trustees**` — the same
  misattribution, on a surface a user reads. It is a one-cell edit and it is
  **not this lane's file**; Wave A is file-disjoint by design and `methodology.py`
  is unowned in it, so changing it here would set exactly the precedent the wave's
  conflict notes exist to prevent. H6 is the natural owner (it is already the
  "what a label may claim" lane). The equivalent line in `docs/METHODOLOGY.md`
  *was* this lane's and is fixed.
