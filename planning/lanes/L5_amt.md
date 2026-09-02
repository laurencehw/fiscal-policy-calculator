# Lane L5 — AMT: a live exemption path and a 2026 sunset ramp

*Pre-registered 2026-09-01 against `main` @ `cff6b88`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §3 L5, under §4's rules and owner
Decision 1 (reported vs derived mode, accepted 2026-09-01).

## 1. Starting numbers

All from the branch point, `python scripts/run_loo.py --donor-matrix` and
`python scripts/cold_holdout.py` on `cff6b88`.

### Leave-one-out (the lane's yardstick)

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| AMT | `extend_tcja_amt` | 450.0 | 450.5 | 779.5 | **+73.2%** |
| AMT | `repeal_individual_amt` | 450.0 | 450.5 | 836.9 | **+86.0%** |
| AMT | `repeal_corporate_amt` | 220.0 | 220.1 | — | not cross-validatable |

AMT module mean 79.6% (n=2 derivable, 1 excluded by the leakage guard).
**Suite aggregate: 59.3% mean / 35.6% median over 18 derivable cases, 6/18
within 15%, 4 not cross-validatable.**

### Fitted (by-construction) errors for the same three benchmarks

| Benchmark | Target | Fitted model | Fitted err |
|---|--:|--:|--:|
| `extend_tcja_amt` | $450B | $450.5B | **0.1%** |
| `repeal_individual_amt` | $450B | $450.5B | **0.1%** |
| `repeal_corporate_amt` | $220B | $220.1B | **0.0%** |

### Battery aggregates

- Tier 1 (out-of-sample): **25 cases, 52.6% mean, 8/25 within 15%, 14/25 within 25%.**
- Calibrated fitted tier: **34 policies, 2.7% mean, 33/34 within 15%.**
- Unfitted module reconstructions: **20 policies, 250.8% mean, 4/20 within 15%.**

## 2. What the lane changes

Two defects named in §3 L5, both in `fiscal_model/amt.py`.

1. **The exemption-change branch is dead.** `estimate_static_revenue_effect`
   computes `baseline_taxpayers` and `policy_taxpayers` from the *same* call
   (`amt.py:357, 360`), so the branch always returns 0.0 and the three
   expressions above it (`:349-359`) are evaluated and discarded. Fix: baseline
   count from the current-law schedule, policy count from the reform schedule.
2. **No ramp / no year index.** The identity delivers one steady-state
   post-sunset level (~$73B/yr, matching `revenue_post_tcja_2030 = 75.0`,
   `amt.py:119`) for every year of the window. Fix: a year-indexed
   affected-payer and average-liability path, sourced and transcribed under
   `fiscal_model/data_files/`.

Plus owner Decision 1: an `AMTPolicy.mode` of `reported` (fitted annual) or
`derived` (structural path). Derived becomes the default in the validation
entry point; the app's presets stay on `reported` unless derived beats fitted.

## 3. The prediction

**Headline: I expect both individual-AMT rows to move *away* from the carried
target, not toward it, and I am pre-registering that rather than tuning to
avoid it.**

§3 L5 hypothesised that the missing 2026 ramp biases the derivation high and
that phasing it in "would close most of this". The published data contradicts
the hypothesis before a line of code is written. TPC's T25-0049 (April 2025,
baseline = law in place as of 1 January 2025, i.e. with the TCJA sunset still
in law) shows the sunset as a **cliff, not a ramp** — AMT payers go 0.2M in
2025 to 7.6M in 2026 — and the post-sunset path then *grows*, from $71.6B in
2026 to $124.2B in 2035. The module's steady-state $73B/yr is therefore the
window's **early-year** level, not its average. A correctly year-indexed path
scores *higher* than the flat one, not lower.

The reason the rows cannot come down is a target problem the repository has
already documented and this lane is forbidden to fix (§1.6, §4):
`fiscal_model/validation/benchmark_sources.py` records `extend_tcja_amt`'s
published line item as **$1,357.1B** (CRS R48286 Table 1, transcribing CBO
pub. 60114) with the note that the *five*-year figure is $466.2B — "the carried
target looks like a five-year number sitting in a ten-year column" — and
records for `repeal_individual_amt` that "$450B looks low on its face".

### Rows I expect to move, and how far

| Row | Now | Predicted | Direction |
|---|--:|--:|---|
| LOO `extend_tcja_amt` | +73.2% | **+85% to +95%** | worse vs the carried target |
| LOO `repeal_individual_amt` | +86.0% | **+105% to +115%** | worse vs the carried target |
| LOO suite mean (n=18) | 59.3% | **61% to 63%** | worse by ~2pp |
| Fitted `extend_tcja_amt` | 0.1% | **~90%** | derived replaces the fitted constant in validation |
| Fitted `repeal_individual_amt` | 0.1% | **~110%** | same |
| Fitted `repeal_corporate_amt` | 0.0% | **~15%** | same; no year data exists for CAMT, so derived = the flat $22B/yr base |
| Fitted tier mean (n=34) | 2.7% | **~9%** | 33/34 to ~30/34 within 15% |

Point predictions from the arithmetic, before the code exists: the derived
10-year cost of extending TCJA AMT relief is **~$860B** (TPC's post-sunset path
2026-2035 sums to $948.9B; the TCJA-regime counterfactual, TPC's 0.2M payers at
their own $29,740 per payer grown at the table's 2024-to-2025 rate, sums to
~$87B), and derived full repeal from 2026 is **~$949B**.

### The number that should improve

Against the **published line item** rather than the carried target,
`extend_tcja_amt` goes from **-66.8%** (fitted $450.5B vs $1,357.1B) to about
**-37%** (derived ~$860B vs $1,357.1B). That is the claim this lane is actually
making: the structural path lands roughly twice as close to the document as the
fitted constant does, and the fitted constant only looks good because it
reproduces a target its own provenance record says is wrong.

Definitional caveat, stated up front: CRS/CBO's $1,357.1B is scored inside a
full TCJA-extension package, where extended rate cuts push far more filers into
AMT; TPC's path is a standalone current-law sunset. They are different
counterfactuals, both published, and the derived model reconstructs TPC's.

### Rows I expect NOT to move

- **No Tier 1 row.** No pre-registered out-of-sample case runs `AMTPolicy`.
  Tier 1 should stay at 52.6% / 8 / 14 exactly.
- **No unfitted-reconstruction row.** `pl119_21_amt_exemption` is scored by the
  TCJA module (`create_tcja_extension(extend_amt=True)`), not by `AMTPolicy`;
  the 20-case reconstruction mean should stay at 250.8% exactly.
- **No other LOO module.** Payroll, Estate, Credits, Expenditures and Capital
  Gains share no code with `amt.py`.
- **App preset output.** The app default stays `reported`, so every shipped AMT
  preset scores exactly what it scores today, including the
  `create_repeal_corporate_amt()` regression band [210, 232].

Anything that moves outside this list is a finding, and gets written into §4.

## 4. Outturn

*Appended 2026-09-01, after the code. Numbers from `python scripts/run_loo.py
--donor-matrix`, `python scripts/cold_holdout.py` and
`python scripts/run_validation_dashboard.py` on the finished branch.*

### Leave-one-out

| Case | Official | By-constr | LOO before | LOO after | Err before | Err after |
|---|--:|--:|--:|--:|--:|--:|
| `extend_tcja_amt` | 450.0 | 450.5 | 779.5 | **855.3** | +73.2% | **+90.1%** |
| `repeal_individual_amt` | 450.0 | 450.5 | 836.9 | **948.9** | +86.0% | **+110.9%** |
| `repeal_corporate_amt` | 220.0 | 220.1 | — | — | not cross-validatable | unchanged |

AMT module mean 79.6% → **100.5%**. Suite aggregate 59.3% → **61.7%** mean,
median **35.6%** (unchanged), **6/18** within 15% (unchanged), 18 derivable and
4 not cross-validatable (unchanged). Ceiling 75%: passes.

### Against the pre-registration

| Row | Predicted | Actual | |
|---|--:|--:|---|
| LOO `extend_tcja_amt` | +85% to +95% | **+90.1%** | in band |
| LOO `repeal_individual_amt` | +105% to +115% | **+110.9%** | in band |
| LOO suite mean | 61% to 63% | **61.7%** | in band |
| Derived extend, 10-year | ~$860B | **$855.3B** | 0.5% off the hand arithmetic |
| Derived repeal, 10-year | ~$949B | **$948.9B** | exact |
| Tier 1 | 52.6% / 8 / 14, unmoved | **52.6% / 8 / 14** | as registered |
| Unfitted reconstructions | 250.8%, unmoved | **250.8%** | as registered |
| Other LOO modules | unmoved | **unmoved** | as registered |
| App presets | unmoved | **unmoved** | as registered |
| Fitted tier mean | ~9% (33/34 → ~30/34) | **2.7%, 33/34** | **missed — see finding 3** |

Every registered row landed where it was registered except the fitted tier,
which did not move because the scorecard flip was not made. That is a scope
change, not a modelling surprise, and it is written up below rather than
quietly absorbed.

### Reported vs derived, per benchmark

| Benchmark | Carried target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `extend_tcja_amt` | $450B | $450.5B | +0.1% | **$855.3B** | +90.1% |
| `repeal_individual_amt` | $450B | $450.5B | +0.1% | **$948.9B** | +110.9% |
| `repeal_corporate_amt` | $220B | $220.1B | +0.0% | **$252.2B** | +14.6% |

**App default stays `reported`** under Decision 1's own rule: derived does not
beat fitted on the carried benchmarks. Nothing a user sees changes.

Against the **published line item** instead of the carried target — CRS R48286
Table 1, transcribing CBO pub. 60114, $1,357.1B over FY2025-2034, recorded in
`validation/benchmark_sources.py`:

| `extend_tcja_amt` | vs $1,357.1B |
|---|--:|
| Reported (fitted $450.5B) | **-66.8%** |
| Derived ($855.3B) | **-37.0%** |

That is the lane's result. The structural path is *closer to the document* than
the fitted constant, by a factor of about 1.8, while scoring worse against the
carried target — which is only possible because the carried target and the
document disagree.

### Findings

1. **The plan's ramp hypothesis is wrong, and the data says so plainly.**
   §3 L5 and `VALIDATION_NOTES.md` §6 both attribute the AMT overshoot to a
   missing 2026 phase-in: "a LOO derivation that phased the ramp in would close
   most of this". TPC T25-0049 shows a cliff — 0.2M AMT payers in 2025, 7.6M in
   2026 — and then *growth*, $71.6B to $124.2B by 2035. The flat ~$73B/yr was
   the window's early-year level, not its average, so indexing the path by year
   raises the score. There is no ramp to add. `tests/test_amt_derived.py`
   pins the cliff so a data refresh cannot quietly reintroduce the assumption.
2. **Interpolating the average liability separately is not safe.** The first
   implementation interpolated payer count and average liability between the
   two regime anchors and multiplied them. Both are individually monotone in
   the exemption — the count falls, the average rises — but their product turns
   upward, so a +$25K exemption increase priced as a revenue *gain*. Revenue
   and payers are each interpolated now and the average is their ratio. This
   was caught by writing the sign test before trusting the shape, and it is
   the kind of defect the dead branch had been hiding: with the branch
   returning 0.0, no exemption change had ever been scored at all.
3. **The scorecard half of Decision 1 is blocked by a locked protocol, not by
   the model.** Decision 1 asks for `derived` to become the default in
   validation. It is the default in the *held-out* path (`run_amt_loo`), which
   is where the honesty claim lives. It is **not** the default in the
   by-construction scorecard, and deliberately so: `repeal_individual_amt` is a
   locked id in `validation/holdout.py`'s
   `revenue-scorecard-post-lock-2026-05-02` protocol, and
   `fiscal_model/readiness.py` **hard-fails** strict readiness on any holdout
   entry rated Poor. Derived rates it Poor at +110% against a target
   `benchmark_sources.py` already records as a five-year figure. Flipping it
   would fail a release gate for a reason that has nothing to do with model
   quality, and loosening the gate to get green is exactly what §4 forbids.
   `AMT_SCORECARD_MODE` in `fiscal_model/amt.py` is the one line that flips it
   once the owner has settled the target. **This needs an owner decision**, and
   it is the same decision as correcting the `extend_tcja_amt` /
   `repeal_individual_amt` targets — E-provenance work, not a modelling lane.
4. **Derived repeal reproduces TPC's revenue column exactly.** Scoring
   `repeal_individual_amt` in derived mode returns $71.6B, $74.7B, $80.0B …
   $124.2B — TPC's printed path, year for year. That started as a plumbing
   check but it is also the substantive claim: for that policy the model no
   longer approximates a projection, it *is* one, and the residual against the
   benchmark is entirely the benchmark's.
5. **The definitional gap between the two published figures is real and should
   not be split.** TPC's path is a standalone current-law sunset. CRS/CBO's
   $1,357.1B is the AMT provision scored inside a full TCJA-extension package,
   where extended rate cuts push far more filers into AMT. Both are published;
   they answer different questions. The derived model reconstructs TPC's, which
   is why -37% and not 0% is the honest expectation against the CRS row.

### What the lane did not do

- Did not touch any target, `preregistered.py`, the yardstick scripts, the
  leakage guard, or any CI threshold.
- Did not add a per-benchmark constant. The module gained one data file, one
  extrapolation rule applied identically to both regimes, and one interpolation
  shape that was already the module's.
- Did not change `AMT_EXEMPTIONS_TCJA` or `AMT_EXEMPTIONS_TCJA_EXTENDED`. Both
  still fall back to their 2034 row past the table's end, which is harmless
  here because each benchmark sits exactly on a regime anchor.
- Did not model the phase-out thresholds. `phase_out_threshold_change` is still
  declared and never read; `AMT_PHASEOUT_TCJA` still stops at 2030. Under the
  post-sunset schedule the phase-out is what claws the exemption back from
  high-income filers, so it is the next real structure this module is missing —
  but it needs a published phase-out path, which T25-0049 does not carry.
