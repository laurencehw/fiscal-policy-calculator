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

*Appended 2026-09-02, after the code. Numbers from `python scripts/run_loo.py
--donor-matrix` and `python scripts/cold_holdout.py` on the finished branch.*

### Leave-one-out

| Case | Official | By-constr | LOO before | LOO after | Err before | Err after |
|---|--:|--:|--:|--:|--:|--:|
| `cap_employer_health` | -450.0 | -449.5 | -11.5 | **-30.5** | +97.4% | **+93.2%** |
| `eliminate_mortgage` | -300.0 | -330.4 | -315.3 | -315.3 | -5.1% | **-5.1%** |
| `repeal_salt_cap` | 1,100.0 | 1,155.6 | 1,143.5 | 1,143.5 | +4.0% | **+4.0%** |
| `eliminate_salt` | -1,200.0 | -1,260.3 | -300.9 | **-1,444.4** | +74.9% | **excluded — see finding 1** |
| `cap_charitable` | -200.0 | -200.6 | -168.5 | **-173.8** | +15.7% | **+13.1%** |
| `eliminate_step_up` | -500.0 | -523.5 | — | — | not x-val | not x-val |

Expenditure module mean 39.4% → **28.8%**, now over **4** derivable cases
rather than 5, with 2 excluded rather than 1.

**Two suite aggregates, and the difference between them matters.**

| | n | mean | median | within 15% |
|---|--:|--:|--:|--:|
| Before | 18 | 58.7% | 32.5% | 6 |
| **After, as the script reports it** | **17** | **57.3%** | **28.0%** | **7** |
| After, like-for-like (counting `eliminate_salt` at its derived +20.4%) | 18 | **55.3%** | **25.3%** | **7** |

The 57.3% is what `run_loo.py` prints. It is **1.4pp better than the 58.7% it
replaces partly because a 74.9% case left the denominator**, and saying so is
the point of printing both rows: the like-for-like number, 55.3%, is the one
that measures the model change. The reported figure improving *because a case
was reclassified as not cross-validatable* is a worse outcome for the
repository than the like-for-like improvement, not a better one — the module
now cross-validates on four benchmarks where it used to claim five.

### Against the pre-registration

| Row | Predicted | Actual | |
|---|--:|--:|---|
| LOO `cap_employer_health` | +91% to +95% | **+93.2%** | in band |
| LOO `eliminate_salt` | +18% to +23% | **+20.4%**, then excluded | in band, then a finding |
| LOO `cap_charitable` | +11% to +15% | **+13.1%** | in band |
| LOO `eliminate_mortgage` | unchanged | **-5.1%** | as registered |
| LOO `repeal_salt_cap` | unchanged | **+4.0%** | as registered |
| Expenditure module mean | 26% to 29% | **28.8%** | in band |
| LOO suite mean (like-for-like) | 54% to 57% | **55.3%** | in band, exactly the point prediction |
| LOO suite median (like-for-like) | ~25% | **25.3%** | exact |
| LOO within 15% (like-for-like) | 7/18 | **7/18** | exact |
| Derived employer health | $2.12B/yr | **$2.116B/yr** | exact |
| Derived SALT elimination | $120.0B/yr | **$120.0B/yr** | exact |
| Derived charitable | $10.83B/yr | **$10.831B/yr** | exact |
| Tier 1 | 34.4% / 12 / 16, unmoved | **34.4% / 12 / 16** | as registered |
| Fitted tier (33) | 2.8%, unmoved | **2.8%, 32/33** | as registered |
| Unfitted reconstructions (21) | 76.7%, unmoved | **76.7%** | as registered |
| Other LOO modules | unmoved | **unmoved** | as registered |
| App presets | unmoved | **unmoved** | as registered |
| Suite case count | 18 derivable | **17 derivable** | **missed — finding 1** |

Every point prediction landed. The one thing the pre-registration did not
foresee is the thing worth writing down.

### Reported vs derived, per benchmark

| Benchmark | Carried target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `cap_employer_health` | -$450B | -$449.5B | +0.1% | **-$30.5B** | +93.2% |
| `eliminate_mortgage` | -$300B | -$330.4B | -10.1% | **-$315.3B** | -5.1% |
| `repeal_salt_cap` | $1,100B | $1,155.6B | +5.1% | **$1,143.5B** | +4.0% |
| `eliminate_salt` | -$1,200B | -$1,260.3B | -5.0% | **-$1,444.4B** | -20.4% |
| `cap_charitable` | -$200B | -$200.6B | -0.3% | **-$173.8B** | +13.1% |
| `eliminate_step_up` | -$500B | -$523.5B | -4.7% | **-$600.3B** | -20.1% |

Mean 4.2% reported against 26.0% derived. **The app default stays `reported`**
under Decision 1's own rule, so nothing a user sees changes — every shipped
preset builds through the same factories with the same fitted annuals, and the
full suite (2,966 tests) passes with every regression band untouched.

Derived wins two of six. Read the other four with the caution the AMT lane
established: five of the six targets are reproduced by a constant fitted to
them, so their sub-1% errors measure bookkeeping. Against the **published**
line item — CBO pub. 60557 Option 49, "Eliminate state and local tax
deductions", $1,621.0B over FY2025-2034, recorded in
`validation/benchmark_sources.py` as `line_item_differs`:

| `eliminate_salt` | vs -$1,621.0B |
|---|--:|
| Reported (fitted -$1,260.3B) | **-22.3%** |
| Derived, before this lane (-$300.9B) | **-81.4%** |
| Derived, after (-$1,444.4B) | **-10.9%** |

That is the lane's result on this row: the structural path is twice as close
to the document as the fitted constant, while scoring worse against the
carried target — the same shape L5 found, and only possible because the
carried target and the document disagree by 35%.

### Findings

**1 — The leakage guard fired on `eliminate_salt`, and it is right to.**
`annual_cost_no_cap = 120.0` is **exactly** the carried target divided by ten.
The moment the `eliminate` rule started reading it, `loo.py`'s
`LEAKAGE_TOLERANCE` reclassified the case as not cross-validatable: "the base
constant is the answer key restated". That guard was not touched by this lane;
it caught a constant this lane made load-bearing.

The guard cannot distinguish "the target restated" from "a round number that
happens to equal the target over ten", and both readings are live here — the
module's *fitted* annual for the same benchmark is 104.7, not 120.0, so
whoever set 120.0 was not simply copying the fitted path. What is not in
doubt is that the constant is unsourced and now matters. This lane hands the
provenance lane two things it did not have:

- an independent check of the *method*: pricing SOI's **limited** SALT
  deduction at the statutory schedule gives **$25.0B/yr** against the base
  table's own `annual_cost = 25.0` — two numbers with no common ancestor
  agreeing to a tenth of a percent;
- the same computation on the **unlimited** deduction gives **$89.6B/yr**,
  **25% below** the record's $120.0B. So either the record's no-cap level
  embeds a 34% itemisation response that nothing documents, or it is the
  target. `tests/test_tax_expenditure_units.py` pins both figures so a data
  refresh cannot close the gap silently.

**`repeal_salt_cap`'s +4.0% should be read as leaked too.** It is
`-(120.0 - 25.0)`, so it is built from the same constant; the guard does not
catch it only because its own target is $1,100B rather than $1,200B. This
lane leaves that row scoring exactly what it scored before and says so here
rather than moving it, because the one alternative available without a new
source makes the module worse. Deriving *both* SALT levels from SOI --
$89.6B uncapped, $25.0B capped -- keeps `eliminate_salt` derivable, at 10.2%,
but takes `repeal_salt_cap` from +4.0% to **-29.4%**; over the same five cases
that is a module mean of **30.2%** against the shipped version's **27.2%**. It
swaps a leaked constant for a bottom-up estimate that disagrees with the
published record by 25%, and buys nothing.

**2 — Correcting the employer-health unit moves the row 4pp, and the
benchmark is why.** This was pre-registered (§3) and it held: +97.4% →
+93.2%. The new mechanism also *prices* the mismatch that
`benchmark_sources.py` describes in words. A $25,000 cap scores **-$520B**
and a $50,000 cap **-$30.5B**, so the carried -$450B target corresponds to a
cap of about **$26,400** — within 8% of CBO's own 50th-percentile family limit
of $24,400, which this model scores at -$552B. The benchmark looks like a real
published design carrying the wrong cap amount, and no correct model of a
$50,000 cap will reach it.

**3 — The mechanism reproduces CBO Option 56 far better than the
pre-registration guessed, and the residual is one named channel.** §3 above
predicted the module would come in about 54% low against Option 56's
income-tax-only alternative, and recommended waiting. That estimate was wrong,
because it compared a 2026-dollar annual against a seven-year *average*.
Scored properly — the option takes effect in January 2028, so the caps and the
premiums are both 2028 quantities:

| year | CBO alt 3 | module, flat growth | module, share recomputed each year |
|---|--:|--:|--:|
| 2028 | 59 | **60.5** | **60.5** |
| 2029 | 86 | 62.9 | 68.6 |
| 2030 | 94 | 65.4 | 77.4 |
| 2031 | 103 | 68.0 | 86.9 |
| 2032 | 112 | 70.7 | 97.1 |
| 2033 | 123 | 73.6 | 108.0 |
| 2034 | 132 | 76.5 | 119.6 |
| **2028-2034** | **709** | **477.7 (-32.6%)** | **618.0 (-12.8%)** |

The first year is **+2.5%**. The whole residual is the shape: CBO's revenue
grows 14%/yr because the limit is indexed to the chained CPI-U while premiums
grow faster, so a widening slice of every premium sits above it. The module's
distribution already produces that widening — its excess share goes 0.185 in
2026 to 0.224 in 2028 — but `estimate_static_revenue_effect` evaluates it
**once, at `start_year`**, and the scoring engine then applies a flat 4%. The
right-hand column recomputes the share year by year using the shipped
`PremiumDistribution` and is hand arithmetic outside the model, not a scored
path.

So: **a year-indexed excess share is the next real structure this module is
missing**, and it is a small change with a clear target. Until it lands the
recommendation on promotion is unchanged in substance but for a different
reason — not "the level is wrong" but "the growth path is". On the strength of
+2.5% in the option's first year, **Option 56 is now a credible Tier 1
candidate**, and the pre-registration lane should promote all three
alternatives together once the path is indexed. This lane does not promote it.

**4 — The charitable rate ceiling was right by coincidence.** The old rule
returned `baseline_cost * 0.15` for any `cap_rate`, a flat share with no
distribution behind it and no relation to the 28% the policy actually sets.
Against the charitable-deduction distribution the correct share is **15.47%**,
so the constant was within half a point of an answer it had no way of knowing.
The row improves by only 2.6pp; what changed is that the number now moves when
the ceiling does.

**5 — `annual_cost_no_limit = 100.0` on the mortgage record names no
statute.** It was dead before this lane and is deliberately still dead. The
natural candidate for what it is the "no limit" level of — TCJA's $750,000
acquisition-debt cap, IRC 163(h)(3)(F) — is worth single-digit billions a
year, not $75B; the figure looks like a pre-TCJA level reflecting the smaller
standard deduction. Giving it a `limitation` block would make it live
automatically and move `eliminate_mortgage` from -5.1% to about **+244%** on
an unsourced constant. It goes to the provenance lane. The declaration
mechanism is built and waiting for it.

**6 — The two SALT benchmarks are scored against contradictory baselines, and
the contradiction is in the sources.** `eliminate` is now year-indexed: the
$10,000 cap expires after 2025, so a 2026 window prices the unlimited
deduction, which is exactly the baseline CBO's Option 49 uses ("Beginning in
2026, deductions for state and local taxes will not be limited"). `expand` is
not year-indexed: repealing a limitation is worth the limitation's own value,
and the $1,100B figure presupposes the cap binds. Under a single baseline one
of the two must be $0. Both rules are written the way their own sources score
them, the asymmetry is commented at the rule, and reconciling it needs a
baseline-vintage concept this module does not have.

### What the lane did not do

- Did not touch any target, `preregistered.py`, `benchmark_sources.py`,
  `target_revisions.py`, the yardstick scripts, `loo.py`'s leakage guard or
  its tolerance, `tests/test_preregistration.py`, or any CI threshold. The
  one `loo.py` change is the held-out mode plus a widened exclusion-reason
  string, both of which the lane brief permits.
- Did not add a per-benchmark constant. No value in `JCT_TAX_EXPENDITURES`
  changed. The module gained two transcribed data files, one statutory rate
  schedule, and rules that read them.
- Did not change any shipped preset. The app default is `reported`; the
  factories carry the same fitted annuals; 2,966 tests pass.
- Did not model the within-AGI-class distribution of a deduction. A per-return
  dollar cap uses each class's *average* claimed deduction, which discards
  within-class dispersion and biases a cap set among the class averages
  downward. It is exact at the two ends and no benchmark depends on it.
- Did not build the year-indexed excess share (finding 3), the employer-health
  plan-switching channel, or a payroll base. Those are what stand between the
  module and CBO Option 56.
- Did not source `annual_cost_no_cap` or `annual_cost_no_limit`. Both are
  provenance work, and finding 1 says what the first one has to beat.
