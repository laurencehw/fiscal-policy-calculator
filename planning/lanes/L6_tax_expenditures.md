# Lane L6 — Tax expenditures: bases with the right units

*Pre-registered 2026-09-02 against `main` @ `9a1e8bc`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §3 L6, under §4's rules and owner
Decision 1 (reported vs derived mode, accepted 2026-09-01, implemented
module-locally by L5 in `fiscal_model/amt.py`).

## 1. Starting numbers

All from the branch point, `python scripts/run_loo.py --donor-matrix` and
`python scripts/cold_holdout.py` on `9a1e8bc`.

### Leave-one-out (the lane's yardstick)

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| Expenditures | `cap_employer_health` | -450.0 | -449.5 | -11.5 | **+97.4%** |
| Expenditures | `eliminate_mortgage` | -300.0 | -330.4 | -315.3 | **-5.1%** |
| Expenditures | `repeal_salt_cap` | 1,100.0 | 1,155.6 | 1,143.5 | **+4.0%** |
| Expenditures | `eliminate_salt` | -1,200.0 | -1,260.3 | -300.9 | **+74.9%** |
| Expenditures | `cap_charitable` | -200.0 | -200.6 | -168.5 | **+15.7%** |
| Expenditures | `eliminate_step_up` | -500.0 | -523.5 | — | not cross-validatable |

Expenditure module mean **39.4%** (n=5 derivable, 1 excluded by the leakage
guard: the derived annual $50.0B equals the published target / 10).

**Suite aggregate: 58.7% mean / 32.5% median over 18 derivable cases, 6/18
within 15%, 4 not cross-validatable.**

### Fitted (by-construction) errors for the same six benchmarks

| Benchmark | Target | Fitted model | Fitted err |
|---|--:|--:|--:|
| `cap_employer_health` | -$450B | -$449.5B | **0.1%** |
| `eliminate_mortgage` | -$300B | -$330.4B | **10.1%** |
| `repeal_salt_cap` | $1,100B | $1,155.6B | **5.1%** |
| `eliminate_salt` | -$1,200B | -$1,260.3B | **5.0%** |
| `cap_charitable` | -$200B | -$200.6B | **0.3%** |
| `eliminate_step_up` | -$500B | -$523.5B | **4.7%** |

### Battery aggregates

- Tier 1 (out-of-sample): **25 cases, 34.4% mean, 12/25 within 15%, 16/25 within 25%.**
- Calibrated fitted tier: **33 policies, 2.8% mean, 32/33 within 15%.**
- Unfitted module reconstructions: **21 policies, 76.7% mean, 4/21 within 15%.**

## 2. What the lane changes

Two defects named in §3 L6, both in `fiscal_model/tax_expenditures_core.py`.

1. **`eliminate_salt` derives against the post-cap expenditure.**
   `annual_cost = 25.0` is the SALT expenditure *with* the $10,000 cap in
   force; `annual_cost_no_cap = 120.0` sits in the same record and is read only
   by the repeal-cap branch. The `eliminate` rule takes `annual_cost`
   unconditionally.
2. **`cap_employer_health` compares two different quantities.** `cap_amount` is
   a $50,000 cap on excludable **premiums**; the share-affected rule compares it
   against `avg_benefit = 1_600`, the average **tax benefit**, and concludes
   0.32% of the base is affected.

The fix is not two constants. Three changes, applied uniformly:

- **Units are declared.** A new `CapUnit` says what a cap parameter measures:
  `BASE_DOLLARS` (dollars of the deducted or excluded quantity), `BENEFIT_RATE`
  (a ceiling on the rate at which the item is valued), `BENEFIT_DOLLARS` (the
  old, almost always wrong, comparison — retained so it must be asked for by
  name). Dollar caps default to `BASE_DOLLARS`; `cap_rate` implies
  `BENEFIT_RATE`.
- **Each expenditure gets a distribution**, transcribed under
  `fiscal_model/data_files/tax_expenditures/` with provenance headers, so a cap
  is applied to the quantity it caps: deduction amounts by AGI class (IRS SOI
  Table 2.1, TY2023) for SALT / mortgage / charitable, and a premium
  distribution for the employer health exclusion.
- **A statutory limitation is a declared object, not a spare field.** The SALT
  record carries the $10,000 cap as a `limitation` with its statute and its
  expiry year, and both the `eliminate` and the `expand` rules read the level
  in force over the policy's own window rather than hard-coding a level or an
  expenditure type.

Plus owner Decision 1: `TaxExpenditurePolicy.mode` of `reported` (the fitted
annual) or `derived` (the structural path). Derived becomes the default in the
held-out validation path; the app's presets stay on `reported` unless derived
beats fitted.

### Data and provenance

| Source | What it supplies | Reachable |
|---|---|---|
| IRS SOI Table 2.1, TY2023 (`irs.gov/pub/irs-soi/23in21id.xls`) | Itemized deductions by size of AGI: returns and amounts for total SALT, *limited* SALT, home mortgage interest, charitable contributions | yes |
| IRC §1 as adjusted for 2025 (Rev. Proc. 2024-40) | The married-joint ordinary rate schedule used to price a deduction at the margin | n/a (statute) |
| CBO, *Options for Reducing the Deficit: 2025 to 2034* (pub. 60557), Option 56 | The employer-premium distribution's **shape and level**: the 50th-percentile cap is $10,000 individual / $24,400 family and the 75th is $12,700 / $31,300, in 2028 dollars | cached PDF (cbo.gov 403s) |
| CBO pub. 60557, Option 49 | "Beginning in 2026, deductions for state and local taxes will not be limited" — the statutory fact the SALT `limitation` encodes | same |
| KFF, *Employer Health Benefits Survey 2024*, Section 1 | Mean premiums ($8,951 single / $25,572 family) and the published distribution points (7% of covered workers at a firm averaging ≥$12,500 single; 10% at ≥$33,000 family) | yes |
| MEPS-IC Statistical Brief #207 | Enrolment split across coverage tiers: 48.9% single / 18.0% employee-plus-one / 33.2% family | yes (2006 vintage; see §4) |

JCT's JCX-48-24 **distribution tables** are what §3 L6 names first, and
`jct.gov` returns HTTP 403 to this environment on every URL tried, exactly as
`cbo.gov` does. The repository's curated snapshot
(`assistant/knowledge/jct_tax_expenditures.md`) carries only totals. IRS SOI
Table 2.1 is the substitute: it is the *microdata source* JCT's own
distribution tables are built from, it is published by tax year with returns
and amounts by AGI class, and it distinguishes total from limited SALT — which
JCT's summary tables do not.

## 3. The prediction

**Headline: the `eliminate_salt` half of this lane works and lands near the
plan's target; the `cap_employer_health` half does not and cannot, and the
reason is in the benchmark, not the model. I am pre-registering the miss.**

§3 L6 asks for `cap_employer_health` +97.4% → **<25%**. It will finish at about
**+93%**. Once a $50,000 cap is compared with a premium distribution instead of
an average tax benefit, the answer is that a $50,000 cap is far above the entire
distribution of employer premiums and raises almost nothing. CBO's own Option 56
puts the 75th percentile of family premiums at **$31,300** and of individual
premiums at **$12,700**; KFF puts 10% of covered workers at a firm averaging
$33,000 or more for family coverage. `benchmark_sources.py` already records this
qualitatively — "no CBO, JCT or Treasury score of a **$50,000 dollar cap** on the
employer health exclusion exists, because no published option is designed that
way" — and this lane turns it into a number: under the corrected mechanism the
carried -$450B target corresponds to a cap of roughly **$26,000**, not $50,000.
Correcting the unit therefore moves this row by about 4pp, not 72pp. The
alternative — reaching <25% — is available only by choosing a cap amount that
hits the target, which is the failure mode §4 exists to forbid.

### Rows I expect to move, and how far

Point predictions from the arithmetic, before the code exists. The scorer's
annual→10-year multiplier is empirical and unchanged by this lane: -14.407 for
employer health (4% growth, 0.2 elasticity), -12.037 for SALT, -12.610 for
mortgage, -16.049 for charitable.

| Row | Now | Predicted band | Point | Direction |
|---|--:|--:|--:|---|
| LOO `cap_employer_health` | +97.4% | **+91% to +95%** | +93.2% | better, but nowhere near the plan's <25% |
| LOO `eliminate_salt` | +74.9% | **+18% to +23%** | +20.4% | much better; narrowly misses the plan's <20% |
| LOO `cap_charitable` | +15.7% | **+11% to +15%** | +13.1% | better |
| LOO `eliminate_mortgage` | -5.1% | **unchanged** | -5.1% | no limitation record, so no change |
| LOO `repeal_salt_cap` | +4.0% | **unchanged** | +4.0% | same two levels, read through the limitation |
| LOO `eliminate_step_up` | not x-val | **unchanged** | — | still caught by the leakage guard |
| Expenditure module mean | 39.4% | **26% to 29%** | 27.2% | |
| LOO suite mean (n=18) | 58.7% | **54% to 57%** | 55.3% | |
| LOO suite median | 32.5% | **~25%** | 25.3% | |
| LOO within 15% | 6/18 | **7/18** | 7/18 | `cap_charitable` crosses |

Derived annuals behind those points: employer health **$2.12B/yr** (a 0.85%
excess share of the premium base at a $50,000 cap), SALT elimination
**$120.0B/yr** (the record's own no-cap level, now reachable by rule), charitable
**$10.83B/yr** (15.47% of the benefit sits above a 28% rate ceiling).

### The number that should improve

`eliminate_salt`'s carried target of -$1,200B is `line_item_differs`:
`benchmark_sources.py` records the published figure as **$1,621.0B** (CBO
pub. 60557, Option 49, "Eliminate state and local tax deductions", FY2025-2034).
Against the document rather than the carried target:

| `eliminate_salt` | vs -$1,200B carried | vs -$1,621.0B published |
|---|--:|--:|
| Reported (fitted -$1,260.3B) | +5.0% | **-22.3%** |
| Derived, today (-$300.9B) | +74.9% | **-81.4%** |
| Derived, after this lane (-$1,444.4B) | +20.4% | **-10.9%** |

The structural path lands **closer to the published line item than the fitted
constant does** (-10.9% against -22.3%), while scoring worse than the fitted
constant against the carried target. That is the lane's actual claim, and it is
the same shape as L5's.

### Rows I expect NOT to move

- **No Tier 1 row.** No pre-registered out-of-sample case constructs a
  `TaxExpenditurePolicy` (`grep` of `validation/preregistered.py` finds none).
  Tier 1 stays at 34.4% / 12 / 16 exactly.
- **No fitted-tier row.** Every benchmark in the by-construction scorecard is
  scored in `reported` mode, which returns the same
  `annual_revenue_change_billions` it returns today. 33 policies, 2.8%.
- **No unfitted-reconstruction row.** The 21 sectoral/line-item reconstructions
  are scored by other modules. 76.7%.
- **No app preset.** `preset_handler.py` builds the expenditure presets from the
  same factories, which keep their fitted annuals and the `reported` default.
  Every shipped number is byte-identical.
- **No other LOO module.** Payroll, Estate, AMT, Credits and Capital Gains share
  no code with `tax_expenditures_core.py`.

Anything that moves outside this list is a finding, and gets written into §4.

### On CBO Option 56 and a Tier 1 promotion

§3 L6 says this lane "unblocks CBO Option 56 for a future Tier 1 promotion".
**It makes Option 56 expressible; it does not yet make it worth promoting, and
this lane does not promote it.** A percentile cap is exactly what the new
`BASE_DOLLARS` path scores, so Option 56's three alternatives can be written as
`TaxExpenditurePolicy` objects for the first time. Scored that way, the
50th-percentile alternative gives an excess share of 18.5% of the premium base,
or about **$46B/yr** against the record's income-tax expenditure — against CBO's
income-tax-only alternative 3, which runs **$59B in 2028 rising to $132B in
2034**. The level is close in the first year and the growth path is not, because
the module has no plan-switching channel (CBO's dominant behavioural term) and
no payroll base. Promoting a row at that error would put a fourth 50%+ case into
Tier 1 for no gain in information. The recommendation to the pre-registration
lane is: **wait for the plan-switching channel**, then promote all three
alternatives together.

## 4. Outturn

*Appended in the lane's last commit.*
