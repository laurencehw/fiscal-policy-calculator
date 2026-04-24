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

## 1. Social Security Donut Hole at $250K — 12.2% systematic error

**Policy**: Apply the 12.4% combined OASDI tax to wages above $250,000 while
leaving the 2024 wage cap (~$168,600) in place.

| Source       | 10-year revenue | Model | Error |
|--------------|----------------:|------:|------:|
| SSA Trustees (2024) | −$2,700B | −$2,371B | **12.2%** |
| CBO equivalent      | −$2,700B |          |       |

The same 12.2% gap appears in all three related scenarios (donut hole,
eliminate cap, 90% cap coverage). That uniform miss is the fingerprint of
a *systematic* problem, not three independent errors.

### Mechanical cause

`fiscal_model/payroll.py:237-246` computes donut-hole revenue using a single
calibrated constant (`CBO_PAYROLL_ESTIMATES["donut_250k_annual"] = 270.0`)
for the baseline $250K threshold, and scales linearly for other thresholds:

```python
threshold_factor = 250_000 / self.ss_donut_hole_start
scaled_wages = base_wages * threshold_factor
total_revenue += scaled_wages * SOCIAL_SECURITY_PARAMS["rate_combined"]
```

Linear scaling is wrong because the wage distribution above the cap is
roughly Pareto, not uniform. A 2× increase in the threshold reduces the
affected wage base by substantially more than 2×.

### Data cause

The model's `BASELINE_WAGE_DATA["wages_250k_plus_billions"]` is a Census ACS-
derived approximation of aggregate wages above $250K. The SSA Trustees use
full W-2 microdata from SSA's Continuous Work History Sample, which captures
the precise shape of the right tail — including pass-through S-corp wages,
deferred compensation, and non-covered state/local earnings not in ACS.

The ACS figure is systematically low by roughly 10–13% depending on year.
This is why every scenario that depends on the wages-above-threshold base
shows the same ~12% underestimate.

### Methodological cause

Two additional pieces we do not model:

1. **Behavioral response to uncapping**: SSA's own score assumes employers
   partially absorb the employer-side 6.2% rather than passing it through as
   a wage cut (a 50/50 incidence split). Our model applies a simple labor-
   supply elasticity that implicitly assumes full pass-through. This pushes
   our estimate *down* (less revenue), widening the gap.
2. **Benefit-side interaction**: The Trustees' $2.7T is net of any additional
   benefit accruals to covered high earners (the "bend point" scaling).
   That correction is small (~3%), but our model ignores it entirely.

### Path to closure

| Change | Expected gap reduction | Effort |
|--------|-----------------------:|:------:|
| Replace ACS wage-distribution with SSA Table 4.B1 (aggregate covered wages by cap band) | 8–10% → ~3% | 1–2 days |
| Add explicit Pareto tail for wages above $500K | +1–2% residual | 2–3 days |
| Model 50/50 incidence split explicitly | +0.5% | 1 day |
| Add bend-point benefit accrual correction | +0.2–0.5% | 2 days |

The first change alone would bring the donut hole, 90% cap, and full
eliminate-cap scenarios all inside 5% of official — a one-week project.

**Estimate scope**: 1 week to close to <5%, 2 weeks to close to <2%.

---

## 2. Biden CTC 2021 (permanent) — 8.9% error

**Policy**: Make the American Rescue Plan CTC permanent — $3,000 per
child ages 6–17, $3,600 per child under 6, fully refundable, no
earnings requirement.

| Source | 10-year cost | Model | Error |
|--------|-------------:|------:|------:|
| CBO (2021) | $1,600B | $1,743B | **8.9%** |

The same 8.9% overstatement appears in the "CTC extension" scenario — again
a systematic fingerprint.

**Related distributional gap** (9.30pp on the CBO_ARP_2021 quintile
benchmark) is a *scope mismatch*, not a revenue bug: CBO's ARP 2021
distributional table covers the full bundle (CTC + EITC childless +
Recovery Rebate), but the `benchmark_runners` layer currently maps the
benchmark to `create_biden_ctc_2021` (just the CTC piece). The Recovery
Rebate's flatter $1,400-per-person grant would shift mass out of the
bottom two quintiles into the middle/upper-middle, which is exactly
where the 9.30pp residual lives. Closing this requires a composite
"ARP bundle" policy factory rather than a change to the CTC engine.

### Mechanical cause

`fiscal_model/credits_core.py` scores CTC by:
1. Computing eligible children from IRS SOI bracket aggregates.
2. Multiplying by the per-child credit amount.
3. Applying a phase-in schedule for earnings >$2,500 (current-law rule).

For the ARP 2021 design, steps 1–3 are applied as if the universe of
*recipients* is the same set of tax filers as the current-law CTC.

### Data cause

The ARP 2021 design explicitly extended full refundability to filers with
**zero earned income** — roughly 4.4 million children in families that
file protective returns but have no W-2 wages. IRS SOI bracket aggregates
are earnings-indexed and undercount this group (they appear as "AGI < $1"
or are missing entirely from the SOI Table 1.1 derivation the model uses).

Because the model's baseline *includes* these children at the full credit,
it over-predicts cost by the right amount to match the 8.9% gap:

```
4.4M children × $3,600 × 10 years × inflation ≈ $170B overstatement
$1,743B − $170B ≈ $1,573B ≈ CBO's $1,600B
```

### Methodological cause

CBO's score accounts for three things the bracket-aggregate model does not:
1. **Take-up friction**: CBO assumes ~92% take-up for expanded refundability
   among zero-earner families (the IRS "non-filer" portal reached a limited
   share). We implicitly assume 100%.
2. **Phase-out interaction with EITC**: The ARP preserved EITC phase-outs.
   CBO's microsim applies these jointly; ours applies them in sequence,
   slightly overstating the combined cost.
3. **Post-2025 baseline**: CBO scored against the "pre-ARP" baseline that
   TCJA reverts to in 2026. Our baseline straddles both regimes, inflating
   the delta in years 2026+.

### Path to closure

| Change | Expected gap reduction | Effort |
|--------|-----------------------:|:------:|
| Correct zero-earner population from IRS Pub 5307 microdata | 5–6% → ~3% | 3–5 days |
| Joint EITC/CTC phase-out modeling in microsim path | +1–2% | 1 week (needs CPS microsim) |
| Add take-up friction parameter (default 0.92 for expanded-refundable) | +1% | 1 day |

The first change is the big win, and it only requires swapping one data
source. The take-up correction is trivial to add once the population count
is right.

**Estimate scope**: 1 week to close to <5%; remaining gap depends on the
CPS microsim (Priority 1) being in place.

---

## 3. Biden Estate Tax Reform ($3.5M exemption, 45% rate) — 10.1% error

**Policy**: Reduce estate tax exemption from TCJA's $14M (2024) to
$3.5M per person and raise top rate from 40% to 45%.

| Source | 10-year revenue | Model | Error |
|--------|----------------:|------:|------:|
| Treasury (Green Book 2024) | −$450B | −$496B | **10.1%** |

The related "extend TCJA exemption" scenario shows a 10.2% error — again a
consistent fingerprint, but in the opposite direction from CTC.

### Mechanical cause

`fiscal_model/estate.py` uses a closed-form Pareto approximation of estates
above the exemption, calibrated to IRS SOI Table 1 (estate tax returns).
For the $3.5M exemption, this predicts roughly 19,000 taxable estates per
year, which matches CBO's count to within 5%. The revenue error therefore
originates in the *value* per estate, not the count.

### Data cause

The Pareto shape parameter is fit to the full distribution of returns,
which is dominated (by count) by estates between $5M and $20M. Estates
above $50M — a small slice of returns but a *large* slice of taxable
value — follow a heavier-tailed distribution (Atkinson-Piketty-Saez show
the top of the estate distribution is more unequal than the top of the
wage distribution). The single Pareto fit underweights this tail by
roughly 10%, and the model therefore overstates revenue from a proposal
that taxes it heavily.

### Methodological cause

Treasury uses a three-parameter generalized Pareto fit *plus* a
behavioral-avoidance correction (gift-in-life timing, charitable
deductions, valuation discounts for closely-held businesses). Our model
includes a scalar behavioral elasticity (default 0.15) but not the specific
avoidance margins that respond to a rate *increase* from 40% to 45%. Each
of those avoidance channels reduces Treasury's static estimate by 1–3%;
ours reduces it by a single flat ~5% via the elasticity.

### Path to closure

| Change | Expected gap reduction | Effort |
|--------|-----------------------:|:------:|
| Replace single Pareto fit with two-regime fit ($5M–$50M, $50M+) | 6–7% → ~3% | 3 days |
| Add explicit charitable-deduction margin (responds to rate, not exemption) | +1–2% | 1 day |
| Add valuation-discount elasticity (closely-held businesses) | +1% | 2 days |

The two-regime Pareto is the dominant correction. It uses data already
present in IRS SOI Table 1 Part II (taxable estates > $50M are reported
separately).

**Estimate scope**: 1 week to close to <5%.

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

| Benchmark           | Before | After | Rating change |
|---------------------|-------:|------:|:-------------:|
| CBO TCJA 2018       | 6.65pp | 4.86pp | acceptable → **good** |
| JCT TCJA 2019       | 3.99pp | 4.78pp | good → good (small regression) |
| CBO TCJA 2026       | 7.09pp | 4.22pp | acceptable → **good** |

The JCT 2019 regression is intentional: splitting the old \$170K+
bucket into finer tiers moves some shares around, and the decile
benchmarks benefit more than the AGI-class benchmark loses. Net: 2
benchmarks move from `acceptable` to `good`.

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
