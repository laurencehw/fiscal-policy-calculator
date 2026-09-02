# Lane W4-3a — Employer-health exclusion: a year-indexed excess share

*Pre-registered 2026-09-02 against `main` @ `5deef17`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §6.2 item 8 — "a year-indexed excess
share in `tax_expenditures_core.py`", the mechanism L6 finding 3 named and did
not build, under §4's rules. The lane touches the expenditure module, the
distribution helpers it reads, and the one engine line that decides which year
a tax-expenditure annual is evaluated in. It adds **no Tier-1 row** and edits
no target, no manifest and no threshold.

## 1. Starting numbers

All from the branch point, `python scripts/cold_holdout.py` and `python
scripts/run_loo.py --donor-matrix` on `5deef17`.

### The case this lane is about

`cbo_opt56_employer_health_income_only` — CBO, *Options for Reducing the
Deficit: 2025 to 2034* (pub. 60557), Option 56, third alternative, report p. 66
(PDF p. 72), row *"Decrease (−) in the deficit"*.

| | Official | Model | Err |
|---|--:|--:|--:|
| **FY2025-2034 total** | **−697.0** | **−529.9** | **24.0%** |

Year by year, against the option's own annual rows in
`fiscal_model/data_files/validation/cbo_options_2025_2034_alternatives.csv`
(rows `56.8` revenue and `56.9` deficit; the model's revenue leg is its static
effect and its deficit leg is static plus the module's 0.2 behavioural term):

| year | CBO revenue (56.8) | model static | CBO deficit (56.9) | model deficit |
|---|--:|--:|--:|--:|
| 2025-2027 | 0 | 0.0 | 0 | 0.0 |
| 2028 | 59 | 55.9 | −59 | −67.1 |
| 2029 | 86 | 58.1 | −85 | −69.8 |
| 2030 | 94 | 60.5 | −92 | −72.6 |
| 2031 | 103 | 62.9 | −101 | −75.5 |
| 2032 | 112 | 65.4 | −111 | −78.5 |
| 2033 | 123 | 68.0 | −120 | −81.6 |
| 2034 | 132 | 70.7 | −129 | −84.9 |
| **total** | **709** | **441.6** | **−697** | **−529.9** |

The level is right and the shape is not, exactly as
`validation/core.py`'s `_KNOWN_LIMITATIONS_BY_POLICY_ID` entry says. CBO's
revenue grows **14.4%/yr** across the window; the model's grows **4.0%/yr**,
which is the expenditure record's own growth rate and nothing else. The excess
share is evaluated **once**, at `start_year`, and never again.

### Leave-one-out (the rows this lane must not regress)

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| Expenditures | `cap_employer_health` | −450.0 | −449.5 | −30.5 | **+93.2%** |
| Expenditures | `eliminate_mortgage` | −300.0 | −330.4 | −315.3 | **−5.1%** |
| Expenditures | `repeal_salt_cap` | 1,100.0 | 1,155.6 | 777.0 | **−29.4%** |
| Expenditures | `eliminate_salt` | −1,200.0 | −1,260.3 | −1,077.9 | **+10.2%** |
| Expenditures | `cap_charitable` | −200.0 | −200.6 | −173.8 | **+13.1%** |
| Expenditures | `eliminate_step_up` | −500.0 | −523.5 | — | not cross-validatable |

Expenditure module mean **30.2%** (n=5 derivable, 1 excluded by the leakage
guard). **Suite aggregate: 18 derivable cases, 28.4% mean / 16.5% median, 9/18
within 15%, 4 not cross-validatable.**

### Battery aggregates

- **Tier 1 (out-of-sample): 26 cases, 31.0% mean, 15.1% median, 13/26 within
  15%, 19/26 within 25%.**
- Calibrated reference models: 28 policies, 2.0% mean, 28/28 within 15%.
- Uncalibrated module reconstructions: 26 policies, 61.8% mean, 5/26 within 15%.

## 2. What the lane changes

One mechanism, in three files.

1. **The excess share becomes a function of the year being scored.**
   `TaxExpenditurePolicy._share_of_benefit_above_cap` takes a year;
   `estimate_static_revenue_effect` takes an optional `year` and defaults it to
   `start_year`, so every existing caller is unchanged to the digit. The
   scoring engine, which already loops over years and already knows which one
   it is in, passes it.

2. **A dollar limit that a published design indexes is declared as indexed.**
   The `employer_health` record gets a `cap_indexation` block carrying CBO's
   own sentence, in the same style as SALT's `limitation`. The rule is
   general and takes no per-case input: **the cap dollars are denominated in
   the policy's own `start_year`** and are grown from there by the repository's
   baseline price path. Option 56's caps are CBO's stated 2028 limits and
   `effective_start_year=2028`, both frozen by `OPTION_56_SHAPE_RULE`, so the
   rule reads that shape rather than adding to it.

3. **The two growth series are named and separated.** Premiums grow at the
   expenditure record's own `growth_rate` (0.04 — the same employer-premium
   growth `ptc.py` carries as `healthcare_growth_rate = 0.04`); the limit grows
   at the baseline's price path (`fiscal_model/baseline.py`,
   `vintage_assumptions(...)["inflation"]`, 2.3/2.2/2.1/2.0…%). Their ratio is
   the entire mechanism: a limit indexed to prices while premiums grow two
   points faster puts a widening slice of every premium above it.

### The design, in CBO's words

The indexation is **not** a shape choice this lane is making. CBO states it in
the option text (pub. 60557, report p. 66; PDF p. 72):

> "To set the tax exclusion limits in 2028 and later years, those 2026 premium
> percentiles would be indexed for inflation using the chained consumer price
> index for all urban consumers (chained CPI-U), one measure of overall price
> inflation."

Implementing a design element the source states is not a change to
`OPTION_56_SHAPE_RULE`, which fixes *which dollars* and *which start year*, not
whether the statute the option writes is indexed.

### Data, and one substitution stated rather than buried

| Quantity | Series used | Where it comes from |
|---|---|---|
| Premium growth | 4.0%/yr | `JCT_TAX_EXPENDITURES["employer_health"]["growth_rate"]`, the same rate `fiscal_model/ptc.py` carries as `healthcare_growth_rate` |
| Limit indexation | the baseline's `inflation` path (2.3, 2.2, 2.1, then 2.0%) | `fiscal_model/baseline.py`, `vintage_assumptions(BaselineVintage.CBO_FEB_2024)` — CBO's February 2024 baseline, which `CBO_OPTIONS_REVENUE_BASELINE` records as the volume's own |
| Premium distribution | lognormal by tier, σ from CBO's own percentile pair | `fiscal_model/data_files/tax_expenditures/employer_health_premium_distribution.csv` (unchanged) |

**The substitution:** the repository carries no chained-CPI-U series. Neither
`baseline.py` nor `data/fred_data.py` has one — the baseline's price variable
is the PCE price index and FRED's wrapper fetches only GDP, unemployment and
the 10-year yield. The baseline's own inflation path is used in its place. In
CBO's February 2024 projections the chained CPI-U and the PCE price index both
sit near 2.0% over 2028-2034 (the CPI-U runs about 0.3pp above the chained
CPI-U, and about 0.3pp above PCE), so the substitution is worth a few basis
points a year on the limit. It is a substitution nonetheless, and it is the
one input in this lane that is not the series the source names.

## 3. The prediction

**Headline: the mechanism closes about half the residual and stops well short
of the target, and the reason is a second named channel, not a parameter.**

- **Option 56 goes from 24.0% to about 13% low** — approximately **−$606B**
  against −$697.0B. This is the arithmetic of the mechanism, computed with the
  shipped `PremiumDistribution` and the shipped baseline inflation path before
  any code was written, in the same status as L6 finding 3's hand table. **No
  parameter was chosen by looking at −$697B.**
- **It will not reach L6's −12.8% by the route L6 described.** That hand table
  held the limit at its 2028 nominal dollars for the whole window, which is not
  CBO's design; it also grew the $250B expenditure from 2026 rather than from
  the policy's start year. Implementing what CBO actually writes — an
  **indexed** limit — takes back roughly a third of the widening the unindexed
  arithmetic produced. Landing near the same number by a different route is a
  coincidence, and this lane records it as one.
- **The pre-registered anti-fitting disclosure.** The residual is monotone in
  the premium-growth assumption: at 5%/yr instead of the record's 4%/yr the
  same mechanism scores **−$693B, 0.6%**. I am **not** taking 5%. The 4% is the
  repository's own employer-premium growth, carried in two independent places,
  and switching to a rate that happens to hit the target is precisely the knob
  §4 forbids. If a future lane changes it, it must change it for the whole
  module and against a health-spending source, not against this row.
- **LOO expenditure rows do not move at all**, and that is a property of the
  harness rather than a claim. `validation/loo.py`'s `derive_expenditure_annual`
  takes one annual — `estimate_static_revenue_effect(0.0)`, evaluated at
  `start_year` — and `_score_with_annual` then grows that constant. At
  `year == start_year` the index factor is exactly 1.0, so all five derivable
  rows and the by-construction column are unchanged to the digit. Expenditure
  module mean stays **30.2%**; suite stays **28.4% / 16.5% / 9 of 18**.
- **No shipped preset moves.** `EXPENDITURE_APP_MODE` is `reported`, and a
  reported annual never reaches the share rule.
- **Tier 1 aggregate**: one row of 26 improving by ~11pp moves the mean by
  about 0.4pp, to roughly **30.6%**; the median and both within-N counts are
  unchanged (24% and 13% are both outside 15% and inside 25%).

### Two related pieces, and what I expect of them

**(a) A payroll base for the exclusion — I expect to write down what is
missing, not to build it.** CBO's alternatives 1 and 2 limit the income *and*
payroll exclusion and their footnote a says the estimates "include the effects
on Social Security payroll tax receipts". A payroll leg therefore needs the
**joint** distribution of premiums and earnings, because the OASDI leg applies
only below the taxable maximum. The repository has the two marginals and not
the joint: `employer_health_premium_distribution.csv` has premiums with no
earnings dimension (its MEPS-IC weights are coverage tiers), and
`microsim/tax_microdata_2024.csv` has wages with no premium column. The
prediction is that this piece ends as a written gap.

**(b) A plan-switching response — I expect CBO to state the direction and not a
magnitude.** The option text names the channel ("some workers would enroll in
lower-premium plans, which would increase their taxable income") without any
elasticity or share. Inventing one would be a per-benchmark constant. The
prediction is that this piece also ends as a written finding.

## 4. What this lane will not do

- Not promote 56.3 or 56.6, not add or edit any row in `preregistered.py`,
  `benchmark_sources.py`, `target_revisions.py` or `cbo_scores.py`.
- Not touch `scripts/cold_holdout.py`, `scripts/run_loo.py`, `loo.py`'s leakage
  guard, `tests/test_preregistration.py` or any CI threshold.
- Not change `OPTION_56_SHAPE_RULE`'s inputs: the caps stay CBO's stated 2028
  dollars and the start year stays 2028.
- Not touch the shared docs (`README.md`, `CLAUDE.md`, `docs/VALIDATION*.md`,
  `docs/METHODOLOGY.md`, `planning/MODELING_IMPROVEMENT.md`,
  `planning/NEXT_STEPS.md`, `CHANGELOG.md`). `docs/VALIDATION.md` and §6.2 item
  8 will both be stale after this lane and a docs pass owns them.
- Not change the module's behavioural elasticity or the engine's offset sign.

Anything that moves outside this list is a finding, and gets written into §5.

## 5. Outturn

*To be appended after the code, in the last commit of the lane.*
