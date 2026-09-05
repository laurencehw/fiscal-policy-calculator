# Lane W5-A — The payroll revenue identity at the margin

*Pre-registered 2026-09-05 against `main` @ `1d35f1b`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §2.1's row **"Payroll identity at the
margin"** — `cbo_opt61` at 54.1% and 55.5%, 109.6 of Tier 1's 468 error points
(23.4%), the largest single mechanism left in the tier. The plan's one-line
scoping was *"Medium. Needs employer-share incidence + income-tax offset, not
new data."* **Both halves of that sentence turn out to be wrong**, and §2 below
says so with the source in hand. §2 of the plan also carries the LOO row
**"Payroll — holds up. Do not touch"**; §1.4 of this doc is the promise that it
does not move, and §5 is the measurement.

The lane touches `fiscal_model/payroll.py`, one new data file under
`fiscal_model/data_files/payroll/`, the payroll tests, six guarded lines of
`fiscal_model/scoring_engine.py`, the Option 61 note in
`fiscal_model/validation/cbo_options.py`, and the two rows'
`known_limitations` in `fiscal_model/validation/core.py`. It adds **no Tier-1
row**, edits no target, no manifest and no threshold.

## 1. Starting numbers

All measured on the branch point, `1d35f1b`, from `python
scripts/cold_holdout.py --json` and `python scripts/run_loo.py --donor-matrix`.

### 1.1 The two cases this lane is about

CBO, *Options for Reducing the Deficit: 2025 to 2034* (pub. 60557, Dec 2024),
**Option 61, "Impose a New Payroll Tax"**, report p. 72 / PDF p. 78; the option's
own landing page is `https://www.cbo.gov/budget-options/60954`. The estimates
are JCT's — the table's data-source line reads *"Staff of the Joint Committee on
Taxation."*

| policy_id | official | model | err |
|---|--:|--:|--:|
| `cbo_opt61_new_payroll_tax_1pct` | −1,281.5 | −1,975.0 | **54.1%** |
| `cbo_opt61_new_payroll_tax_2pct` | −2,540.0 | −3,950.0 | **55.5%** |

Year by year for the 1% alternative, against CBO's own annual rows in
`fiscal_model/data_files/validation/cbo_options_2025_2034_alternatives.csv`
(row `61.1`, *"Decrease (−) in the deficit"*):

| FY | CBO deficit | model static | model behavioural | model deficit |
|---|--:|--:|--:|--:|
| 2025 | −56.7 | 140.0 | −24.5 | −164.5 |
| 2026 | −118.2 | 145.6 | −25.5 | −171.1 |
| 2027 | −122.8 | 151.4 | −26.5 | −177.9 |
| 2028 | −127.2 | 157.5 | −27.6 | −185.0 |
| 2029 | −131.1 | 163.8 | −28.7 | −192.4 |
| 2030 | −135.3 | 170.3 | −29.8 | −200.1 |
| 2031 | −140.1 | 177.1 | −31.0 | −208.1 |
| 2032 | −145.0 | 184.2 | −32.2 | −216.5 |
| 2033 | −150.0 | 191.6 | −33.5 | −225.1 |
| 2034 | −155.0 | 199.3 | −34.9 | −234.1 |
| **total** | **−1,281.5** | **1,680.9** | **−294.1** | **−1,975.0** |

Three things are visible in that table before any source is read.

1. **$140.0B in year one.** That is `medicare_rate_change × 100 × 140.0`, and
   the 140.0 is the comment *"Medicare revenue is ~$400B at 2.9%, so 1pp ≈
   $140B"* (`payroll.py`) — a rounded receipts aggregate divided by a statutory
   rate. `BASELINE_WAGE_DATA` carries `additional_medicare_billions: 15.0` four
   lines above it, so the $400B being divided by 2.9% **includes** the 0.9%
   Additional Medicare Tax, which is levied on a different and much smaller
   base. The identity double-counts by construction.
2. **4.0%/yr growth**, from `_growth_tax_policy_handlers`' `(PayrollTaxPolicy,
   0.04, False)`. CBO's own row grows at **3.45%/yr** across FY2026-2034.
3. **The behavioural term makes the tax raise more money.** −24.5 against a
   static of +140.0 and a final of −164.5: the engine computes `deficit =
   −revenue + behavioural`, so an offset carrying the *opposite* sign to static
   **magnifies** the revenue gain — here by 17.5%, the sum of an unsourced
   `labor_supply_elasticity = 0.1` and half of an unsourced
   `tax_avoidance_elasticity = 0.15`. `TaxPolicy.estimate_behavioral_offset`
   returns the *same* sign as static and its docstring says why. The payroll
   module returns the other one.

The 2% alternative is the same identity at twice the rate and lands at the same
proportional error, which is the tell that nothing in the module responds to the
size of the change.

### 1.2 What the module does today

`PayrollTaxPolicy.estimate_static_revenue_effect` is a five-branch cascade. Four
of the branches — `ss_eliminate_cap`, `ss_cover_90_pct`, `ss_donut_hole_start`,
`expand_niit_to_passthrough` — are the calibrated OASDI/NIIT machinery, and this
lane does not open any of them. The fifth pair is a rate change scored as
`rate_pp × a constant`: `CBO_PAYROLL_ESTIMATES["rate_1pp_annual"] = 90.0` for
Social Security and a bare literal `140.0` for Medicare. Option 61 enters
through the Medicare literal, because `create_policy_from_score`'s `payroll_rate`
shape builds `PayrollTaxPolicy(payroll_tax_type=MEDICARE,
medicare_rate_change=score.rate_change)` — deliberately not the OASDI cap
machinery, whose covered-wage bands *are* calibrated to the Trustees' own reform
annuals and would be leakage.

`estimate_behavioral_offset` is `|static| × (labor_supply_elasticity +
tax_avoidance_elasticity × {1.0 if a cap or donut change else 0.5})`, signed
against static. It is a **flat share of the revenue effect**, not an elasticity:
a 0.1pp tax and a 10pp tax both erode (or here, magnify) by the same 17.5%.

### 1.3 What CBO actually says, and where the plan's scoping was wrong

The option page's own text (`cbo.gov/budget-options/60954`, Dec 12 2024) and the
extended discussion it links in the previous volume (*Options for Reducing the
Deficit, 2023 to 2032 — Volume I*, pub. 58164, `cbo.gov/budget-options/58636`,
Dec 7 2022) settle every design question this lane needed, and two of the
answers are the opposite of what the repository's own `known_limitations` note
asserts.

> "This option consists of two alternatives. The first would impose a new
> payroll tax of 1 percent on all earnings, and the second would impose a new
> payroll tax of 2 percent. **The new tax would be paid entirely by employees.**
> Self-employed individuals would face the same tax rates as those who work for
> an employer. The proceeds of the new tax would be part of general revenues…
> This option would not make any changes to existing payroll taxes."
> — 60954

> "For both alternatives, **the income subject to the tax would match that of
> the Medicare payroll tax, so there would be no taxable maximum.**"
> — 58636, *Option*

> "Although the payroll tax in this option would be levied on employees,
> additional payroll taxes could be levied on employers instead… The budgetary
> effect of a payroll tax levied on employers would be different, however,
> because the reduction in employees' earnings would reduce the income base for
> individual income and payroll taxes. **That effect would partially offset the
> increase in payroll taxes.** Therefore, a payroll tax split between employers
> and employees would be estimated to result in less additional revenue than a
> payroll tax paid entirely by employees."
> — 58636, *Other Considerations*

> "The higher payroll tax would create an incentive for employers and employees
> to seek to change the composition of compensation, shifting from taxable
> compensation, such as wages and salary, to forms of nontaxable compensation,
> such as employment-based health insurance. **The estimates account for that
> behavioral response.**"
> — 58636, *Effects on the Budget*

> "In addition to having the behavioral effects reflected in conventional budget
> estimates… a new payroll tax would also affect taxpayers' incentive to work…
> people would reduce the average number of hours they work."
> — 58636, *Economic Effects*

> "This option would take effect in January 2025." — 60954

Read against the row's carried note in `validation/core.py` —

> "That identity covers all Medicare wages including the employer share, while
> CBO's option is employee-side only and is reduced by the income-tax offset a
> new payroll tax generates — neither adjustment exists in the module."

— the score is one right, one wrong, one confused.

* **Right:** the option is employee-side only. CBO says so in one sentence.
* **Wrong:** there is **no income-tax offset in this option's estimate**, and
  the reason is precisely that it is employee-side. CBO's *Other Considerations*
  paragraph exists to explain that the offset would appear only if the tax were
  levied on employers, and that an employer-side or split tax would therefore
  raise **less**. Adding an offset here would move the model the wrong way for a
  reason the source explicitly rules out.
* **Confused:** "all Medicare wages including the employer share" is a category
  error. The Medicare base is *earnings*; the 1.45/1.45 split is who remits, not
  what is taxed. A 2.9% tax on a base B raises 0.029·B whoever writes the
  cheque, so dividing $400B by 2.9% does not double-count an employer share —
  it double-counts the **0.9% Additional Medicare Tax**, which is a different
  defect the note does not name.

**The plan's §2.1 scoping is therefore wrong on both halves.** "Employer-share
incidence" is not the missing mechanism for *this* option (it is 0% employer),
and the "income-tax offset" is not applied to it. The lane still builds the
incidence rule, because the module needs it to score the employer-side variant
CBO describes and because Medicare rate changes are half employer-side — but it
evaluates to **zero** on Option 61 and closes none of the error. What CBO's
conventional estimate *does* carry is compensation shifting, which the module
has no representation of and which the plan did not name.

### 1.4 The rows this lane must not move

Leave-one-out (`python scripts/run_loo.py --donor-matrix`):

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| Payroll | `ss_cap_90_pct` | −800.0 | −800.0 | −749.5 | **+6.3%** |
| Payroll | `ss_donut_250k` | −2,700.0 | −2,700.0 | −2,664.0 | **+1.3%** |
| Payroll | `ss_eliminate_cap` | −3,200.0 | −3,200.0 | −3,319.5 | **−3.7%** |
| Payroll | `expand_niit` | −250.0 | −250.0 | — | not cross-validatable |

Payroll module mean **3.8%** (n=3 derivable, 1 excluded). **Suite aggregate: 18
derivable, 29.6% mean / 19.1% median, 8/18 within 15%, 4 not cross-validatable.**

### 1.5 Battery aggregates

- **Tier 1 (out-of-sample): 26 cases, 18.0% mean, 12.6% median, 14/26 within
  15%, 21/26 within 25%.**
- Fitted calibrated references: **23 policies, 1.6% mean**, 23/23 within 15%.
- Unfitted module reconstructions: **31 policies, 56.6% mean**, 9/31 within 15%.

CI gate in force: `cold_holdout.py --max-mean-error 25 --min-within-25pct 20`.

## 2. What the lane changes

One mechanism — **a base, an incidence rule and a shifting response** — replacing
one literal and one sign.

### 2.1 The base: covered earnings, from the option's own baseline

Option 61's base is stated by CBO to be the Medicare payroll tax base, i.e. HI
taxable payroll: *"the total amount of wages, salaries, tips, self-employment
income, and other compensation subject to HI taxes"* (2024 Medicare Trustees
Report, p. 63 fn. 35). The battery scores this option on
`BaselineVintage.CBO_FEB_2024`, which is also the baseline JCT used (*"The
estimates rely on the Congressional Budget Office's projections of the
economy"*, 58636), so the **path** must be CBO's and the **level** must be an HI
covered-earnings level.

| Quantity | Value | Source |
|---|---|---|
| Wages and salaries, FY2025-2034 | 12,808.2 … 18,217.2 | CBO, *The Budget and Economic Outlook: 2024 to 2034* (Feb 2024, pub. 59710), supplemental economic projections `51135-2024-02-Economic-Projections.xlsx`, sheet **"3. Fiscal Year"**, row *"Wages and salaries"* |
| HI total expenditures, CY2023 | 403.1 | 2024 Medicare Trustees Report, **Table III.B4**, p. 56, column *Expenditures — Total* |
| HI cost rate, CY2023 | 3.31% | 2024 Medicare Trustees Report, **Table III.B7**, p. 63 |
| Wages and salaries, CY2023 | 11,807.6 | same CBO file, sheet **"2. Calendar Year"** |

The cost rate is *defined* as expenditures ÷ taxable payroll, so HI taxable
payroll for CY2023 is **403.1 / 0.0331 = $12,178.2B**, and the covered-earnings
ratio is

    k = 12,178.2 / 11,807.6 = 1.0314

— covered earnings exceed NIPA wages because the base adds self-employment
earnings, and fall short because some employment is not HI-covered; the two
roughly offset, which is why k sits just above one. **k is measured once, on the
last completed historical year both documents share**, and never on a projection
year. `base_t = k × wages_t` for the ten fiscal years of the window.

That base grows at **3.9%/yr**, the CBO baseline's own wage path, replacing the
module's flat 4.0%.

### 2.2 The incidence rule: who the statute names

`employer_share` on the new-tax branch, defaulting to **0.0** because CBO says
this option's tax "would be paid entirely by employees." Where a share *is*
levied on employers, CBO's own rule applies: employers reduce earnings to hold
compensation cost constant, so that share of the tax shrinks the income and
payroll tax bases and is booked net of the marginal rate on labour income. On
Option 61 the term is exactly zero. It is built because a module that cannot
represent the employer side cannot represent an existing payroll tax either
(Medicare is 1.45/1.45), and because CBO states the rule rather than leaving it
to be invented.

### 2.3 The shifting response: the one behavioural channel a conventional
estimate carries

CBO names two behavioural channels and puts them in different buckets. Shifting
compensation toward nontaxable forms is *"account[ed] for"* in the conventional
estimate; reduced hours is an *Economic Effect*, i.e. dynamic. The module today
has neither — it has a flat 17.5% magnification with the wrong sign, of which
0.10 is called labour supply, a channel CBO explicitly excludes from a
conventional score.

The replacement is the standard net-of-tax-share response, with the
repository's own frozen elasticity:

    s   = ε · r / (1 − τ)                 fraction of compensation shifted out of the base
    Δrev = base · [ r·(1 − s) − τ·s ]     new tax, net of the existing bases lost

where

| Symbol | Value | Source |
|---|--:|---|
| ε | **0.25** | `TaxPolicy.taxable_income_elasticity`, the repository's module-wide frozen ETI (Saez, Slemrod & Giertz 2012), inherited unchanged by `PayrollTaxPolicy`. **No new constant.** |
| τ | **0.31** | CBO, *Marginal Federal Tax Rates on Labor Income: 1962 to 2028* (Jan 2019, pub. 54911), Summary: the economywide marginal tax rate on labor income was 27% in 2018, rises 2pp in 2026 when the 2017 tax act's individual provisions expire, and drifts to **31 percent** by the end of the projection. That publication is listed by CBO under Option 61's own *Related Publications*, and its rate is defined to "account for forms of labor compensation that are not subject to federal taxes — for instance, many fringe benefits", which is exactly the margin being shifted along. |

Nine of the window's ten years sit in the post-2025 regime under the Feb-2024
current-law baseline, so 31% is the rate in force for the window rather than a
number chosen from a range.

As a share of the gross static effect the erosion is `(r + τ)·ε / (1 − τ)` —
**11.6%** at 1pp, **12.0%** at 2pp. It rises with the rate, which the flat 17.5%
could not do.

### 2.4 The first fiscal year: a calendar identity, not a lag estimate

CBO: *"This option would take effect in January 2025."* FY2025 runs
October 2024 – September 2025, so nine of its twelve months are inside the
policy. The first year is scored at **9/12 = 0.75**. That is a calendar
identity, applied from the source's stated effective month; it is not an
estimate of remittance lag, and §3 pre-registers that it will over-book.

### 2.5 Where the code goes

- **`fiscal_model/payroll.py`** — a `PayrollTaxType.NEW_EARNINGS_TAX`, the
  fields `new_payroll_tax_rate`, `employer_share`, `effective_month`, a
  `covered_earnings_base(year)` reader, the constants above with their
  citations, and the sign correction to `estimate_behavioral_offset`.
- **`fiscal_model/data_files/payroll/covered_earnings_base.csv`** — the ten
  transcribed CBO fiscal-year wage figures and the four numbers behind `k`,
  with the table and page references in the header.
- **`fiscal_model/scoring_engine.py`** — six guarded lines passing `year=` to
  `estimate_static_revenue_effect` and zeroing the 4% growth when, and only
  when, a payroll policy's own year-indexed base is in play. This mirrors the
  line W4's Option-56 lane added for `TaxExpenditurePolicy` and is a no-op for
  every payroll policy that exists today. It is outside this lane's nominal file
  list and is recorded here rather than done quietly.
- **`fiscal_model/validation/core.py`** — the `payroll_rate` shape builds the
  new branch, and the two rows' `known_limitations` are rewritten to say what is
  actually left.
- **`fiscal_model/validation/cbo_options.py`** — the Option 61 note. **The shape
  was not wrong** (the Medicare base is the option's own base, and CBO says so);
  the *identity behind it* was. The note is corrected to say which.

## 3. The prediction

**Headline: the two rows go from 54.1% / 55.5% to roughly 7.5% / 8.1%, and a
third of what is left is one year.** Every number below was computed by hand
from the sources in §2 before any code was written; nothing was chosen by
looking at −1,281.5 or −2,540.0.

| | official | predicted | predicted err | today |
|---|--:|--:|--:|--:|
| `cbo_opt61_new_payroll_tax_1pct` | −1,281.5 | **−1,378.2** | **+7.5%** | 54.1% |
| `cbo_opt61_new_payroll_tax_2pct` | −2,540.0 | **−2,745.0** | **+8.1%** | 55.5% |

Year by year, 1% alternative:

| FY | base | predicted | CBO | err |
|---|--:|--:|--:|--:|
| 2025 | 13,210.3 | 87.6 | 56.7 | **+54.5%** |
| 2026 | 13,795.7 | 122.0 | 118.2 | +3.2% |
| 2027 | 14,364.6 | 127.0 | 122.8 | +3.4% |
| 2028 | 14,942.0 | 132.1 | 127.2 | +3.8% |
| 2029 | 15,544.0 | 137.4 | 131.1 | +4.8% |
| 2030 | 16,167.0 | 142.9 | 135.3 | +5.6% |
| 2031 | 16,805.6 | 148.6 | 140.1 | +6.0% |
| 2032 | 17,457.3 | 154.3 | 145.0 | +6.4% |
| 2033 | 18,117.6 | 160.2 | 150.0 | +6.8% |
| 2034 | 18,789.0 | 166.1 | 155.0 | +7.2% |
| **total** | | **1,378.2** | **1,281.5** | **+7.5%** |

**The three pieces, separately.** Base and timing alone, with no behavioural
channel at all, land at **+21.7% / +22.8%**. Adding the shifting response takes
them to **+7.5% / +8.1%**. The current 54.1% is those 21.7 points plus a 17.5%
magnification pointed the wrong way plus a base literal 4% too high in the first
year and growing 0.1pp/yr too fast.

**Where the residual sits, pre-registered.** Of the 1% row's +$96.7B,
**+$30.9B — 32% — is FY2025 alone** (87.6 against 56.7). CBO's first-year row is
**0.48** of its second-year row where the calendar says 0.75; the same volume's
income-tax options run 0.77–0.85 and its other payroll options run 0.29–0.31, so
there is no single convention to read off, and inventing a 0.48 to match this
row is exactly the fitting §4 of the plan forbids. Excluding FY2025 entirely,
the remaining nine years are **+5.4%** high and drifting up from +3.2% to +7.2%
— CBO's base grows more slowly than CBO's own wage projection, which is the
second piece of residual and is not something this lane can source.

**The anti-fitting disclosures.** The result is monotone in ε and mildly
monotone in τ, and both knobs are declared here rather than discovered later:

| ε | total | err | | τ | total | err |
|--:|--:|--:|---|--:|--:|--:|
| 0.10 | 1,486.6 | +16.0% | | 0.27 | 1,409.4 | +10.0% |
| 0.20 | 1,414.3 | +10.4% | | 0.29 | 1,394.2 | +8.8% |
| **0.25** | **1,378.2** | **+7.5%** | | **0.31** | **1,378.2** | **+7.5%** |
| 0.30 | 1,342.0 | +4.7% | | 0.33 | 1,361.1 | +6.2% |
| 0.40 | 1,269.7 | −0.9% | | | | |

**ε = 0.40 lands the row at 0.9% and I am not taking it.** 0.25 is the
repository's frozen ETI, inherited by every `TaxPolicy` subclass, and a lane
that raised it for one benchmark would have failed §4 whatever the error did.
Likewise the first-year fraction: 0.50 would land the row at +5.3%, and 0.75 is
the calendar.

**What does not move, and why it cannot.**

- **The Payroll LOO rows.** `validation/loo.py`'s `derive_payroll_annual` reads
  `SSA_COVERED_WAGES_ABOVE_BILLIONS`, `SOCIAL_SECURITY_PARAMS["rate_combined"]`
  and `cap_2025`, none of which this lane touches, and re-scores through the
  four factories, all of which set `labor_supply_elasticity = 0.0` and
  `tax_avoidance_elasticity = 0.0` — so the sign correction multiplies a zero.
  Payroll module mean stays **3.8%**; the suite stays **18 @ 29.6% / 19.1% /
  8**.
- **The four fitted payroll benchmarks.** Same factories, same zeros, plus a
  pinned `annual_revenue_change_billions` that returns before the cascade is
  reached. Fitted tier stays **23 @ 1.6%**.
- **Every shipped preset.** All four payroll presets
  (`💰 SS Cap to 90%`, `💰 SS Donut Hole $250K`, `💰 Eliminate SS Cap`,
  `💰 Expand NIIT`) route through `preset_handler.py`'s `payroll_type` to those
  same factories. Tailor builds no payroll policy. **Decision 6 is not
  expected to be triggered**; if a shipped number moves anyway, the lane adds
  the caption in its own commit and says here that the prediction was wrong.

**Tier 1 aggregate, predicted:**

| | before | predicted |
|---|--:|--:|
| mean | 18.0% | **14.4%** |
| median | 12.6% | **11.4%** |
| within 15% | 14/26 | **16/26** |
| within 25% | 21/26 | **23/26** |

The CI gate (`--max-mean-error 25 --min-within-25pct 20`) passes with room in
both directions.

## 4. Falsification tests

Written before the code, and each one fails the lane rather than being adjusted:

1. **No fitted-tier or LOO payroll row moves by a single digit.** Checked to the
   decimal against §1.4 and §1.5.
2. **Only the two named Tier-1 rows move.** Every other row identical to the
   dollar.
3. **`k` is invariant to the year it is measured in, to within the rounding of
   the published cost rate.** If the same construction on CY2022 or CY2024
   returns a materially different ratio, the derivation is an artefact and the
   lane says so. (CY2022 is known to be distorted by the Accelerated and Advance
   Payments repayments the Trustees footnote, so the test is stated on 2023 and
   2024 with 2022 excluded *for the stated reason*, not because it disagrees.)
4. **The behavioural offset carries the same sign as the static effect**, for
   every branch, matching `TaxPolicy` — asserted directly, and asserted to erode
   rather than magnify at the engine level by scoring a policy and checking that
   `|final| < |static|`.
5. **The response scales with the rate.** The 2pp erosion share must exceed the
   1pp erosion share; a flat share fails.
6. **The employer-share term is zero on Option 61 and positive on a
   half-employer variant**, so the incidence rule is exercised rather than dead.
7. **No constant in the lane equals a target over ten.** `−1281.5/10 = −128.15`
   and `−2540/10 = −254.0` appear nowhere.

## 5. What this lane will not do

- Not open `preregistered.py`, `holdout.py`, `loo.py`'s guards,
  `target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`, any CI threshold, or
  `tests/test_cold_holdout.py`.
- Not touch the OASDI cap/donut/90%/NIIT branches, `SSA_COVERED_WAGES_ABOVE_BILLIONS`,
  or `CBO_PAYROLL_ESTIMATES`' Social Security entries.
- Not build the reduced-hours labour-supply channel. CBO puts it under *Economic
  Effects*, i.e. outside a conventional score; the module's
  `labor_supply_elasticity` is the wrong bucket and this lane retires it from
  the new branch rather than re-estimating it.
- Not promote Option 62 or 63 (the OASDI options), which stay excluded as
  leakage against the calibrated covered-wage bands.
- Not touch the shared docs (`README.md`, `CLAUDE.md`, `docs/VALIDATION*.md`,
  `docs/METHODOLOGY.md`, `planning/MODELING_IMPROVEMENT.md`,
  `planning/NEXT_STEPS.md`, `CHANGELOG.md`). §2.1 of the modelling plan and the
  Tier-1 paragraph of `CLAUDE.md` will both be stale after this lane and a docs
  pass owns them.

Anything that moves outside this list is a finding, and gets written into §6.

## 6. Outturn

*Appended 2026-09-05, after the code. Numbers from `python
scripts/cold_holdout.py --json`, `python scripts/run_loo.py --donor-matrix` and
`python scripts/run_validation_dashboard.py` on the finished branch. Main did
not move under the lane, so §1's baseline is the one these are measured
against.*

**The prediction held to the decimal on both rows and on every aggregate.**
§3 said −$1,378.2B / +7.5% and −$2,745.0B / +8.1%, computed by hand before a
file was opened. The runner reports −$1,378.2B / 7.5% and −$2,745.0B / 8.1%.

### The two rows

| policy_id | official | before | after | before | after |
|---|--:|--:|--:|--:|--:|
| `cbo_opt61_new_payroll_tax_1pct` | −1,281.5 | −1,975.0 | **−1,378.2** | 54.1% | **7.5%** |
| `cbo_opt61_new_payroll_tax_2pct` | −2,540.0 | −3,950.0 | **−2,745.0** | 55.5% | **8.1%** |

Year by year, 1% alternative, against CBO's own row:

| FY | CBO | before | after | after err |
|---|--:|--:|--:|--:|
| 2025 | −56.7 | −164.5 | **−87.6** | +54.5% |
| 2026 | −118.2 | −171.1 | **−122.0** | +3.2% |
| 2027 | −122.8 | −177.9 | **−127.0** | +3.4% |
| 2028 | −127.2 | −185.0 | **−132.1** | +3.8% |
| 2029 | −131.1 | −192.4 | **−137.4** | +4.8% |
| 2030 | −135.3 | −200.1 | **−142.9** | +5.6% |
| 2031 | −140.1 | −208.1 | **−148.6** | +6.0% |
| 2032 | −145.0 | −216.5 | **−154.3** | +6.4% |
| 2033 | −150.0 | −225.1 | **−160.2** | +6.8% |
| 2034 | −155.0 | −234.1 | **−166.1** | +7.2% |
| **total** | **−1,281.5** | **−1,975.0** | **−1,378.2** | **+7.5%** |

### Everything else

| | before | after |
|---|--:|--:|
| **Tier 1 mean** | 18.0% | **14.4%** |
| **Tier 1 median** | 12.6% | **11.4%** |
| **Tier 1 within 15%** | 14/26 | **16/26** |
| **Tier 1 within 25%** | 21/26 | **23/26** |
| Fitted calibrated references | 23 @ 1.6% | **23 @ 1.6%** |
| Unfitted reconstructions | 31 @ 56.6% | **31 @ 56.6%** |
| Payroll LOO (n=3 derivable) | 3.8% | **3.8%** |
| LOO suite | 18 @ 29.6% / 19.1% / 8 | **18 @ 29.6% / 19.1% / 8** |
| Tests | 3,322 passed, 1 skipped | **3,335 passed, 1 skipped** |

`run_loo.py --donor-matrix` output is **byte-identical** before and after, and
so is the shipped-preset sweep (all 53 `PRESET_POLICIES` entries scored on both
commits). Every Tier-1 row other than the two named ones is identical to the
dollar. The two payroll rows are now the 8th and 10th most accurate of 26,
where they were the 25th and 26th.

`run_validation_dashboard.py` exits 1 on this branch — and it exits 1 on
`1d35f1b` too, for the same two reasons: `runtime [degraded] Python 3.14.0
(supported >=3.10,<3.14)` and `microdata [warn] SOI 2023: returns 119% / AGI
81%`. Diffing the two runs, the only substantive line that changed is the
out-of-sample summary. Neither degraded component is touched by this lane.

### All seven falsification tests fired, and none of them fired against the lane

`tests/test_payroll_new_earnings_tax.py`, 13 tests. Test 3 is the one worth
reading: the covered-earnings ratio measured on CY2024 is 1.0220 against
CY2023's 1.0314 — 0.9% apart, and worth 0.9pp on the row (+6.6% instead of
+7.5%). **CY2022 gives 0.9342, which would take the row to −2.6%**, i.e. the
excluded year is the flattering one. It is excluded on the Trustees' own
footnote 10 ($33.4B of Accelerated Payments repayments inside that year's
expenditures break the expenditures-over-cost-rate identity), and the exclusion
was written into the data file's header and this document's §2.1 in the
commit *before* the row was scored. The test now says so in as many words, so
nobody has to take it on trust.

### Six findings

**1 — The plan's own scoping was wrong on both halves, and the source says so
in two sentences.** §2.1 of `MODELING_IMPROVEMENT.md` scoped this row as
"employer-share incidence + income-tax offset". CBO's option text says *"The
new tax would be paid entirely by employees"* and its *Other Considerations*
paragraph exists to explain that an employer-side tax would raise **less**,
because only then does the reduction in earnings shrink the income and payroll
bases. Adding the offset the plan named would have moved the model further from
the target, for a reason the source explicitly rules out. The employer-share
rule is built anyway — the module could not otherwise represent Medicare, which
is half employer-side — and it evaluates to exactly zero here. **Reading the
option before writing the mechanism is what this lane did differently, and it
is the whole finding.**

**2 — The identity was not double-counting an employer share; it was dividing
one tax's receipts by another tax's rate.** `$400B / 2.9% = $13,793B` treats
Medicare payroll receipts as if they all came from the 2.9% base, when
`BASELINE_WAGE_DATA` carries `additional_medicare_billions: 15.0` four lines
above it — the 0.9% Additional Medicare Tax, levied on a far smaller base. The
row's carried `known_limitations` note named the wrong defect ("all Medicare
wages including the employer share"), which is a category error: the Medicare
base is *earnings*, and the 1.45/1.45 split is who remits, not what is taxed.
A note that describes a plausible defect is worse than no note, because it
tells the next lane where not to look.

**3 — The behavioural offset made a tax increase raise more than it levied, and
it is the second module to have done so.** `estimate_behavioral_offset` returned
the *opposite* sign to the static effect while the engine computes `deficit =
−revenue + behavioural`, so 0.10 of labour supply plus 0.075 of avoidance
**magnified** the score by 17.5%. That is the same defect L8 found in
`trade.py`'s tariff offset in Wave 3, in a different module, with the same
consequence and the same fix. Two of the repository's fourteen modules have now
been found with an inverted offset convention, and both were found by a lane
that happened to be reading the file — **not by any test, because both modules'
calibrated factories zero the elasticity, so the fitted tier and the LOO
column are structurally blind to the sign**. Worth a sweep of the other twelve.

**4 — The module's "elasticities" are flat shares of the revenue effect, so
nothing responded to the size of the change.** `labor_supply_elasticity = 0.1`
and `tax_avoidance_elasticity = 0.15` multiply `|static|`, not a net-of-tax
share, so a 0.1pp tax and a 10pp tax erode by the same 17.5%. That is why the
1% and 2% alternatives had errors 1.4pp apart before the lane and 0.5pp apart
after: the model was exactly linear in the rate where CBO's is very slightly
concave. The new branch's erosion is `(r + τ)·ε / (1 − τ)`, 11.6% at 1pp and
12.0% at 2pp, which is slightly *convex* — so the model now misses the
curvature in the other direction, by less. The two legacy constants are left in
place for the OASDI branches, where every factory zeroes them, and they remain
unsourced. **Carry-over.**

**5 — Two-thirds of what is left is a base-growth gap the option text does not
explain, and a third is one year.** FY2025 alone is +$30.9B of the +$96.7B
residual: CBO's own first-year row is **0.48** of its second-year row where a
January effective date and a fiscal year give **0.75**. The volume gives no
convention to read off — its income-tax options run 0.77–0.85 and its other
payroll options 0.29–0.31 — so 0.75 is the calendar and the gap is unexplained.
The other two-thirds is growth: the model prices the base off CBO's own
February 2024 wage path at 3.9%/yr, while the base implied by CBO's published
revenue row grows **3.45%/yr**, which is why the annual error drifts from +3.2%
in FY2026 to +7.2% in FY2034. Nothing in the option text says why JCT's earnings
base should grow more slowly than CBO's wages. **Both are carry-overs, and
neither is closable from the published record this lane could reach.**

**6 — The engine now has two year-indexed policy classes and no general
concept.** `_score_growth_tax_policy_year` grows one annual by a per-class
constant, and two classes have now had to opt out of it: `TaxExpenditurePolicy`
in Wave 4 (a cap's bite is a function of the year) and `PayrollTaxPolicy` here
(the base is a path). Each opt-out is six lines of `isinstance` in the engine.
A third will make it a pattern worth naming — `Policy.scores_by_year()`, say —
rather than a third special case. **Not this lane's to build**, and on the
carry-over list.

### What this lane did not do

- Did not open `preregistered.py`, `holdout.py`, `loo.py`, `target_revisions.py`,
  `KNOWN_SCORES`, `CBO_SCORE_MAP`, any CI threshold or
  `tests/test_cold_holdout.py`. Both rows keep their pre-registered targets and
  their `.v1` case ids.
- Did not touch the OASDI cap/donut/90%/NIIT branches,
  `SSA_COVERED_WAGES_ABOVE_BILLIONS` or `CBO_PAYROLL_ESTIMATES`.
- Did not build the reduced-hours labour-supply channel (CBO files it under
  *Economic Effects*, outside a conventional score) or re-estimate the two
  legacy flat shares (finding 4).
- Did not promote Options 62 or 63, which stay excluded as leakage against the
  calibrated covered-wage bands.
- **Did not add a Decision 6 caption, because no shipped number moved.** All 53
  `PRESET_POLICIES` entries score identically before and after; the four payroll
  presets route through factories with pinned annuals and zeroed elasticities,
  and Tailor builds no payroll policy. The one user-visible surface that *can*
  reach the corrected sign is `bill_tracker/auto_scorer.py`'s `payroll` branch,
  which builds a policy with module-default elasticities — an exploratory-tier,
  demo-grade path whose numbers were being magnified rather than eroded and are
  now correct.
- Did not touch the shared docs. `planning/MODELING_IMPROVEMENT.md` §2.1's
  payroll row and `CLAUDE.md`'s Tier-1 paragraph are both stale after this lane
  and a docs pass owns them; §2.1's scoping sentence is wrong on the merits, not
  merely out of date (finding 1).
