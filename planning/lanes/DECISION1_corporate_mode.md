# Decision 1 for corporate — flip `CORPORATE_APP_MODE` to `derived`

*Pre-registered 2026-09-05 against `main` @ `ee5f563`, in this lane's first
commit, before any module was touched. Outturn appended at the end, in the last
commit.*

This lane makes **one decision and no model**. Nothing is derived, no constant
is retuned, no target moves, and no mechanism is added: the whole of the change
is one module-level string, the docstring table that explains it, the
user-facing caption Decision 6 owes for the numbers that move with it, and the
tests that pin all three.

The reason it needs a lane at all is that the constant it flips is the app's
default, so flipping it moves two shipped presets, two composite packages, every
Tailor corporate row, the Ask assistant's corporate hypotheticals and three
scorecard rows — and the margin it turns on is **1.31 percentage points**. The
owner pre-authorised the flip if `derived` still led after
`planning/lanes/W6_corporate_base_projection.md` landed, and it does. The owner
confirms on the PR because the margin is thin; this document exists so that
confirmation is a yes/no rather than a re-derivation.

## 1. The rule, stated before the numbers

`planning/MODELING_IMPROVEMENT.md` §1, owner **Decision 1**:

> `reported` stays the app default per module until that module's derived error
> is below its fitted error across the benchmarks it carries.

and owner **Decision 6**:

> a shipped number that moves ships with a user-facing caption in the same PR.

Both bite here. Decision 1 is satisfied — that is §3 — and Decision 6 is owed on
two presets, two packages, seven Tailor steps and the assistant's corporate
branch, which is §5's commit.

Two things the rule is **not**, worth saying because both were live temptations:

- It is not "derived is better". It is "derived's mean error over this module's
  carried benchmarks is below reported's". §4 says what that mean is made of,
  and it is not a flattering story for either mode.
- It is not a licence to improve the number. **No constant is retuned to make
  the flip look better**, and the falsification tests in §6 are written so that
  any attempt would show up as a moved row somewhere it should not be.

## 2. Starting numbers

All from the branch point, `ee5f563` — the merge of PR #121 (W6's base
projection) and PR #122 (the corporate/PTC provenance lane), which is the first
tree on which this comparison can be taken over three **published** corporate
targets.

### 2.1 The mode constants today

| Constant | Value | Read by |
|---|---|---|
| `CORPORATE_APP_MODE` | **`reported`** | `CorporateTaxPolicy.mode`'s field default, all five factories' `mode=` default, and — because the corporate module has **no separate scorecard constant** — `validation/specialized_business.py`'s `validate_corporate_policy(mode=None)` |
| `CORPORATE_VALIDATION_MODE` | `derived` | `validation/core.py`'s `create_policy_from_score`, i.e. the Tier 1 uncalibrated shape for `cbo_opt64_corporate_rate_1pp` |

**There is no `CORPORATE_SCORECARD_MODE`.** `amt.py` carries two constants
(`AMT_APP_MODE` and `AMT_SCORECARD_MODE`) and `planning/lanes/PROVENANCE_amt_insulin.md`
§2-§3 treats them as separable — both stayed `reported` there, but for two
different reasons, and the lane said so. `corporate.py` carries one, and
`specialized_business.py` defaults to it, so **for corporate the app default and
the by-construction scorecard mode are the same switch and move together**.
That is not a decision this lane makes; it is the shape of the module, and it is
recorded here because the AMT convention would otherwise suggest a second
constant exists to be held back. **Splitting them is not in this lane's scope**
— it would be a new mechanism, and inventing one to keep three scorecard rows
still would be exactly the tuning Decision 1's rule is meant to prevent. It is
carry-over 3 in §9.

`CORPORATE_VALIDATION_MODE` is **not touched**, so Tier 1 must not move at all.

### 2.2 Both modes, all three carried benchmarks — `validate_all_corporate(mode=...)`

| Benchmark | Provenance | Target | `reported` | Err | `derived` | Err | Winner |
|---|---|--:|--:|--:|--:|--:|---|
| `biden_corporate_28` | `line_item_differs` (scope) | −$1,347.0B | −$1,397.21B | **−3.73%** | −$1,292.62B | +4.04% | reported, by 0.31pp |
| `biden_corporate_28_fy2022` | `line_item` | −$857.8B | −$1,397.21B | −62.88% | −$1,292.62B | **−50.69%** | derived, by **12.19pp** |
| `trump_corporate_15` | `line_item_differs` (range [+$595.0B, +$673.1B], anchor +$673.1B) | +$673.1B | +$1,491.76B | **+121.63%** | +$1,545.24B | +129.57% | reported, by 7.95pp |
| **Mean abs** | | | | **62.75%** | | **61.43%** | **derived, by 1.31pp** |

Ratings do not move: Excellent / Poor / Poor before, Excellent / Poor / Poor
after.

### 2.3 The shipped surfaces, under today's `reported`

Everything below is what a user sees today. The app window is **FY2026–FY2035**
(`baseline.APP_DEFAULT_START_YEAR = 2026`), which is why the preset figures are
not the benchmark figures in §2.2 — those are scored on FY2025–FY2034, the
window their targets are quoted for.

| Surface | Today |
|---|--:|
| 🏢 Biden Corporate 28% (CBO: −$1.35T) | **−$1,397.21B** |
| 🏢 Trump Corporate 15% | **+$1,491.76B** |
| Package *Biden FY2025 Tax Plan* | −$2,170.68B |
| Package *Progressive Revenue Package* | −$4,821.29B |
| Tailor corporate −6pp / −2pp / −1pp | +1,197.61 / +399.20 / +199.60 |
| Tailor corporate +1pp / +2pp / +5pp / +7pp | −199.60 / −399.20 / −998.01 / −1,397.21 |
| Ask `score_hypothetical_policy` corporate −6pp / +4pp / +7pp (FY2025 window) | +1,197.61 / −798.41 / −1,397.21 |

**45 of the 53 `PRESET_POLICIES` entries build a policy through
`create_policy_from_preset`; 2 of those 45 are `CorporateTaxPolicy`.** The other
8 entries carry a bare `rate_change`/`threshold` and are built as `TaxPolicy` by
`ui/policy_execution.py`, so none of them can reach the corporate module. **10 of
the 12 composite packages** contain no corporate preset.

### 2.4 The tiers, and the gates

| | `ee5f563` |
|---|---|
| Tier 1 (out-of-sample) | **26 @ 15.20% mean / 11.40% median**, 16 within 15%, 22 within 25% |
| Fitted calibrated | **21 @ 1.733%**, 21/21 within 15% |
| Unfitted reconstructions | **34 @ 57.556% / 34.15% median**, 9/34 within 15%, 13/34 within 25% |
| `cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | exit **0** |
| `run_loo.py --donor-matrix` | exit 0; **no `Corporate` row exists in the suite** |
| `run_validation_dashboard.py` | exit **1**, pre-existing: `runtime` (Python 3.14.0 against `>=3.10,<3.14`) and `microdata` (SOI 2023 coverage 119% returns / 81% AGI) |
| `check_readiness.py --strict` | exit **2** (`ready_with_warnings`) |
| `strict_readiness_issues` | **`[('runtime', None)]`** |
| `check_streamlit_boot.py` | exit **0** |
| `ruff check` | **0** |

## 3. The decision, and what it turns on

**Derived leads, 61.43% against 62.75%, so Decision 1's rule says flip.** The
rule is satisfied on its own terms and this lane applies it. What follows is
what the margin is made of, because a 1.31pp lead over three rows two of which
are missed by more than double is not the same claim as "the derived path is
right".

### 3.1 The composition: one row won, two lost

| | Δ (derived − reported), pp | Direction |
|---|--:|---|
| `biden_corporate_28` | **+0.31** | derived worse |
| `biden_corporate_28_fy2022` | **−12.19** | derived better |
| `trump_corporate_15` | **+7.95** | derived worse |
| **Mean** | **−1.31** | **derived better** |

Derived wins **one** of three rows and loses the other two. The whole of its lead
is `biden_corporate_28_fy2022`, and 7.95 of the 12.19 points it wins there are
handed straight back on `trump_corporate_15` — the row a user actually sees, as a
preset.

### 3.2 The mean is dominated by rows both modes miss by more than double

Two of the three rows read 50–130% in **both** modes. Their movement therefore
swamps the one row either mode gets close to. Ranking two modes by a mean over a
population like that is what Decision 1's rule literally asks for, and it is also
why the rule is a *tie-break* rather than evidence: on `biden_corporate_28`,
which is the row nearest either mode, reported wins by three tenths of a point.

### 3.3 The module returns **one** number for two published targets 57% apart

This is the finding that most deserves the owner's eye, and it is arithmetic
rather than argument. `biden_corporate_28` and `biden_corporate_28_fy2022` are
the same reform — 21% → 28% — scored by the same factory, and the repository has
no 2021 vintage, so both are scored on FY2025–2034 and **the model returns the
identical figure for both**: −$1,397.21B in `reported`, −$1,292.62B in `derived`.
Their published targets are −$1,347.0B (Treasury FY2025) and −$857.8B (Treasury
FY2022), **57.0% apart**.

So no mode can win both, and moving toward one moves away from the other.
`derived` wins the pair not by tracking a vintage — it cannot, on a single
window with a single transcribed receipts path — but by sitting **lower**:
−$1,292.62B is nearer the midpoint of two targets that straddle nothing the model
can express. That is the honest description of 12.19 of the 13.5 points derived
is ahead on that row.

**What would actually resolve it** is the January 2025 / February 2026 receipts
paths (W6 carry-over 1, blocked: cbo.gov 403s and no Wayback snapshot) plus a
2021 vintage to score the FY2022 row on its own window. Neither is this lane's,
and neither is available.

### 3.4 The row that decides Decision 1 is now published, which is new

Before PR #122 this comparison was taken over two rows, one of which
(`trump_corporate_15`) carried provenance `model_estimate` — the model's own
output written down as an expectation. `SWEEP_offset_sign.md` §7.6 item 1
declined to flip on that basis and was right to. All three rows are now
published targets, which is what makes the comparison decidable at all. It is
also what moved it: on `model_estimate` targets derived led by 3.35pp (9.67% vs
13.02%); on published ones it leads by 1.31pp.

## 4. What flips, mechanically

One constant:

```python
CORPORATE_APP_MODE = CORPORATE_MODE_DERIVED   # was CORPORATE_MODE_REPORTED
```

Three things follow from it, and **all three are consequences of the one line**,
not separate edits:

1. `CorporateTaxPolicy.mode`'s field default and all five factories' `mode=`
   defaults become `derived`, so every app surface scores the derived identity.
2. `validate_corporate_policy(mode=None)` resolves to `derived`, so the three
   corporate scorecard rows report the derived column of §2.2.
3. `results_summary.behavioural_sign_caption` **stops firing** on the Trump
   preset, because its `_offset_sign_changed` branch for `CorporateTaxPolicy` is
   `mode == reported and behavioural < 0`. That is correct — `derived`'s offset
   was already signed before the offset-sign sweep, so "this module returned the
   other sign until 2026-09-05" is not true of the path now scored — but it
   means a caption a user sees today disappears, and §5's caption is what
   replaces it.

`CORPORATE_VALIDATION_MODE` stays `derived` and is not edited.

The module's Decision 1 docstring table is rewritten from the registry-read
figures. `PROVENANCE_corporate_ptc.md` §9 flagged it as stale **in all three
columns** for `trump_corporate_15` (it says target +$1,920.0B, reported −0.1%,
derived −11.5%, provenance `model_estimate`; all four are now false) and left it
for this lane because that file was the corporate lane's.

## 5. The Decision 6 caption

`fiscal_model/ui/tabs/results_summary.py` gains `corporate_base_caption`, added
to `render_headline_block` **after** the existing captions, firing on a
`CorporateTaxPolicy` in `derived` mode with a non-zero rate change. It says the
three things the brief names — the base is projected off the scored vintage, the
behavioural offset is signed to erode, and which mode is in force — and every
number in it is read from the module's own constants and the scored result, so
it cannot drift from the headline above it:

- CBO's projected corporate receipts for `CORPORATE_RECEIPTS_VINTAGE`, first and
  last year of the *scored window*, from `cbo_corporate_receipts`;
- `BASE_PER_DOLLAR_OF_RECEIPTS` and the base it implies in those years, from
  `projected_statutory_base`;
- `BASELINE_TAXABLE_PROFITS_BILLIONS` and `CORPORATE_BASE_GROWTH`, which is what
  the app scored until this PR;
- the behavioural offset's own sign, from `result.behavioral_offset`.

## 6. The prediction

Computed on `ee5f563` by overriding `policy.mode` on every corporate surface,
before `CORPORATE_APP_MODE` was touched. These are **exact** figures, not
tolerances: a flip is a switch, so anything other than an exact match means
something else changed.

### 6.1 The three benchmark rows, under the new default

| Row | Now | Predicted |
|---|--:|--:|
| `biden_corporate_28` | −1,397.21, −3.73% | **−1,292.62, +4.04%** |
| `biden_corporate_28_fy2022` | −1,397.21, −62.88% | **−1,292.62, −50.69%** |
| `trump_corporate_15` | +1,491.76, +121.63% | **+1,545.24, +129.57%** |
| Decision 1 mean, new default | 62.75% | **61.43%** |

### 6.2 Every shipped number that moves

| Surface | Now | Predicted | Move |
|---|--:|--:|--:|
| 🏢 Biden Corporate 28% | −1,397.21 | **−1,310.92** | **+6.18%** |
| 🏢 Trump Corporate 15% | +1,491.76 | **+1,562.75** | **+4.76%** |
| Package *Biden FY2025 Tax Plan* | −2,170.68 | **−2,084.39** | +3.98% |
| Package *Progressive Revenue Package* | −4,821.29 | **−4,735.00** | +1.79% |
| Tailor −6pp | +1,197.61 | **+1,274.24** | +6.40% |
| Tailor −2pp | +399.20 | **+409.30** | +2.53% |
| Tailor −1pp | +199.60 | **+202.72** | +1.56% |
| Tailor +1pp | −199.60 | **−198.86** | +0.37% |
| Tailor +2pp | −399.20 | **−393.86** | +1.34% |
| Tailor +5pp | −998.01 | **−955.68** | +4.24% |
| Tailor +7pp | −1,397.21 | **−1,310.92** | +6.18% |
| Ask hypothetical −6pp (FY2025) | +1,197.61 | **+1,256.45** | +4.91% |
| Ask hypothetical +4pp (FY2025) | −798.41 | **−761.48** | +4.62% |
| Ask hypothetical +7pp (FY2025) | −1,397.21 | **−1,292.62** | +7.49% |

Two properties of that table are the derived identity showing through, and both
are pre-registered as *expected*, not as surprises. The moves are **not uniform
in the rate step** — +0.37% at +1pp against +6.18% at +7pp — because `derived` is
concave in the rate and `reported` is exactly linear. And **every move is in the
same direction**, toward a smaller deficit effect, because the projected base is
below the fitted aggregate aged at 4%/yr everywhere in the app's window.

### 6.3 The tiers

| | Now | Predicted |
|---|---|---|
| Tier 1 | 26 @ 15.1962% / 11.4000% / 16 / 22 | **identical, to the cent, every row** |
| Fitted calibrated | 21 @ **1.7333%** | **21 @ 1.7494%**, exactly one row moves (`biden_corporate_28`), 21/21 within 15% |
| Unfitted reconstructions | 34 @ **57.5559%** / 34.15% median | **34 @ 57.4312%** / 34.15% median, exactly two rows move, 9/34 within 15%, 13/34 within 25% |
| Leave-one-out | 18 @ 29.6% | **byte-identical** — the suite holds no `Corporate` module |

Tier 1 must not move **because it never read this constant**: `cbo_opt64`'s
shape is pinned to `CORPORATE_VALIDATION_MODE`, which is already `derived`. The
prediction is therefore not "small movement" but "no movement", and the
falsification test is written that way.

### 6.4 The gates

| Gate | Predicted |
|---|---|
| `cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | exit **0**, unchanged |
| `run_loo.py --donor-matrix` | **byte-identical** |
| `run_validation_dashboard.py` | exit **1**, unchanged, differing only in the corporate rows and the reconstruction-tier mean |
| `strict_readiness_issues` | **`[('runtime', None)]`**, unchanged |
| `check_streamlit_boot.py` | exit **0** |
| `ruff` | **0** |
| CI thresholds | **not edited** — Tier 1 does not move, so the workflow's own rule re-derives to the 20/21 already there |

### 6.5 Where I expect to be wrong, or to be misread

- **`trump_corporate_15` gets worse and a user sees it.** +121.6% → +129.6%
  against the published range's anchor, on a preset. This is registered as a
  regression, not discovered as one. About a third of that row is scope — the
  preset extends bonus depreciation and neither published estimate includes it
  (`PROVENANCE_corporate_ptc.md` §3 measures the leg at +$294.15B reported /
  +$287.06B derived) — and this lane does not touch it.
- **The fitted tier's mean rises**, 1.7333% → 1.7494%. Trivially, but in the
  wrong direction, and on the row with the strongest document behind it.
- **`biden_corporate_28` is arguably no longer a fitted row after this**, and
  this lane cannot fix that. Its `calibrated_to_target` is `True` because
  `scenarios.py` says so, and `BASELINE_TAXABLE_PROFITS_BILLIONS` is the
  constant fitted to it — but the `derived` path does not read that constant
  (`tests/test_corporate_derived.py::test_the_uncalibrated_path_never_reads_the_fitted_aggregate`
  pins a >15% gap). So after the flip the fitted tier carries a row scored by a
  path with nothing fitted in it. `scenarios.py` is on this lane's prohibited
  list and changing a row's tier to improve a tier mean would be the exact move
  the prohibition exists to stop, so it is **recorded as carry-over 1 in §9** and not
  acted on. Read the fitted 21 @ 1.75% with that attached.
- **Two of three rows still read 50–130%.** Flipping the default does not make
  this module accurate; it picks the nearer of two inaccurate paths. The
  residual is `CORPORATE_PER_POINT_YIELD.md` §5(c) — credit carryforwards under
  §38(c) and §904(c), CAMT, and the individual-side dividend interaction — and
  none of it is in this module's power to close from a published source.
- **A caption disappears as another arrives.** §4 item 3. If the swap were not
  intended it would look like a regression in the offset-sign lane's work; it is
  not, and the tests say so in both directions.

## 7. Falsification tests

Each is a specific thing that, if it fires, is a finding and goes in §9 rather
than being quietly absorbed.

1. **Any non-corporate preset moves.** 43 of the 45 built presets, and all 8
   `TaxPolicy` entries, must be identical to the cent.
2. **Any composite package other than the two naming the Biden corporate preset
   moves.** 10 of 12.
3. **Any scorecard row outside the three corporate benchmarks moves.** 21 fitted
   minus 1, 34 reconstructions minus 2 — 52 rows identical.
4. **Tier 1 moves at all.** It scores `cbo_opt64` through a `mode=derived` pin
   already; a single cent of movement means the flip reached a path it must not.
5. **`run_loo.py --donor-matrix` is not byte-identical.**
6. **Any of the three benchmark rows lands anywhere but the §6.1 figure**, to the
   cent — a flip is a switch, and an unexpected figure means a constant moved.
7. **`strict_readiness_issues` returns anything but `[('runtime', None)]`** —
   in particular a `revenue_scorecard` entry, which is what a Poor on a *fitted*
   calibrated benchmark produces.
8. **The Decision 1 margin is not 1.31pp** on the finished branch, i.e. the two
   means are not 62.75% and 61.43%. This lane may not move them; if they move,
   something was retuned.
9. **`ruff`, `check_streamlit_boot.py` or the CI gate changes exit code.**

## 8. What this lane may not do

- No constant retuned. `BASELINE_TAXABLE_PROFITS_BILLIONS`,
  `PROFIT_SHIFTING_SEMI_ELASTICITY`, `CORPORATE_BASE_GROWTH`,
  `BASE_PER_DOLLAR_OF_RECEIPTS`, `ESTIMATED_PAYMENT_SAME_FY_SHARE`,
  `corporate_elasticity` and every non-rate channel keep their values.
- No target moved, and nothing in `fiscal_model/validation/{preregistered,
  holdout,loo,target_revisions,benchmark_sources,scenarios,cbo_scores}.py`.
- No CI threshold, no `.github/workflows/` edit.
- No docs. `CLAUDE.md`, `README.md`, `docs/`, `planning/NEXT_STEPS.md`,
  `planning/MODELING_IMPROVEMENT.md` and `docs/CHANGELOG.md` are a concurrent
  docs-sync lane's, and this lane does not open them. §10 is the handoff.
- No new mechanism — in particular, **no `CORPORATE_SCORECARD_MODE`**. §2.1.

## 9. Carry-overs this lane opens

Sequencing is the owner's; each names the artefact it lives in.

1. **`biden_corporate_28`'s tier.** After the flip it scores through a path that
   reads no constant fitted to it, while `scenarios.py` still declares
   `calibrated_to_target=True` and the fitted tier still carries it (§6.5). The
   three mechanisms `CLAUDE.md` names for moving a row out of the fitted tier are
   a revised target, a deleted constant and an unfitted reconstruction; **a mode
   flip is a fourth**, and the repository has no rule for it. Deciding it is a
   `scenarios.py` edit, which no modelling lane may make.
2. **`biden_corporate_28` and `biden_corporate_28_fy2022` return one number for
   two targets 57% apart** (§3.3). Closing it needs the January 2025 / February
   2026 receipts paths (W6 carry-over 1, blocked on cbo.gov's 403 and an absent
   Wayback snapshot) plus a 2021 baseline vintage the repository does not have.
3. **Whether corporate should have a `CORPORATE_SCORECARD_MODE`** the way
   `amt.py` does (§2.1). Today the app default and the by-construction scorecard
   mode are one switch. Splitting them is a new mechanism and was deliberately
   not built here.
4. **`trump_corporate_15`'s bonus-depreciation scope gap**, +$287.06B of
   +$1,545.24B in `derived`, against two published figures that price the rate
   change alone. Unchanged from `PROVENANCE_corporate_ptc.md` §3.
5. **The corporate module still has no leave-one-out row** —
   `MODELING_IMPROVEMENT.md` §6.2 item 23, unchanged by this lane and now
   sharper: the shipped app scores a path the cross-validation suite has never
   held out.
6. **The residual.** Two of three rows read 50–130% in both modes. The mechanisms
   are named in `CORPORATE_PER_POINT_YIELD.md` §5(c) and none is buildable from a
   published source this module reads.
7. **`run_validation_dashboard.py` does not print the calibrated tiers' means**
   (§10.5 finding 1), so a change confined to calibrated rows passes the
   repository's own CI dashboard byte-identically. Widening it is a script edit
   and a separate decision; recorded so that "the dashboard is unchanged" is not
   read as stronger evidence than it is.

## 10. Outturn

*Appended 2026-09-05, after the code. Numbers from `python scripts/cold_holdout.py
--json`, `python scripts/run_loo.py --donor-matrix`, `python
scripts/run_validation_dashboard.py`, `validate_all_corporate(mode=...)` and a
sweep of every shipped surface, run on the finished branch and diffed against
the same commands at `ee5f563`.*

### 10.1 Against the pre-registration

| Row | Predicted | Actual | |
|---|---|---|---|
| `CORPORATE_APP_MODE` | `derived` | **`derived`** | as registered |
| `biden_corporate_28` | −1,292.62, +4.04% | **−1,292.62, +4.04%** | as registered |
| `biden_corporate_28_fy2022` | −1,292.62, −50.69% | **−1,292.62, −50.69%** | as registered |
| `trump_corporate_15` | +1,545.24, +129.57% | **+1,545.24, +129.57%** | as registered |
| Decision 1 mean, new default | 61.43% | **61.43%** (reported 62.75%) | as registered |
| Tier 1 | identical, to the cent, every row | **identical** — the `out_of_sample` block of `cold_holdout.py --json` diffs to zero lines | as registered |
| Fitted calibrated | 21 rows, one moves | **21 rows, one moves**; the runner's own summary 1.7% → **1.8%** | as registered |
| Unfitted reconstructions | 34 rows, two move | **34 rows, two move**; summary 57.6% → **57.4%** | as registered |
| Leave-one-out | byte-identical | **byte-identical** | as registered |
| 🏢 Biden Corporate 28% | −1,310.92 (+6.18%) | **−1,310.92** | as registered |
| 🏢 Trump Corporate 15% | +1,562.75 (+4.76%) | **+1,562.75** | as registered |
| Package *Biden FY2025 Tax Plan* | −2,084.39 (+3.98%) | **−2,084.39** | as registered |
| Package *Progressive Revenue Package* | −4,735.00 (+1.79%) | **−4,735.00** | as registered |
| Seven Tailor corporate steps | +0.37% to +6.40%, each figure named | **all seven exactly** | as registered |
| Three Ask hypothetical rows | +4.62% to +7.49%, each figure named | **all three exactly** | as registered |
| Every other preset / package | 43 built presets, 8 `TaxPolicy` entries, 10 packages | **unchanged, to the cent** | as registered |
| `cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | exit 0 | **exit 0** | as registered |
| `strict_readiness_issues` | `[('runtime', None)]` | **`[('runtime', None)]`**, and `check_readiness.py --strict` byte-identical at exit 2 | as registered |
| `check_streamlit_boot.py` | exit 0 | **exit 0** | as registered |
| `ruff` | 0 | **0** | as registered |
| `pytest tests/ -q` | — | **3,525 passed, 7 skipped** (3,518 + 7 at the branch point) | — |
| `run_validation_dashboard.py` | exit 1, differing in the corporate rows and the reconstruction mean | exit 1, **byte-identical** | **missed — finding 1** |

**Every shipped figure landed on the registered number to the cent**, which is
what a flip should do: it is a switch, not a model, and an unexpected figure
would have meant a constant moved. `3,525 tests pass` (7 skipped), 7 of them
new.

### 10.2 The Decision 1 table under the new default

| Benchmark | Target | `reported` | Err | `derived` (**shipped**) | Err |
|---|--:|--:|--:|--:|--:|
| `biden_corporate_28` | −$1,347.0B | −$1,397.21B | −3.73% | **−$1,292.62B** | **+4.04%** |
| `biden_corporate_28_fy2022` | −$857.8B | −$1,397.21B | −62.88% | **−$1,292.62B** | **−50.69%** |
| `trump_corporate_15` | +$673.1B (range [+$595.0B, +$673.1B]) | +$1,491.76B | +121.63% | **+$1,545.24B** | **+129.57%** |
| **Mean abs** | | | **62.75%** | | **61.43%** |

Ratings unchanged in both modes: Excellent / Poor / Poor.

### 10.3 Every shipped number that moved

| Surface | Before | After | Move |
|---|--:|--:|--:|
| 🏢 Biden Corporate 28% (CBO: −$1.35T) | −1,397.21 | **−1,310.92** | **+6.18%** |
| 🏢 Trump Corporate 15% | +1,491.76 | **+1,562.75** | **+4.76%** |
| Package *Biden FY2025 Tax Plan* | −2,170.68 | **−2,084.39** | +3.98% |
| Package *Progressive Revenue Package* | −4,821.29 | **−4,735.00** | +1.79% |
| Tailor −6pp | +1,197.61 | **+1,274.24** | +6.40% |
| Tailor −2pp | +399.20 | **+409.30** | +2.53% |
| Tailor −1pp | +199.60 | **+202.72** | +1.56% |
| Tailor +1pp | −199.60 | **−198.86** | +0.37% |
| Tailor +2pp | −399.20 | **−393.86** | +1.34% |
| Tailor +5pp | −998.01 | **−955.68** | +4.24% |
| Tailor +7pp | −1,397.21 | **−1,310.92** | +6.18% |
| Ask hypothetical −6pp (FY2025 window) | +1,197.61 | **+1,256.45** | +4.91% |
| Ask hypothetical +4pp | −798.41 | **−761.48** | +4.62% |
| Ask hypothetical +7pp | −1,397.21 | **−1,292.62** | +7.49% |

Nothing else moved. **43 of the 45 built presets, all 8 `TaxPolicy` preset
entries and 10 of the 12 composite packages are identical to the cent**, and so
is every scorecard row outside the three corporate benchmarks.

Two shapes in that table are the derived identity showing through and both were
registered in advance. The moves are **not uniform in the rate step** — +0.37%
at +1pp against +6.18% at +7pp — because `derived` is concave in the rate where
`reported` is exactly linear. And **every move is in the same direction**,
toward a smaller deficit effect, because CBO's own projected receipts imply less
base than the fitted $1,900B aggregate aged at 4%/yr does anywhere in the app's
window.

### 10.4 Falsification results

All nine were checked. **One fired**, and in the direction of *less* change than
registered.

| # | Test | Result |
|---|---|---|
| 1 | Any non-corporate preset moves | 43 + 8 identical |
| 2 | Any package but the two naming the Biden corporate preset moves | 10 of 12 identical |
| 3 | Any scorecard row outside the three corporate benchmarks moves | 52 rows identical |
| 4 | Tier 1 moves at all | **`out_of_sample` block diffs to zero lines** |
| 5 | `run_loo.py --donor-matrix` not byte-identical | byte-identical |
| 6 | A benchmark row lands off its registered figure | all three to the cent |
| 7 | `strict_readiness_issues` returns anything but `[('runtime', None)]` | unchanged |
| 8 | The Decision 1 margin is not 1.31pp | 62.75% and 61.43%, pinned by two tests |
| 9 | `ruff`, boot or the CI gate changes exit code | 0 / 0 / 0, unchanged |
| — | `run_validation_dashboard.py` differs as predicted | **byte-identical — finding 1** |

### 10.5 Findings

1. **The repository's own CI dashboard cannot see this flip.**
   `run_validation_dashboard.py` is **byte-identical** before and after, where
   the pre-registration expected it to move. It prints health components,
   distributional calibration, the out-of-sample tier and the leave-one-out
   suite — and **not** the calibrated tiers' means — so a change confined to
   three calibrated rows passes it invisibly. The two tier means did move
   (fitted 1.7% → 1.8%, reconstructions 57.6% → 57.4%) and are visible only in
   `cold_holdout.py --json`. That is not an argument for widening the
   dashboard here; it is a note that "the dashboard is unchanged" is weaker
   evidence about this class of change than it reads, and it is carry-over 7.

2. **The mean that decided the app default rose in the fitted tier and fell in
   the reconstruction tier, and neither movement is an accuracy claim.** The
   fitted tier's 1.7% → 1.8% is `biden_corporate_28` moving 3.73% → 4.04% —
   the row with the strongest document behind it, going the wrong way. The
   reconstruction tier's 57.6% → 57.4% is 12.19 points won on
   `biden_corporate_28_fy2022` net of 7.95 lost on `trump_corporate_15`. Both
   are composition inside a decision, not evidence for it.

3. **`biden_corporate_28` is now a fitted row scored by a path with nothing
   fitted in it.** `BASELINE_TAXABLE_PROFITS_BILLIONS` is the constant fitted to
   that target, `scenarios.py` still declares `calibrated_to_target=True`, and
   the `derived` path does not read the constant —
   `test_the_uncalibrated_path_never_reads_the_fitted_aggregate` pins a >15%
   gap. So the fitted tier's 21 rows now include one whose scored path is a
   reconstruction. `CLAUDE.md` names three mechanisms that move a row out of the
   fitted tier — a revised target, a deleted constant, an unfitted
   reconstruction — and **a mode flip is a fourth the repository has no rule
   for**. `scenarios.py` is on this lane's prohibited list and moving a row's
   tier to improve a tier mean would be exactly what the prohibition exists to
   stop, so it is recorded as carry-over 1 and not acted on. **Read the fitted
   21 @ 1.8% with that attached.**

4. **A caption disappeared as another arrived, on the same preset.**
   `behavioural_sign_caption`'s corporate branch fires only in `reported` mode —
   `derived`'s offset was already signed before the offset-sign sweep — so Trump
   Corporate 15% stopped carrying the sign note and started carrying
   `corporate_base_caption`. That is correct in both directions and neither is a
   silence: the sign note would have been false about the path now scored, and
   the flip's own move is the larger one. Both are asserted, in
   `test_the_caption_fires_on_exactly_the_presets_the_sweep_moved`, so "the
   caption disappeared" and "the caption was replaced" cannot be confused.

5. **The app's window outruns the transcribed receipts path by a year, and the
   caption now says so.** `APP_DEFAULT_START_YEAR` is 2026, so the app scores
   FY2026-2035 while CBO's February 2024 table ends at FY2034; FY2035 is the
   module's own continuation of the terminal growth rate. `reported` mode could
   not expose this because its base was a growth rule with no published years in
   it. Nothing is wrong — `cbo_corporate_receipts` documents the rule and a test
   pins it — but a published figure and an extrapolated one were about to be
   printed side by side under a user's headline, and now they are labelled.

6. **`cold_holdout.py --json` rounds `abs_percent_error` to a tenth**, so a tier
   mean recomputed from the JSON differs in the third decimal from one computed
   on unrounded errors: 1.7476 against the 1.7494 this lane registered, and
   57.4324 against 57.4312. Immaterial, recorded because the prediction was
   stated to four decimals and the difference is arithmetic on the file rather
   than movement in the model.

### 10.6 The tests, and which edits the flip forced

`tests/test_corporate_derived.py` — **four forced, six added.** Forced:
`test_reported_is_exactly_linear_in_the_rate_step` and `test_reported_mode_pins`
both relied on the module default being `reported` and now name the mode;
`test_the_app_default_is_reported` became
`test_the_app_default_is_derived`; and the Decision 1 test's closing assertion
flipped. **The comparison itself was not deleted** — both means stay pinned to
0.6275 and 0.6143, so a lane that improved the margin by retuning a constant
fails there rather than passing quietly. Added: the scorecard runner follows the
app default; derived-mode pins; every corporate preset equals the derived
figure; the margin is one row of three (including that the two Green Book rows
return one model number for targets 57% apart); and the two caption tests.

`tests/test_offset_sign_contract.py` — **two forced, one corrected beyond what
was forced, and it is named here because the brief asks.**
`test_the_caption_fires_on_exactly_the_two_presets_that_moved` had to change
(the corporate preset no longer carries the sign caption) and now asserts both
halves of finding 4 rather than a smaller number.
`test_the_caption_carries_the_scored_figures_and_the_old_headline` names
`reported` explicitly. The third, `test_the_caption_stays_silent_on_a_rate_increase`,
**passed after the flip without being touched — for the wrong reason**: it
asserts a silence that used to mean "an `abs()` and the signed rule agree on a
positive static" and would now have meant "this is not `reported` mode". It now
names the mode too. That is one edit beyond what the flip forced, and it is a
test that had quietly stopped testing its own claim.

`tests/test_cbo_regression.py` — **one forced, one added.** The corporate band
was `[-1460, -1330]` around `reported`'s −$1,397.2B and is now `[-1355, -1230]`
around `derived`'s −$1,292.6B. The added test pins `reported` at −$1,397.21B
under an explicit `mode=`, so that if a later lane retunes a corporate constant
the band moving would no longer look like a decision.

`tests/test_cold_holdout.py` — **untouched**, as required, and it did not need
touching: Tier 1 did not move.

### 10.7 What this lane did not do

- Did not retune a constant. `BASELINE_TAXABLE_PROFITS_BILLIONS`,
  `PROFIT_SHIFTING_SEMI_ELASTICITY`, `CORPORATE_BASE_GROWTH`,
  `BASE_PER_DOLLAR_OF_RECEIPTS`, `ESTIMATED_PAYMENT_SAME_FY_SHARE` and
  `corporate_elasticity` are byte-identical, and `reported` mode scores
  −$1,397.21B and +$1,491.76B after the flip exactly as before it — pinned, so
  the claim is checkable rather than asserted.
- Did not touch any target, or `preregistered.py`, `holdout.py`, `loo.py`,
  `target_revisions.py`, `benchmark_sources.py`, `scenarios.py`,
  `cbo_scores.py`, `KNOWN_SCORES` or `CBO_SCORE_MAP`.
- Did not move `CORPORATE_VALIDATION_MODE`, which is why Tier 1 is identical.
- Did not edit a CI threshold or a workflow. Tier 1 did not move, so the
  workflow's own rule re-derives to the 20 / 21 already there.
- Did not touch `fiscal_model/app_data.py`. Neither corporate preset's
  description quotes a model figure: the Biden entry quotes CBO's −$1.35T target
  and the Trump entry quotes the published +$595B–$673B range, both of which are
  targets and neither of which moved. The 2026-09-05 provenance lane had already
  removed the "~$1.9T" that was this model's own output quoted back at users.
- Did not build a `CORPORATE_SCORECARD_MODE`, did not open `reported` mode, did
  not touch the four unsourced non-rate channels, and did not open any docs file
  — those are the concurrent docs lane's and §11 is the handoff.
- **Did not edit `scripts/audit_offset_signs.py`**, which is outside this lane's
  files and now carries one false line: its `CorporateTaxPolicy [reported]` case
  is annotated *"CORPORATE_APP_MODE — what the shipped app scores"*, and it is
  not any more. The script still runs and its sweep is unaffected — it names
  both modes explicitly rather than reading the default — so this is a stale
  note, not a break. §11 carries it.

## 11. Handoff to the docs lane

`CLAUDE.md`, `README.md`, `docs/`, `planning/NEXT_STEPS.md`,
`planning/MODELING_IMPROVEMENT.md` and `docs/CHANGELOG.md` were **not touched**.
The rows this branch invalidates:

| File | Says today | Should say |
|---|---|---|
| `CLAUDE.md`, Wave 5 §, corporate | "`CORPORATE_APP_MODE` stays `reported` under Decision 1 (1.92% against derived's 9.67%), so no shipped number moved" | on three published targets it is **62.75% reported against 61.43% derived**, the module **flipped to `derived` on 2026-09-05**, and **two presets, two packages, every Tailor corporate row and the assistant's corporate branch moved with it** |
| `CLAUDE.md` "Model maturity" + "Target Validation", fitted tier | "23 fitted at 1.6%" (already stale after PR #119/#122: the tier is 21) | **21 @ 1.8%**, up from 1.7%, the whole of the rise being `biden_corporate_28` 3.73% → 4.04% — and carrying **one row whose scored path reads no constant fitted to it** (finding 3) |
| `CLAUDE.md` Target Validation, reconstruction tier | "31 rows at 56.6%" (stale; PR #122 left it 34 @ 57.6%) | **34 @ 57.4% / 34.2% median**, 9/34 within 15%; the constant-population read is the same 34 rows, and the −0.1pp is 12.19 points won on `biden_corporate_28_fy2022` net of 7.95 lost on `trump_corporate_15` |
| `CLAUDE.md` Target Validation, the corporate benchmark rows | `biden_corporate_28` model −$1,397B / 3.7% in the examples table | **−$1,293B / 4.0%**, and the table's "Corporate 21%→28%" row with it |
| `CLAUDE.md`, every statement that a module keeps `reported` as the app default | "Every module keeps `reported` as the app default under Decision 1" (Waves 2, 3, 4, 5) | **corporate is the first module to leave `reported`**; AMT and the rest are unchanged |
| `docs/VALIDATION.md` corporate rows | still on pre-PR-#122 figures — line 491 reads "Trump corporate 15% \| $1,920B \| $1,918B \| −0.1%", and line 866 "Biden 21% to 28% \| −$1,347B \| −$1,397B \| 3.7%"; PR #122's own §10 already flagged both | model **−$1,292.6B** on the two Green Book rows and **+$1,545.2B** on `trump_corporate_15`, errors +4.04% / −50.69% / +129.57%, against targets −$1,347.0B / −$857.8B / +$673.1B |
| `docs/METHODOLOGY.md` §"Corporate Tax" (l. 452, 467) and the limitations table (l. 1339) | "ΔRevenue = ΔRate × Corporate_Taxable_Income"; "calibrated to CBO's −1.347T (model: −1.397T, error 3.7%)"; "Corporate rate +1pp \| −$136B \| −$220B \| 62%" | the shipped path is CBO's own projected corporate receipts × 4.80133 with an IRC §6655 convolution, not a fitted $1,900B aggregate; the model is **−$1,293B, 4.0%**; and the +1pp row has been **−$196B, 44.5%** since PR #121, so that line was already stale |
| `planning/MODELING_IMPROVEMENT.md` §6 | W6 carry-over 4, "Decision 1 for corporate is due a re-measure" | **done**; and this lane's six carry-overs (§9) join the list, of which carry-over 1 (a mode flip as a fourth mechanism moving a row out of the fitted tier) needs an owner rule |
| `planning/NEXT_STEPS.md` | — | the corporate flip, and that it is the first Decision 1 flip in the repository |
| `docs/CHANGELOG.md` | — | the flip, the two presets, the two packages and the caption |
| `scripts/audit_offset_signs.py` l. 261 | the `[reported]` case is noted "CORPORATE_APP_MODE — what the shipped app scores" | it is not, since 2026-09-05; the `[derived]` case is. One line, and the script's behaviour does not depend on it |
