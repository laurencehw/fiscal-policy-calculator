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

## 10. Outturn

*Appended in this lane's last commit.*

## 11. Handoff to the docs lane

*Written with the outturn.*
