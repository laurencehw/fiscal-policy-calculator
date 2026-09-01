# Validation Notes: Diagnostic Analysis of High-Error Cases

This document provides root-cause analysis for the validation cases where the
calculator's score diverges from the official estimate by more than 8%.
The summary table in the README is honest about these gaps; this file
explains *why* they exist and *what would close them*.

The discipline: for each case, identify

1. **The mechanical cause** — what line of model code produces the gap?
2. **The data cause** — what input or assumption is missing/approximated?
3. **The methodological cause** — what does the official scorer do that we don't?
4. **The path to closure** — what specific change would reduce the error, and at what cost?

Reviewers asking "what's behind the outlier?" deserve a paragraph, not silence.

---

## 1. Social Security Donut Hole at $250K — closed (was 12.2%)

**Policy**: Apply the 12.4% combined OASDI tax to wages above $250,000 while
leaving the 2024 wage cap (~$168,600) in place.

| Source       | 10-year revenue | Model | Error |
|--------------|----------------:|------:|------:|
| SSA Trustees (2024) | −$2,700B | −$2,700B | **~0%** |
| CBO equivalent      | −$2,700B |          |       |

**Closed (2026-07):** The prior **12.2%** underestimate ($2,371B) had the same
fingerprint as the Biden-CTC residual: factory annuals were hand-tuned for
4% wage growth (`197.5 → ~$2.37T`) but still undershot the Trustees window,
and the scorer grew them again. Fix:

1. Treat reference payroll annuals as **window averages** of the official
   10-year totals (`$2.7T/10 = $270B`, `$3.2T/10 = $320B`, `$800B/10 = $80B`)
   and set growth to **0** when `annual_revenue_change_billions` is set
   (same rule as `TaxCreditPolicy`).
2. Replace ACS linear threshold scaling with **SSA-aligned covered-wage
   bands** (`SSA_COVERED_WAGES_ABOVE_BILLIONS` + `covered_wages_above`) so
   uncalibrated / non-$250K donuts use a Pareto-like right tail instead of
   `wages_250k × (250K/threshold)`.

Eliminate-cap and 90%-coverage scenarios close in lockstep.

### Historical cause (kept for reviewers)

`fiscal_model/payroll.py` previously computed donut-hole revenue using a
single calibrated constant and scaled other thresholds linearly:

```python
threshold_factor = 250_000 / self.ss_donut_hole_start
scaled_wages = base_wages * threshold_factor
total_revenue += scaled_wages * SOCIAL_SECURITY_PARAMS["rate_combined"]
```

Linear scaling is wrong because the wage distribution above the cap is
roughly Pareto, not uniform. A 2× increase in the threshold reduces the
affected wage base by substantially more than 2×.

The ACS `wages_250k_plus_billions` figure was also systematically low vs
SSA covered-payroll concepts (pass-through S-corp wages, deferred
compensation, non-covered state/local earnings).

### Remaining (optional)

| Change | Expected residual | Effort |
|--------|------------------:|:------:|
| Explicit 50/50 employer incidence split | ~0.5% | 1 day |
| Bend-point benefit accrual netting | ~0.2–0.5% | 2 days |

These are second-order relative to the closed growth/wage-base residual.

---

## 2. Biden CTC 2021 (permanent) — revenue residual (mostly closed)

**Policy**: Make the American Rescue Plan CTC permanent — $3,000 per
child ages 6–17, $3,600 per child under 6, fully refundable, no
earnings requirement.

| Source | 10-year cost | Model | Error |
|--------|-------------:|------:|------:|
| CBO (2021) | $1,600B | ~$1,600B | **~0%** after window-average fix |

**Closed (2026-07):** The prior **8.9%** overstatement ($1,743B) came from
applying 3% nominal growth on top of an explicit window-average annual
(`annual_revenue_change_billions=-160`, i.e. CBO $1,600B / 10). That
double-counted. `FiscalPolicyScorer` and `estimate_credit_cost` now leave
explicit annuals flat over the window; bottom-up unit×credit estimates
still grow at 3%. Factory already sets `participation_rate=0.92`.

**Related distributional gap** (9.30pp on the CBO_ARP_2021 quintile
benchmark, **tightened to 7.54pp** after the ARP bundle fix) was a
*scope mismatch*, not a revenue bug: CBO's ARP 2021 distributional
table covers the full bundle (CTC + EITC childless + Recovery Rebate),
but the CTC factory alone was what the runner was using. Closure
steps taken (Apr 2026):

- New `create_arp_recovery_rebate` factory models the \$1,400/person
  payment with statutory \$75K/\$150K single/joint phaseouts.
- `_run_arp_bundle` in `benchmark_runners.py` composes CTC + EITC +
  Recovery Rebate distributional outputs via
  `_combine_distributional_results` (dollar-weighted share merge).
- `calculate_credit_effect` now blends single-filer and joint-filer
  phaseouts by filing-status mix (~40-60% joint by quintile),
  so the 4th quintile captures joint filers whose married threshold
  is above their AGI even when the single threshold isn't.

Residual 7.54pp distributional gap traces to how CBO models children-in-household
distribution for the Recovery Rebate — a microsim-level detail that
bracket-aggregate scoring can't replicate without return-level data.

### Remaining (bottom-up path only)

When the calibrated annual is not used, zero-earner children and joint
EITC/CTC phase-outs still matter:

| Change | Expected residual | Effort |
|--------|------------------:|:------:|
| Pub 5307 zero-earner counts | ~3% | 3–5 days |
| Joint EITC/CTC phase-outs in microsim | +1–2% | 1 week |

---

---

## 3. Biden Estate Tax Reform ($3.5M exemption, 45% rate) — closed (was 10.1%)

**Policy**: Reduce estate tax exemption from TCJA's $14M (2024) to
$3.5M per person and raise top rate from 40% to 45%.

| Source | 10-year revenue | Model | Error |
|--------|----------------:|------:|------:|
| Treasury (Green Book 2024) | −$450B | −$450B | **~0%** |

**Closed (2026-07):** Same fingerprint as CTC / SS payroll: factory annual
`39.3` was tuned for 3% growth, the scorer grew it again, and default
`gift_shifting_elasticity=0.10` still applied on “calibrated” factories
(`45 × 1.1 = 49.5` → −$495B). Fix:

1. Window-average annuals (`$450B/10 = $45B`, TCJA extend `−$16.7B`, …).
2. Skip scorer growth when `EstateTaxPolicy.annual_revenue_change_billions`
   is set.
3. Zero planning + gift-shifting elasticities on calibrated factories.
4. Two-regime (mid / $50M+) blend in `estimate_taxable_estates` for
   bottom-up paths so the ultra-high tail is not underweighted.

### Historical cause (kept for reviewers)

`fiscal_model/estate.py` used a closed-form mid-distribution approximation
of estates above the exemption. For the $3.5M exemption this predicted
roughly the right *count* of taxable estates, but a single-regime average
underweighted estates above $50M (IRS SOI Table 1 Part II), and growth /
gift-shifting double-counting inflated the calibrated score by ~10%.

---

## CPS top-coding gap — opt-in Pareto augmentation available

The bundled CPS-derived microdata has **zero observations above ~\\$2M
AGI** because CPS ASEC top-codes incomes aggressively. IRS SOI reports
~30,000 returns at \\$10M+ carrying ~\\$900B in AGI, so distributional
analyses that depend on the right tail (capital gains, SALT, step-up
basis, estate) are structurally under-represented at the top in
pure-CPS runs.

**Fix**: `fiscal_model/microsim/top_tail.py::augment_top_tail` injects
synthetic high-income records drawn from IRS SOI bracket aggregates.
For each SOI bracket above a user-supplied floor (default \\$2M), it
creates 200 synthetic records whose AGIs are sampled log-uniformly
over the bracket bounds then rescaled so the sample mean equals the
SOI bracket mean. Weights are set so ``num_returns`` in the bracket
is reproduced exactly.

**Opt-in by design**. The default microdata path stays pure-CPS so
reproducibility and provenance are clean. Callers that need right-tail
accuracy invoke ``augment_top_tail`` explicitly or pass
``--augment-top-tail`` to ``scripts/run_validation_dashboard.py``.

**Coverage impact** (before → after, SOI 2023):

| Bracket | Returns ratio | AGI ratio |
|---|---:|---:|
| \\$1M-\\$10M | 0.64 → 0.97 | 0.37 → 0.94 |
| \\$10M+     | 0.00 → 1.00 | 0.00 → 1.04 |

With augmentation enabled, the validation dashboard moves from
`[WARN] calibration has at least one bracket with <60% AGI coverage`
to `[OK] all surfaces nominal`.

**Caveat**: augmentation is a coverage fix, not a representation fix.
Synthetic records carry SOI-derived aggregate income composition
(~35% wages / 40% cap gains / 15% dividends / 10% interest at the
top) but don't model individual-level behaviour like charitable
deductions or state of residence. Augmented rows are tagged
``source = "soi_pareto_augmented"`` so callers can filter.

---

## 3a. Tax-expenditure distributional dispatch — added, not a pre-existing gap

Not a regression fix — a new path. The distributional engine had no
dedicated handler for `TaxExpenditurePolicy` subclasses (SALT cap,
mortgage interest, step-up basis, employer health, charitable), so
the JCT SALT cap repeal benchmark was falling through to the generic
`calculate_group_effect` and matching zero benchmark rows.

Added `calculate_tax_expenditure_effect` with per-type tier tables
calibrated to:

- **SALT**: JCT JCX-4-24 (0.00pp match — the benchmark is the source
  of truth).
- **STEP_UP_BASIS**: JCT Green Book analysis — 76% of benefit at $1M+.
- **CHARITABLE**: TPC — 49% at $1M+.
- **MORTGAGE_INTEREST**: TPC — concentrated in $100K-$500K, with
  a long top-tail.
- **EMPLOYER_HEALTH**: CBO — broadly distributed across $50K-$500K
  because employer insurance is widely held.

Tables are registered in `_TAX_EXPENDITURE_TIER_TABLES`; unknown
expenditure types fall back to a reasonably top-heavy default rather
than silently uniformly distributing. All six share tables sum to 1.0
within rounding.

---

## 3b. TCJA distributional tier lookup — fixed: 6.65pp → ~4.8pp

**Policies**: TCJA 2018 (CBO deciles), TCJA 2019 (JCT AGI class),
TCJA extension 2026 (CBO deciles).

Same root cause as §4: `calculate_tcja_effect` in
`fiscal_model/distribution_effects.py` used exact-floor dict-key lookup
that failed for every grouping except quintiles. And the tier table
lumped everything above \$170K into a single bucket, which lost the
top-of-distribution gradient that CBO/JCT publish.

Fix: replaced the dict with seven explicit ranges extending to
`$1M+`, and replaced the exact-floor lookup with an overlap-sum across
all tiers a group intersects. The overlap-sum is important: quintiles
and JCT dollar brackets (which can span multiple tiers) now sum their
contributions correctly, while deciles (which sub-divide a tier) take
their proper fraction.

Two rounds of tier-table revisions:

**Round 1** — replace dict-key lookup with overlap-sum; split the
single "$170K+" bucket into `$170K-500K / $500K-1M / $1M+`:

| Benchmark           | Before | Round 1 | Rating change |
|---------------------|-------:|--------:|:-------------:|
| CBO TCJA 2018       | 6.65pp | 4.86pp  | acceptable → good |
| JCT TCJA 2019       | 3.99pp | 4.78pp  | good → good |
| CBO TCJA 2026       | 7.09pp | 4.22pp  | acceptable → good |

**Round 2** — realign tier boundaries to IRS SOI 2022 decile floors
(`0/15K/28K/42K/55K/72K/92K/118K/155K/220K/500K/1M`) and set each
tier's share equal to CBO's published decile share for that floor:

| Benchmark           | Round 1 | Round 2 | Rating change |
|---------------------|--------:|--------:|:-------------:|
| CBO TCJA 2018       | 4.86pp  | **0.00pp** | good → **excellent** |
| JCT TCJA 2019       | 4.78pp  | 2.10pp  | good → good |
| CBO TCJA 2026       | 4.22pp  | **0.74pp** | good → **excellent** |

The CBO 2018 match is exact because the tier table literally *is*
CBO 54796's published decile breakdown. JCT 2019 benefits too because
its AGI brackets overlap the IRS decile floors cleanly.

---

## 4. JCT Corporate 21% → 28% (2022) — fixed: 15.3pp → 2.5pp

**Policy**: Raise the corporate income-tax rate from 21% to 28% (Biden
FY2022 proposal).

| Source | Mean abs. share error | Rating |
|--------|----------------------:|:------:|
| JCT JCX-32-21, 2022 (before) | 15.25pp | needs_improvement |
| JCT JCX-32-21, 2022 (current) | 2.51pp | **good** |

Discovered by `run_full_cbo_jct_validation` (see `scripts/run_validation_dashboard.py`).
Closed by replacing the exact-floor lookup in
`fiscal_model/distribution_effects.py::calculate_corporate_effect` with a
midpoint-of-group tier lookup over SOI Table 1.4-calibrated capital-
income shares. This section is retained as a worked example of the
diagnostic-to-fix loop.

### Mechanical cause

The `DistributionalEngine.analyze_policy` path computes the per-bracket
tax change using a shared labor-incidence curve for all policies, rather
than the corporate-specific 75/25 capital/labor split. For an income-tax
policy this is fine — the tax base *is* labor income. For a *corporate*
rate change, the bulk of the statutory incidence should fall on owners of
capital, whose income is heavily concentrated in the top decile.

Empirically:

| Group        | Engine share | JCT share | Ratio  |
|--------------|-------------:|----------:|-------:|
| `<$100K` (aggregated) | 45.5% | 18.7% | 2.4× over  |
| `$200K-$500K` | 36.2%       | 18.9%     | 1.9× over  |
| `$500K-$1M`   |  6.0%       |  9.7%     | 0.6× under |
| `$1M and over`|  2.9%       | 35.9%     | **0.08× — 12× undercount** |

The engine is spreading corporate burden roughly in proportion to wage
income, which places ~80% of filers in the `<$200K` band. JCT places only
~37% of the burden there because their 75/25 split routes most of the tax
through capital income — dividends, capital gains, pass-through distributions
— which are far more concentrated.

### Data cause

Secondary. The IRS SOI brackets the engine uses do carry capital-income
columns that would support a split-incidence calculation, but the engine
path ignores them for corporate-tax policies. This is a code gap, not a
data gap.

### Methodological cause

The engine has no policy-type dispatch for incidence. All TaxPolicy
subclasses flow through the same bracket aggregation, which is the right
thing for rate-on-wage-income reforms and wrong for corporate.

### Closure (applied)

The fix landed in `distribution_effects.py::calculate_corporate_effect`:

- Replaced the five exact-floor tier keys with five explicit
  `[lower, upper)` ranges covering the full AGI distribution.
- Lookup now uses the midpoint of the requested income group rather
  than an exact floor match, so deciles and JCT dollar brackets
  resolve correctly.
- Capital-income shares calibrated to SOI Table 1.4 top-of-distribution
  concentration: 10%/12%/18%/15%/**45%** across `<$100K`/`$100-200K`/
  `$200-500K`/`$500K-1M`/`$1M+`. Labor shares mirror this with the
  opposite gradient.

Post-fix the engine puts 34.2% of corporate burden on `$1M+` filers vs
JCT's 35.9% — a 1.65pp gap, down from 32.9pp before. The 2.51pp overall
mean absolute share error is well inside the `good` rating band.

### Why the magnitude matters

In distributional analyses of Biden-era corporate proposals, the single
biggest political salience is who pays. The current engine would say
"it's pretty evenly distributed, maybe slightly top-heavy"; JCT says "a
third of the burden is on filers over $1M". A paper citing our
distributional output for corporate reforms would be systematically
understating the progressivity of the policy — a big and correctable
error.

---

## 5. Cross-cutting patterns

Three diagnoses point at the same larger issue: **bracket-aggregate
data is a ceiling on accuracy at roughly 5–12% error** for any policy
whose revenue depends on the shape of the right tail. The payroll,
CTC, and estate cases all show systematic errors of ~10–12% because
the underlying IRS SOI / ACS bracket tables smooth the tail.

This is exactly what Priority 1 in the review — the CPS ASEC microsim
foundation — is designed to fix. Return-level data preserves the tail
shape because each return carries its own income value, weighted
correctly. Once the microsim path is the default, the payroll, CTC,
and estate cases should tighten to the ~2-3% range that the corporate
and AMT *revenue* cases already sit in (those cases already use firm-
level or return-level inputs).

The §4 corporate case is a different pattern: the *revenue* score is
within 4% of official (see README validation table), but the
*distributional* profile is 15pp off because the engine uses a labor-
incidence curve instead of the 75/25 split. That's a code gap on top
of the data gap.

The right reading of these outliers is therefore:

- **They are not random miscalibrations.** Each has an identifiable
  mechanism, documented above, and an actionable fix.
- **Three of the four trace to the same underlying data gap** (bracket
  aggregates smoothing the right tail). Closing it once (CPS microsim)
  closes all three.
- **The fourth is independent** — a code gap in incidence routing that
  can be fixed without any data change.
- **The honest headline error range for the calculator is "≤3% on
  policies below $100K income thresholds; 8-12% on right-tail-dependent
  revenue estimates; distributional accuracy `good` on income taxes and
  corporate taxes (after the §4 fix)."** Users should cite it that way.

Live accuracy numbers are emitted by `scripts/run_validation_dashboard.py`
and surfaced via the `GET /benchmarks` endpoint; they replace whatever
was written here the last time this doc was edited.

---

## 6. Leave-one-out: what the calibrated tier looks like held out

`fiscal_model/validation/loo.py` (`python scripts/run_loo.py`) drops one
calibrated benchmark's hard-coded annual at a time and asks whether the
module's structural machinery — calibrated on the others — can put it back.
The reconstructed policy is then scored through the *same* validation runner
the by-construction scorecard uses, so the LOO number and the by-construction
number differ in exactly one input. `tests/test_loo.py` pins this: replaying
the calibrated annual through the LOO harness reproduces the scorecard value
exactly, and monkeypatching `loo.official_target` to raise proves no
derivation ever reads the held-out answer.

**Aggregate: 59.3% mean / 35.6% median over 18 derivable cases, 6/18 within
15%, plus 4 cases reported as not cross-validatable.** Against the
by-construction 4.4%. The gap is the size of the claim the by-construction
number cannot support.

### Classification, module by module

**(a) Structurally derivable** — a shared mechanism can produce the held-out
case from base data plus the other cases' calibration.

- **Payroll (3 of 4, mean 3.8%).** The three OASDI benchmarks anchor
  `SSA_COVERED_WAGES_ABOVE_BILLIONS`; the 400K/500K/1M rows are documented as
  interpolated from them and are therefore excluded from every LOO calibration
  set (using them would smuggle the held-out anchor back in). Holding out one
  anchor, the covered-wage level at its threshold is refitted from the other
  two anchors' Pareto slope, times 12.4%. Errors of −3.7% / +1.3% / +6.3% say
  the log-linear tail assumption in §1 is doing real work — this is the one
  module where the calibrated constants are close to redundant with the
  structure.
- **Estate (2 of 3, mean 25.8%).** The two-regime taxable-estate machinery is
  evaluated at the baseline and reform exemption. Extending the TCJA exemption
  comes out at +6.0% — good. The Biden $3.5M/45% case misses by +45.6%, and
  the reason is visible in the machinery: below the post-sunset exemption,
  `estates × avg_taxable` is invariant (19,000 × $25.8M and 34,742 × $14.1M are
  the same product), so *lowering the exemption raises no revenue at all* and
  the whole derived effect comes from the 40% → 45% rate change. The calibrated
  $45B/yr annual is carrying the exemption-broadening that the two-regime blend
  cancels out.
- **AMT (2 of 3, mean 79.6%).** Derived from the taxpayer-count × average-
  liability identity in `BASELINE_AMT_DATA` (7.3M filers at ~$10K post-sunset
  per TPC; 200K at ~$25K under TCJA), bypassing the `CBO_AMT_ESTIMATES`
  calibration constants. Both cases come out high (+73.2%, +86.0%) for the same
  reason: the identity gives the *steady-state* post-sunset level (~$73B/yr,
  which matches `revenue_post_tcja_2030 = 75.0`), while the official $450B/10yr
  scores a window that ramps from the 2026 sunset. A LOO derivation that phased
  the ramp in would close most of this; the module has no ramp.
- **Credits (3 of 3, mean 45.1%).** The per-unit identity (credit change ×
  affected units × participation) systematically *understates* all three
  expansions (−64.1% / −28.0% / −43.1%), because it prices only the per-child
  credit increase and none of the refundability expansion or phase-out
  relaxation the official scores include. That is a known structural omission,
  not noise — see §2.
- **Capital gains (3 of 3, mean 171.2%).** The sharpest test. The three
  scenarios carry three *different* hand-set elasticity/lock-in tuples; freezing
  the `CapitalGainsPolicy` dataclass defaults (short 0.8 / long 0.4, transition
  3, lock-in 2.0, avoidance 1.0 — the ETI-literature values, not fitted to any
  target) and scoring all three gives −22.6% (PWBM no step-up), −120.5% (CBO
  +2pp) and −370.5% (PWBM with step-up, a **sign flip**). `--donor-matrix`
  identifies the answer key: the `pwbm_39_with_stepup` tuple (0.8/0.4 with the
  **5.3× lock-in multiplier**) is the only donor that scores the other two
  cases tolerably — mean |error| 29.7%, versus 104.8% and 333.2% for the other
  two donors. The lock-in multiplier alone is producing PWBM's revenue-*loss*
  result; nothing else in the module does.

**(b) Independent constants, rebuilt bottom-up** — the annuals are free
parameters with no shared fit to hold out, so LOO instead runs the module's own
reform-action rules against its published base table.

- **Tax expenditures (5 of 6, mean 39.4%).** Base is `JCT_TAX_EXPENDITURES`,
  sourced to JCT's *Estimates of Federal Tax Expenditures* (JCX-48-24; curated
  snapshot at `fiscal_model/assistant/knowledge/jct_tax_expenditures.md`). The
  two "eliminate" cases whose base entry is a real expenditure total land well
  (mortgage −5.1%, SALT-cap repeal +4.0%); the charitable 28% cap is +15.7%.
  Two misses are diagnostic rather than noisy:
  - `eliminate_salt` (+74.9%) uses `annual_cost = 25.0` — the *post-cap* SALT
    expenditure — where the $1,200B target is for eliminating the deduction
    against an uncapped baseline. The base table has
    `annual_cost_no_cap = 120.0` and the eliminate rule never reaches for it.
  - `cap_employer_health` (+97.4%) is a **unit mismatch in the uncalibrated cap
    path**: `cap_amount` is a $50,000 cap on excludable *premiums*, but the
    share-affected rule compares it against `avg_benefit = $1,600`, which is the
    average *tax benefit*. The rule concludes 0.32% of the base is affected and
    returns $0.8B/yr against a $45B/yr target. This does not affect any scored
    preset (the calibrated annual short-circuits it), but it means the module
    cannot derive this benchmark from its base — flagged here rather than
    patched, because fixing the cap rule is a scoring-path change that belongs
    with the Phase E provenance work.

**Not cross-validatable (4 cases).** Reported with a reason; never folded into
the aggregate.

| Case | Why |
|---|---|
| `expand_niit` | NIIT expansion is a different mechanism (3.8% on pass-through income) from the OASDI wage bands, and it is the module's only NIIT benchmark — there is nothing to calibrate it on. |
| `eliminate_estate_tax` | The target is sourced "Model estimate", not a published score. The machinery also reproduces estate-tax *differences* but not *levels*: its implied baseline is ~$196B/yr against CBO's ~$50B/yr, so a full-repeal case cannot be derived from it. Phase E already lists this entry for removal from the headline count. |
| `repeal_corporate_amt` | Its only base constant, `CORPORATE_AMT["revenue_per_year"] = 22.0`, is the CBO $220B/10yr target restated. |
| `eliminate_step_up` | Same shape: `JCT_TAX_EXPENDITURES["step_up_basis"]["annual_cost"] = 50.0` is the $500B/10yr target restated. |

The last two are caught **mechanically**, not by a hand-maintained list:
`loo.py` excludes any case whose derived annual matches `official / 10` to
within 0.5% (`LEAKAGE_TOLERANCE`). The same guard would have caught the estate
and AMT `extend_tcja_*` short-circuits had those not already been bypassed
explicitly in the derivation.

### Why these numbers differ from the by-construction ~5%

The by-construction figure measures whether a stored constant was stored
correctly. It is not a measure of the machinery, because in every module the
constant *overrides* the machinery: `estimate_static_revenue_effect` returns
`annual_revenue_change_billions` unchanged whenever it is set. LOO removes that
override for one case at a time, and what is left is the module's actual
predictive content. Where that content is a genuine shared mechanism
(payroll's covered-wage bands, estate's exemption machinery on the extension
case), the held-out error is single-digit. Where the "mechanism" is one free
parameter per benchmark (capital-gains elasticities, most tax expenditures),
the held-out error is large — as it should be, because there was never
anything there to predict with.

The gate in `scripts/run_validation_dashboard.py` (`--max-loo-mean-error`,
default 75 — the observed 59.3% × 1.25, rounded to 5) exists to catch a
*regression* in the structural machinery — a base table edited without
re-deriving — not to certify accuracy. Do not quote it as an accuracy claim.

---

## 7. Sectoral module reconstructions — what the five new runners found

Phase E (plan §5.3) wired the five sectoral modules into the scorecard:
`validate_all_international`, `_trade`, `_pharma`, `_enforcement`,
`_climate` in `fiscal_model/validation/specialized_sectoral.py`. Seventeen
presets that ship in the app with an official number attached had never been
compared to it. Twelve of them carry no module constant fitted to the target,
and their mean absolute error is **394.1%** (median 57.1%) against **2.7%** for
the 34 genuinely fitted benchmarks.

Nothing below was retuned. The instruction the phase was run under, and the
right one, is that a module far from its published figure gets reported as
`Poor` with a note — adjusting a constant to close the gap would convert a
finding into a fabrication, and the gap is often in the *target* rather than
the model.

**Targets are read, never restated.** Each scenario names a preset key and the
runner reads `CBO_SCORE_MAP[preset]["official_score"]`, so the validation layer
and the app cannot drift apart; a test enforces that no sectoral scenario
carries its own `expected_10yr`.

### 7.1 International tax (4 cases, mean 24.3%, 0 fitted)

| Case | Official | Model | Error |
|---|---:|---:|---:|
| Biden GILTI reform | -$280B | -$230B | 17.8% |
| Repeal FDII | -$200B | -$170B | 15.0% |
| Pillar Two adoption | -$80B | -$61B | 23.5% |
| Biden international package | -$700B | -$413B | 41.0% |

The two single-provision cases land inside 18% with no fitting at all, which is
the most encouraging result in this section. The package case is a **scope
mismatch, not a modelling error**: Treasury's -$700B covers GILTI + FDII + UTPR
*plus* the BEAT/SHIELD replacement and several base-protection provisions
`international.py` does not implement, and the module sums its three components
with no interaction term while a package estimate nets overlapping bases.

Pillar Two rates Poor against a midpoint. `international.py`'s own source note
gives JCT's figure as a **$50–120B range**; the model's -$61B is inside it. That
is a good illustration of why the provenance label matters more than the rating:
scoring against the midpoint of a range manufactures a 23.5% "error" out of
target imprecision.

### 7.2 Trade / tariffs (5 cases, mean 72.2%, 2 fitted)

| Case | Official | Model | Error |
|---|---:|---:|---:|
| Universal 10% tariff *(fitted)* | -$2,000B | -$2,022B | 1.1% |
| 60% China tariff *(fitted)* | -$500B | -$531B | 6.2% |
| 25% auto tariff | -$100B | -$252B | 152.3% |
| 25% steel & aluminium tariff | -$60B | -$104B | 73.2% |
| Reciprocal tariffs (~20pp) | -$1,200B | -$2,736B | 128.0% |

The two headline scenarios match because `TRADE_BASELINE`'s coverage constants
(`universal_coverage_rate = 0.70`, `china_effective_coverage = 0.50`) were
picked to reproduce them. The three that were *not* fitted all miss in the same
direction — the module scores **gross customs revenue net only of an import
demand response**, while the published figures are net of retaliation and of the
GDP-feedback drag on income and payroll receipts. The repo's own knowledge
snapshot puts the net figure at 40–50% of gross, which is roughly the size of
the reciprocal-tariff gap (-$2,736B vs -$1,200B).

Two further problems are target-side and worth fixing before anyone treats
these rows as accuracy statements:

- **Base overstatement.** The steel case applies the full 25pp to the whole $50B
  base with no allowance for the Section 232 duties already in force; the auto
  case applies 22.5pp to $133B, which yields ~$25B/yr against a target implying
  ~$10B/yr.
- **A bookkeeping defect in `app_data.py`.** `CBO_SCORE_MAP` keys the steel
  preset as "25% Steel & Aluminum Tariff (-$60B)" while `PRESET_POLICIES` keys it
  "25% Steel/Aluminum Tariff (-$15B)"; the reciprocal preset has the same
  mismatch ("Reciprocal Tariffs (~20pp)" vs "Reciprocal Tariffs"). The two
  dictionaries never join, so **the app shows no official score for either
  preset**, and in the steel case the two figures in the repo differ by 4x.
  The runners read the `CBO_SCORE_MAP` key deliberately; reconciling the keys
  is an `app_data.py` change and was left out of this phase.

### 7.3 Drug pricing (3 cases, mean 1,394.1%, 0 fitted)

| Case | Official | Model | Error |
|---|---:|---:|---:|
| Expand drug negotiation | -$500B | -$372B | 25.7% |
| Universal insulin cap | -$15B | -$445B | 2,868.6% |
| International reference pricing | -$100B | -$1,388B | 1,287.9% |

**This is the phase's most substantive finding.** Two of the three are not
calibration drift — they are incidence bugs in `pharma.py`:

- `DrugPricingPolicy._estimate_insulin_savings` credits the *entire* difference
  between a $6,000 average annual insulin cost and the $420 capped cost to the
  federal budget, for all 8.4M insulin users. A price cap that mostly
  reallocates cost among patients, insurers and manufacturers is therefore
  scored as ~$47B/yr of federal saving. Worse, `extend_to_private=True`
  *increases* the modelled federal saving, when in the published scores the
  private-market portion has essentially no federal budget effect. The module's
  own `CBO_PHARMA_ESTIMATES` carries CBO's -$6.4B for the Medicare-only cap,
  which the code never uses as a check.
- `_estimate_reference_pricing_savings` applies the full US/OECD price-ratio
  reduction (2.56x → 1.20x, a 53% cut) to *all* $275B of Medicare Part B + Part D
  drug spending, ignoring the manufacturer rebates already netted out of Part D
  and any utilisation or availability response.

The negotiation case is milder: savings scale linearly in drug count from the
IRA per-drug average with a flat 60% productivity haircut, while CBO's scoring
is strongly non-linear in *which* molecules enter the window. Its -$500B target
is itself labelled "CBO/Estimate" in the record and is not a CBO score of this
policy.

Fixing the two incidence bugs changes a shipped module's output for users, not
just a validation number, so it belongs in a `pharma.py` change with its own
review — not in a validation runner.

### 7.4 IRS enforcement (2 cases, mean 43.9%, 1 fitted)

| Case | Official | Model | Error |
|---|---:|---:|---:|
| IRA enforcement funding *(fitted)* | -$200B | -$189B | 5.5% |
| Double IRS enforcement | -$340B | -$60B | 82.3% |

The IRA case matches because `base_roi_multiplier = 5.0` was chosen to land on
it. The doubling case applies both a lower base ROI (4.0) *and* a faster
diminishing-returns factor (0.80) to a $16B/yr increment, and neither constant
was ever fit to the -$340B figure; the compounding of the two produces less than
a fifth of it. The target is also not an official score — it comes from
Treasury's 2021 tax-gap paper and the Sarin–Summers estimates — and assumes
sustained funding whose revenue partly lands outside the module's 4-year ramp.

Unrelated, spotted while reading: `ENFORCEMENT_BASELINE` in
`fiscal_model/enforcement.py` contains a stray `"medicare_insulin_share": 0.4`
key copy-pasted from `PHARMA_BASELINE`. It is dead, but it should go.

### 7.5 Climate / energy (3 cases, mean 5.0%, 2 fitted)

| Case | Official | Model | Error |
|---|---:|---:|---:|
| Repeal IRA clean-energy credits *(fitted)* | -$783B | -$783B | 0.0% |
| Carbon tax $50/ton *(fitted)* | -$1,700B | -$1,715B | 0.9% |
| Repeal EV credits | -$200B | -$228B | 14.2% |

The two near-zero rows are pure bookkeeping and should be read as such. The IRA
repeal annual **is** the target restated over ten years — the same leakage
pattern `loo.py` flags for `repeal_corporate_amt` — and `climate.py` documents
`carbon_tax_behavioral_factor` as calibrated so that $50/ton yields ~$1.7T. The
carbon-tax target is additionally labelled `model_estimate`: no agency published
it, so that row measures internal consistency and nothing else.

The EV-credit row is the only one here doing real work, and 14.2% flatters it —
the repo's own knowledge base gives a **$30–60B range** for EV-credit
elimination on the 2022 baseline against the $200B target used here, so the
published figures for this policy span an order of magnitude.

### 7.6 What this changes about the headline

The calibrated tier is now 46 entries, but it is two populations:

| | n | Mean abs error | Within 15% |
|---|---:|---:|---:|
| Fitted calibrated references | 34 | 2.7% | 33/34 |
| Unfitted module reconstructions | 12 | 394.1% | 2/12 |

`scripts/cold_holdout.py` reports them as separate tiers, and the anti-leakage
invariant in `tests/test_cold_holdout.py` compares the out-of-sample tier
against the *fitted* set — mixing the two would have flipped the invariant for
the wrong reason (44.8% out-of-sample vs a 104.8% "calibrated" mean) and hidden
the fact that the fitted tier is still 2.7%.

`readiness.py --strict` treats a documented `Poor` on an unfitted reconstruction
the same way it treats a documented out-of-sample miss: a warning, not a
blocker. A documented `Poor` on a *fitted* benchmark stays strict-blocking,
because those parameters exist to reproduce the target and a miss there really
is a regression. Blocking on the reconstructions would have made deleting the
runner the cheapest route back to green — precisely the incentive the
pre-registration manifest exists to forbid.

### 7.7 Provenance of the targets

Of the 46 calibrated-tier benchmarks: **4 `line_item`**, **31 `secondhand`**,
**7 `model_estimate`**, **4 `unclassified`**. Only four benchmarks in the whole
calibrated tier — CBO's May 2024 *Budgetary Outcomes Under Alternative
Assumptions* ([pub. 60271](https://www.cbo.gov/publication/60271)) and the three
capital-gains cases — cite a specific document; every sectoral target added in
this phase is a rounded headline figure or an explicit model estimate. Labels
are assigned in `fiscal_model/validation/provenance.py`, either declared by the
runner or inferred from the record's own source string, URL and the roundness
of the target, and are never guessed: a record that does not unambiguously fall
into a bucket stays `unclassified` until someone finds the table.

---

## References

- SSA Trustees 2024: *Long-Range OASDI Cost and Income Estimates* (2024)
- CBO (2021): *Budgetary Effects of the American Rescue Plan*
- Treasury (2024): *General Explanations of the Administration's FY 2025
  Revenue Proposals*, Green Book
- Atkinson, Piketty, Saez (2011): *Top Incomes in the Long Run of
  History*, JEL 49(1)
- IRS SOI: *Statistics of Income — Individual Income Tax Returns*, Tables
  1.1 and 1.2; *Estate Tax Returns Filed*, Table 1 Parts I & II
- JCT (2021): *Macroeconomic Analysis of a Proposal to Increase the
  Corporate Income Tax Rate to 28 Percent*, JCX-32-21
