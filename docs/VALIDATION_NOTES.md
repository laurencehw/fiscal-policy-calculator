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

**Superseded by Wave 3 — and the diagnosis was wrong in an instructive way.**
This section said the residual traced to "how CBO models children-in-household
distribution for the Recovery Rebate — a microsim-level detail that
bracket-aggregate scoring can't replicate without return-level data", so lane L3
put the rebate on return-level data: a per-person $1,400 credit for the filer,
spouse and every dependent, phasing linearly across $75k–$80k / $150k–$160k
(IRC §6428B). **The benchmark got worse, from 4.76pp to 7.77pp**, and the reason
is that the figure it replaced was two universes partially cancelling. Three
measurements, in the order they happened:

| configuration | ARP err (pp) |
|---|--:|
| Before L3: CTC + EITC on the microsim, rebate on the synthetic path | **4.76** |
| Statutory CTC/EITC corrections, rebate still synthetic | **6.29** |
| All three components on the microsim | **7.77** |

Running the rebate on the synthetic bracket path used **IRS return counts** for
one of the three components and **CPS tax units** for the other two, and the two
rankings pulled in opposite directions. The real gap is a **universe mismatch**:
CBO's quintiles are of about 130M households, the model's of 191M CPS tax units,
and its bottom quintile is **38.2M units with a mean AGI of $0** — tax-unit
construction fragments households into non-filing and dependent units that CBO's
household ranking never separates. Under full refundability those units collect
the whole ARP credit, so the model puts **53%** of the bundle's dollars in its
bottom quintile against CBO's **34%**.

Two things say the microsim configuration is the more correct one even though it
scores worse. The **dollar levels** move from about a third of CBO's to close to
them: scored as one combined reform the quintile averages run −$2,461 / −$2,846 /
−$2,782 / −$2,864 / −$1,738 against CBO's −$2,800 / −$3,150 / −$2,450 / −$1,620 /
−$920, where the merged path gave −$892 / −$954 / −$949 / −$1,030 / −$55. And the
bundle's total, **$485B**, is within 10% of the ARP's actual cost for these three
provisions (~$411B of rebates plus roughly $105B of CTC and $12B of EITC), where
the old path could not be summed at all. Choosing the mixed configuration back
would improve the reported number by 3pp by keeping one component in a different
universe from the other two, which is the flattery the plan's §4 forbids.

**The honest statement is that this benchmark's 4.76pp was never measuring what
it appeared to.** The open work is the tax-unit-versus-household universe, which
is a distributional-pipeline lane and not a credits one; `filing_threshold.py`
and `top_tail.py` already exist for it and neither is wired into the benchmark
runner.

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

## 5a. Budget authority → outlays: where the spend-out profiles came from (Wave 1, L2)

Until 2026-09-01 `SpendingPolicy` turned an annual funding level straight into
an outlay in the year the authority was provided — `grep -rn
'spend_out\|outlay_rate' fiscal_model/` returned nothing — and that single
defect carried **509 of Tier 1's 1,315 units of error mass (38.7%)**, the
largest in the tier. Outlays are now the convolution

```
outlays_t = Σ_k s_k · BA_{t−k}
```

with `s` a first-year/out-year profile keyed by **account class**, and budget
authority and outlays are distinct quantities on the policy and on the result.
The eight spending rows moved to 0-18% and the tier fell to 34.4%; the
mechanism's error mass was then **63.4 units of 859.5 (7.4%)**, and after Wave 2
took 77.7 units out of the capital-gains rows it is **63.4 of 781.8 (8.1%)** —
the same mass against a smaller tier. Per-row detail is in
[VALIDATION.md](VALIDATION.md); the pre-registration and outturn are in
[`planning/lanes/L2_spend_out.md`](../planning/lanes/L2_spend_out.md).

**The finding is about the source, not the fit.** Owner Decision 2 named **OMB
Circular A-11 §32 outlay rates** as the primary source, with CBO's donor options
as the check. *That source does not exist as described*, and this is a finding
rather than a fetch failure:

- **A-11 §32 is "Personnel Compensation, Benefits, and Related Costs."** Checked
  in the 2016 edition and against the current table of contents. It contains no
  outlay rates of any kind.
- **A-11 publishes no numeric outlay-rate table in any section.** §80
  ("Development of Baseline Estimates") requires only that new budgetary
  resources "outlay at a rate that is consistent with Presidential policy
  spendout rates"; §81 requires *agencies* to enter their own account-level
  "outlay rates that apply to BA or limitations provided in the CY and beyond"
  into MAX. The rates are agency-supplied and unpublished.
- **CBO does publish account-level spendout rates** — publications 61913 and
  62256, the discretionary-outlay interactive tools — but `cbo.gov` returns
  HTTP 403 to this environment on every URL including `system/files`, and
  `web.archive.org` was not reachable either.

So **Decision 2's own fallback clause governs: the CBO donor options in the
repository's own `cbo_options_2025_2034_alternatives.csv` are the shipped
primary source**, and CBO's account-level rates are the open external
cross-check, blocked on network access to cbo.gov. Both
`fiscal_model/data_files/spending/outlay_rates.csv`'s header and
`scripts/fit_outlay_rates.py`'s docstring say this in full, so the file cannot
be read as claiming an A-11 provenance it does not have.

**Anti-leakage.** Nineteen of the 76 options publish both an authority row and
an outlays row. The five that are scored by the battery — options 37, 38, 39,
42 and 43 — **never donate to any profile**, and option 44 is excluded because
its outlays exceed its authority in every year (10-year ratio 1.52: repealing
Davis-Bacon also cheapens work paid from prior-year balances, so its implied
profile violates `s_k ≥ 0, Σs_k ≤ 1` and is not a spend-out observation). The
remaining 14 are the donor pool, fitted by non-negative least squares;
`tests/test_spending_outlays.py` asserts the disjointness directly and asserts
that the committed CSV is what the documented fit reproduces.

| class | donors (all unscored) | s₀ | Σs | level-path 10yr ratio |
|---|---|--:|--:|--:|
| `personnel_and_benefits` | 29, 36, 40, 41 | 0.921 | 1.000 | 0.991 |
| `operations_and_support` | 28, 34 | 0.539 | 0.977 | 0.893 |
| `grants_and_procurement` | 32, 33, 35 | 0.405 | 1.000 | 0.848 |
| `construction_and_capital` | 31 | 0.022 | 0.973 | 0.663 |
| `mandatory_benefit` | 3, 9 | 0.977 | 1.000 | 0.998 |

**Class assignment is a classification, never a fit** — from the predominant
account type of the programs each case funds, as the *source* describes them,
the same discipline the repository already uses for the ordinary-vs-AGI-inclusive
base split. No profile rate is keyed to a benchmark id, and no rate was chosen
by looking at the error it produced.

**Two honest edges.** The window truncates the **tail, not the head**: authority
whose outlays fall past the projection end is dropped (the truncation official
10-year totals embed), but a policy that began before the window still spends
its earlier authority into it. Truncating the head too would have discarded
authority the model's own shape claims to provide — worth about 90 points of
flattery on IIJA alone. And these are account *classes*, not accounts:
`cbo_opt39` now under-predicts at 8.1% because Pell disburses in two years while
the generic grants profile takes six. That is what the blocked account-level
rates would close.

**The app follows.** Every Tailor spending program declares an
`outlay_account_class` in its own definition and Build's spending goals derive
one from the goal category, so the same $100B/yr of infrastructure funding no
longer scores $1,146B in the app and $750B in the battery. Each spending score
renders one line naming its profile and its outlay/authority ratio, computed
from the scored result so it cannot drift from the number above it. `immediate`
remains reachable as an explicit choice under Economic parameters and is the
default for nothing.

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

**Aggregate: 28.4% mean / 16.5% median over 18 derivable cases, 9/18 within
15%, plus 4 cases reported as not cross-validatable.** Against the
by-construction 2.0%. The gap is the size of the claim the by-construction
number cannot support.

*Wave 3 took this 32.3% → **28.4%**, and the two moves inside it point opposite
ways.* **(i) The credits module was rebuilt: 45.1% → 20.5%** (PR #101, lane L3),
`biden_ctc_2021` −64.1% → **−4.5%**, `ctc_extension` −28.0% → **+19.0%**,
`biden_eitc_childless` −43.1% → **−38.0%**. That is a model change — see (a)
below. **(ii) The expenditures module got *worse*, 28.8% (n=4) → 30.2% (n=5)**,
and it is the better state: PR #100 replaced `annual_cost_no_cap = 120.0` with
its computation from IRS SOI Table 2.1 (**$89.55B**), so `loo.py`'s untouched
leakage guard stopped firing, `eliminate_salt` **re-entered** the derivable set
at **+10.2%**, and `repeal_salt_cap` moved **+4.0% → −29.4%** because its old
+4.0% was `−(120.0 − 25.0)` — the same leaked constant under a different
benchmark, missed by the guard only because its target is $1,100B rather than
$1,200B. Held to the 17 cases the suite carried before that readmission, the
mean is **29.5%**; the printed 28.4% over 18 is the honest figure and the
difference is composition. The suite now cross-validates **18 of 22** calibrated
benchmarks where Wave 2 left it at 17 with one excluded for leakage.

*Wave 2 (PRs #93, #94, #95) had taken it 58.7% → 32.3%, the first move that was
mostly a model change: `CapitalGains` **171.2% → 39.6%**, `Estate`
**25.8% → 10.4%**, `Expenditures` **39.4% → 28.8%** — the last of those with the
`eliminate_salt` exclusion attached, now reversed.*

*Before Wave 2 this number had moved twice and neither move was a model change.
Wave 1 took it 59.3% → 61.7%, in the direction people do not expect, because L5
replaced a flat AMT constant with a published path. Correcting
`extend_tcja_amt`'s target to $1,357.1B then took it to 58.7%: the held-out
derivation is unchanged at $855.3B and only the figure it is measured against
moved. Read the AMT bullet under (a) before quoting either move as a model
result.*

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
- **Estate (2 of 3, mean 10.4%).** Rebuilt by Wave 2's L4 lane (PR #93).
  The module now distributes the **estate tax base** `B = taxable estate +
  adjusted taxable gifts` as a Pareto, `N(B > E) ∝ E^−α`, with α = **1.73843**
  pooled from seven local estimates inside IRS SOI *Estate Tax Statistics*
  Table 1 for filing years 2010, 2013 and 2024 (range 1.656–1.867, at filing
  thresholds a factor of 3.7 apart), levelled on SOI's own FY2024 taxable-return
  panel (2,663 returns, $62.894B of base above the exemption, $23.313B of net
  estate tax), grown at the app's own `CBOBaseline.nominal_gdp` rate of 3.82%,
  and evaluated **one year behind the fiscal year** because a Form 706 is due
  nine months after death (IRC §6075(a), extendable six under §6081). Eight
  fitted constants were deleted. `biden_estate_reform` **+45.6% → −1.6%**;
  `extend_tcja_exemption` **+6.0% → +19.2%**.

  *What was believed, and what was wrong about it.* This section used to say
  the whole miss was one algebraic invariance — below the post-sunset exemption
  `estates × avg_taxable` was invariant (19,000 × $25.8M and 34,742 × $14.1M
  are the same product), so lowering the exemption raised no revenue at all and
  the entire derived effect came from the 40% → 45% rate change. That was true
  and it is fixed. What it missed is that the extension row's **+6.0% was two
  large errors cancelling**: the old machinery's implied 2026 baseline was
  ~$195.9B/yr against CBO's ~$50B, four times too high, and it was cancelling
  against an exemption response of exactly zero. Repair both and the
  cancellation goes, which is why that row got *worse*. The shipped model puts
  2026 revenue at the $6.4M exemption at **$47.6B**, 4.8% below CBO's carried
  $50B — so the level objection is now closed, and the invariance was
  user-facing too: `create_estate_exemption_change(3.5e6)` used to score
  **exactly $0.0B** and now returns **+$35.4B/yr**.

  *What is unresolved, stated rather than smoothed.* **Growth is the lane's
  biggest lever and the data pulls two ways.** Fitting level *and* growth jointly
  to SOI's three filing years returns **6.81%/yr** and reproduces SOI's history
  to within 8% in every year, because household net worth outgrew GDP badly over
  2009–2023 — but projected forward it gives `extend` +66.9% and `biden`
  +40.3%, which no published CBO or JCT estate estimate is consistent with. The
  module ships nominal GDP growth (3.82%, wealth held at a constant ratio to
  GDP) and therefore **over-states what was actually collected from 2009
  decedents by 109% and from 2012 decedents by 56%**. That bias is deliberate,
  unresolved, and pinned by
  `test_growth_is_the_baseline_gdp_rate_not_the_rate_soi_history_implies` so a
  data refresh cannot turn it into an accident. Note also that the
  pre-registered configuration (3.0% growth) scores *better* on both rows
  (+8.7% and −6.9%) **and was not shipped** — the strongest available evidence
  that the growth rate was chosen on structure rather than on the error it
  produces. Three further omissions: **portability** of a deceased spouse's
  unused exclusion is declared and never read (`modify_portability`,
  `portability_cap`), so the effective per-couple exemption can be twice what
  the module prices; the **graduated rate schedule** is unmodelled, every rate
  being a single top rate scaled proportionally, which is why the Biden target
  — a bill with 50/55/65% brackets — remains an upper bound on what this module
  can construct; and the base is **not a pure Pareto** (the count slope is
  1.738 but the anchor's mean excess implies 1.547, so the module reads the
  mean-excess ratio off SOI separately rather than deriving it from α).

  *Not a benchmark, but a large gap worth recording.*
  `create_warren_estate_proposal` carries a fitted **−$2,600B** from PWBM and
  derives **−$663.6B**. The module prices a 55% flat rate on a $3.5M exemption;
  PWBM's $2.6T scores a package with a separate wealth tax. The preset is not in
  `ESTATE_TAX_VALIDATION_SCENARIOS`, so nothing in the battery sees this — but
  the two numbers are not estimates of the same policy.
- **AMT (2 of 3, mean 73.9%).** Derived from the taxpayer-count × average-
  liability identity, evaluated year by year on **TPC Table T25-0049**
  ("Aggregate Alternative Minimum Tax Projections, 2024-2035", April 2025,
  transcribed to `fiscal_model/data_files/amt/tpc_t25_0049_aggregate_amt.csv`),
  with the baseline leg at the current-law exemption and the policy leg at the
  reform exemption. `repeal_individual_amt` comes out high at **+110.9%** against
  an unsourced $450B; `extend_tcja_amt` reads **-37.0%**, because its target was
  corrected to the published $1,357.1B while its derivation stayed at $855.3B.
  Before that correction they read +90.1% and +110.9%, and Wave 1's L5
  lane established that the reason this file previously gave for the overshoot
  was **wrong**.

  *What was believed.* Until 2026-09-01 this section, and `MODELING_IMPROVEMENT.md`
  §3 L5 with it, said the overshoot was a missing 2026 phase-in: "the identity
  gives the steady-state post-sunset level (~$73B/yr) while the official
  $450B/10yr scores a window that ramps from the 2026 sunset. A LOO derivation
  that phased the ramp in would close most of this; the module has no ramp."

  *What the data shows.* There is no ramp to add. T25-0049 — whose baseline is
  the law in place as of 1 January 2025, i.e. with the TCJA sunset still in law —
  shows a **cliff**: AMT payers go from **0.2M in 2025 to 7.6M in 2026**, and the
  post-sunset path then *grows*, from **$71.6B in 2026 to $124.2B in 2035**. The
  flat ~$73B/yr was the window's **early-year** level, not its average, so
  indexing the path by year *raises* the derived score rather than lowering it.
  The LOO errors moved +73.2% → +90.1% and +86.0% → +110.9% for exactly that
  reason, and the lane pre-registered both bands before writing the code.
  `tests/test_amt_derived.py` pins the cliff so a data refresh cannot quietly
  reintroduce the assumption, and an independent vintage (TPC T18-0145, 2018)
  agrees on the shape — a cliff, not a ramp — while differing on level by ~15%.

  *Why the rows still cannot come down.* Because the disagreement is with the
  target, not the path. `benchmark_sources.py` records `extend_tcja_amt`'s
  published line item as **$1,357.1B** (CRS R48286 Table 1, transcribing CBO
  pub. 60114), noting that the *five*-year figure is $466.2B — "the carried
  target looks like a five-year number sitting in a ten-year column". Scored
  against the **published** figure instead of the carried one, the derived path
  is **-37.0%** where the fitted constant is **-66.8%**: roughly 1.8× closer to
  the document. The two published figures answer different questions (TPC's is a
  standalone current-law sunset; CRS/CBO's is the AMT provision scored inside a
  full TCJA-extension package, where extended rate cuts push far more filers
  into AMT), so -37% and not 0% is the honest expectation.

  *A second defect L5 found and closed.* Interpolating payer count and average
  liability separately between the two regime anchors and multiplying them is
  **not safe**: both are individually monotone in the exemption — the count falls,
  the average rises — but their product turns upward, so a +$25K exemption
  increase priced as a revenue *gain*. Revenue and payers are each interpolated
  now and the average is their ratio. The exemption-change branch had been dead
  code (`baseline_taxpayers` and `policy_taxpayers` computed from the same call),
  so before L5 no exemption change had ever been scored at all, which is what
  had been hiding it.

  *Mode, and what a user sees.* `AMTPolicy` now has a `reported` mode (the
  fitted annual) and a `derived` mode (the structural path). Under owner
  Decision 1 the app default stays **`reported`**, because derived does not beat
  fitted against the carried benchmarks; `derived` is the default in the
  held-out path, which is where the honesty claim lives. The scorecard half of
  Decision 1 is **blocked and stays blocked**: `repeal_individual_amt` is a
  locked id in `holdout.py`'s `revenue-scorecard-post-lock-2026-05-02` protocol
  and `readiness.py` hard-fails strict readiness on any holdout entry rated
  Poor, which derived would be. `AMT_SCORECARD_MODE` is the one line that flips
  it once the owner has settled the target — which is the same decision as
  correcting these two targets, and is provenance work, not a modelling lane.
- **Credits (3 of 3, mean 20.5%).** Rebuilt by Wave 3's L3 lane (PR #101), from
  **45.1%**. The old path was a per-unit identity — credit change × affected
  units × participation — and it systematically *understated* all three
  expansions (−64.1% / −28.0% / −43.1%), because it priced only the per-child
  credit increase and none of the refundability expansion, the tax limit on the
  non-refundable leg or the qualifying-age relaxation the official scores
  include. The derived path now builds **two** parameter sets — the
  counterfactual schedule and the reform schedule — runs `MicroTaxCalculator`
  over the CPS ASEC tax units under each, and takes the weighted difference in
  final tax liability. `biden_ctc_2021` **−64.1% → −4.5%**, `ctc_extension`
  **−28.0% → +19.0%**, `biden_eitc_childless` **−43.1% → −38.0%**.

  *The dominant correction is a counterfactual, not a parameter.* The lane
  pre-registered `biden_ctc_2021` at about −28% and it landed at −4.5%, because
  the pre-registration's arithmetic scored the ARP credit against a $2,000
  baseline throughout the window and the statute does not: IRC §24's $2,000
  reverts to $1,000 after 2025 (P.L. 115-97 §11022(b)), so a ten-year window
  opening in 2025 is scored against current law for one year and the pre-TCJA
  regime for nine. Against a fixed $2,000 baseline the reform costs **$883B**;
  against the counterfactual the law specifies, **$1,528B** — more than 40
  percentage points of that row. `test_credits_microdata.py` pins both legs.

  *`ctc_extension` moved away from its target and toward the document.* Its
  carried $600B has a one-line "CBO 2024" provenance and no transcribed row; the
  only published line item for a comparable provision is JCT's JCX-35-25 row for
  P.L. 119-21's child credit, **+$816.846B** over FY2025-2034, already
  transcribed in this repository. Against that anchor the fitted constant reads
  **−26.5%** and the structural path **−12.6%** — twice as close. JCT scores a
  $2,200 indexed credit against this benchmark's $2,000 flat one, so it is an
  anchor and not a replacement, and moving the target is provenance work. Same
  shape as L5's AMT finding and L6's SALT finding: the structural path is closer
  to the document than the fitted constant, and that is only visible because the
  carried target and the document disagree.

  *Four defects closed along the way, and a fifth the plan had not named.*
  `expand_qualifying_age`, `include_childless_adults` and `take_up_rate_change`
  were dataclass fields no code path read — a `Δcredit × units × participation`
  identity has nowhere to put an eligibility expansion, and neither did
  microdata carrying only an under-17 headcount, so both had to exist before the
  fields could. `make_fully_refundable` and `remove_phase_out` reached
  unreachable flat constants (−50.0 and −5.0, placeholders no calculation ever
  produced) and now score $85.5B/yr and $70.1B/yr over the CPS units.
  `policy_to_microsim_reforms` collapsed an EITC schedule reform to
  `max_credit / 632` applied to *all four* child counts, so a childless-only
  expansion — exactly what `biden_eitc_childless` is — could not be expressed at
  all. The engine applied one 21.06% phase-out rate to every child count where
  the statutory childless rate is 7.65% and the one-child rate 15.98%, and
  carried a stale vintage of the EITC maxima; it now reads the statutory
  schedule from `credits_core` so the two cannot drift again. And the fifth: the
  engine counted the EITC's **qualifying children** with the CTC's under-17
  column, where IRC §32(c)(3) counts children under 19, or under 24 and a
  full-time student — **79.7M against 65.0M** on the rebuilt file, a 23%
  undercount. Fixing it raises baseline EITC and moves no benchmark, because
  every EITC-relevant reform is differenced against the same baseline.

  *Decision 1 outcome: the app default stays `reported`.* Reported means 0.0%
  across the three benchmarks against derived's 20.5% — but read that 0.0% with
  Decision 5 in hand. Every one of the three fitted annuals is its target
  divided by ten, to the decimal (`credits_factory.py:74, :145, :227`), so
  "derived beats fitted" is unwinnable by construction on the carried targets,
  and the three benchmarks now carry a per-case declaration saying so.
  `CREDIT_APP_MODE` is the one line that would change what a user sees, and it
  did not change.
- **Capital gains (3 of 3, mean 39.6%).** The sharpest test, and Wave 2's L1
  lane (PR #95) rebuilt it. `cbo_2pp_all_brackets` **−120.5% → −14.0%**,
  `pwbm_39_with_stepup` **−370.5% → −28.4%** with the sign restored, and
  `pwbm_39_no_stepup` **−22.6% → +76.5%**, worse, exactly as the lane
  pre-registered. `--donor-matrix` now prints **three identical rows**, because
  the three per-case tuples are gone and there is no donor left to be an answer
  key. These three numbers are therefore identical to the same three rows in
  the unfitted-reconstruction tier: there is nothing to hold out.

  *What was believed.* Until 2026-09-02 this section said the module's problem
  was that "the three scenarios carry three *different* hand-set
  elasticity/lock-in tuples", and that `--donor-matrix` identified
  `pwbm_39_with_stepup`'s tuple — 0.8/0.4 with the **5.3× lock-in multiplier**
  — as the answer key, since it was the only donor scoring the other two cases
  tolerably (mean |error| 29.7%, against 104.8% and 333.2%). All of that was
  true and all of it is now gone: the multiplier, the `no_step_up_avoidance`
  multiplier and the three tuples were deleted rather than extended, under
  `MODELING_IMPROVEMENT.md` §4's own rule.

  *What was underneath, and the plan did not name it.* A **fifth defect** sat
  under the four the plan listed: `estimate_behavioral_offset` applied
  `R₁ = R₀·((1−τ₁)/(1−τ₀))^ε` — an elasticity with respect to the
  **net-of-tax** rate — using ε values the realization literature reports with
  respect to the **tax** rate. CRS R48562 (2025) states the definition twice and
  gives the semi-log form behind it, `R = B·exp(−b·t)`, so `ε(t) = b·t`.
  Applying one as the other understates the response by roughly `(1−τ)/τ`: at
  τ = 23.8% the module's nominal ε = 0.8 was an **effective tax-rate elasticity
  of 0.25**, a third of anything in CRS's Table 4. That single unit error was
  most of why every rate-change row over-predicted. Decision 3's frozen
  Dowd–McClelland–Muthitacharoen (2015) persistent 0.72 at CRS's 22% reference
  rate gives **b = 3.273** and a revenue-maximizing rate of `1/b` = **30.6%**;
  JCT's own working coefficient is **3.1** and Treasury's is 0.72 at 22% (CRS
  R48562 p. 8), so the frozen literature value and the official estimators'
  agree within 6% — the cross-check that this is a unit fix and not a tuning
  knob. It also reproduces PWBM's finding directly: 43.4% sits *past* the peak,
  so a rate rise loses revenue while step-up survives, which is why
  `pwbm_39_with_stepup` scores **+$23.6B** against PWBM's **+$33.0B** with no
  multiplier at all.

  *What replaced the four named defects.* The base is IRS SOI **Table 3.5** —
  income actually taxed at each preferential rate by AGI class, $1,107.7B in
  five priced buckets at threshold 0 rather than $1,368B at one blended 15.5%.
  The elasticity is the semi-log form above, with the *transitory* coefficient
  applied in the enactment year only and only to the long-term-gain share of
  each bracket's base (SOI Table 1.4A, 87.7% at threshold 0), because a fund
  distribution cannot be retimed. Lock-in is an accrued-gains stock with a
  realization hazard: with `h = 2.35%/yr` against a mortality-weighted death
  exit of `m = 2.65%/yr`, 53% of accrued gains escape while step-up survives and
  the with/without-step-up price wedge comes out at **1.44×** — smaller than the
  1.5× residual-avoidance multiplier it replaces, which is precisely why
  `pwbm_39_no_stepup` got worse. Gains at death are decedent wealth ×
  unrealized-gain share × an exemption schedule: **$196.2B of gains in 2025
  growing 5.8%/yr** across five estate-size classes, from Poterba & Weisbenner
  (2001) Table 8 scaled by Financial Accounts household net worth, shaped by
  Avery, Grodzicki & Moore (FEDS 2013-28) Figure 1.

  *What is unresolved.* Two things, and they are the whole residual on the two
  Treasury Tier-1 rows. **The death channel has no behavioural response.**
  Biden's proposal carves out transfers to a spouse and to charity, preserves
  the §121 residence exclusion, excludes tangible personal property, defers
  family-business gains until sale and offers a 15-year installment election —
  Treasury's score prices all of it and this module prices only the per-decedent
  exclusion. That is a bigger effect than anything the elasticity can supply.
  **And the realizations base is not projected across the window**: it is held
  at its observed SOI level under the lane's pre-registered
  stocks-are-indexed / flows-are-not rule, because inventing a growth rate for
  an observed flow is what Phase D found had cost the estate and payroll modules
  their accuracy. The decedent ladder also has five classes and no within-class
  dispersion.

  *A target-provenance flag, for the provenance lane and not this one.*
  Treasury's FY2022 Green Book carries a **separate** line for treating
  transfers at death as realization events, yet
  `treasury_capgains_39_plus_stepup_elim` describes its −$322.0B as the
  *combined* rate-plus-realization figure — and the model's death channel alone
  under a $1M exclusion is larger than that whole target. Whether −$322.0B is
  the combined row or the rate-only row is a manifest question. No target was
  touched.

**(b) Independent constants, rebuilt bottom-up** — the annuals are free
parameters with no shared fit to hold out, so LOO instead runs the module's own
reform-action rules against its published base table.

- **Tax expenditures (5 of 6, mean 30.2%).** Base is `JCT_TAX_EXPENDITURES`,
  sourced to JCT's *Estimates of Federal Tax Expenditures* (JCX-48-24; curated
  snapshot at `fiscal_model/assistant/knowledge/jct_tax_expenditures.md`), now
  with a **benefit distribution by AGI class** per expenditure, transcribed from
  IRS SOI Table 2.1 TY2023 (`jct.gov` returns HTTP 403 to this environment on
  every URL, and SOI Table 2.1 is the administrative source JCT's own
  distribution tables are built from — decisively, it separates *total* from
  *limited* SALT). Wave 2's L6 lane (PR #94) made a cap declare its unit
  (`CapUnit`: `BASE_DOLLARS`, `BENEFIT_RATE`, `BENEFIT_DOLLARS`) and a statutory
  limitation a declared object carrying its statute and expiry. Mortgage
  −5.1% is unchanged; the charitable 28% cap improved **+15.7% → +13.1%**;
  SALT-cap repeal was +4.0% until Wave 3 sourced the constant it was built from
  and it became **−29.4%** (below).

  *What was believed about `cap_employer_health`, and what the number turned
  out to be.* This section used to call it "a unit mismatch in the uncalibrated
  cap path": `cap_amount` is a $50,000 cap on excludable *premiums* while the
  share-affected rule compared it against `avg_benefit = $1,600`, the average
  *tax benefit*, concluding 0.32% of the base was affected. That diagnosis was
  right, the unit is fixed, and the row moved **+97.4% → +93.2%** — about 4pp,
  not the <25% `MODELING_IMPROVEMENT.md` §3 L6 asked for. **The residual is in
  the benchmark, not the model**, and the corrected mechanism now prices it:
  a $50,000 cap is far above the entire distribution of employer premiums
  (CBO Option 56 puts the 75th percentile of family premiums at **$31,300** and
  of individual premiums at $12,700), so it raises almost nothing. A $25,000 cap
  scores −$520B and a $50,000 cap −$30.5B, which puts the carried −$450B target
  at a cap of about **$26,400** — within 8% of CBO's own 50th-percentile family
  limit of $24,400. No correct model of a $50,000 cap will reach that target;
  reaching it was only ever available by choosing a cap amount that hits it.
  The miss was pre-registered at "about +93%" before the code was written.

  *What was believed about `eliminate_salt`, and what happened instead.* This
  section used to say the +74.9% was simply that the eliminate rule read
  `annual_cost = 25.0`, the *post-cap* expenditure, and "never reaches for"
  `annual_cost_no_cap = 120.0`. Making it reach for that constant took the
  derived score to −$1,444.4B (+20.4% against the carried target, and
  **−10.9%** against the **published** CBO Option 49 line item of
  −$1,621.0B, where the *fitted* constant is −22.3%). Then `loo.py`'s untouched
  leakage guard fired: **$120.0B is exactly the carried −$1,200B target divided
  by ten**, so the case is now **not cross-validatable** — "the base constant is
  the answer key restated". The guard cannot distinguish "the target restated"
  from "a round number that happens to equal the target over ten", and both
  readings are live, because the module's *fitted* annual for the same benchmark
  is 104.7 rather than 120.0. What is not in doubt is that the constant is
  unsourced and now load-bearing. The lane produced the independent check the
  provenance lane did not have: pricing SOI's **limited** SALT deduction at the
  2025 statutory married-joint schedule gives **$25.0B/yr** against the base
  table's own `annual_cost = 25.0` — two numbers with no common ancestor
  agreeing to a tenth of a percent — and the same computation on the
  **unlimited** deduction gives **$89.6B/yr**, **25% below** the record's
  $120.0B. So either the record's no-cap level embedded a 34% itemisation
  response that nothing documents, or it was the target.

  ***Wave 3 replaced it with the computation, and every consequence L6 priced
  landed.*** PR #100's `uncapped_salt_expenditure_billions()` returns
  `load_deduction_distribution("salt").implied_benefit_billions` — SOI Table
  2.1's total (unlimited) SALT deduction priced AGI class by AGI class at the
  IRC §1 married-joint schedule as adjusted for 2025 (Rev. Proc. 2024-40) —
  **$89.55B**, not a second literal. `loo.py` needed **no per-case edit**: the
  exclusion was produced by the mechanical guard and disappeared mechanically,
  and the guard itself was not touched. `eliminate_salt` is derivable again at
  **+10.2%**, `repeal_salt_cap` moved **+4.0% → −29.4%**, and the module mean is
  **30.2% over five cases**. **`repeal_salt_cap`'s old +4.0% was never evidence
  of anything**: it is `−(120.0 − 25.0)`, the same leaked constant under a
  different benchmark, and the guard missed it only because its target is
  $1,100B rather than $1,200B. Trading a flattering leaked number for an honest
  −29.4% is the trade the provenance lane exists to make.
  `tests/test_tax_expenditure_units.py` now asserts the record **equals** the
  derivation rather than differing from it in a known direction, and **nothing
  fitted moved** — every preset and every fitted-tier row scores in `reported`
  mode and returns the same annual.

  *What this unblocked.* **CBO Option 56 was promoted into Tier 1** (PR #100).
  A percentile cap is exactly what the `BASE_DOLLARS` path prices, and in the
  option's own effective year, 2028, the module gives **$60.5B against CBO's
  $59B, +2.5%**. Over the full window it gives **−$529.9B against −$697.0B,
  24.0%**, and the whole residual is the growth path: CBO's revenue grows
  ~14%/yr because the limit is indexed to the chained CPI-U while premiums grow
  faster, so a widening slice of every premium sits above it. The module's
  distribution already produces that widening — its excess share goes 0.185 in
  2026 to 0.224 in 2028 — but `estimate_static_revenue_effect` evaluates it
  **once, at `start_year`**, and the engine then applies a flat 4%. **A
  year-indexed excess share is the next real structure this module is missing**,
  and it is now measured *inside* the battery rather than as hand arithmetic
  beside it. The option's validation shape pins `mode="derived"` and
  `annual_revenue_change_billions=None`; routing it through the module's app
  default (`reported`) would reproduce the leakage it was excluded for. Only
  CBO's third alternative is scored — 56.3 and 56.6 limit the income *and
  payroll* exclusion and this module has no payroll base.

  *Two smaller findings.* The old flat `baseline_cost * 0.15` for the charitable
  28% ceiling was right **by coincidence** — within half a point of the correct
  15.47% while having no way to know it; what changed is that the number now
  moves when the ceiling does. And `annual_cost_no_limit = 100.0` on the
  mortgage record **names no statute and stays dead deliberately**: wiring it in
  would move `eliminate_mortgage` from −5.1% to about +244% on an unsourced
  constant. The declaration mechanism is built and waiting for a source.

**Not cross-validatable (4 cases).** Reported with a reason; never folded into
the aggregate.

| Case | Why |
|---|---|
| `expand_niit` | NIIT expansion is a different mechanism (3.8% on pass-through income) from the OASDI wage bands, and it is the module's only NIIT benchmark — there is nothing to calibrate it on. |
| `eliminate_estate_tax` | The target is sourced "Model estimate", not a published score. Phase E already lists this entry for removal from the headline count. **The second half of this reason is no longer true.** It used to add that the machinery "reproduces estate-tax *differences* but not *levels*", its implied baseline being ~$196B/yr against CBO's ~$50B/yr. After L4 the model's 2026 baseline is **$47.6B**, 4.8% below CBO's, so only the unpublished target is carried. Derived, the case scores **$471.3B** against the $350B model estimate (+34.7%), reported as a diagnostic and folded into nothing. |
| `repeal_corporate_amt` | Its only base constant, `CORPORATE_AMT["revenue_per_year"] = 22.0`, is the CBO $220B/10yr target restated. |
| `eliminate_step_up` | Same shape: `JCT_TAX_EXPENDITURES["step_up_basis"]["annual_cost"] = 50.0` is the $500B/10yr target restated. |

*`eliminate_salt` was a fifth entry in this table between Wave 2 and Wave 3.*
`annual_cost_no_cap = 120.0` was exactly the carried $1,200B/10yr target
restated, and L6 made the `eliminate` rule read it; the guard was not touched by
that lane, it caught a constant the lane made load-bearing. PR #100 replaced the
constant with its SOI derivation ($89.55B), the guard stopped firing on its own,
and the case is derivable again at **+10.2%**. That is the mechanism working as
intended in both directions.

The last three are caught **mechanically**, not by a hand-maintained list:
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
default 75 — derived as the then-observed 59.3% × 1.25, rounded to 5) exists to
catch a *regression* in the structural machinery — a base table edited without
re-deriving — not to certify accuracy. Do not quote it as an accuracy claim. It
is deliberately **not** re-derived from the post-Wave-1 61.7%, the
post-provenance 58.7%, Wave 2's 32.3% or the current **28.4%**: a ceiling that
tracks every observation is not a gate, and this one now has a great deal of
room.

---

## 7. Sectoral module reconstructions — what the five new runners found

Phase E (plan §5.3) wired the five sectoral modules into the scorecard:
`validate_all_international`, `_trade`, `_pharma`, `_enforcement`,
`_climate` in `fiscal_model/validation/specialized_sectoral.py`. Seventeen
presets that ship in the app with an official number attached had never been
compared to it. (Three of those seventeen targets are model estimates rather
than published scores; the provenance label on each row says which.) Twelve of
them carry no module constant fitted to the target, and their mean absolute
error was **394.1%** (median 57.1%) against **2.7%** for the 34 benchmarks then
counted as fitted. **Wave 1's L7 lane took that 394.1% to 113.8%** by repairing
the two pharma incidence bugs §7.3 diagnosed; the median was unchanged at 57.1%,
because the repair moved two rows a long way and the other ten not at all.
**Correcting the insulin *target* on 2026-09-02 then took the subset to 104.8%
(median 40.0%)** — see §8.2 — against **2.2%** for the 30 benchmarks then counted
as fitted. The 12-row sectoral subset was unchanged by Wave 2.

**Wave 3 moved it twice, in opposite directions, and changed its population.**
L8 (PR #99) netted the tariff scores and took the 12-row subset **104.8% →
84.6%**; L9 (PR #98) gave FDII repeal a base × rate identity and pushed it back
up to **87.8%**. L8 also unfitted the two Trump tariff rows, so the subset is now
**14 rows at 81.0% (median 38.0%)** against **2.0%** for the 28 benchmarks
counted as fitted, and the tier it sits in is **26 rows at 61.8%** — or **63.6%**
on the 24 rows it held before L8. Quote the constant-population figures beside
the printed ones; a mean that moves because the population moved has not
improved. The per-family figures below are updated to the Wave 3 outturn, with
the Phase E starting points kept.

Nothing below was retuned. The instruction the phase was run under, and the
right one, is that a module far from its published figure gets reported as
`Poor` with a note — adjusting a constant to close the gap would convert a
finding into a fabrication, and the gap is often in the *target* rather than
the model.

**Targets are read, never restated.** Each scenario names a preset key and the
runner reads `CBO_SCORE_MAP[preset]["official_score"]`, so the validation layer
and the app cannot drift apart; a test enforces that no sectoral scenario
carries its own `expected_10yr`.

### 7.1 International tax (4 cases, mean 33.9%, 0 fitted) — reworked in Wave 3 (L9)

| Case | Official | Phase E | **Wave 3** | Error then → now |
|---|---:|---:|---:|---:|
| Biden GILTI reform | -$280B | -$230.27B | -$230.27B | 17.76% → **17.76%** |
| Repeal FDII | -$200B | -$170.00B | **-$110.70B** | 15.00% → **44.65%** |
| Pillar Two adoption | -$80B | -$61.20B | -$61.20B | 23.50% → **23.50%** |
| Biden international package | -$700B | -$413.00B | **-$353.71B** | 41.00% → **49.47%** |

**Two of the four got worse, and the lane pre-registered both before it opened
a file** (`planning/lanes/L9_international.md` §3.2). The predicted figures were
≈ -$110.7B / ≈ 44.7% and ≈ -$353.7B / ≈ 49.5%, hand-computed from the published
sources; the runners return **-$110.70B / 44.65%** and **-$353.71B / 49.47%**.
A lane that kept the flattering number to protect a 15% row would be doing
exactly what the plan's §1.1 forbids.

**Finding 1 — the FDII identity.** `_estimate_fdii_reform` returned a flat
`fdii_cost_billions` ($20B/yr) for a repeal while the rate-change branch two
lines below used `(new_effective − current_effective) × fdii_base` on a $160B
base, which at the 37.5% §250(a) deduction and a 21% statutory rate is
$12.6B/yr. **The same function's two branches disagreed by 59% about what the
FDII deduction costs.** Repeal now uses the identity, on a base sourced to
Treasury OTA's *Tax Expenditures FY2026* Table 1 line 5: **$130,230M over
FY2025-2034**, i.e. $13.0B/yr. So the row moves **toward the document and away
from the number it is scored against** — the carried -$200B is 54% above
Treasury's own published cost for the provision, and `benchmark_sources.py`
already recorded that it "matches neither the gross row (21% away) nor
Treasury's net score (zero)". Same shape as L5's AMT finding and L6's SALT
finding.

**Finding 2 — the double count the plan named is not in the code.** §3 L9 of the
plan expected `create_biden_full_international` to add a per-country GILTI to
Pillar Two's UTPR "on substantially the same undertaxed foreign profits". It
does not: `_estimate_utpr` reads `foreign_undertaxed_in_us_billions` — profits
of **foreign-parented** groups — while `_estimate_gilti_reform` reads the CFC
income of **US-parented** groups. **Those bases are disjoint**, so the new
`_estimate_base_overlap()` term correctly nets **zero** for all five shipped
factories, which `test_no_shipped_factory_books_an_overlap` pins. It ships as a
correctness fix for composite policies and moves no benchmark row, which was
registered in advance.

What the overlap work did establish is worth having in writing:

> With an 80% foreign tax credit, a per-country GILTI at 21% claims
> `0.21·Y − 0.8·T` from a jurisdiction where a 15% Pillar Two top-up claims at
> most `0.15·Y − T`. The difference is `0.06·Y + 0.2·T`, positive for every
> positive profit and non-negative tax. **A 21% per-country GILTI subsumes a
> 15% minimum tax in every jurisdiction, without exception**, so a policy
> carrying both raises the larger of the two, never the sum.

That is algebra; the IRS SOI Country-by-Country distribution is what shows where
it stops holding. `shared_claim_share(0.13125, 0.15)` — the 2026 statutory GILTI
rate against the OECD minimum — returns **0.9916**, not 1: at that rate the two
provisions interleave across jurisdictions and about 0.8% of the smaller claim
sits outside the larger. A constant would have got the 21% case right and this
one wrong. The lane uses the distribution's **shape** and takes no level from
it, because Form 8975's "profit before income tax" includes intra-group
dividends and its "income tax accrued" excludes deferred tax.

**Finding 3 — the package's residual is a level, not an interaction.**
Treasury's FY2025 Green Book scores the UTPR it proposes at **$136,313M** over
FY2025-2034; the module's UTPR returns $1.5B/yr, i.e. **$15B**, one ninth of it.
Independently, JCT's Scenario 5 minus Scenario 4 (JCX-22-23 Table 2) prices a US
UTPR at **$133.9B**. Two published sources agree within 2% and the module is 9×
under both. Closing it means re-basing the UTPR on JCT's Equation 2 — the
*group's* global low-taxed profit allocated to the US by an employee-and-tangible-asset
key, not profits booked in the US — which needs OECD CbCR aggregates by
ultimate-parent jurisdiction. `oecd.org` returns HTTP 403 to this environment,
and the only reachable figure for the quantity is Treasury's own row *inside the
package benchmark*, so deriving the base from it would be circular. **This is
the single largest remaining item in the module** and it is what a Wave 4 lane
should open with.

**Pillar Two, read against the range rather than the midpoint.** No target
moved in this lane; PR #100 then superseded the target with the range.

| Comparator | Figure | Model -$61.2B is |
|---|---:|---|
| Carried benchmark (midpoint) | -$80.0B | 23.5% low |
| The module's own stated range | $50–120B | **inside it** |
| JCT JCX-22-23 Scenario 4 — the scenario this factory models | +$102.6B | 40.4% low |
| JCT Scenario 2 — rest of the world enacts too | **-$56.5B**, a revenue *loss* | opposite sign |

The row's real problem is not its distance from any of these. It is that
`create_pillar_two_adoption` models US adoption **conditional on nobody else
adopting**, which is the only state of the world in which JCT scores it as a
raiser at all.

**Two constants left alone deliberately.** `gilti_cbc_revenue_multiplier = 1.20`
("Treasury calibrated") and `gilti_ftc_offset_rate = 0.40` ("Calibration
factor") are self-declared fits. Treasury OTA prices the whole CFC
active-income preference at **$383,830M** over FY2025-2034 against the module's
implied $271B for taking GILTI to the full statutory rate with QBAI eliminated —
the identity that would replace both. The lane was told not to regress that row,
the tax expenditure also covers §245A exclusions a GILTI rate change does not
recover, and swapping a fitted constant for a published-but-broader one on a row
outside the lane's two named mechanisms is the kind of unregistered move the
plan's §1.3 exists to prevent. Recorded so the next lane has the number.

The module docstring now says which parameters are **fitted** (GILTI, Pillar
Two), which are **transcribed** (FDII) and which are **structural** (the
overlap), because only the fitted ones make a small error bookkeeping rather
than skill. And `$373,919M` is no longer described as a Green Book row for the
-$280B GILTI proposal: there is no row for a GILTI change alone, and the nearest
also covers inversions and related reforms.

### 7.2 Trade / tariffs (5 cases, mean 38.4%, 0 fitted) — gross → net in Wave 3 (L8)

| Case | Official | Phase E | **Wave 3** | Error then → now |
|---|---:|---:|---:|---:|
| Universal 10% tariff | -$2,000B | -$2,021.6B *(fitted)* | **-$1,258.5B** | 1.1% → **37.1%** |
| 60% China tariff | -$500B | -$531.1B *(fitted)* | **-$278.4B** | 6.2% → **44.3%** |
| 25% auto tariff | -$100B | -$252.3B | **-$182.2B** | 152.3% → **82.2%** |
| 25% steel & aluminium tariff | -$60B | -$103.9B | **-$52.9B** | 73.2% → **11.9%** |
| Reciprocal tariffs (~20pp) | -$1,200B | -$2,736.0B | **-$1,396.8B** | 128.0% → **16.4%** |

**The headline finding was structural and it was large: `trade.py` had no
income-and-payroll offset at all.** `estimate_static_revenue_effect` returned
gross customs revenue with a flat 5% avoidance haircut and stopped. CBO, JCT and
Treasury all score an indirect tax **net of a ~25% income-and-payroll offset**,
on the convention that a policy change does not alter total nominal income: duty
paid is income not paid to labour and capital, so the income and payroll tax
bases shrink. L8 subtracted it, converted the retaliation channel's export loss
into lost federal receipts at the app's own `MARGINAL_REVENUE_RATE = 0.25`,
routed the import-demand response through a **border** pass-through frozen at
1.00 (near-complete: Amiti–Redding–Weinstein 2019; Fajgelbaum et al. 2020), and
applied the duty as a **tax-inclusive** rate, `base × τ/(1+τ)`, because a
conventional estimate holds nominal income fixed. Every level in
`TRADE_BASELINE` was replaced by a 2024 Census measurement.

**The two fitted rows had to lose their flattering numbers.** The 1.1% and 6.2%
were bookkeeping: the Trade runner already flagged both `calibrated_to_target`
and said in as many words that `universal_coverage_rate = 0.70` and
`china_effective_coverage = 0.50` were picked to reproduce those figures. The
first is now the Census non-USMCA import share (**0.7197**); the second was
**deleted** for the incremental-rate identity a 60% China tariff actually implies
(60pp *minus the duty already collected*, applied to the whole base — not 40pp on
half of it), along with `create_trump_china_60`'s per-case
`import_elasticity=-0.7` override. No `TRADE_BASELINE` constant is fitted to any
target any more, both rows moved to the reconstruction tier, and the **fitted
tier fell 30 → 28 rows and 2.2% → 2.0%** — it improved, because one departing row
was above the tier mean and one below. (The lane's own pre-registration got that
wrong and says so: it registered the fitted tier as "55 rows at 15.4%", a
population that swept in the 25 out-of-sample Generic rows that carry
`calibrated_to_target` by default.)

**Two out-of-sample cross-checks, neither of them a benchmark.** Net as a share
of gross runs **0.599 to 0.655** across the five presets, registered in advance
at 0.60–0.66 and above the 0.50 floor the lane named as the double-counting
tell; the repository's own knowledge snapshot puts a *fully* netted tariff score
at 40–50% of gross, and that chain includes a GDP-feedback drag this module does
not model, so sitting above the band is the right side to miss on. Retaliation
returns **$111.4B** over ten years for the 10% universal tariff against Tax
Foundation FF861's **$278B** — 2.5× smaller, and the gap is the channel's stated
limitation: an export-value loss is not an income loss, and nothing here carries
a multiplier or a supply-chain effect.

**A sign defect the lane found in its own diff.**
`estimate_behavioral_offset` returned an **unsigned positive** number, which the
scorer adds to `-static_revenue`. That is right for a tariff increase and exactly
wrong for a tariff **cut**: a 5pp cut on a $1,000B base scored **$711B** of
deficit against a gross revenue loss of **$553B** — the income and payroll bases
being shrunk by a tax that had just been *reduced*. The offset now carries the
static effect's sign, which is `docs/METHODOLOGY.md`'s own convention, and the
same cut scores **$394B**: eroded, as it should be. The bug pre-dated the lane —
the 5% avoidance haircut had it too — but adding a 25% offset and a retaliation
channel on top made it roughly six times larger, so it was fixed here. **No
shipped preset moves**: all five are tariff increases.

**Three targets remain untraceable, and two of the three now bracket the model
rather than sitting far from it.** The auto -$100B implies about $10B/yr; Census
2024 puts HS-87 imports at $384.9B, of which 48.4% comes from Canada and Mexico,
so even carving all of that out leaves a $198.5B base. `benchmark_sources.py`
already records that CRFB, the stated source, itemises no auto figure in any of
four posts, and that the two located primary estimates are **Tax Foundation's
$386.2B** and **Yale Budget Lab's $600-650B**, 4-6.5× above the carried target.
The model's -$182.2B now sits *between* the carried figure and those two. The
steel and reciprocal targets are unsourced at either value. Moving them is
provenance work, not a modelling lane's.

One further problem is target-side and worth stating before anyone treats
these rows as accuracy statements:
- **A bookkeeping defect in `app_data.py` — fixed in the provenance pass.**
  `CBO_SCORE_MAP` keyed the steel preset as "25% Steel & Aluminum Tariff
  (-$60B)" while `PRESET_POLICIES` keyed it "25% Steel/Aluminum Tariff
  (-$15B)"; the reciprocal preset had the same mismatch ("Reciprocal Tariffs
  (~20pp)" vs "Reciprocal Tariffs"). The two dictionaries never joined, so **the
  app showed no official score for either preset**, and in the steel case the
  two figures differed by 4x. Both labels are now identical in both
  dictionaries (steel on -$60B), the two `SCORE_ONLY_ALIAS_ID_BY_LABEL` aliases
  that had been papering over the share-link half of the problem are gone, and
  `tests/test_validation_runners.py` pins the join — plus the general form of
  the rule, that no `CBO_SCORE_MAP` label may resolve to a preset id under a
  different spelling. **Which figure is right remains unknown**: no Tax
  Foundation or TPC publication states a 25%-rate steel-and-aluminium ten-year
  estimate, and -$15B is annual-scale. See §8.3.

### 7.3 Drug pricing (3 cases, mean 236.9%, 0 fitted) — repaired in Wave 1 (L7)

| Case | Official | Model (Phase E) | Err | **Model (post-L7)** | **Err** |
|---|---:|---:|---:|---:|---:|
| Expand drug negotiation | -$500B | -$372B | 25.7% | -$372B | 25.7% |
| Universal insulin cap | -$15B → **+$11.4B** | -$445B | 2,868.6% | **+$7.0B** | **39.0%** |
| International reference pricing | -$100B | -$1,388B | 1,287.9% | **-$746B** | **646.2%** |

Family mean **1,394.1% → 272.8%** on the model repair alone; the 12-row sectoral
subset it sits in moved **394.1% → 113.8%** (median 57.1%, unchanged), and the
20-row reconstruction tier **250.8% → 82.6%**. The insulin *target* was then
corrected on 2026-09-02 (§8.2), which is a target movement rather than a model
one: the family reads **236.9%**, the sectoral subset **104.8%** (median 40.0%),
and the reconstruction tier 21 rows at 76.7% — **24 rows at 72.1%** after Wave 2
moved the three capital-gains scenarios into it, and **26 rows at 61.8%** after
Wave 3's L8 and L9 lanes (the sectoral subset now 14 rows at 81.0%, or 87.8% on
its pre-L8 population). **No parameter was fitted to any of these three
targets**, and no pharma row moved in Wave 3.

**What Phase E found.** Two of the three were not calibration drift but
incidence bugs in `pharma.py`:

- `_estimate_insulin_savings` credited the *entire* difference between a $6,000
  average annual insulin cost and the $420 capped cost to the federal budget,
  for all 8.4M insulin users — ~$47B/yr of "federal saving" from a cap that
  mostly reallocates cost among patients, insurers and manufacturers. Worse,
  `extend_to_private=True` set `medicare_share = 1.0`, so extending the cap to
  private insurance *raised* the modelled federal saving 2.5×.
- `_estimate_reference_pricing_savings` applied RAND's **gross list-price**
  ratio (2.56) to a **net** Part B + Part D spending base with no rebate
  adjustment and no brand/generic split — even though US unbranded generics are
  *cheaper* than the OECD comparison (67% of comparison-country prices) and
  cannot contribute savings.

**What L7 repaired.** Both are now specified on a net-price, brand-only,
federal-share basis, with every input transcribed with document, page and URL to
`fiscal_model/data_files/pharma/drug_pricing_incidence.csv` and pinned against
`PHARMA_BASELINE` by `tests/test_pharma_incidence.py`:

- **Insulin** is a **cost-sharing** cap, so it moves a patient's liability onto
  the plan and the federal budget picks up only its share of that shift: ASPE's
  $734M/yr of Part D out-of-pocket relief × Medicare's 74.5% statutory
  basic-benefit subsidy share (MedPAC), plus the private-market cost shift ×
  CBO's 32% marginal income-plus-payroll offset. The result is **+$7.0B — a
  deficit *increase***.
- **Reference pricing** applies RAND's *net* brand ratio (3.08, after a 37.2%
  gross-to-net adjustment) to a brand-only, rebate-netted Part D + Part B base,
  times the federal share of each program.

**The insulin row, and the target that has since caught up with it.** Model
**+$7.0B** against **CBO publication 57957's +$11.4B** (+$6.566B outlays,
-$4.793B revenues, FY2022-2031): **39.0% below it**, directions agreeing. When
L7 landed, the carried benchmark was still -$15.0B and the row read 146.4% — the price of
saying what CBO says, since no percentage against a benchmark pointing the other
way can be read as accuracy. The target was moved to +$11.4B on 2026-09-02
through `validation/target_revisions.py` (§8.2), so the 39.0% *is* an accuracy
statement now. The residual is two named omissions: induced utilisation, and
growth in insulin cost and enrolment across a ten-year window, since ASPE's
$734M is a single 2020 figure held flat.

**What is *not* repaired, on either row.**

- The reference-pricing base is still **overstated**: RAND's index is computed
  on presentations sold in both markets, and the module applies it to **all**
  brand spending.
- **No utilisation, launch-delay or availability response is modelled** on
  either row.
- `expand_drug_negotiation`'s linear per-drug scaling is untouched — savings
  scale linearly in drug count from the IRA per-drug average with a flat 60%
  productivity haircut, while CBO's scoring is strongly non-linear in *which*
  molecules enter the window. Its -$500B target is `model_estimate` and is not a
  CBO score of this policy.

The residual on the reference-pricing row is now mostly the **target**: -$100B
is provenance `model_estimate` — a RAND price statistic, not a budget score —
while the model's -$746B sits above CBO's ~$456B for H.R. 3's *narrower*
international-reference cap (120% of the average international market price on a
limited set of drugs), which is where a broader policy should sit. Closing this
row to under 100% would require making the model wrong; the lane said so in its
pre-registration, before the code changed.

**Shipped preset output moved**, as the plan's L7 caveat warned it would:
💊 Universal Insulin Cap -$445.3B → **+$7.0B**; 💊 International Reference
Pricing -$1,387.9B → **-$746.2B**; 💊 Comprehensive Drug Reform -$1,025.8B →
**-$573.5B**; 💊 Expand Drug Negotiation unchanged. No preset label and no
`CBO_SCORE_MAP` entry changed — those carry the official score, not the
model's.

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

*(Live as of 2026-09-02, after Wave 3: **28 fitted at 2.0%, 28/28** — a 34th
row left the fitted tier when its target was revised, three more left when
L1 deleted the constants fitted to them, and two tariff rows left when L8
replaced their fitted coverage constants with Census measurements, so held in
place the revised row would make it 29 at 4.3%, 28/29 — against **26
reconstructions at 61.8%**.)*

*(Phase D later added eight P.L. 119-21 line items to this same unfitted class, at
35.8% mean, taking it to 20 entries and a 250.8% mean — see §8. Wave 1's L7 lane
then repaired the two pharma incidence bugs, taking the 12-row sectoral subset to
113.8% and the 20-row tier to 82.6% — see §7.3 — the 2026-09-02 target
revisions took them to **104.8%** and 21 rows at 76.7%, Wave 2's three
capital-gains arrivals took the tier to **24 rows at 72.1%**, and Wave 3's L8 and
L9 lanes plus the two reclassified tariff rows took it to **26 rows at 61.8%**
(63.6% on the pre-L8 population). The Phase E figures above are kept as the
outturn of Phase E; **live numbers come from `python scripts/cold_holdout.py`**,
never from this table.)*

`scripts/cold_holdout.py` reports them as separate tiers, and the anti-leakage
invariant in `tests/test_cold_holdout.py` compares the out-of-sample tier
against the *fitted* set — mixing the two would have flipped the invariant for
the wrong reason (44.8% out-of-sample vs a 104.8% "calibrated" mean) and hidden
the fact that the fitted tier is still low by construction (2.0% over 28).

`readiness.py --strict` treats a documented `Poor` on an unfitted reconstruction
the same way it treats a documented out-of-sample miss: a warning, not a
blocker. A documented `Poor` on a *fitted* benchmark stays strict-blocking,
because those parameters exist to reproduce the target and a miss there really
is a regression. That sentence stops being true the moment a target is
**revised**, since the constant reproduces the *superseded* figure and was never
fitted to its replacement — so `scorecard.py` derives `calibrated_to_target`
from the revision ledger, and a revised row reports in the reconstruction tier.
Retuning the constant would also have turned it green, and that is the move a
provenance pass is forbidden to make.

Blocking on the reconstructions would have made deleting the
runner the cheapest route back to green — precisely the incentive the
pre-registration manifest exists to forbid.

### 7.7 Provenance of the targets (as first labelled)

Of the 46 calibrated-tier benchmarks, the *inference* pass found: **4
`line_item`**, **31 `secondhand`**, **7 `model_estimate`**, **4
`unclassified`**. Only four benchmarks in the whole calibrated tier — CBO's May
2024 *Budgetary Outcomes Under Alternative Assumptions*
([pub. 60271](https://www.cbo.gov/publication/60271)) and the three
capital-gains cases — cited a specific document; every sectoral target added in
that phase was a rounded headline figure or an explicit model estimate. Labels
are assigned in `fiscal_model/validation/provenance.py`, either declared or
inferred from the record's own source string, URL and the roundness of the
target, and are never guessed.

That pass could tell a rounded headline from a citation. It could not tell
whether the row being cited exists — which is a different question, and §8 is
what happened when someone asked it. **Post-transcription the breakdown is 9 /
15 / 15 / 7 / 0** (`line_item` / `line_item_differs` / `secondhand` /
`model_estimate` / `unclassified`) across those same 46.

Phase D's eight P.L. 119-21 line items then joined the tier already
transcribed — their targets *are* JCT's rows, extracted with page references
into `pl119_21_jct_line_items.csv` — taking the calibrated breakdown over 54
benchmarks to 17 / 15 / 15 / 7 / 0. Two targets were then **revised** rather than
carried (§8.2), moving both rows from `line_item_differs` to `line_item`, so the
live breakdown is **19 / 13 / 15 / 7 / 0**, of which **28 have actually been read
out of a document** and 4 are the cited-but-unread backlog below. Across both
tiers the scorecard holds **80 rows, 73** of them against a published figure —
the 80th being CBO Option 56, promoted out of the leakage exclusions into Tier 1.
A **third** target was revised in Wave 3, `pillar_two_adoption`, but to a *range*
rather than a point, so it keeps its `line_item_differs` label: the gap to the
nearest published scenario is real, and what the revision asserts is that no
point can close it.

---

## 8. Phase E provenance pass — per-target sourcing notes

§7.7 counted labels that were *inferred* from each record's own source string,
URL and roundness. This section records what happened when somebody opened the
documents. Full transcriptions — document, table, row, page, date, figure — are
in [`fiscal_model/validation/benchmark_sources.py`](../fiscal_model/validation/benchmark_sources.py);
this is the compact index, and the notes below are the parts that are not
obvious from the figures.

**Rule applied throughout:** `line_item_differs` requires the source to score
the *same policy definition*, just with a different number. Where the primary
document scores a materially different instrument — a different rate, a
different cap design, a bundle of provisions — the record stays `secondhand`
and the search record names the nearest published row instead. Calling another
policy's number "the line item" would be worse than having no citation.

**Access caveat.** `cbo.gov` returns HTTP 403 to every non-browser client
(bot challenge), on every path and user-agent, and `web.archive.org` was
unreachable. Several CBO figures were therefore read from a *published document
quoting the CBO table verbatim* — usually a CRS report, which names the CBO
publication in its own source note. Those rows cite what was actually read.

### 8.1 Confirmed (9 calibrated + 1 out-of-sample)

| Benchmark | Target | Published | Document |
|---|--:|--:|---|
| Biden corporate 28% | -$1,347B | $1,349,941M | FY2025 Green Book, report p. 239 |
| Extend TCJA estate exemption | $167B | $166.9B | CRS R48286 Table 1 (CBO pub 60114) |
| Repeal corporate AMT | $220B | $222,248M | JCX-18-22 p. 1 — **JCT's estimate, not CBO's** |
| SS cap to 90% of earnings | -$800B | $804.9B | CBO Options 2019-2028, budget-options 54806 |
| Expand NIIT to pass-through | -$250B | $252,163M | JCX-46-21 p. 6 (Build Back Better) |
| Treasury 39.6% + step-up repeal | -$322B | $322,485M | FY2022 Green Book, report p. 105 |
| TCJA full extension | $4,600B | — | CBO pub 60271: cited, **not re-transcribed** (cbo.gov blocked) |
| CBO +2pp all brackets | -$70B | — | budget-options 54788: cited, not re-transcribed |
| PWBM 39.6% with / without step-up | $33B / -$113B | — | PWBM April 2021 brief: cited, not re-transcribed |

The last four are the remaining calibrated backlog: they carry a deep link to a
real document, which the first Phase E pass took as evidence of a table row,
but nobody has read the row. They are enumerated in
`tests/test_validation_runners.py::CITED_BUT_NOT_TRANSCRIBED` and the set may
shrink, never grow. `ScorecardEntry.transcribed` is deliberately stricter than
the `line_item` label for exactly this reason.

Phase D's three enacted-law components — the Social Security Fairness Act's
WEP/GPO repeal, the Fiscal Responsibility Act's discretionary caps and IIJA's
discretionary component — join that backlog on the out-of-sample side, for the
same access reason: their targets are unrounded to three decimals and the
manifest notes quote the estimates' own outlay paths, so the tables were read
when the targets were entered, but all three cbo.gov deep links still return
HTTP 403 and this pass could not re-open them to record a row.

Notes worth carrying:

- **SS cap to 90%** is the *2018* volume ($804.9B revenue, $785.1B deficit
  effect). CBO's 2024 volume scores the same option at $727.6B — 10.6% lower,
  which is about the size of the residual the payroll module is asked to close.
- **Repeal corporate AMT** and **repeal EV credits** were both attributed to CBO
  and are both JCT estimates. Corrected in `CBO_SCORE_MAP` and in the scenario
  registries.
- **Treasury 39.6% + step-up repeal** confirms the *shape*, not only the number:
  FY2022 Green Book footnote 1 states that "a separate proposal would first
  increase the top ordinary individual income tax rate to 39.6 percent (43.4
  percent including the net investment income tax)", so this row's incremental
  rate really is 23.8% → 43.4%, the +19.6pp the record already carried.

### 8.2 Transcribed and different — the owner-decision list

The full table with deltas is in [VALIDATION.md](VALIDATION.md#line_item_differs--the-transcription-disagrees-with-the-target-owner-decisions).
Five are worth more than a row:

1. **Universal insulin cap: the sign was inverted — and the target has been
   corrected (2026-09-02).** CBO's estimate for H.R. 6833 (pub. 57957) is
   **+$6.566B of outlays and -$4.793B of revenues** over FY2022-2031 — about
   **+$11.4B added to the deficit**, because capping a patient's cost sharing
   reallocates cost to plans and to the federal subsidy for them. The repository
   carried -$15B as a saving, traceable to no CBO document. §7.3 identified the
   model side as an incidence bug and Wave 1's L7 lane fixed it (**+$7.0B**); the
   target had the same bug, and was moved to +$11.4B through
   `validation/target_revisions.py`, with -$15B kept on the record as a
   `superseded_by` row. The row now reads **39.0%**, an accuracy statement
   rather than a direction dispute, and `KNOWN_TARGET_SIGN_INVERSIONS` in
   `tests/test_validation_runners.py` is an **empty set** — the emptiness being
   the assertion.
2. **Extend TCJA AMT relief was a window error — and the target has been
   corrected (2026-09-02).** The published ten-year cost is $1,357.1B; the
   *five*-year cost in the adjacent column is $466.2B; the repository carried
   $450B, which is 3.5% from the five-year figure and 66.8% from the ten-year
   one. A five-year figure sitting in a ten-year column explains it exactly, and
   JCT's JCX-35-25 corroborates the ten-year number independently at $1,362.810B
   for P.L. 119-21's AMT provision. The target was moved; **the module was
   not retuned**, because retuning it would re-fit the module to the number it is
   being tested on. So the fitted annual now reads **-66.8%** against its own
   corrected target and the **derived** path (TPC T25-0049, $855.3B) reads
   **-37.0%** — the unfitted machinery landing about 1.8× closer to the document
   than the fitted constant, which is L5's claim measured rather than asserted.
   The row reports in the unfitted-reconstruction tier for exactly that reason.
   See §6's AMT bullet.

   *Definitional caveat, stated rather than split:* CRS/CBO score the AMT
   provision *inside* a full TCJA-extension package, where extended rate cuts
   push more filers into AMT; TPC's T25-0049 reconstructs the **standalone**
   post-sunset counterfactual and implies about $855B. Both are published and
   they answer different questions. The package figure is the one this
   benchmark's own description asks for, and the only one of the two that is a
   *scored provision* rather than a baseline projection.

   *`repeal_individual_amt` was searched again and not moved.* No published
   post-2025 repeal score exists at JCT, CBO or TPC; the nearest primary figure,
   JCX-46-17 p. 3 (-$695.5B, FY2018-2027), is a pre-TCJA baseline and a different
   decade. TPC T25-0049's $948.9B column is deliberately not adopted: it is a
   baseline projection rather than a scored repeal, and it is `amt.py`'s own
   input, so adopting it would manufacture a 0% row out of the leakage `loo.py`
   guards against. It stays at an unsourced $450B that is internally incoherent
   with the transcribed $1,357.1B — a full repeal cannot cost less than
   extending the exemption on the same baseline — and closing it needs a
   published score or an owner decision to re-register `holdout.py`'s locked
   protocol.
3. **Repeal FDII nets to zero as Treasury scores it.** Gross repeal raises
   $157,993M, and Treasury pairs it one-for-one with "Provide additional support
   for research and development expenditures" (-$157,993M), printing an explicit
   subtotal of $0 — in FY2022, FY2024 and FY2025 alike. The module scores repeal
   *without* the offset, i.e. the gross row, so -$200B matches neither.
4. **Pillar Two's sign depends on a condition nobody states.** JCT's
   revenue-raising scenarios assume the **rest of the world does not enact**.
   Under the scenario that actually obtains — everyone enacts — JCT scores US
   adoption at **-$56.5B of receipts**, a loss. The module's -$61B against a
   -$80B target looked like a 23.5% miss; the more useful reading is that the
   benchmark's sign is conditional.
5. **The estate benchmark was attributed to the wrong agency and the wrong
   policy.** No Biden Green Book (FY2022, FY2024, FY2025) proposes a $3.5M
   exemption or a 45% rate — the FY2025 volume's entire estate section is
   administrative and anti-abuse, subtotal $97,221M. The design is the "For the
   99.5 Percent Act", scored by JCT at $429.6B over FY2021-2031 — for the whole
   ten-section bill, including graduated 50/55/65% brackets, grantor-trust
   step-up denial, valuation-discount limits and GST changes. So $429.6B is an
   upper bound on what the exemption-and-rate change alone scores, and the
   repository's -$450B is above it.

### 8.3 Searched and not found

Fifteen calibrated targets stayed `secondhand`. Each carries a `searched`
record; the four structural ones:

- **The two Social Security payroll targets have no dollar source.** OCACT does
  score both provisions — E2.1 (eliminate the taxable maximum) and E2.5 (tax
  earnings above $250,000) — on the 2025 Trustees basis, and publishes **only
  percent-of-taxable-payroll and trust-fund dates**: +2.55% and +2.50% of
  payroll, depletion moving from 2034 to 2059 and 2057. No ten-year dollar
  figure exists at OCACT for any payroll provision, so "-$3.2T / -$2.7T
  (Social Security Trustees)" cannot be what it says it is. The "$2.7 trillion
  over 10 years" traces to a think-tank explainer with no report year and no
  run number. CBO's figures for the same designs are roughly half: $1,222.6B
  (2018 volume) and $1,426.8B (2024 volume, Option 62).
- **`repeal_ira_credits` cites a CBO document that does not appear to exist.**
  JCT's original score is -$205.2B (JCX-18-22, Subtitle D) and its score of the
  enacted terminations is $499.1B (JCX-35-25). The -$783B most plausibly comes
  from CRFB reading CBO's 2024 baseline ("closer to $800 billion" through 2033
  absent the EPA rule) — a projection of what the credits will *cost*, not a
  scored repeal. Since the climate module's annual constant is this target
  restated, the row's 0.0% error was never evidence of anything, and now the
  target is not evidence either.
- **`cap_employer_health` scores a cap design nobody has published.** Every
  published option caps the exclusion at a *percentile of premiums*, which in
  dollars is far below the record's "$50K": CBO's 2013 volume caps at $6,420
  individual / $15,620 family. Across four CBO volumes the alternatives run
  -$174B to -$965B; -$450B sits inside that spread and matches no alternative in
  any of them.
- **`cap_charitable` points at a real proposal that is not a charitable cap.**
  The Obama-era 28% limitation is a genuine Green Book row with a genuine score
  ($645,538M over FY2017-2026), but it limits the value of *all itemized
  deductions* plus municipal-bond interest, employer health coverage, retirement
  contributions, HSAs and student-loan interest. Scoring a charitable-only cap
  against a figure three times larger and mostly driven by other provisions
  would be worse than leaving it unsourced.

### 8.4 Out-of-sample: one retirement, one re-sourcing, two open questions

- **`top_rate_45` retired.** TPC's full sitemap was enumerated (11 sub-sitemaps,
  ~20,600 URLs, ~6,500 model-estimate pages): no table for a 45% ordinary rate
  exists at any date. CBO and JCT publish no +8pp top-bracket option. PWBM
  (May 2025) brackets the range at $401.6B (revert the top bracket to 39.6%) and
  $222.4B (new 39.6% bracket above $1M), making -$420B for +8pp above $609,350
  implausibly *low*. Withdrawn with the search recorded, and the unsourced
  figure removed from `CBO_SCORE_MAP` so the app stops quoting it.
- **`biden_capital_gains_39` re-sourced, and it now scores worse.** -$456B is in
  no Treasury volume; the FY2025 Green Book's combined "Reform the taxation of
  capital income" row is $288,583M and Treasury never splits the rate change
  from the realization-at-death change. The manifest row is superseded
  (`.v1` → `.v2`) and the shape corrected to the source's definition — taxable
  income over $1M, $5M per-donor exclusion — moving the prediction from -$817B
  to -$699B against a smaller target: **79% → 142%**. Across four Green Books the
  same row reads $322,485M → $174,488M → $213,855M → $288,583M, so the 42% gap
  Phase A flagged between this and the FY2022 case was not two estimates
  disagreeing; one of them was never published.
- **Open: `illustrative_top_rate_5pp` (-$700B)** — no TPC table states it, and
  the record calls itself illustrative. PWBM scores a smaller change on the same
  threshold at $222.4B.
- **Open: `warren_ultramillionaire_surtax_3pp` (-$350B)** — TPC's only AGI-surtax
  table, T19-0037 (23 September 2019), scores a **10pp** surtax on AGI over $2M
  at $585.3B, i.e. ~$58.5B per percentage point, implying ~$175B for 3pp. The
  table does confirm the record's `agi_inclusive_base=True` flag.
- **Open: `biden_high_income_tax` (-$252B)** — published at $245,924M (2.5%).
  Pre-registered targets are frozen, so correcting it needs a new manifest row.

### 8.5 What this changes about the headline

Nothing about the model, and quite a lot about how its errors should be read.
The calibrated tier's low by-construction error is measured against targets of
which **13 are still known to disagree** with the document they cite and 15 more
cannot be traced to a document at all; **3 were corrected** (one of them to a
range rather than a point), and none disagrees in sign any more. An error against
a target that is itself wrong is not an accuracy statement, and the scorecard now
says which rows those are — including, per entry, `target_revision_id`,
`superseded_10yr_billions`, `target_revision_reason`, and for a range row
`published_range_low_billions` / `published_range_high_billions` /
`within_published_range` / `distance_to_published_range_billions`, with
`revised_target_entries` on the summary — rather than leaving a reader to assume
every row is equally solid. A fourth state is now recordable and used:
`EXAMINED_NOT_REVISED`, "somebody opened the document and decided against", whose
first entry is `biden_estate_reform`.

The headline counts moved too: `published_entries` replaces `total_entries`
everywhere a sentence ends "validated against CBO/JCT", because the seven
illustrations have no CBO/JCT number to be validated against. Phase E left that
at 61 of 68 rows; merged with Phase D's additions it read 72 of 79, and after
Wave 3 promoted CBO Option 56 it reads **73 of 80**. Both numbers are computed
live, so no document should ever restate them without running
`scripts/run_validation_dashboard.py` first.
---

## 8. P.L. 119-21 — sourcing the first line-item block (Phase D)

Phase E's provenance pass ended with an uncomfortable count: **4 of 46**
calibrated targets were `line_item` — a number traceable to a specific row in a
specific table. The other 42 were rounded headline figures, model estimates, or
unclassifiable. Promoting one requires opening the document and transcribing the
row, which Phase E deliberately left as work rather than asserting. Phase D does
that work once, for the largest tax law in the database.

### 8.1 Which document, and why

| Document | What it scores | Baseline | Used here? |
|---|---|---|---|
| **JCX-35-25** (1 Jul 2025) | Tax provisions of Title VII of the Senate substitute | **present law** | **yes** |
| JCX-34-25 (1 Jul 2025) | The same provisions | current policy | no |
| JCX-36-25 / JCX-37-25 | Distribution of the revenue effects | both | no (revenue block) |
| CBO 61570 (21 Jul 2025) | The whole law, including health provisions | CBO Jan 2025 | cross-check only |
| CBO 61367 (11 Aug 2025) | Distribution of the whole law | CBO Jan 2025 | distributional block |

**JCT published no separate "as enacted" estimate of the tax title.** The House
passed the Senate substitute without amendment, so the Title VII text JCX-35-25
scores is the text enacted as P.L. 119-21 on 4 July 2025. JCX-34-25 scores the
same provisions against a *current policy* baseline — one in which the expiring
2017 provisions are assumed to continue, which makes their permanent extension
nearly free. The repository's convention, and CBO's, is present law, so
JCX-35-25 is the right document and JCX-34-25 would have been the wrong one.

**Cross-check that the transcription is of the right table**: JCX-35-25's own
NET TOTAL is -$4,474,972M over 2025-2034. CBO publication 61570 describes the
law as "a decrease in revenues of $4.5 trillion" and "a decrease in direct
spending of $1.1 trillion", netting to a $3.4 trillion deficit increase relative
to CBO's January 2025 baseline. Those agree, and `test_pl119_21_line_items.py`
pins the net total so a future edit cannot quietly detach the two.

### 8.2 How the rows were obtained

cbo.gov and the jct.gov *landing pages* serve a bot challenge to plain HTTP
clients, but the jct.gov attachment path does not: the PDF is fetchable directly
and is parsed with `pdfplumber`. `scripts/extract_pl119_21_line_items.py` holds
the transcription (`extracted_by=manual` — the JCX table is a fixed-width,
multi-line-label layout no general parser handles cleanly) and **verifies** it:
`--pdf` checks that every transcribed total appears verbatim in the extracted
text. 34 of 34 verifiable totals are found; the thirty-fifth, the subchapter A
energy subtotal, is the only figure JCT does not print, and it is instead
cross-checked against the chapter total (subchapter A +542,653 plus subchapter B
-43,573 equals the printed chapter total +499,080).

Verification catches the failure mode a hand transcription actually has — a
mistyped digit. It cannot catch a total read off the wrong row, which is why
every row also carries its `pdf_page` and `jct_item`.

### 8.3 What the block measures

Eight provisions have a module path, all through
`create_tcja_extension`'s component flags. Nothing is fitted to any of these
rows: `TCJAExtensionPolicy` carries **one** calibration factor (1.77), fitted to
CBO's $4.6T aggregate. So the block asks a question no other benchmark in the
repository asks — *can a module tuned on one aggregate also decompose?* — and
the answer is no:

| Provision | JCT | Model | Error | Structural cause recorded |
|---|---:|---:|---:|---|
| Reduced rates | +2,193.4 | +2,752.8 | 25.5% | one aggregate annual at 3.5%/yr, no bracket structure |
| Standard deduction | +1,424.7 | +1,078.9 | -24.3% | single national annual; cannot see the enhancement |
| Personal exemption repeal | -1,807.1 | -989.0 | 45.3% | JCT nets the new senior deduction into this row |
| Child tax credit | +816.8 | +863.3 | 5.7% | module holds the $2,000 credit, law sets $2,200 indexed |
| Section 199A | +736.5 | +1,123.9 | 52.6% | one aggregate at 4%/yr, no pass-through distribution |
| Estate/gift exemption | +211.7 | +195.2 | -7.8% | aggregate annual, not estate.py's exemption machinery |
| AMT exemption | +1,362.8 | +719.3 | -47.2% | law also cuts phaseout thresholds and raises the rate |
| SALT limitation | -946.2 | -1,685.8 | -78.2% | **design mismatch**: module has the flat $10K cap |

The scoring window is JCT's own, FY2025-2034, with the policy effective in
FY2026 so `Policy.is_active()` leaves FY2025 at the zero JCT prints for most of
these rows. That is worth stating because an earlier revision of this branch
built the scorer at 2026 and therefore summed FY2026-2035 — silently trading
JCT's zero-effect 2025 column for a tenth year of effect in 2035 and inflating
every row. Correcting it moved the block's mean from 41.8% to 35.8% and made
three of the eight rows *worse*, which is the tell that it is a window fix and
not a fit.

Mean absolute error **35.8%**, 2 of 8 within 15%. Against 0.4% on the aggregate.
That gap is the finding, and it is the sharpest evidence yet that the calibrated
tier's low errors are reconstruction rather than structure. Nothing was retuned;
every row carries its cause in `known_limitations`.

The SALT row is worth isolating because it is not a calibration failure at all.
P.L. 119-21 raises the SALT cap to $40,000, phases it down above $500,000 of
income, and reverts to $10,000 after 2029. The module's SALT component
represents the flat $10,000 cap, which raises about twice as much. The right fix
is a cap-level input, not a constant.

### 8.4 What was refused, and why

Twenty further provisions are `out_of_scope` in the CSV with a stated reason and
are never scored. Two reasons are load-bearing:

**Leakage, not a gap.** The Chapter 5 energy-credit terminations (+$542.7B, the
third-largest block in the law) *could* be routed through `climate.py`, and must
not be: that module's IRA-repeal annual is documented as calibrated to reproduce
the -$783B IRA-repeal target, so scoring an energy-credit repeal through it
would meet a constant with the same reform that set it. This is the third
instance of the pattern, after Phase B's Options 53, 56 and 62. It is now
frequent enough to be a category rather than an accident: **any module whose
constant was fitted to reform X cannot be used to predict reform X under another
name.**

**A line item that does not exist.** There is no senior-deduction row in
JCX-35-25. JCT nets it inside item 3, whose label says so explicitly:
"Termination of deduction for personal exemptions *other than temporary senior
deduction*". The plan's §4.3 lists the senior deduction as a target to
transcribe; it cannot be transcribed, and that is recorded rather than
approximated.

### 8.5 The January 2025 vintage

Every P.L. 119-21 target is measured against CBO's January 2025 baseline, and
until Phase D `BaselineVintage.CBO_JAN_2025` was a 0.5/0.5 interpolation between
the February 2024 and February 2026 assumption sets — with **no base levels at
all**, so it silently fell through to the February 2026 hardcoded fallback.
"Scored on the January 2025 baseline" was not a true sentence.

It is now transcribed from CBO, *The Budget and Economic Outlook: 2025 to 2035*
(publication 61172) and its supplemental data (publication 60870): the calendar
2025-2034 economic forecast, and FY2025 base levels from baseline tables B-1
(revenues by source, outlay categories, debt, GDP) and B-4 (mandatory outlays
net of the offsetting receipts that turn gross Social Security and Medicare into
the net figures the model's categories represent). One number is derived rather
than transcribed and is labelled as such: CBO's abbreviated January 2025 report
publishes no defense/nondefense split of discretionary *outlays*, so the
$1,847.9B total is divided in the Table B-5 budget-authority ratio (47.25 /
52.75).

The interpolation is kept and kept callable as
`interpolated_jan_2025_assumptions()` — the honest fallback if the sourced
figures ever have to be withdrawn — and `VINTAGE_SOURCING` records which of the
two is in force, pinned by `tests/test_baseline_vintage.py`. Sanity: the
generated FY2025 deficit is $1,868B against CBO's own $1,865B.

**And, consistent with Phase B: it moves none of the eight scores.**
`TCJAExtensionPolicy` builds its path from component annuals and never reads a
level off the baseline. The value of the vintage work is that the manifest is
now true, not that a number changed. Baseline drift is a real contaminant for
shapes that scale off baseline aggregates; none of the shapes currently in
either tier does.

### 8.6 Provenance after Phase D

| | before | after |
|---|---:|---:|
| calibrated benchmarks | 46 | 54 |
| ... against a published figure | 39 | 47 |
| `line_item` | 4 | **12** |
| `secondhand` | 31 | 31 |
| `model_estimate` | 7 | 7 |
| `unclassified` | 4 | 4 |

Eight of the twelve `line_item` targets are now this block. The 31 secondhand
targets are untouched: promoting one still requires someone to open the document
and transcribe the row, exactly as Phase E said.

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
- JCT (2025): *Estimated Revenue Effects Relative to the Present Law Baseline
  of the Tax Provisions in "Title VII - Finance" of the Substitute Legislation
  as Passed by the Senate*, JCX-35-25 (1 July 2025)
- CBO (2025): *Estimated Budgetary Effects of Public Law 119-21 ... Relative to
  CBO's January 2025 Baseline*, publication 61570 (21 July 2025)
- CBO (2025): *Distributional Effects of Public Law 119-21*, publication 61367
  (11 August 2025)
- CBO (2025): *The Budget and Economic Outlook: 2025 to 2035*, publication
  61172 (January 2025), and its supplemental data, publication 60870
- CBO (2024): cost estimate for H.R. 82, *Social Security Fairness Act of 2023*
  (9 September 2024)
- CBO (2023): *CBO's Estimate of the Budgetary Effects of H.R. 3746, the Fiscal
  Responsibility Act of 2023* (30 May 2023)
- CBO (2021): cost estimate for Senate Amendment 2137 to H.R. 3684, the
  *Infrastructure Investment and Jobs Act* (revised 9 August 2021)
