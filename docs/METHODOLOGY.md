# Scoring Methodology

> How the Fiscal Policy Calculator estimates budget impacts

---

## Table of Contents

1. [Overview](#overview)
2. [Static Scoring](#static-scoring)
3. [Behavioral Response](#behavioral-response)
4. [Dynamic Scoring](#dynamic-scoring)
5. [Distributional Analysis](#distributional-analysis)
6. [Microsimulation Engine](#microsimulation-engine)
7. [Corporate Tax](#corporate-tax)
8. [International Tax](#international-tax)
9. [Estate Tax](#estate-tax)
10. [Payroll Tax and Social Security](#payroll-tax-and-social-security)
11. [Alternative Minimum Tax](#alternative-minimum-tax)
12. [Tax Credits](#tax-credits)
13. [Tax Expenditures](#tax-expenditures)
14. [Premium Tax Credits (ACA)](#premium-tax-credits-aca)
15. [TCJA Extension](#tcja-extension)
16. [Tariff and Trade Policy](#tariff-and-trade-policy)
17. [IRS Enforcement](#irs-enforcement)
18. [Drug Pricing and Pharmaceutical Policy](#drug-pricing-and-pharmaceutical-policy)
19. [State-Level Modeling](#state-level-modeling)
20. [Overlapping Generations Model](#overlapping-generations-model)
21. [Spending Multipliers](#spending-multipliers)
22. [Uncertainty Analysis](#uncertainty-analysis)
23. [Comparison to Official Methods](#comparison-to-official-methods)
24. [Validation Results](#validation-results)
25. [References](#references)

---

## Overview

The Fiscal Policy Calculator uses a **three-stage approach** consistent with Congressional Budget Office (CBO) methodology:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Static Score   │ ──▶ │   Behavioral    │ ──▶ │    Dynamic      │
│                 │     │   Adjustment    │     │   Feedback      │
│ Direct revenue  │     │ ETI response    │     │ GDP/employment  │
│ effect of rate  │     │ to tax changes  │     │ feedback        │
│ changes         │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   $X billion              $X × (1-ETI×0.5)        + revenue feedback
```

### Key Principles

1. **Current Law Baseline**: All estimates are relative to current law (not current policy)
2. **10-Year Budget Window**: the app scores **FY2026–FY2035**, the window the CBO February 2026 baseline projects — `fiscal_model.baseline.APP_DEFAULT_START_YEAR`, which every app surface and the public API route through. The **validation suite keeps its own window**, `DEFAULT_VALIDATION_START_YEAR = 2025`: each benchmark is scored over the window its own document used, which for the P.L. 119-21 line items is JCT's **FY2025–FY2034** (see [VALIDATION.md](VALIDATION.md), “Scoring window”). The library defaults (`FiscalPolicyScorer`, `Policy.start_year`) stay at 2025 for that reason. Inputs are **tax-year** (calendar-year) SOI aggregates; outputs are fiscal-year totals, and the model carries the former into the latter without a calendar-to-fiscal conversion
3. **Conventional Scoring**: Behavioral but not macroeconomic by default
4. **Dynamic Scoring**: Optional macroeconomic feedback via FRB/US-calibrated adapter
5. **Tiered validation**: the calibrated modules *reconstruct* official CBO/JCT/Treasury estimates; a separate pre-registered battery *predicts* them cold. The tiers are reported separately and never averaged into one tolerance — see [Validation Results](#validation-results)

The calculator currently exposes 14 preset policy areas: TCJA / individual tax, general income tax, corporate, international, tax credits, estate tax, payroll / Social Security, AMT, ACA / healthcare, tax expenditures, IRS enforcement, drug pricing, trade / tariffs, and climate / energy.

### The baseline is CBO's own table

Since PR #159 every vintage's **economic** path and two of three **budget** paths
are transcribed from CBO's own published tables in
[`US-CBO/cbo-data`](https://github.com/US-CBO/cbo-data) @ `284a9566`, pinned by
commit and verified by **SHA-256 per file**, cross-checked against
`US-CBO/budgetary-feedback-model`. The route is recorded rather than assumed:
`cbo.gov` returns HTTP 403 to this environment and the Wayback Machine holds no
snapshot of the relevant workbooks, while `github.com/US-CBO` is not blocked and
publishes the same tables as machine-readable CSV under a public-domain
dedication. Both CBO repositories count as "CBO's own table" for the `sourced`
grade, `cbo-data` preferred.

`VINTAGE_SOURCING` is **computed from what the transcription actually contains,
per line**, rather than asserted for a whole vintage — which matters, because all
three vintages had previously been graded `sourced` and the grade was **false for
two of them**. Two errors it was hiding are worth naming. First,
`real_gdp_growth + inflation` **is not nominal GDP growth and never was**: the
reconstruction added a real rate to a *PCE* price index, where CBO publishes
`gdp_pct_change`, the nominal path itself. Second, the February 2026 block's
ten-year Treasury note **fell** 4.5% → 3.9% where CBO's own table **rises** 4.10%
→ 4.38%, so a baseline whose interest-rate path pointed the wrong way was pricing
debt service the wrong way.

| vintage | economic | budget | ten-year deficit |
|---|---|---|--:|
| February 2024 | transcribed | **reconstructed** | $29,440.30B |
| January 2025 | transcribed | transcribed | $21,758.26B |
| **February 2026** (app default) | transcribed | transcribed | **$23,143.30B** |

**February 2024 keeps a reconstructed budget path** because `cbo-data`'s
`ten_year_budget` ships `2024-06`, `2025-01` and `2026-02` only, and June 2024 is
publication **60039**, *An Update to the Budget and Economic Outlook* — a
different document whose FY2025 deficit is $1,937.9B against the January 2025
edition's $1,865.3B. Borrowing it would have graded a vintage `transcribed`
against a document it does not name. **That vintage's debt/GDP ratio is therefore
a mixture and must not be quoted**: its GDP is CBO's and its debt is this module's
reconstruction.

The app's default February 2026 vintage is CBO publication **61882**, *The Budget
and Economic Outlook: 2026 to 2036*, through CBO's 51118 data release. It
reproduces that report's own printed headlines — **FY2026 −$1,852.7B**,
**FY2027–2036 −$24,406.0B** and **FY2036 −$3,115.4B** — and every *year*'s deficit
matches CBO's own `proj_deficit_total` to within $0.05B. The app quotes
**$23,143.3B** because it sums the same table over its own **FY2026–2035** window;
**CBO's headline ten-year window is FY2027–2036**, so the two figures are
different decades of one table rather than a disagreement.
`tests/test_cbo_baseline_transcription.py` pins all four.

The correction is a **growth rate** rather than a level, which is why it moved
eleven out-of-sample rows in both directions: CBO's own FY2023 → FY2025 nominal
growth is **10.70%** where the hand-entered February 2026 block assumed **8.99%**.
Ten rows moved through `_income_base_projection_factor`; an eleventh,
`cbo_opt56_employer_health_income_only`, moved through a baseline **assumption**
rather than a level, because the cap limit's chained-CPI proxy reads
`vintage_assumptions(vintage)["inflation"]`. **A baseline has two surfaces a score
can read.**

---

## Static Scoring

### Tax Rate Changes

For income tax rate changes, the static revenue effect is:

```
ΔRevenue = ΔRate × Marginal_Income × Num_Taxpayers
```

Where:
- **ΔRate**: Change in tax rate (e.g., +0.026 for a 2.6 pp increase)
- **Marginal_Income**: Average income *above the threshold* for affected filers
- **Num_Taxpayers**: Number of taxpayers above the threshold

**Example**: Biden's $400K+ rate increase (37% → 39.6%)
```python
rate_change = 0.026  # 2.6 percentage points
threshold = 400_000
affected_filers = 1.8M  # From IRS SOI
avg_income = 1.2M       # Average total income of filers above $400K
marginal_income = 1.2M - 0.4M = 800K  # Income ABOVE threshold

static_revenue = 0.026 × 800,000 × 1,800,000 = $37.4B/year
```

Only income *above* the threshold is subject to the rate change. A filer earning $500K with a $400K threshold has only $100K of marginal income affected.

### The generic income-tax base, in three parts

Every generic income-tax score is one base times one rate change, and the base is
settled by three independent questions that Waves A and B of the high-stakes plan
answered one at a time. They are independent, so the answers compose, and the
repository had a different defect in each.

**(1) Which SOI column — AGI or taxable income? (`income_measure`)**

SOI Table 1.1's rows are **AGI size classes** and its columns include **both**
total AGI and total taxable income. The generic path selects returns by the class
boundary — an **AGI** boundary — and then prices the reform as
`Σ max(0, avg_income(above the floor) − T) × N`. Until Wave B the `avg_income` in
that expression was always **taxable income**, so a threshold stated on AGI was
subtracted from an average of a different quantity. On CBO Option 46 alternative
1 that is `$92,658 − $20,000` where the option says *"a surtax of 1 percentage
point would be imposed on **AGI** above $20,000 for single filers and $40,000 for
joint filers"* (publication 60557, report p. 56); the single-filer **AGI** average
above that floor is `$120,414`. Same returns, same floor, a base **1.4052×**
larger.

**The defect is a unit mismatch rather than a level**, and naming it that way is
what made it tractable: read as "the base is a bit low" it invites a fudge factor;
read as "these are two different quantities" it has exactly one fix, and the fix
is **per source**. `TaxPolicy.income_measure` is `"taxable"` or `"agi"`, and which
one a validation row reads is transcribed from that row's own sentence rather than
chosen. Of the six records carrying `agi_inclusive_base`, **three say AGI** (both
CBO Option 46 alternatives and the Warren surtax), **two say taxable income** in as
many words (both TPC illustrative rows), and one —
`medicare_surcharge_2pp`, whose statutory base is wages plus net investment income —
states a base that is **neither SOI column**, since AGI also carries proprietors'
income, pensions and IRA distributions less above-the-line deductions, while
taxable income is net of the standard or itemised deduction and of the QBI
deduction. Where a source is ambiguous the row **stays on the taxable column and
the ambiguity is recorded**; it is not resolved with the nearer-looking column.

**(2) Ordinary or AGI-inclusive? (`ordinary_income_base`)**

An *ordinary*-bracket rate change (e.g. restoring the 39.6% top rate) does **not**
apply to long-term capital gains or qualified dividends, which are taxed at
preferential rates, so the preferentially-taxed share (sourced from
`CapitalGainsBaseline`) comes out of the base. An **AGI-inclusive surtax** reaches
that income and the share stays in.

**There is now one default and it is shared.** `DEFAULT_ORDINARY_INCOME_BASE`
(`fiscal_model/policies_core.py`) is what the `TaxPolicy` dataclass, Tailor's
checkbox, the composer's preset path, the API's `ScoreRequest` and Ask's
`score_hypothetical_policy` all read; a test greps every constructor in the tree
and fails if any of them re-acquires a literal of its own. Before Wave A there
were **three** different defaults across those four surfaces, and the same policy
specification scored **−$166.5B on Tailor and −$314.6B on Ask** on the same
commit — 1.89× apart, with the scorecard validating only the second. Set the flag
`False` (UI: uncheck "Ordinary-income base"; or `CBOScore.agi_inclusive_base=True`)
for AGI-inclusive surtaxes. Reproduce the legacy-vs-corrected comparison with
`python scripts/cold_holdout.py --ordinary-base`.

The two flags are **not** the same question and the invariant says so: an
`income_measure="agi"` base already contains preferential income, so combining it
with `ordinary_income_base=True` would remove that income from a total defined to
include it. The constructor **refuses** the combination rather than silently
normalising it — a refusal, because a silent normalisation would have hidden the
one caller that comes close (`cold_holdout.py --ordinary-base`, which forces the
flag on every generic row in both directions as a diagnostic).

**(3) Which year is the base? (the vintage's own nominal path)**

SOI publishes a **tax year**; the app scores a **ten-fiscal-year window**. Until
Wave B the generic path returned the same tax-year-2023 annual ten times — `yr1 ==
yr10` to the cent on every shape — across a decade in which the scored baseline's
own nominal GDP grows **28.8%** (3.878%/yr on CBO's February 2024 vintage). The
base is now indexed to **the nominal-GDP path of the vintage the run is scored
on**, so a score on the February 2024 baseline and a score on a later one do not
silently share a 2023 level. On the app's default FY2026–2035 window the window
mean of that index is **1.355952**, which is exactly the factor every generic
shipped preset moved by.

Three things about this are worth stating rather than leaving implied. **Nominal
GDP, not the wage path**, and the choice does not turn on fit: on the one vintage
where both are transcribed the two window means are 1.30719 and 1.31182, a **0.35%**
difference, so availability and base definition decide it. **The projection
implicitly indexes the threshold**, because scaling an aggregate above a fixed
nominal floor by `f` is identical to indexing that floor by `f`; the real base of
an unindexed-threshold reform grows faster, so the projection is a **lower bound**
and the two Option 46 rows stay under. And **a caller-supplied base is never
projected** — if the caller states the base, the model uses the base it was given.

**What the three steps are worth, measured.** On CBO Option 46 alternative 1 the
chain runs 49.8% → 34.1% (growth) → **7.4%** (AGI column); on alternative 2, 37.4%
→ 17.9% → **−2.9%**. They compose in either order, and neither step alone reaches
either figure.

#### Filing-status thresholds (`threshold_by_filing_status`)

Statutory income-tax boundaries are stated **per filing status**. CBO's Option
46 surtax applies "on AGI above **$20,000 for single filers and $40,000 for
joint filers**"; the 2025 24% bracket starts at **$206,700** for joint returns
and **$103,350** for everyone else; the FY2025 Green Book's top-rate proposal
prints **four** amounts. Until Wave 7, `TaxPolicy.affected_income_threshold` was
a scalar and `IRSSOIData` read only Table 1.1, which carries no filing-status
dimension at all — so one status's floor was applied to all four populations.
At Option 46 alternative 1 that taxed 46.1M joint returns from $20,000 up where
JCT starts them at $40,000: **$839.8B of base, 9.2% of the whole**.

`TaxPolicy.threshold_by_filing_status` is an optional **partial** mapping over
the four SOI statuses; anything it does not name falls back to
`affected_income_threshold`, so `{"joint": 40_000}` against a $20,000 threshold
*is* the option's wording, and `None` keeps the pooled path byte for byte. The
split base comes from `IRSSOIData.get_bracket_distribution_by_status`, which
takes only the **composition** from **SOI Table 1.2** (`scripts/build_filing_status_data.py`
transcribes it): each Table 1.1 AGI-class total times that status's share of the
class in Table 1.2. **Reading Table 1.2 wholesale would have been simpler and
wrong** — its taxable-income column is measured on *all* returns ($11,944.4B)
where Table 1.1's is measured on *taxable* returns ($11,625.3B), a **$319.2B**
gap concentrated below $50,000 that neither table mentions, so switching tables
would move every split score by 2.7% for a reason unrelated to filing status.
Apportioning makes the split exactly neutral at a uniform threshold, which is
the lane's own control and is asserted by test.

Where a source names only two statuses, `FILING_STATUS_THRESHOLD_RULE` (in
`fiscal_model/validation/core.py`) reads it the way IRC §1411(b) is written:
**joint returns take the joint amount; separate, head-of-household and single
returns take the single amount.** The rule was fixed in the lane doc before any
row was scored on a split base.

**Two cautions.** First, the single-threshold approximation was **not uniformly
generous**, though every note in this repository used to say so: the FY2025
Green Book's married-filing-separately floor of $225,000 is $175,000 *below* the
unmarried $400,000 the model applied, so that base had been **under**-counted.
Second, **splitting a base double-counts a correction unless the correction is
held still.** Recomputing `preferential_income_share` against the split
denominator raises it from 21.6% to 29.1% on the bracket row — joint returns
between the two floors are removed from the base once and their preferential
income removed from the remainder again — which is worth eight points of pure
bookkeeping. The shipped code holds the share at the pooled threshold.

**A third caution, from the AGI column.** A ratio measured on the *pooled*
base is not the ratio that applies to a split one. Marginal AGI over marginal
taxable income is **1.3820** at $20,000 and **1.3094** at $100,000 pooled, but
**1.4052** and **1.2535** inside the filing-status split — one higher and one
lower, because the joint floor is twice the single floor and joint returns are
a different share of the two populations. Sizing the AGI step with the pooled
ratios would have missed both Option 46 rows in opposite directions.

#### Year-indexed statutory thresholds (`threshold_indexation`)

A statutory bracket boundary is a function of the **year** as well as the filing
status, and until PR #165 the model held one fixed number. The row's own
limitation had said so since Phase B — *"the bracket boundary is filing-status
specific and moves in 2026 when the pre-2018 rate schedule returns; the model
holds one fixed threshold"* — and the second half stayed open because
`cbo_scores.py` recorded that the data did not exist: *a published post-2025 rate
table*. **It exists.** `US-CBO/cbo-data`'s
`data/budget/tax_parameters/annual_cy_{2024-06,2025-01,2026-02}.csv` (CBO
publication 53724) is 130–150 variables × CY2021–CY2036 across three vintages,
transcribed verbatim to
`fiscal_model/data_files/cbo_tax_parameters/cbo_tax_parameters.csv` (**5,531
rows**, SHA-256 pinned per file by `scripts/fetch_cbo_tax_parameters.py`) and read
through `fiscal_model/cbo_tax_parameters.py`.

**The 2026 reversion is not a uniform shift, which is why this needed the
filing-status split to exist first.** On the June 2024 vintage `tp_rate_2..7` go
12/22/24/32/35/37 → **15/25/28/33/35/39.6** in CY2026, and the fourth bracket's
floor moves **−3.5% for joint returns, +15.9% for single and +65.5% for
head-of-household**, because the pre-TCJA 28% bracket sits differently against
TCJA's 24% bracket in each status. A scalar cannot express that, and neither can a
scalar plus one joint amount.

`TaxPolicy.threshold_indexation` is a three-valued enum, and writing it down is
half the value of the change, because the shipped behaviour had been an unnamed
assumption:

| value | meaning | who gets it |
|---|---|---|
| `"income"` | the threshold rides the nominal-income index — **today's arithmetic, exactly** | **default**: every preset, every Tailor row, every unmoved validation row is byte-identical |
| `"statutory"` | the boundary is read from CBO's schedule per year per filing status | the rows whose own sources describe a statutory ordinary-income bracket |
| `"nominal"` | the amount is fixed in year-`t` dollars, i.e. deflated by the index | nobody today; built, measured and reachable |

**The unit conversion is not a choice.** The base projection already scales
aggregate marginal income above a fixed nominal threshold by an index `g(t)`,
which is arithmetically identical to indexing the threshold by `g(t)` too. So to
apply a **statutory** threshold `T(t)`, stated in year-`t` dollars, against a base
measured in SOI tax-year dollars:

```
base(t) = g(t) · Σ_status Σ_returns max(0, y_i − T_status(t) / g(t)) · n_i
```

with `g(t) = nominal_income_index(t) / nominal_income_index(SOI tax year)`, read
from the **scored vintage's own** transcribed path and applied exactly once.

**The arithmetically wrong variant scores four times better and is recorded rather
than taken.** Applying `T(t)` directly to SOI-year incomes — a 2031 threshold
against a 2023 income — takes CBO Option 45's top-four-brackets row to **3.61%**;
the correct conversion takes it to **17.86%**, worse than the 14.31% a fixed
threshold gave. A repository that keeps finding two errors cancelling should
record the one it declined to introduce.

**Which rows get a schedule is fixed by rule, not by proximity.**
`STATUTORY_BRACKET_SCHEDULE_RULE` (`fiscal_model/validation/core.py`): a record's
threshold is read from the schedule **if and only if** its own source describes
the boundary as a statutory ordinary-income bracket; the record declares the
bracket *index* (1–7) and the schedule supplies the four dollar amounts per year.
An amount a source states in its own words stays where the source put it, however
close it sits to a bracket floor — **numeric coincidence is not evidence**, and
the trap is real: `$20,000` **is** `tp_bracket_2_hoh` in CY2033, and CBO's Option
46 still means $20,000. A test asserts the coincidence, the record's `None` and
the rule's own sentence together.

Schedule vintage is matched to the scored baseline vintage, the same discipline
`build_scorer_for_vintage()` already imposes — `exact` for January 2025 and
February 2026, **`nearest_vintage`** for the February 2024 Options battery, since
`cbo-data`'s oldest `tax_parameters` edition is June 2024. That substitution is
graded in the data rather than hidden, and it was **sized**: re-scoring the one
moving row with CY2025 forced to Rev. Proc. 2024-40's actual floors gives −671.20
against −671.21, **one cent**.

### Data Source: IRS SOI

We use IRS Statistics of Income (SOI) Table 1.1, Table 1.2 and Table 3.3 to obtain:
- Number of returns by income bracket
- Total taxable income by bracket
- Tax liability by bracket
- The **filing-status composition** of each AGI class (Table 1.2, tax year 2023)

```python
from fiscal_model.data import IRSSOIData

irs = IRSSOIData()
bracket_info = irs.get_filers_by_bracket(year=2023, threshold=400_000)
# Returns: {'num_filers': 1.8M, 'avg_taxable_income': 1.2M, ...}
```

**Tax-year basis and data lag.** SOI tables are compiled on a **tax year**
(calendar-year) basis, while every score in this document is reported over a
**fiscal-year** budget window. The repository ships Table 1.1 and Table 3.3 for
tax years **2021, 2022 and 2023** (`fiscal_model/data_files/irs_soi/`), and
auto-population takes the **latest available year** unless a policy sets
`data_year` — so production scoring runs on **tax year 2023**
(`policies_core._estimate_from_irs_data`; confirmed by the `irs_soi` row of
`python scripts/run_validation_dashboard.py`, which reports `latest 2023`).
SOI runs roughly two years behind the current tax year.

### Credits and Deductions

For tax credits:
```
ΔRevenue = -Credit_Amount × Num_Beneficiaries × (1 if refundable else avg_liability_rate)
```

For deductions:
```
ΔRevenue = -Deduction_Amount × Marginal_Rate × Num_Beneficiaries
```

---

## Behavioral Response

### Elasticity of Taxable Income (ETI)

Taxpayers respond to rate changes by adjusting reported taxable income through a combination of labor supply, avoidance, and evasion channels:

```
%ΔTaxable_Income = -ETI × %Δ(1 - marginal_rate)
```

The **behavioral offset** shrinks the magnitude of the static estimate:

```python
behavioral_offset = static_effect * ETI * 0.5   # signed, same sign as static
```

The factor of 0.5 converts from the income elasticity to the revenue offset (accounting for the fact that the base only partially overlaps the rate change).

*(This line carried a leading minus until the 2026-09 docs sync. `TaxPolicy.estimate_behavioral_offset` returns `static_effect * self.taxable_income_elasticity * 0.5` and its docstring says "Returns a SIGNED value with the same sign as `static_effect`", so the minus was a transcription error — and reading it as written is precisely the defect PR #119's sweep found in seven modules.)*

#### The sign contract every module must follow

`fiscal_model/scoring_engine.py` books a score as
`static_deficit = static_spending − static_revenue`, then
`deficit_after_behavioral = static_deficit + behavioral`. The quantity handed to
`estimate_behavioral_offset` is the **static revenue** effect for that year, not
the deficit effect. So:

- an offset carrying the **same sign as the static revenue effect erodes** it —
  a tax increase raises less than its static figure because the base shrinks, a tax
  cut loses less because the base grows. `TaxPolicy` implements exactly this, and
  the final effect is `static × (1 − ETI·0.5)`, which shrinks the magnitude
  whichever way the static points;
- an offset carrying the **opposite sign magnifies** it, which is backwards in both
  directions at once;
- an offset whose magnitude exceeds `|static|` is not erosion either, even when
  correctly signed — it flips the score's sign.

A 2026-09 sweep (PR #119) probed all fifteen implementations at the function
(`f(+100)` and `f(−100)`, the sign rule the class implements regardless of what its
own factories produce) and at the score (an increase and a cut of equal size through
the engine). **Seven were against the contract**: `AMTPolicy`, `EstateTaxPolicy` and
`PremiumTaxCreditPolicy` were **inverted** — all three carrying the identical
comment pair `# Reduces revenue gain` / `# Reduces revenue loss` above a
`return -total_offset`, one copy-paste in three files by an author who read
`behavioral` as a quantity the engine *subtracts* — and `CorporateTaxPolicy` in
`reported` mode, the `TaxCreditPolicy` fallback branch, `IRSEnforcementPolicy` and
`InternationalTaxPolicy` returned **`abs()`**, eroding whichever direction happened
to match and magnifying the other. The magnification was not small: AMT booked 25%
more than its own static in both directions, corporate `reported` 12.5% more on a
rate **cut**, international 15%, PTC 13% on a repeal. Six were fixed with
`math.copysign` (and, in `credits_core.py`, by dropping an `abs`); no elasticity
value, base or growth rate changed.

**The contract's one exception is `TaxExpenditurePolicy`, and since PR #128 it
is settled per reform rather than per module.** An offset may legitimately carry
the *opposite* sign when a source says the behavioural response raises revenue —
a second channel, not a haircut on the first. **"One direction" was the defect,
not "which direction":** CBO's Option 49 puts four alternatives over the same
deductions in one table and its own 2022 discussion (`budget-options/58635`)
gives them **three different behavioural directions**, and CBO's charitable
option reverses its verdict for a *floor* design, because a taxpayer can bunch
gifts to clear a floor and a rate ceiling offers no such move. So
`TaxExpenditurePolicy` carries an `OffsetDirection` keyed on the **reform**
— `(expenditure type, action)`, each entry holding the source sentence that
establishes it — with `erode` the default and `magnify` only where a source says
the response **raises** revenue. The question is well posed here because JCT
states (JCX-48-24, report p. 12) that tax-expenditure calculations *do not*
incorporate behavioural change, so the offset is the whole behavioural
adjustment; and the itemisation margin is already inside the base, because JCT
counts a deduction only to the extent total itemised deductions exceed the
standard deduction (p. 4).

| Reform | Source | Direction |
|---|---|---|
| Cap employer health (and CBO Option 56) | CBO 60557 Option 56, report pp. 66–67: "revenues would also increase because fewer workers would enroll in employment-based coverage" | **magnify** |
| Cap charitable (28% benefit-rate ceiling) | CBO 58635 alt 3, the identical design: "an effect that would increase tax revenues" | **magnify** |
| Eliminate SALT deduction | CBO 58635 alt 2, this exact reform: "would further decrease their itemized deductions and increase their tax liability" | **magnify** |
| Repeal the SALT cap | the mirror of alt 2, priced by Yale Budget Lab — new itemisers then deduct mortgage interest, $323B → $497B | **magnify** |
| Eliminate the mortgage deduction | Poterba & Sinai, NBER WP 14253 §6.1 / Table 8: $72.4B with no behavioural response, $61.9B with portfolio adjustment, "about 85 percent" | **erode** — *flipped* |
| Eliminate step-up at death | CBO `budget-options/54792`: "heirs might choose to delay the sales … and thereby reduce their tax liability" | **erode** |
| Cap retirement contributions | CBO `2018/54799`: the Roth-conversion constraint "would reduce revenues by $6 billion" inside the window | **erode** |
| Eliminate like-kind exchanges | no source found | **erode** (default) |

**Four reforms magnify on a document, five erode, and exactly one scored row's
direction flipped**: `eliminate_mortgage`, −$330.4B → **−$270.3B**, 10.1% →
**9.9%**. It stays Acceptable, so no constant was retuned and no preset moved.
The price was pre-registered and paid in the leave-one-out suite —
`Expenditures` **35.7% → 37.5%**, the suite **29.6% → 30.1%** — because the old
−5.1% was two errors cancelling: the held-out annual is JCT's $25.0B against
the fitted $26.2B, a static path 4.5% low, and magnifying it by 10% put the
score 5.1% high. `CONVENTION_EXCEPTIONS` is now a set of **policies** rather
than class names — the whole of `TaxExpenditurePolicy` had been exempt, so the
contract said nothing about any reform that class could express — and
`test_no_whole_class_is_exempt_from_the_contract` fails if any class ever has
all its cases exempted again. The audit reads **14 correct, 1 convention, 1
zero**, against 13/1/1 at the branch point and 6 correct against 7 defects at
PR #119's.

**The magnitudes were unsourced on all five entries when this was written, and
Wave D's PR #157 sourced two of them.** The paragraph is corrected here rather
than deleted, because its own arithmetic turned out to be wrong. Mortgage repeal
moved **0.10 → 0.14502762**, which is `1 − 61.9/72.4` from Poterba & Sinai,
*Income Tax Provisions Affecting Owner-Occupied Housing* (NBER WP 14253, §6.1 and
Table 8) — the paper's own "about 85 percent", not the 15% quoted above. The
charitable benefit-rate ceiling moved **0.40 → 0.22077987**, and the route
matters: CRS R40518 supplies only a central **price elasticity of ε = 0.5**
(report p. 27; band 0.1 / 0.5 / 0.79), which is converted through the module's own
identity

```
e = c · Σ A_b · ε · (m_b − c)⁺ / (1 − m_b)  ÷  Σ A_b · (m_b − c)⁺
```

evaluated at `c = 0.28` on the existing SOI Table 2.1 charitable distribution,
**because a price elasticity and a share of a revenue effect are different
quantities**. The "something nearer 18%" above is **not reproducible**: at a 37%
marginal rate the factor is `c/(1 − m) = 0.28/0.63 = 0.4444` per unit of ε, so 18%
would require ε = 0.405, which CRS does not print. Read the 18% as an estimate
made in passing. Two findings came out of the conversion. The shipped 0.40
**inverts to ε = 0.906 — above CRS's own published high of 0.79 by 15% and above
its central 0.5 by 81%**. And **a magnitude is a property of the reform for a
second reason directions are**: tightening the ceiling 28% → 15% roughly halves
the share, **0.2208 → 0.1140**, because the recapture rate *is* the cap rate — so
a module-wide constant would have over-magnified CBO 60557 Option 49's 15%
alternative by 94%, and the shipped 0.40 by 251%. **Three magnitudes remain
unsourced with their searches recorded** — employer health 0.20, retirement 0.30,
SALT 0.05 — and `BEHAVIORAL_ELASTICITIES` keeps all five values as the documented
fallback. Employer health is the one that matters, since it is the only one of
the three sitting on an out-of-sample row (CBO Option 56, **12.8%**); the one
published elasticity near it prices employer *offer* rates by firm size (−0.07 at
1,000+ employees through −1.14 at the smallest), which is the channel Option 56's
own text ranks **below** plan switching, so the finding is that the available
elasticity is attached to the wrong half of the mechanism rather than that none
exists. **A sixth sign
defect turned up in the same pass, in a place neither end of the pipeline
looks.** `estimate_expenditure_revenue()`, a public helper the package exports,
aggregates in **revenue** space and returned `static + behavioral`, where the
offset it adds is the engine's **deficit**-space quantity — so it disagreed with
the engine before this lane and would have disagreed in the opposite direction
after it. The test covering it asserted `net_effect == static + offset`, a
tautology that passes under either sign. **A sign contract enforced at the two
ends of a pipeline says nothing about the middle of it.**

`tests/test_offset_sign_contract.py` enforces all of this: **92 tests, 86 passing
and 6 skipped**, probing ±$100B in both directions, plus
`test_every_offset_implementation_is_covered`,
which greps the package for `def estimate_behavioral_offset` and fails if a class
is missing from the case list — because "a module nobody swept" is how all four
previously-found defects got in. Note that `CapitalGainsPolicy` has no
function-level sign rule to probe: it ignores `static_effect` and rebuilds the
response bracket by bracket, so it is classified from the window instead, where it
erodes in both directions. And `IRSEnforcementPolicy` returns a static of exactly
0.0 for a funding cut, so its `abs()` was unreachable through its own constructor —
which is why the sign must be probed at the function and not only at the score. A
clamp is not a contract.

### ETI Values in the Literature

| Source | ETI Estimate | Context |
|--------|--------------|---------|
| Saez, Slemrod & Giertz (2012) | 0.25 | Preferred central estimate |
| Gruber & Saez (2002) | 0.40 | Upper bound from 1980s tax reform |
| CBO (2014) | 0.25 | Conventional scoring default |
| JCT | 0.25 | Revenue estimates |

**Default**: ETI = 0.25 (user-adjustable in policy definition)

### Capital Gains: Realizations Elasticity

**The response is to the tax rate, not to the net-of-tax rate.** The realization
literature reports an elasticity defined as the percentage change in
realizations over the percentage change in the *capital gains tax rate*, and the
functional form behind it is semi-log. CRS R48562, *Boundaries on the Long-Run
Realization Response to Changes in Capital Gains Taxes* (2025), states both
(pp. 1 and 13): `R = B·exp(−b·t)`, so `ε(t) = b·t`. The module therefore applies

```
R₁ = R₀ × exp(−b × (τ₁ − τ₀))        b = elasticity / reference rate
```

Until Wave 2 it applied `R₁ = R₀ × ((1−τ₁)/(1−τ₀))^ε` — an elasticity with
respect to the **net-of-tax** rate — using values the literature reports on the
**tax** rate. That understates the response by roughly `(1−τ)/τ`: at τ = 23.8% a
nominal ε = 0.8 is an effective tax-rate elasticity of **0.25**, a third of
anything in CRS's Table 4. The unit error, not a parameter choice, was most of
why every rate-change row over-predicted.

Two properties come free with the correct form and neither is a second
parameter. The implied elasticity `ε(τ) = b·τ` **rises with the rate**, so the
top bracket responds more than the 15% bracket to the same percentage-point
change. And there is a **revenue-maximizing rate**, `τ* = 1/b`.

**Frozen elasticity parameters.** One set for every scored case — the
`CapitalGainsPolicy` dataclass defaults, per owner Decision 3 of
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md). The
`scenarios.py` per-case behavioural tuples earlier revisions of this file
described no longer exist.

| Parameter | Value | Source |
|-----------|------:|--------|
| `persistent_elasticity` | 0.72 | Dowd, McClelland & Muthitacharoen (2015), *New Evidence on the Tax Elasticity of Capital Gains*, NTJ 68(3) |
| `transitory_elasticity` | 1.20 | same |
| `elasticity_reference_rate` | 0.22 | CRS R48562 Table 4 note — the tax rate its estimates are adjusted to |

That gives **b = 3.273** and **τ\* = 30.6%**. JCT's own working coefficient is
**3.1** (CRS R48562 p. 8, supplied by the committee) and Treasury's is 0.72 at
22%, the same as DMM's — agreement to within 6%, which is the cross-check that
this is a unit fix rather than a tuning knob. Agersnap & Zidar (2021) estimate a
much lower 0.3–0.5 and imply a higher τ\*; they are named in the docstring as
the alternative and are deliberately **not** used.

The transitory coefficient is a **retiming** response, so it applies in the
enactment year only, and only to the share of the base a taxpayer can choose
when to realize: net long-term gain (IRS SOI Table 1.4A), **87.7%** of the base
at threshold 0. Qualified dividends and capital-gain distributions have no
timing margin and do not get it.

**The base is IRS SOI Table 3.5.** Table 3.5 publishes, for every AGI class, the
income actually taxed at each preferential rate and the tax it generated, so a
rate change applies to each bracket's own price rather than to one blended
aggregate. At threshold 0, tax year 2023 (the §1411 NIIT surtax is added where
the AGI class lies above its threshold):

| Bracket | Realizations | Effective rate |
|---|--:|--:|
| 0% | $66.8B | 0.0% |
| 0% + NIIT | $13.9B | 3.8% |
| 15% | $81.1B | 15.0% |
| 15% + NIIT | $263.1B | 18.8% |
| 20% + NIIT | $682.6B | 23.8% |
| **Total** | **$1,107.7B** | |

**And it is projected across the window.** SOI reports a tax year; a ten-year
score prices ten later ones. Realizations are a flow off the accrued-gains stock
at the observed hazard — `R = h·A` — so the flow grows at the rate the stock
already grows at, **5.80%/yr**, the Federal Reserve Distributional Financial
Accounts' 1998–2024 net-worth CAGR (`realizations_projection_factor`). Holding it
flat instead would assert a hazard falling 5.8% a year, which is a behavioural
claim nobody made, and no new constant enters either way. The projection applies
only where the base's tax year is known: a caller who supplies
`baseline_realizations_billions` supplies an aggregate whose vintage this class
has no field for, so that base is used exactly as given.

**What the rate channel does not do.** There is no receipts lag — the enactment
year is scored at full strength against a fiscal year scorekeepers book at a
fraction of one, which is most of what is left on `cbo_opt47_ltcg_qdiv_2pp`. And
5.80% is a net-worth CAGR carried forward, not a realizations projection: CBO's
own baseline returns realizations toward a historical share of GDP, and tax year
2023 is a trough ($1,283.6B in 2022, $943.4B in 2023, $1,368.1B in 2024). The
level anchor is probably low and the growth possibly high, in opposite
directions, and neither is corrected.

### Step-Up Basis at Death

Under current law unrealized gains are forgiven at death, so holding until death
avoids the tax entirely.

**Lock-in is not a multiplier.** The `5.3×` and `2.0×`
`step_up_lock_in_multiplier` earlier revisions of this file described were
deleted in Wave 2, along with `no_step_up_avoidance_multiplier`. The wedge is
derived instead. A share `ω = m/(h+m)` of the accrued-gains stock leaves it at
death rather than by sale, where `h` is the observed realization hazard and `m`
the mortality-weighted death-exit rate, so those gains are never taxed while
step-up survives. The price of realizing now is `τ·(1 − (1−ω)·d)` with step-up
against `τ·(1 − d)` once death is a realization event, where `d` discounts the
deferral over the expected holding horizon `1/(h+m)`:

| Quantity | Value | Where from |
|---|--:|---|
| Realization hazard `h` | 2.35%/yr | SOI realizations over the DFA accrued-gains stock |
| Death exit rate `m` | 2.65%/yr | NCHS *United States Life Tables, 2022* (NVSR 74-02) Table 1 against DFA net worth by age of head |
| Escape share `ω` | 53% | `m/(h+m)` |
| Holding horizon | 20 years | `1/(h+m)` |
| `deferral_discount_rate` | 4% | module default |
| **Lock-in wedge** | **1.44×** | `CapitalGainsPolicy.lock_in_wedge()` |

DMM estimated their elasticity under current law, so the literature `b` is the
**with**-step-up value; eliminating step-up divides it by the wedge, and that
division is the whole difference between the with- and without-step-up scores.
Realizations that do not happen stay in the stock, which then supplies later
realizations and a larger flow of gains at death; that feedback is tracked as a
**ratio** to the baseline stock (`stock_ratio`), so the baseline's own growth
cancels and no growth rate enters the realizations flow.

#### The flow of gains transferred at death

The flat **$54B/yr** constant this section used to quote is gone as well.
Poterba & Weisbenner (2001) Table 8 report, from the 1998 Survey of Consumer
Finances, expected estates of $118.9B/yr and expected unrealized capital gains at
death of $42.8B — **36% of estate value** — on the convention that transfers to a
surviving spouse are not realization events. Both are carried as shares of
household net worth in the same year and grown with the Financial Accounts stock,
so the flow is indexed to the asset stock rather than frozen at a constant:
**$196.2B in 2025**, spread over **3,384,194 decedents**.

The count is **not** taken from that same flow, and since Wave C it no longer
can be. `estate_flow_rate` is a **dollar** ratio — expected estates over
household net worth — and using it as a *headcount* rate gave 408,532 decedents
a year against roughly 3.09 million NCHS deaths, while the same module has
priced the lock-in wedge and the accrued-gains stock's drift off
`death_exit_rate()` — `mortality_weighted_net_worth_share`, **2.647%/yr**, the
NCHS 2022 life table against Distributional Financial Accounts net worth by age
— since Wave 2. One module, two death rates **8.3× apart**. The count is now the
second of those. It is the right rate on *heads* as well as on dollars because of
the module's own gains distribution: gains are spread in proportion to
`households × wealth × gain share`, which asserts that dollars die at a uniform
rate across the distribution, so within a slice the headcount rate **is** the
dollar rate. **The level is untouched** — still $196.2097B in 2025 — so the count
enters only as a divisor, and gains at death by DFA group are identical to twelve
significant figures before and after.

**Grading the rate by estate size was measured and rejected, and the direction is
the reason.** The wealthy are older, so they die at a *higher* rate, not a lower
one: head-weighted **1.6456%**, net-worth-weighted **2.6468%** (the shipped
parameter), size-graded at the top of the distribution **2.8400%**. Grading takes
the implied count above $12.92M to 38,908 where the uniform swap takes it to
36,262 — both further from IRS SOI's 7,194 estate-tax returns above that
threshold, not nearer. The two rejected rates ship as regenerable **CHECK-ONLY**
parameters (`crude_adult_mortality_rate`, `size_graded_tail_mortality_rate`) that
the loader refuses to read, with a test that fails if their ordering ever
reverses.

#### What such a proposal actually reaches

Every published realization-at-death proposal states reliefs. The module prices
the ones that bite on a base measured as *unrealized gains*, in this order, and
the per-donor exclusion is applied **after** all of them, because both Green
Books grant it against *"other* unrealized capital gains" (FY2022 report
pp. 62–63; FY2025 pp. 80–81):

| Relief | How it is priced | Source |
|---|---|---|
| Charitable bequests | The charitable deduction over the gross estate net of spousal bequests, by size of estate: **36.20%** at $50M+, 12.03% ($20–50M), 6.20% ($10–20M), 4.30% below $10M, and zero below SOI's smallest printed class | IRS SOI *Estate Tax Statistics* Table 1, filing year 2024 |
| Family-owned-business deferral | The active-business share of unrealized gain (72.3% at $10M+, 0.6% at the bottom), recaptured inside the window at the module's own realization hazard, `1 − (1−h)^(t+1)` | PW Table 8; the election is stated by both Green Books |
| §121 principal residence | `min(residence gain, $250,000)` per decedent, on PW Table 8's residence share of unrealized gain (100.1% below $250K of net worth, 3.6% at $10M+) | 26 U.S.C. §121(b)(1) |
| Rate response at death | `exp(−b·Δτ)` with the **persistent** coefficient only, divided by the lock-in wedge | Death cannot be retimed, so the transitory term has no place here |
| Charitable substitution | Taxing gains at death makes a charitable bequest cheaper by `τ·g` per dollar given, so the share rises by `(1 − τ·g)^(−ε_c)`, `ε_c = 1.617` | Bakija, Gale & Slemrod (2003), NBER WP 9661, Table 1 spec (a) — the *smallest* magnitude in their own table; their (d) is 2.142 and Joulfaian (2000) reports 0.74 |

**Two of the six stated reliefs remove nothing, and deducting them would be the
error rather than the fix.** Poterba & Weisbenner's own Table 8 note settles it:
*"Bonds, vehicles, and collectibles are assumed to have no accrued capital
gains. … It is assumed a decedent transfers his/her full estate to a surviving
spouse. Such inter-spousal transfers are not included in the estate totals
reported above."* So the tangible-personal-property share is carried at **0.0**
with the quotation attached and the marital-bequest share (24.4–34.7% of the
gross estate by size class) is carried purely as a magnitude cross-check;
neither is ever applied.

Whether the family-business deferral applies is a **design** switch, not a
behavioural parameter, and `GREEN_BOOK_DEATH_DESIGN_RULE` in
`fiscal_model/validation/core.py` sets it from the documents: a Treasury Green
Book proposal carries the reliefs its own volume states, and a budget option
carries only what its own text describes. **CBO's Option 51 states none** — its
whole text is *"capital gains would be taxed as if the decedent had sold the
asset at death"* — so `defer_family_business_gains` is off by default and off for
that row. The carve-outs and behavioural channels above are *not* design
switches: a tax-exempt donee, a statutory §121 exclusion and a price response
are properties of any constructive-realization regime, so Option 51 gets them.

#### How big each estate is

Every one of those reliefs is a function of estate size, and all three published
ladders are step functions. Until Wave 7 the module evaluated them at **five
class means**, so seven of their eighteen published rows were never read by any
scored case — including the whole $1M–$5M band both Green Book per-donor
exclusions sit in — and a per-decedent exclusion applied to a group mean was
itself a step function, removing a whole class at once when it moved from $1M to
$5M.

`CapitalGainsBaseline.decedent_classes` now integrates over a **piecewise-Pareto
size distribution of net worth at death**, fitted so that each Distributional
Financial Accounts percentile group's own published aggregate is reproduced
exactly, with the published wealth breakpoints of all three ladders forced in as
quadrature edges and each bin represented by its analytic conditional mean
(`DECEDENT_SLICES_PER_REGION = 200`; a convergence test pins that doubling the
count moves the ten-year death channel by less than half a percent). The
open-ended top class takes the index of the class below it, the convention
`pareto_tail_index` already applies to SOI's open-ended top AGI class. **The
level is untouched** — still Poterba & Weisbenner's flow — and only the shape
changed.

| Region | α | Threshold |
|---|--:|---|
| `s ≤ 0.01` (top 1%) | 1.526 | $61.01M at the 99.9th percentile, $13.50M at the 99th |
| `0.01 < s ≤ 0.10` | 1.470 | $2.818M at the 90th |
| `0.10 < s ≤ 0.50` | 0.813 | **not integrated** |

**The fit refuses below the top decile and says so twice.** The third region's
index comes back below one — a Pareto with no finite mean, which is what "these
aggregates are not a tail" looks like in arithmetic — and the median it implies,
$389,500, is 2.02× the Survey of Consumer Finances' published 2022 figure of
$192,700. The two groups below the top decile therefore keep the group means they
always had, which holds the death channel down.

#### What is not modelled

- **The *level* of the flow is now the coarsest thing left in the channel, and it
  is half of the ratio Wave C corrected.** The headcount was the other half and
  is fixed (above). `gains_at_death_share_of_net_worth` is
  `estate_flow_rate × gain_share_of_estates` — the **same** Poterba & Weisbenner
  dollar flow — and held against the module's own `death_exit_rate` it implies
  **0.372% of the accrued-gains stock** where the stock's death exit is priced at
  **2.647%**, a factor of **7.1**. Some of that gap is real and sourced: PW's
  flow already excludes inter-spousal transfers, which is the convention every
  realization-at-death proposal uses and which removes most of a first death.
  Nobody has measured how much. It matters because it points the **other way**
  from the headcount fix — CBO Option 51 under-predicts at 35.5%, so a larger
  level would close what the count opened — and because it is a level nobody may
  change by implication.
- **The decedent universe is an open question and two of its three candidates
  score better than the one in use.** PW's flow measures **non-spousal** estates,
  a universe *smaller* than all deaths, while the shipped rate puts 3,384,194
  decedents against roughly 3.09 million NCHS deaths, 9.5% over. The crude adult
  life-table rate (1.6619%) gives 2,124,898 and the crude all-age rate (1.2910%)
  gives 1,650,702; they read Option 51 at 32.1% and 28.4% against the shipped
  35.5%. **They are recorded and deliberately not taken** — picking the best of
  three would be fitting a parameter to a benchmark. Deciding which universe PW's
  flow describes needs a document, not a preference.
- **The $1M → $5M exclusion step now overshoots Treasury's own figure.** It was
  $82.26B at five class means (Wave 4), $85.02B on the fitted size distribution
  (Wave 7) and is **$9.40B** on the corrected headcount, against Treasury's
  **$33.4B**. Wave 7 had predicted that *doubling* the count would land on it;
  the authorised constant multiplies it by 8.3. Note also that $33.4B was never a
  like-for-like comparator — Treasury's two published rows sit on different
  windows on different baselines.
- **The SOI headcount check needs a unit before it is a check.** SOI Table 1
  counts **individual** decedents whose **gross estate** clears a threshold; the
  model counts **households** whose net worth clears the same number, and a
  married household at $13M usually produces two estates of roughly $6.5M,
  neither of which files. So a model count above SOI's is the expected sign, and
  the implied 36,262 above $12.92M against SOI's 7,194 is partly that gap.
- **Dispersion was not the cause of the exclusion-step gap, and Wave 7 disproved
  the hypothesis it was built to test.** `max(0, gain − E)` is convex in the
  gain, so a mean-preserving spread *raises* the taxable excess: replacing the
  five means with the fitted distribution moved the $1M → $5M step **82.26 →
  85.02**, further from Treasury's own $33.4B rather than nearer.
- **The 15-year installment election** both Green Books state is not modelled; no
  share of it is separately measurable in PW Table 8, and it would move both
  Green Book rows down.
- **The estate-tax deduction** for the capital gains tax paid at death — stated
  by both Green Books *and* by Option 51 — is not modelled either. It is an
  estate-tax interaction rather than a capital-gains one, worth roughly a tenth
  of the channel on SOI's taxable returns.
- **No lock-in unwind.** Constructive realization at death removes the incentive
  to hold appreciated assets and so raises lifetime realizations; the module
  reaches that channel only through a coefficient a zero rate change leaves
  inert, which is why Option 51 gets none of it.
- **The death rate does not vary with wealth.** One mortality-weighted exit rate
  is applied across every wealth group.

---

## Dynamic Scoring

### When to Use Dynamic Scoring

CBO provides dynamic scores for major legislation (>0.25% of GDP) and at Congressional request. The calculator offers dynamic scoring as an option for all policies.

### Default engine vs. FRB/US comparison engine

The app ships **two** dynamic engines, and it matters which one the default "Dynamic scoring" toggle uses:

- **Default — `EconomicModel` (state-dependent, CBO-conventional).** The `dynamic=True` path on `FiscalPolicyScorer.score_policy` runs this engine. It uses normal-times multipliers of **1.0 (spending)** and **0.5 (tax)**, decomposes demand vs. supply effects, adds capital/labor channels, and raises the multipliers in recessions / at the zero lower bound (see [Spending Multipliers](#spending-multipliers)). All of its parameters are sourced from `constants.py`.
- **Comparison only — `FRBUSAdapterLite` (reduced-form FRB/US).** A separate reduced-form adapter implementing multiplier effects consistent with the Federal Reserve's FRB/US model (also used by the Yale Budget Lab), with **1.4 (spending)** and **0.7 (tax)** first-year multipliers and 0.75 annual decay. It is surfaced in the multi-model **Scoring Models** tab as a cross-check; it is *not* the default toggle.

The remainder of this section describes the FRB/US comparison engine; the default engine's parameters are detailed under [Spending Multipliers](#spending-multipliers) and [Uncertainty Analysis](#uncertainty-analysis).

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Fiscal Shock   │ ──▶ │   GDP Effect    │ ──▶ │    Feedback     │
│                 │     │                 │     │                 │
│ Tax cut or      │     │ Apply FRB/US    │     │ Revenue from    │
│ spending change │     │ multipliers     │     │ GDP + crowding  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Fiscal Multipliers (FRB/US comparison engine)

*These are the `FRBUSAdapterLite` parameters. The default dynamic engine uses the lower CBO-conventional normal-times values in [Spending Multipliers](#spending-multipliers).*

| Shock Type | Year 1 Multiplier | Decay Rate | Source |
|------------|------------------:|----------:|--------|
| Spending | 1.4 | 0.75/year | FRB/US |
| Tax Cut | 0.7 | 0.75/year | FRB/US |
| Tax Increase | −0.7 | 0.75/year | FRB/US |

Multiplier decay:
```
multiplier(t) = base_multiplier × decay_rate^(t-1)
# Spending multiplier: Year 1 = 1.40, Year 2 = 1.05, Year 3 = 0.79 ...
```

### GDP and Employment Effects

```python
# Annual GDP effect from fiscal shock
gdp_change_pct = (fiscal_shock_billions / baseline_gdp) * multiplier(t) * 100

# Employment via Okun's Law (coefficient = 0.5)
employment_change_pct = gdp_change_pct * 0.5
employment_change_millions = employment_change_pct * labor_force / 100  # ~165M
```

### Revenue Feedback and Crowding Out

```python
# Revenue feedback from GDP change
marginal_tax_rate = 0.25  # Combined federal revenue/GDP ratio
revenue_feedback_billions = gdp_change_billions * marginal_tax_rate

# Crowding out from cumulative deficit
crowding_out_rate = 0.15
interest_cost = cumulative_deficit * crowding_out_rate

# Net budget effect
net_effect = revenue_feedback - interest_cost
```

### Long-Run Production Function

```
%ΔGDP = labor_share × %ΔLabor + capital_share × %ΔCapital + ΔTFP
# labor_share = 0.65, capital_share = 0.35 (BLS)
```

### FRBUSAdapterLite Output Fields

| Field | Description | Units |
|-------|-------------|-------|
| `gdp_level_pct` | GDP change from baseline | % |
| `gdp_growth_ppts` | Change in growth rate | ppts |
| `employment_change_millions` | Employment change | millions |
| `unemployment_rate_ppts` | Unemployment rate change | ppts |
| `short_rate_ppts` | Federal funds rate change | ppts |
| `long_rate_ppts` | 10-year Treasury change | ppts |
| `revenue_feedback_billions` | Revenue from GDP | $B |
| `interest_cost_billions` | Higher interest costs | $B |
| `cumulative_gdp_effect` | Total GDP %-years over horizon | %-years |
| `cumulative_revenue_feedback` | Total revenue feedback | $B |
| `net_budget_effect` | Revenue feedback minus interest cost | $B |

---

## Distributional Analysis

The `DistributionalEngine` produces TPC/JCT-style tables by income group.

### Income Group Definitions

| Group Type | Brackets | Usage |
|------------|----------|-------|
| Quintile | 5 equal-population groups | Standard TPC |
| Decile | 10 groups | Detailed analysis |
| JCT Dollar | $10K increments | JCT-style tables |
| Custom | User-defined | Targeted analysis |

**2024 Quintile Thresholds** (TPC/Census data):
- Lowest: $0–$35,000
- Second: $35,000–$65,000
- Middle: $65,000–$105,000
- Fourth: $105,000–$170,000
- Top: $170,000+

### Distributional Metrics

For each income group:
1. **Average Tax Change** ($): Per-return dollar impact
2. **Tax Change as % of Income**: After-tax income impact
3. **Share of Total Change**: Group's portion of total revenue effect
4. **Winners/Losers**: Fraction with tax increase/decrease
5. **Effective Tax Rate Change**: Change in ETR (percentage points)

### Policy-Specific Handlers

| Policy Type | Distribution Logic |
|-------------|-------------------|
| `TaxPolicy` | Rate change × income above threshold |
| `TaxCreditPolicy` | Credit phase-in/phase-out by income |
| `TCJAExtensionPolicy` | TPC-based component distribution |
| `CorporateTaxPolicy` | 75/25 capital/labor incidence |
| `PayrollTaxPolicy` | Wage distribution up to SS cap |

### Corporate Tax Incidence

Following CBO/TPC assumptions:
- **75%** borne by capital owners (concentrated in top quintile)
- **25%** borne by workers (distributed with wage income)

Capital income shares by quintile (SCF data):
- Top quintile: 80%
- Fourth: 12%
- Middle: 5%
- Second: 2%
- Bottom: 1%

---

## Microsimulation Engine

The `MicroTaxCalculator` (`fiscal_model/microsim/engine.py`) is a vectorized, individual-level tax calculator that applies the full tax code to synthetic or actual taxpayer records. It captures interactions that aggregate bracket-level models miss: the SALT cap interaction with itemized deductions, AMT liability, EITC phase-in/phase-out, CTC phaseout, and NIIT.

### Inputs

The engine consumes a `DataFrame` with one row per tax unit:

| Column | Description |
|--------|-------------|
| `agi` | Adjusted gross income |
| `wages` | Wage and salary income |
| `married` | Filing status (bool) |
| `children` | Number of qualifying children |
| `weight` | CPS/IRS sampling weight |
| `age_head` | Age of the primary filer |
| `itemized_deductions` | Itemized deductions (before SALT cap) |
| `investment_income` | Investment income (for NIIT) |

### Outputs

The calculator returns per-unit estimates of:
- Regular tax liability (after brackets, standard/itemized deduction)
- AMT liability
- EITC credit
- CTC (refundable and non-refundable)
- NIIT surtax
- Final tax (regular or AMT, net of credits)
- Effective tax rate

### 2025 Parameters Built In

- Brackets: 10%, 12%, 22%, 24%, 32%, 35%, 37% (indexed for inflation)
- Standard deduction: $15,000 single / $30,000 MFJ
- SALT cap: $10,000 *(the microsim's own constant; see **SALT Cap** below — current law is $40,400 in 2026 with a phasedown, reverting to $10,000 in 2030, and reconciling the two is an open carry-over)*
- AMT exemption: $88,100 single / $137,000 MFJ
- CTC: $2,000 per child, phases out above $200K/$400K at 5 cents per dollar
- NIIT: 3.8% on net investment income above $200K/$250K

### State Extension

`FederalStateCalculator` (`fiscal_model/models/state/calculator.py`) layers state income tax on top of the federal calculation. State taxable income starts from federal AGI, with state-specific standard deductions and bracket schedules. SALT interactions are modeled at the federal level before state tax is applied.

---

## Corporate Tax

The `CorporateTaxPolicy` module scores changes to the statutory corporate rate, pass-through treatment, and related provisions.

### Rate Change Scoring

```
ΔRevenue = ΔRate × Corporate_Taxable_Income × (1 - behavioral_offset)
```

Behavioral offset follows the ETI framework with `corporate_elasticity = 0.25`.

### Pass-Through Effects

Pass-through income (S-corps, partnerships, sole proprietorships) is partially affected by corporate rate changes through competitive and structural channels. The model applies a partial pass-through adjustment factor when `include_passthrough_effects=True`.

### Book Minimum Tax (CAMT)

The 15% Corporate Alternative Minimum Tax (IRA 2022) is modeled as a separate tax on adjusted financial statement income for firms with >$1B in profits, with a carve-out for R&D credits.

### Which mode the app serves: `derived` since PR #166

`CorporateTaxPolicy` carries a module-local mode, like `TaxCreditPolicy` and
`AMTPolicy`. **`CORPORATE_APP_MODE` is `CORPORATE_MODE_DERIVED` since 2026-09-11**,
which is the first time Decision 1's comparison has moved a corporate default.

- **`reported`** prices a rate change against a **fitted** profits aggregate,
  `BASELINE_TAXABLE_PROFITS_BILLIONS = 1900.0`, self-documented as fitted and
  grown by the engine from the *policy's own* start year. A consequence worth
  knowing: **it returns the same answer whichever decade is asked about**, because
  shifting the window shifts the policy with it and the totals cancel exactly.
- **`derived`** prices it against **CBO's February 2024 corporate receipts path**
  (publication 59710 Table 1-1) times a **4.80133** base-$/receipts-$ ratio
  anchored on SOI TY2022 ÷ MTS FY2022, with a §6655 convolution for the
  fiscal-year phase. It is indexed by *fiscal* year, so FY2026–2035 is genuinely a
  different decade from FY2025–2034 and is worth **$18.30B** on a 21% → 28%
  reform.

**The flip was taken on a rule fixed in advance**, requiring **both** of these to
favour `derived`, with no tie-break and no re-weighting:

| Metric | `reported` | `derived` |
|---|---:|---:|
| Mean abs error over the three published corporate targets | 62.75% | **61.43%** |
| Position in the four-house estimator span at **+7pp** (−$1,349.9B to −$935.8B) | −$1,397.21B, **$47.27B outside**, larger than all four | **−$1,292.62B, inside** |
| Implied marginal share of the vintage's average base, +7pp | 82.29% | **76.13%** |

**Three qualifications belong with the default and the module docstring carries
all three.** (i) `derived` wins the mean **while losing two rows of three** — it
takes the FY2022 rate-only Green Book row by 12.19 points and gives up the FY2025
row by 0.31 and `trump_corporate_15` by 7.94; the row it wins is the only one
whose *scope* matches what the factory builds, and the row it loses by a whisker
is one `reported`'s constant is **fitted** to. (ii) **Neither mean is small**:
61.43% against 62.75% is a choice between two wrong answers taken on a stated
rule. (iii) **Nothing was retuned** — the fitted constant reads 1900.0 either
side, asserted by a test.

**CBO's published loss-firm haircut is transcribed and deliberately not applied.**
`dmyrevnfc = 0.85` and `dmyrevx = 0.80`
(`US-CBO/business-investment-model` @ `6cb4cea6`,
`source_code/Create_Tax_Data.prg:32-33`, derivation at `:21-27`) adjust a
**statutory rate** inside a user-cost-of-capital expression. This module
multiplies a **base** that is CBO receipts ÷ the statutory rate, and receipts are
what loss-making firms' zero tax already produces. CBO itself *divides the factor
back out* at `:172-175` where the other input carries it, **"to avoid
double-counting"**; the module's own SOI file measures those losses at
**8.69–11.58%** of the pre-NOL base (10.25% mean) against CBO's 12.81%. Note the
two constants are **nested, not a financial / non-financial pair**: 0.85 is
loss-making firms alone and 0.80 is that factor times the nonprofit share of
nonresidential investment. `fiscal_model/data_files/corporate/cbo_loss_firm_haircut.csv`
carries them with a computed applicability test so the refusal is checkable.

**Two channels are bounded and unpriced.** The §38(c) general-business-credit
carryforward stock is **$124.47B** (IRS Publication 5108, TY2022) against $72.17B
of claims, under a statutory cap of 75% of regular tax that *rises with the rate*
— the one channel CBO has put a mechanism in writing for (2018 Option 24) and the
one pointing the score *down*. The §904 foreign-tax-credit carryover is a labelled
**$78.02B residual**. Neither can be priced: SOI's excess-credit /
excess-limitation tables exist for **TY2010 only**. CAMT is blocked on a TY2023
Complete Report that does not exist yet.

### Calibration

The Biden corporate rate increase from 21% to 28% is calibrated to Treasury's
−$1.347T/10yr row (model: **−$1.293T, error 4.0%** in `derived`, the app default;
−$1.397T and 3.7% in `reported`). Read the 3.7%/4.0% as bookkeeping plus a scope
gap rather than as accuracy: from the FY2023 Green Book onward that row moves the
GILTI effective rate with the statutory rate, while the factory scored against it
sets `gilti_rate_change=0.0`.

---

## International Tax

The `InternationalTaxPolicy` module (`fiscal_model/international.py`) models GILTI, FDII, Pillar Two, and profit-shifting provisions.

### GILTI (Global Intangible Low-Taxed Income)

Under current post-TCJA law, GILTI is taxed at a 10.5% effective rate (50% deduction on the 21% statutory rate). Biden's proposal raises the GILTI rate to 21% and eliminates the per-country blending that allows cross-crediting of foreign taxes.

Key modeling parameters:
- Gross GILTI base: ~$250B/year
- Current GILTI revenue (after FTCs): ~$25B/year
- Country-by-country revenue multiplier: 1.20 (eliminates cross-crediting)
- FTC offset rate: ~40% of incremental revenue is offset by foreign tax credits
- Calibration: Treasury FY2025 Green Book, ~$280B/10yr

### FDII (Foreign-Derived Intangible Income)

FDII provides a 37.5% deduction on export-related intangible income, yielding a 13.125% effective rate. Repeal raises the effective rate to 21%, estimated at ~$200B/10yr (exact match to JCT estimate).

### Pillar Two Global Minimum Tax

The OECD Pillar Two framework imposes a 15% global minimum on large multinationals (>€750M revenue). The model uses:
- Carve-out fraction: ~60% of profits after substance carve-outs (OECD guidance)
- UTPR capture rate: ~50% of undertaxed profits
- Behavioral offset: 0.30 (lower than domestic, due to anti-avoidance rules)

### Profit Shifting

Following Clausing (2020), the model estimates ~$300B in shifted profits taxed at ~5% in havens. Anti-avoidance provisions recapture a fraction of this base.

---

## Estate Tax

The `EstateTaxPolicy` module models changes to the estate tax exemption, marginal rate, and step-up basis.

### Static Revenue Calculation

```
ΔRevenue = ΔRate × Taxable_Estates × Num_Taxable_Estates_per_Year
         - ΔExemption × Marginal_Rate × New_Taxable_Estates_Brought_In
```

### Exemption-Based Modeling

When the exemption changes (e.g., TCJA doubled it to ~$13M per person), the model estimates:
1. Estates previously above the old exemption that fall below the new one (freed)
2. The average taxable estate value for the marginal group
3. Behavioral response (portfolio reallocation, charitable giving)

### Behavioral Response

Estate planning elasticity varies with exemption level. At higher exemptions, fewer estates are affected and avoidance is less prevalent. The model uses a conservative offset (20% behavioral reduction) consistent with CBO estimates.

**Calibration**: Biden estate reform (Treasury ~−$450B/10yr) scores −$450B (~0% — window-average annuals, no growth/behavioral double-count; two-regime taxable-amount blend for bottom-up path).

---

## Payroll Tax and Social Security

The `PayrollTaxPolicy` module (`fiscal_model/payroll.py`) scores changes to the Social Security taxable wage cap, donut hole provisions, and Net Investment Income Tax (NIIT).

### SS Wage Cap Changes

The Social Security payroll tax applies to wages up to the annual cap ($168,600 in 2024). Scoring removes or adjusts this cap:

```
ΔRevenue = rate × (Wages_above_cap) × Num_Workers_above_cap
         × (1 - behavioral_offset)
         × (benefit_offset_fraction)
```

The benefit offset accounts for the fact that higher earnings generate higher Social Security benefit entitlements, partially offsetting the revenue gain. This is a key difference from ordinary income tax scoring.

### Donut Hole Provision

The "donut hole" exempts wages between the current cap ($168,600) and a higher threshold (e.g., $400,000), then reapplies the payroll tax above that threshold. Revenue is lower than full cap removal because high earners between the two thresholds are exempt.

### The two fitted Social Security targets — read this before quoting either

The $250K donut scores **-$2,700B** against a carried **-$2,700B**, and eliminating the cap scores **-$3,200B** against **-$3,200B**. Neither 0.0% is a measurement. `payroll.py`'s covered-wage bases *are* those targets run backwards through the statutory rate — `BASELINE_WAGE_DATA` says so in its own comments, `wages_above_cap_billions = 2_581.0  # 320 / 0.124` and `wages_250k_plus_billions = 2_177.0  # 270 / 0.124` — so the two rows report arithmetic.

**And the source attribution is wrong.** Both targets are credited to the Social Security Trustees. SSA's Office of the Chief Actuary does score both designs — **E2.1** (eliminate the taxable maximum, no benefit credit) and **E2.5** (12.4% above $250,000, no benefit credit), runs 415 and 418 on the 2025 Trustees Report's intermediate assumptions, dated 6 January 2026 — and publishes them **only** as a change in the long-range actuarial balance in percent of taxable payroll (**+2.55%** and **+2.50%**), a change in the 75th year's annual balance (+2.60% each), and a reserve-depletion date (2034 → **2059** and **2057**). The detailed single-year tables are percent-of-payroll and trust-fund ratio to 2100, with no dollar column. **There is no OCACT ten-year dollar figure for either provision**, so the round trillions are a conversion the cited source never performed. `-$2.7T` is a Peter G. Peterson Foundation explainer's sentence, verbatim; `-$3.2T` matches nothing OCACT or PGPF prints.

Published ten-year dollar scores for the same designs *do* exist and are **not** registered here: CBO's Option 62 alternative 2 puts the donut at **$1,426.8B over FY2025-2034**, 47% below the carried figure, and both CBO's annual path and OCACT's own income-rate path for that design **ramp** across the decade where the module stamps a flat $270B a year.

**The honest figures are the held-out ones**, from `python scripts/run_loo.py` — each case's own covered-wage anchor withheld and refitted from the other two anchors' Pareto slope: the donut returns **-$2,664.0B (1.3%)** and cap elimination **-$3,319.5B (3.7%)**. Both now print on the results surface beside the shipped number. Full provenance, with the provision text and the search: [`docs/VALIDATION.md`](VALIDATION.md#the-two-ocact-payroll-targets-said-out-loud).

### NIIT Expansion

The 3.8% Net Investment Income Tax expansion (applying NIIT to active pass-through income above $400K) is modeled using the IRS SOI distribution of pass-through income above the threshold.

---

## Alternative Minimum Tax

The `AMTPolicy` module (`fiscal_model/amt.py`) scores the individual AMT and the Corporate Alternative Minimum Tax (CAMT).

### Individual AMT

The individual AMT applies a parallel tax system using an alternative income measure (AMTI) with a flat rate (26%/28%) after a large exemption ($88,100 single in 2025). A taxpayer pays the higher of regular tax or AMT.

```
AMT_Liability = max(Regular_Tax, AMT_Rate × (AMTI - Exemption))
ΔRevenue_AMT = ΔExemption_or_Rate × (AMTI > Threshold) × Filers
```

TCJA dramatically reduced AMT exposure by doubling the exemption and adding a phaseout. Extending TCJA AMT relief versus reverting to pre-TCJA rules is calibrated to JCT estimates.

**Two modes.** `AMTPolicy.mode` selects between `reported` — the fitted annual,
which reproduces the carried benchmark by construction — and `derived`, a
year-indexed affected-payer and average-liability path read from **TPC Table
T25-0049** ("Aggregate Alternative Minimum Tax Projections, 2024–2035", April
2025), transcribed to `fiscal_model/data_files/amt/tpc_t25_0049_aggregate_amt.csv`
with the table's own footnotes. The baseline leg is evaluated at the current-law
exemption and the policy leg at the reform exemption; revenue and payers are each
interpolated between the two regime anchors and the average liability is their
ratio (interpolating the average separately is unsafe — the two are individually
monotone in the exemption but their product turns upward, so an exemption
*increase* prices as a revenue gain).

The TPC table's baseline is the law in place as of 1 January 2025, so it carries
the TCJA sunset: AMT payers go from **0.2M in 2025 to 7.6M in 2026** — a cliff,
not a ramp — and the post-sunset path then grows from **$71.6B in 2026 to
$124.2B in 2035**. The derived ten-year cost of extending TCJA AMT relief is
therefore **$855.3B**, above the flat identity's ~$73B/yr, and full repeal from
2026 is **$948.9B**.

**`reported` is the app default, and stayed there when the targets were
corrected.** Owner Decision 1's rule is that a module keeps its fitted mode
until its derived error beats its fitted error, and across the three AMT
benchmarks it does not: **22.3% reported against 54.2% derived**.

| Benchmark | Target | Reported (fitted) | Err | Derived (structural) | Err |
|---|--:|--:|--:|--:|--:|
| `extend_tcja_amt` | $1,357.1B | $450.5B | **−66.8%** | **$855.3B** | **−37.0%** |
| `repeal_individual_amt` | $450.0B | $450.5B | +0.1% | $948.9B | +110.9% |
| `repeal_corporate_amt` | $220.0B | $220.1B | +0.05% | $252.2B | +14.6% |
| **Mean abs** | | | **22.3%** | | **54.2%** |

Read the two rows on which derived loses before treating that mean as evidence
for the fitted path: both are targets a constant was fitted to, so their ~0% is bookkeeping,
and `repeal_corporate_amt`'s derived path is the flat base `loo.py`'s leakage
guard already flags. **The one AMT benchmark whose target no constant was fitted
to is the one derived wins**, by a factor of 1.8. `AMT_SCORECARD_MODE` also stays
`reported`; `derived` is the default in the held-out validation path.

Not modelled: the phase-out thresholds. `phase_out_threshold_change` is declared
and never read, and under the post-sunset schedule the phase-out is what claws
the exemption back from high-income filers — but it needs a published phase-out
path, which T25-0049 does not carry.

### Corporate AMT (CAMT)

The IRA 2022 established a 15% book minimum tax on adjusted financial statement income for corporations with >$1B in book profits. Scoring uses aggregate estimates from CBO (2022) of ~$35B/year in additional corporate minimum tax revenue.

**Calibration**: Repeal Corporate AMT estimated at +$220B/10yr (exact match to CBO).

---

## Tax Credits

The `TaxCreditPolicy` module (`fiscal_model/credits.py`) models the Child Tax Credit (CTC) and Earned Income Tax Credit (EITC), including phase-in, phaseout, refundability, and expansion scenarios.

### Child Tax Credit

```
CTC = min(credit_per_child × children, eligible_amount)
CTC_phaseout = max(0, CTC - phaseout_rate × max(0, AGI - phaseout_threshold))
```

**Key parameters (2025)**:
- $2,000 per child
- Phaseout: 5 cents per dollar above $200K (single) / $400K (MFJ)
- Refundable up to 15% of earnings above $2,500 (Additional CTC)

**Biden 2021 expansion** raised the credit to $3,000–$3,600 and made it fully refundable, calibrated to CBO's $1,600B/10yr estimate (model matches when the explicit annual is treated as a window average).

### The derived path — per-unit over CPS ASEC tax units (Wave 3, lane L3)

`TaxCreditPolicy` carries a module-local `mode`. In `reported` mode — the app
default, unchanged — it returns the fitted annual. In `derived` mode it builds
**two** parameter sets, the counterfactual schedule and the reform schedule, runs
`MicroTaxCalculator` over the CPS ASEC tax units under each, and takes the
**weighted difference in final tax liability**. That is the right quantity rather
than a gross credit total: it carries the non-refundable credit's tax limit and
the refundable leg's earnings phase-in, which is precisely what a
`Δcredit × units × participation` identity omits and why the old path understated
every expansion.

**The counterfactual moves with the law.** IRC §24's $2,000 reverts to $1,000
after 2025 (P.L. 115-97 §11022(b)), so a ten-year window opening in 2025 is
scored against current law for one year and the pre-TCJA regime for nine. Against
a fixed $2,000 baseline the ARP credit costs **$883B**; against the
counterfactual the statute specifies, **$1,528B**. That single point is worth
more than 40 percentage points on the held-out `biden_ctc_2021` case, and both
legs are pinned by `tests/test_credits_microdata.py`.

**`expand_qualifying_age`, `include_childless_adults` and `take_up_rate_change`
are read now.** They were dataclass fields no code path touched, because the old
identity had nowhere to put an eligibility expansion and the microdata carried
only an under-17 headcount. `make_fully_refundable` and `remove_phase_out`
reached unreachable flat constants and now score $85.5B/yr and $70.1B/yr over the
CPS units.

**Microdata provenance (owner Decision 4: fetch, never vendor).**
`scripts/fetch_cps_asec.py` downloads the March 2024 CPS ASEC public-use archive
(`asecpub24csv.zip`, 148,664,101 bytes, SHA-256
`cdb39cdac34bef99dd0940ab28e306f692404c2eea44d85dfd634214872a0a09`) into a cache
**outside the repository**, verifies the checksum and extracts `pppub24.csv` and
`hhpub24.csv`; `data_builder.py` then rebuilds `tax_microdata_2024.csv` with five
new dependent age-band columns (under 6, 6–16, 17, 18, and 19–23 enrolled in
school). Every one of the twenty pre-existing columns comes back **byte for
byte**, and the SOI calibration ratios (119% of returns, 81% of AGI) did not
move — which is what makes fetch-not-vendor safe: a future rebuild that changes
an old column is a bug, and now it is a visible one.

### Earned Income Tax Credit

The EITC is modeled by income quintile using IRS SOI data on the distribution of EITC recipients. Phase-in rates, maximum credits, and phaseout rates vary by filing status and number of children (Rev. Proc. 2023-34 §2.06, tax year 2024):

| Children | Phase-in Rate | Max Credit | Phaseout Rate |
|----------|-------------|----------|--------------|
| 0 | 7.65% | $632 | 7.65% |
| 1 | 34.0% | $4,213 | 15.98% |
| 2 | 40.0% | $6,960 | 21.06% |
| 3+ | 45.0% | $7,830 | 21.06% |

`microsim/engine.py` reads this schedule from `credits_core` rather than
duplicating it. Two defects closed with that change: the engine had applied a
single 21.06% phaseout rate to *every* child count, and carried a stale vintage
of the maxima. A third is arithmetically larger — the engine counted the EITC's
**qualifying children** with the CTC's under-17 column, where IRC §32(c)(3)
counts children under 19, or under 24 and a full-time student. On the rebuilt
file that is **79.7M against 65.0M**, a 23% undercount of the population the
credit is scaled on. Fixing it raises baseline EITC and moves no benchmark,
because every EITC-relevant reform is differenced against the same baseline.

---

## Tax Expenditures

The `TaxExpenditurePolicy` module (`fiscal_model/tax_expenditures.py`) scores changes to major itemized deductions and exclusions.

### SALT Cap

The TCJA capped the State and Local Tax (SALT) deduction at $10,000. **That is no
longer current law, and since PR #161 the module says so.** `SaltCapBaseline`
carries three named cap paths, transcribed from IRC §164(b)(6)–(7) as amended by
**P.L. 119-21 sec. 70120**:

| taxable year beginning in | limitation | MFS | phase-out threshold | MFS threshold |
|---|--:|--:|--:|--:|
| 2025 | $40,000 | $20,000 | $500,000 | $250,000 |
| 2026 | $40,400 | $20,200 | $505,000 | $252,500 |
| 2027 | $40,804 | $20,402 | $510,050 | $255,025 |
| 2028 | $41,212.04 | $20,606.02 | $515,150.50 | $257,575.25 |
| 2029 | $41,624.16 | $20,812.08 | $520,302.01 | $260,151.00 |
| 2030 and after | $10,000 | $5,000 | — | — |

2027–2029 are computed from the statute's own **101 percent** rule rather than
from a Revenue Procedure, because the 2027 adjustment is not yet published. The
phasedown of §164(b)(7)(B)–(C) reduces the cap by **30 percent of the excess** of
modified AGI over the threshold, with a floor at $10,000 ($5,000 MFS), and does
not apply to years beginning after 31 December 2029:

```
cap(y, magi) = max(10_000, L(y) − 0.30 × max(0, magi − T(y)))
```

It completes at MAGI of $600,000.00 (2025) rising to $625,715.87 (2029). Two
mechanism notes follow from the statute with no new constant: cap dollars are
nominal and indexed at **1%/yr** against SALT payments growing at the expenditure
record's own **3%/yr**, so the cap's bite widens every year of the window; and the
deductible amount above the cap is extrapolated by a **lognormal fitted per AGI
class to two published IRS SOI Table 2.1 columns** (`salt` and `salt_limited`),
with the phasedown read across a bounded-Pareto AGI distribution inside each
class. The anchor check is that at `C = $10,000` the fit returns the published
limited column by construction — **$25.020B** against the base table's own
`annual_cost = 25.0`.

**`CURRENT_LAW` is the app default; each benchmark scores the baseline its own
document was measured on.** `repeal_salt_cap` scores `PERMANENT_10K` (PWBM's
+$1,169.0B is priced against a permanent $10,000 cap) and `eliminate_salt` scores
`LAPSED_CAP` (CBO publication 60557 Option 49's −$1,621.0B is measured where the
cap lapses after 2025), declared in `scenarios.SALT_SCORING_BASELINES` in the
commit *before* the one that first scores them. **Neither benchmark moved**; the
shipped preset did, **+$1,155.6B → +$740.3B**, because the old figure repealed a
cap current law does not impose until 2030. An independent check the repository
already held: `pl119_21_salt_cap_40k` is JCX-35-25 line 20 at **+$946,209M**,
which is sec. 70120 measured against a lapsed cap — the new mechanism returns
**$723.1B, −23.6%** against it, and the largest named term in that gap is **new
itemisers**, since JCT puts SALT claimants at **11.8M → 17.8M returns** under the
$40,000 cap and SOI's TY2023 itemiser panel observes none of them.

*Two surfaces still hard-code the old cap and are a recorded carry-over rather
than a fix:* `microsim/engine.py` sets `self.salt_cap = 10000` and
`distribution_effects.py` reads `getattr(policy, "salt_cap", 10000)`, so a policy
object's revenue score and its distributional table currently disagree about what
year it is.

The model also scores:
- Changes in the cap level ($10K → unlimited, or $20K–$25K)
- Distributional effects (primarily concentrated in high-tax states, top quintiles)
- SALT cap interaction with AMT (the AMT historically limited SALT for high earners anyway)

**The uncapped SALT level is derived, not stored.**
`uncapped_salt_expenditure_billions()` returns
`load_deduction_distribution("salt").implied_benefit_billions` — IRS **SOI Table
2.1 TY2023**'s total (unlimited) state-and-local-tax deduction, priced AGI class
by AGI class at the IRC §1 married-joint schedule as adjusted for 2025
(Rev. Proc. 2024-40) — which gives **$89.55B/yr**. It replaced a stored
`annual_cost_no_cap = 120.0` that was **exactly the carried $1,200B benchmark
divided by ten**: unsourced, and load-bearing once lane L6 made the `eliminate`
rule read it. The check that the method is not made up is that the *identical*
computation on SOI's **limited** column returns **$25.0B** against the base
table's own `annual_cost = 25.0` — two numbers with no common ancestor agreeing
to a tenth of a percent. Both are pinned in
`tests/test_tax_expenditure_units.py`. Nothing fitted moved: every preset scores
in `reported` mode and returns the same annual.

*The `annual_cost_no_limit = 100.0` on the mortgage record has not had the same
treatment.* It names no statute, is still dead, and stays unread until somebody
sources it — wiring it in would move `eliminate_mortgage` from −5.1% to about
+244% on an unsourced constant.

### Employer-Sponsored Health Insurance Exclusion

The employer health insurance exclusion costs ~$200–250B/year in foregone revenue. Capping the exclusion at the 75th percentile premium level (c. $15,000/year) raises ~$450B/10yr (model: $450B, 0.1% error vs. JCT-calibrated estimates).

### Mortgage Interest Deduction

The MID is modeled by applying the deduction to the distribution of mortgage interest claimed by bracket, multiplied by the filer's marginal rate.

### Step-Up Basis

See [Step-Up Basis at Death](#step-up-basis-at-death) in the Behavioral Response section.

---

## Premium Tax Credits (ACA)

The `PremiumTaxCreditPolicy` module (`fiscal_model/ptc.py`) scores changes to Affordable Care Act premium subsidies.

ACA premium tax credits are income-adjusted subsidies that reduce the cost of marketplace health insurance for households with income between 100–400% of the federal poverty line (expanded to 600% under IRA 2022). The model:

1. Estimates the number of affected marketplace enrollees by income band using Kaiser Family Foundation/CMS data
2. Calculates the per-enrollee credit change from the policy
3. Applies a take-up adjustment for the fraction of newly eligible households that enroll

**Calibration**: Extension of enhanced PTCs (ARP + IRA) estimated at ~$220B/10yr.

### Repeal — CBO's own credit path, net of its own offsets (Wave 7, PR #131)

A **repeal** of §36B no longer scores off a fitted annual. Until Wave 7,
`create_repeal_ptc` carried `annual_revenue_change_billions = 83.0`, grown 4%/yr
by the engine — and 83.0 is `1100 / (1.10 × Σ 1.04ᵗ)`, the carried −$1,100B
target run backwards through that growth factor and the inverted offset PR #119
corrected. **A fitted number wearing a baseline's clothes, and it looked fine**:
$996.5B over the window against CBO's own $959B is 3.9%, invisible to any
ten-year error metric, while being **21% low in FY2026 and 21% high in FY2028**,
because a smooth 4% ramp cannot see the cliff the ARPA/IRA expiry puts in the
credit. A ten-year total is a weak test of a path, and the app shows the annual
profile, the distributional tables and the dynamic feedback off that same series.

The static effect is now the vintage's own published annual cost:

```
static(FY) = outlays_for_the_credit(FY, vintage) + revenue_reductions(FY, vintage)
```

read from `fiscal_model/data_files/ptc/cbo_premium_tax_credit_baseline.csv`, a
transcription of **CBO and JCT publication 51298 Table 2** ("Premium tax credits
and related spending", *both* legs) for two vintages — **June 2024** (FY2024–2034)
and **February 2026** (FY2026–2036), the default, matching `CBOBaseline`'s own.
An untranscribed vintage **raises** rather than falling back to another one's
numbers, which is `corporate.cbo_receipts_by_fiscal_year`'s rule; extrapolation
outside the tabulated years is deliberately asymmetric, holding the nearest
endpoint's level below the first year rather than extrapolating a policy cliff
backwards.

The behavioural leg is CBO's own published net-to-gross, from its letter to
Chairmen Arrington and Smith (**publication 60437**, 24 June 2024, report p. 3):
$335B net against a $415B gross increase in the credit's cost, so

```
CBO_OFFSETTING_SHARE = 1 − 335/415 = 0.192771
```

**19.28% of any §36B change never reaches the deficit**, and the ratio's
denominator is exactly what Table 2 prints, which is why the two documents
compose. The module's two unsourced knobs (`adverse_selection_factor = 0.1`,
`coverage_elasticity`) are switched off on this path and left in place for every
other one — the 10% was in the wrong *place* as well as the wrong size, since
CBO's itemisation carries no premium-spiral line at all: the offset is $101B of
compensation shifting into taxable wages plus $3B of employer penalties against
$21B of Medicaid and CHIP, $17B of Basic Health Program and §1332 waivers and
−$13B of other outlays. **There is no CBO score of a full repeal**, and the
transfer — from an *extension of the enhancement* to a *repeal of the whole
credit*, in the opposite direction — is stated in the constant's own docstring
and in the row's `known_limitations`, along with the letter's footnote 4 as a
2.4pp sensitivity.

`repeal_ptc` moves **−$896.9B → −$774.1B**, 18.5% → **29.6%** against the
unchanged −$1,100B target: a **pre-registered regression**, whose whole $326B is
three published steps (the target understates its own source by $43B; vintage
and window are worth $184B; CBO's offset share against the unsourced 10% is
worth $185B). The **Repeal ACA Premium Credits** preset moves with it, with a
Decision 6 caption computed from the scored result.

**Wave D's lane H11 (2026-09-11) replaced that single transferred ratio with the
composition CBO itemises**, and the argument is that a ratio is the wrong
*object* rather than the wrong size: the effects it aggregates are responses to
**people** moving between sources of coverage, so they scale with person-years,
while the gross scales with dollars. Each of 60437's lines is now divided by the
coverage movement it is a response of — **$2,971.43** per employment-based
person-year (the $101B of compensation shifting plus $3B of penalties over a
3.5M decline), **$4,200** per Medicaid/CHIP person-year, **$57.97** per
marketplace person-year for the Basic Health Program, §1332 waivers and other
outlays, and **$0** for a person who becomes uninsured — and applied to the
scored vintage's own subsidized marketplace enrolment from publication **51298
Table 1**, which also replaces `MARKETPLACE_DATA`'s uncited "19 million lose
coverage" with CBO's **13.4M in 2026, 11.06M on average over FY2026-2035**.
Handed 60437's own coverage vector the rates return its own **$79B**, which is
the identity check and not a fit.

The resulting share is **12.32%**, not 19.28%, and the whole of the difference is
one line of arithmetic CBO prints both halves of: a repeal's average enrollee
holds an **$8,671** credit where the extension's marginal enrollee holds the
**$5,370** of 60437 Table 3. `repeal_ptc` moves −$774.1B → **−$840.8B**,
29.6% → **23.6%**, with no constant retuned and the target unmoved, and the
preset moves with it under an extended Decision 6 caption. Two asymmetries are
**measured and deliberately not shipped**, because both move the row toward the
−$1,100B this repository refuses as a baseline projection: 60437 Table 3 puts
3.5M of the 6.9M marginal enrollees above 400% FPL against an employment-based
decline of 3.5M, so on a vintage where the enhancement has lapsed that channel's
population is absent (zeroing it gives −$996.3B, 9.4%); and 42 U.S.C.
§18051(d)(3) ties Basic Health Program funding to 95% of the credit, so a
repeal zeroes it rather than reversing +$17B. Both are in
`DestinationSplit`'s docstring and the row's `known_limitations`. See
`planning/lanes/HSD_h11_ptc_coverage.md`.

---

## TCJA Extension

The `TCJAExtensionPolicy` module (`fiscal_model/tcja.py`) scores extension or expiration of the Tax Cuts and Jobs Act (2017), which expires after 2025.

### Component Breakdown

| Component | 10-year Cost (extend) | Notes |
|-----------|----------------------|-------|
| Rate cuts (income brackets) | ~$1,200B | Lower rates at all brackets |
| Standard deduction increase | ~$800B | $15K/$30K vs ~$8K/$16K pre-TCJA |
| SALT cap ($10K) | −$1,900B | Saves revenue (relative to no cap) |
| AMT relief | ~$800B | Higher exemption, fewer filers |
| Estate tax exemption | ~$350B | $13M+ vs ~$7M without TCJA |
| Pass-through deduction (199A) | ~$600B | 20% deduction on qualified income |
| CTC expansion ($2K, no SALT interaction) | ~$750B | Broader eligibility |
| Other | ~$180B | Various smaller provisions |

Full extension calibrated to CBO's $4,600B/10yr estimate (model: $4,582B, 0.4% error).

### SALT Interaction

The SALT cap is politically contentious and modeled separately:
- `keep_salt_cap=True`: Full extension at $4.6T
- `keep_salt_cap=False`: Full extension without SALT cap (+$1.9T, totaling ~$6.5T)

---

## Tariff and Trade Policy

The `TariffPolicy` module (`fiscal_model/trade.py`) models revenue from new tariffs, consumer price effects, trade retaliation, and import volume responses.

### Revenue Model — net, not gross (Wave 3, lane L8)

**The headline a tariff produces is net of the offsets CBO, JCT and Treasury
apply to any indirect tax.** Until Wave 3 the module returned gross customs duty
with a flat 5% avoidance haircut and stopped, which is not a budget effect. The
scored chain is now:

```
Δτ      = stated rate − duty already collected on the base
p       = border_pass_through × Δτ                       (pass-through frozen at 1.00)
V       = 1 + ε·p                                        for p ≤ 0.30
        = 1 + ε(0.30) + (p − 0.30)·ε·2                   above it, floored at 0.20
gross   = Import_Base × V × Δτ/(1 + Δτ)                  tax-inclusive rate
avoid   = avoidance_rate × gross
offset  = income_payroll_offset_rate × (gross − avoid)
retal   = MARGINAL_REVENUE_RATE × [retaliation_rate × Δτ × export_base]
net     = gross − avoid − offset − retal
```

One value per mechanism, cited, applied to every tariff policy; nothing is keyed
to a benchmark id.

| Parameter | Value | Source |
|---|---:|---|
| Border pass-through to duty-inclusive import prices | **1.00** | Amiti, Redding & Weinstein (2019); Fajgelbaum, Goldberg, Kennedy & Khandelwal (2020) — the duty-inclusive US import price rose one-for-one and foreign export prices did not fall |
| Import-demand elasticity | **−0.997** | Ghodsi, Grübler & Stehrer (2016), the binding US weighted average adopted by Tax Foundation FF861 p. 4; USITC pub. 5405 finds ≈−1 in year one |
| High-rate elasticity multiplier above 30pp | **2.0** | Boehm, Levchenko & Pandalai-Nayar (2023): −0.76 in year 1 converging to −1.75/−2.25 within 7-10 years |
| Duty avoidance / evasion | **0.05** | Module default; FF861 uses 8% noncompliance, so this is the conservative end |
| **Income-and-payroll offset** | **JCT's published year path, 0.244 (2025) → 0.241 (2035); window mean 0.2442 on the validation window and 0.2439 on the app's** | **CBO's own tariff model** (`US-CBO/conventional-tariff-analysis-model` @ `59ea68fd`, `inputs/offset/2025OffsetPostHR1.csv`), which ships JCT's percentages and applies them multiplicatively once per year at `code/model/add_offset.py:18`. It replaced a round **0.25** cited only secondhand. *(As cited before PR #164:)* The longstanding CBO/JCT/OTA convention: duty paid is income not paid to labour and capital, so the income and payroll bases shrink. FF861 p. 4 nn. 3 and 11 cite JCT **JCX-59-11** and **JCX-9-24**; Tax Foundation's own calculator gives 26.2% over this window, and the round 25% is used rather than 26.2% precisely because 26.2% is an output fitted to one of the benchmarks |
| Retaliation intensity | **0.30** | Module default |
| Federal receipts per dollar of lost export income | **0.25** | `constants.MARGINAL_REVENUE_RATE`, the app's own convention |

*(Before PR #164:)* `jct.gov` and `cbo.gov` both return HTTP 403 to this
environment, so the offset convention was cited **secondhand** through Tax
Foundation FF861 — already this repository's transcribed benchmark source for the
universal-tariff row — which states the convention and names both JCT documents
for it. **Since PR #164 the primary is in hand**: CBO publishes JCT's own
percentages inside its conventional tariff-analysis model, so the parameter is a
published *path* rather than a round number. FF861's own **26.2%** was recorded as
an `external_check` and deliberately **not** adopted, because it is Tax
Foundation's model output for this window and adopting it would move a parameter
toward a benchmark; JCT's path is neither.

**Why a year path can be read exactly through a year-blind call.**
`scoring_engine.py:341` calls `estimate_behavioral_offset(revenue[idx])` with no
year, and `TariffPolicy` is in no growth handler and has no `soi_base_tax_year`,
so **the tariff gross is flat across the window** — and for a flat gross the
window mean is not an approximation but an identity,
`Σ_t g·(1−o_t) = n·g·(1−ō)`. The module therefore carries the whole path and reads
the mean over its own `[start_year, start_year + duration_years)`. A test asserts
the identity rather than the docstring claiming it. It would become an
approximation for a **phased** tariff, which is a carry-over rather than a
silence, as is CBO's own calendar-to-fiscal conversion
(`FY_y = CY_{y−1}·0.2976 + CY_y·0.7024`), which this module has no concept of.

**Sign convention.** `estimate_behavioral_offset` carries the static effect's
sign, per this document's own rule for a behavioural offset. It used to return an
unsigned positive number, which the scorer added to `−static_revenue`: right for
a tariff increase and exactly wrong for a tariff **cut**, where a 5pp cut on a
$1,000B base scored $711B of deficit against a gross revenue loss of $553B. The
same cut now scores $394B — eroded, as it should be.

### The retaliation export base

`estimate_retaliation_cost` used to multiply `retaliation_rate × rate ×
$2,100B` — *total* US exports — for every policy, which implied retaliation
losses larger than the whole tariff base for a $50B steel tariff. `TariffPolicy`
now carries `retaliation_export_base_billions`: US goods exports **to the
targeted country** where the policy names one, and total goods exports scaled by
the affected import share otherwise.

### Non-Linear Import Response

Above a 30% tariff rate, substitution accelerates (elasticity doubles). A floor
ensures imports never fall below 20% of baseline. Note that with the elasticity
roughly doubled the `min_volume_factor = 0.20` floor now binds above about 55pp
where it previously bound only above 95pp; it is an unsourced constant doing more
work than it used to.

### Consumer Price Pass-Through (display, not score)

The **retail** pass-through is a different object from the border pass-through
above, and a lower number. The household-cost display uses 60% (Cavallo et al.
2021); the score's import-demand response uses the near-complete border
pass-through of 1.00.

```
Household_Cost = Tariff_Rate × Import_Base × pass_through_rate / us_households
```

The model reports per-household consumer cost by income quintile (lower-income households spend a larger share of income on imported goods).

### Country-Specific Modeling

Every level below is a **2024 Census measurement**
(`fiscal_model/data_files/trade/tariff_scoring_inputs.csv`, USA Trade Online /
Census API, retrieved 2026-09-02): general imports at customs value
(`GEN_VAL_YR`), effective duty rates as calculated duty over imports for
consumption (`CAL_DUT_YR / CON_VAL_YR`, which includes the Section 232 and 301
duties actually collected), exports as `ALL_VAL_YR`.

| Quantity | Value | Constant it replaced |
|---|---:|---|
| US goods imports, 2024 | **$3,263.9B** | 3,200.0 |
| US goods exports, 2024 | **$2,063.0B** | 2,100.0 |
| Average duty collected, all imports | **2.36%** | 0.03 |
| Imports from China | **$440.3B** | 430.0 |
| Duty collected on China imports | **10.93%** | 0.20 |
| US goods exports to China | **$143.3B** | *(new)* |
| ⇒ universal-tariff coverage, 1 − USMCA share | **0.7197** | `universal_coverage_rate` 0.70 (**was fitted**) |
| HS-87 vehicles and parts imports | **$384.9B** | 380.0 |
| HS-87 imports from Canada + Mexico, share | **48.42%** | `auto_usmca_exempt_share` 0.65 |
| **Section 232 steel base, primary list, ex auto parts (1,167 HS-10 lines)** | **$96.75B** at 4.64% | *(lane R8)* |
| **Section 232 steel base, derivative annex, content-weighted `0.75·108.755 + 0.25·164.141`** | **$122.60B** at 3.87% | *(lane R8)* |
| **⇒ Section 232 steel total** | **$219.35B** | HS-72+76 "floor" $58.9B / +HS-73 "ceiling" $107.6B (**both wrong**) |
| **Section 232 autos, less the USMCA US-content carve-out** | **$214.28B** at 1.37% | *(lane R8)* |
| **Section 232 auto parts** | **$340.67B** at 2.18% | *(lane R8)* |
| **⇒ Section 232 auto total** | **$554.95B** at 1.84% | HS-87 × (1 − 48.42%) = $198.5B |
| *(superseded)* HS-72 + HS-76 imports | *$58.9B* | 50.0 |
| *(superseded)* Duty collected on HS-72 + HS-76 | *3.06%* | *(the Section 232 netting)* |
| *(superseded)* HS-73 derivative articles (lane H8) | *$49.5B* | *(lane H8's declared ceiling)* |
| *(superseded)* Duty collected on HS-73 | *5.63%* | *(its own rate, not blended)* |
| — | — | `china_effective_coverage` 0.50 **deleted** |
| — | — | `reciprocal_coverage_rate` 0.50 **deleted** (lane H8) |

**No constant in `TRADE_BASELINE` is fitted to a benchmark, and since lane H8
none of them is a shape assumption either.** `china_effective_coverage` was
replaced by the incremental-rate identity a 60% China tariff actually implies —
60pp *minus the duty already collected*, applied to the whole base, not 40pp
applied to half of it — and `create_trump_china_60`'s per-case
`import_elasticity=-0.7` override was deleted with it. `reciprocal_coverage_rate
= 0.50` — "a flat 20pp on half of goods imports", which nobody proposed — is now
a partner-by-partner schedule built from Executive Order 14257's own formula
(bilateral goods deficit over goods imports from that partner, halved, floored
at 10%) applied to Census 2024, with the Annex II sectors removed partner by
partner and the USMCA partners out. It reproduces all sixteen published Annex I
rates within 0.80pp, and those rates ride in the same CSV marked
`external_check` where the loader refuses to read them
(`fiscal_model/data_files/trade/reciprocal_schedule.csv`,
`scripts/build_reciprocal_schedule.py`).

### The three columns a tariff has

Published tariff estimates print three figures for one policy, and since lane
H8 so does this module. Tax Foundation FF861 on a 10% universal tariff:
**$2,171.1B conventional, $1,721.0B dynamic, $1,443.0B dynamic with
retaliation**.

* **Conventional — the scored number.** Gross customs duty at the tax-inclusive
  rate after the import-demand response, less duty avoidance and the 25%
  income-and-payroll offset, and nothing else. That is exactly `0.95 × 0.75 =
  **0.7125** of gross` for every tariff in either direction, against the 0.738
  FF861's own Table 2, Table 3 and p. 4 imply. **Retaliation used to be
  subtracted here and no longer is**: a conventional estimate does not net
  foreign retaliation, and every published figure this module is checked
  against is a conventional one, so netting it made the model a different
  object from its own benchmark.
* **GDP feedback — reported, not scored.** The tariff's own price and volume
  effect, `border_pass_through × Δτ × base × V`, run through
  `FRBUSAdapterLite`. That impulse is *larger* than the receipts collected —
  $211.5B/yr against $125.9B/yr for the universal preset — because households
  pay `Δτ` on every dollar that still arrives while the Treasury collects
  `Δτ/(1+Δτ)`, and the goods that stop arriving cost surplus and raise no duty.
  No macro constant lives in `trade.py`; the multiplier, decay, crowding-out and
  monetary-offset terms are all the adapter's.
* **Retaliation — reported, not scored.** Unchanged in construction: an
  export-value loss converted at the app's marginal revenue rate, **$111.4B**
  over ten years for the 10% universal tariff against FF861's **$278B**. An
  export-value loss is not an income loss, and the channel carries no multiplier
  and no supply-chain effect.

`get_trade_summary()` returns all three, and the Decision 6 caption under a
tariff headline names them.

**A denominator warning.** The knowledge snapshot's "40-50% of gross" divides by
gross customs revenue *before* the import-demand response; `net_to_gross_ratio`
divides by gross *after* it. On the snapshot's own denominator the universal
preset reads **0.589 conventional and 0.485 dynamic-with-retaliation** — inside
the band, not above it. Comparing the two ratios directly is a category error,
and it is the reason the repository spent a wave believing the missing channel
was worth about ten times what it is.

**What is left open**: the Section 232 derivative annex at HS-10 and a
steel-content share (whole-chapter HS-73 is an upper bound on what the statute
reaches, and HS-72 + HS-76 the floor); the Annex II exemption list below HS-4;
the retaliation channel's reduced form; and wiring the tariff impulse into
`EconomicModel`, which is what `score_policy(dynamic=True)` actually calls.

---

## IRS Enforcement

The `IRSEnforcementPolicy` module (`fiscal_model/enforcement.py`) models the revenue return from increased IRS enforcement investment.

### Revenue Multiplier Model

Unlike tax rate changes, enforcement spending yields a multiplied return by closing the tax gap rather than changing statutory rates.

```
Annual_Revenue = Enforcement_Spending × base_roi
               × diminishing_returns_factor^(n_years)
               × (1 + voluntary_compliance_boost)
               × phase_in_factor(t)
```

**Key parameters:**
- Base ROI: $5 revenue per $1 spent (first-dollar yield)
- Diminishing returns: 85% — each additional $1B yields 85% of the prior dollar
- Voluntary compliance boost: 15% (deterrence effect)
- Ramp-up: 3 years to reach full audit capacity (hiring and training)

### Tax Gap Context

- Annual gross tax gap: ~$600B (IRS 2022)
- Net tax gap (after enforcement and late payments): ~$440B
- Audit rate for returns >$1M: 2% in 2022 (vs. 16% in 2010)
- High-income and large partnership audits yield the highest per-return revenue

### Calibration

- IRA 2022 enforcement funding ($80B/10yr): ~$200B net revenue (CBO 2022) — model matches
- Doubling enforcement beyond IRA: ~$340B (Treasury 2021/Sarin-Summers, diminishing returns)

---

## Drug Pricing and Pharmaceutical Policy

The `PharmaPricingPolicy` module (`fiscal_model/pharma.py`) scores budget savings from pharmaceutical pricing reforms, primarily through Medicare.

### Medicare Drug Negotiation

The IRA 2022 authorized CMS to negotiate prices for high-spend Medicare Part D and Part B drugs. The model estimates savings as:

```
Savings = Current_Medicare_Spending_per_Drug
        × (1 - negotiated_price_ratio)
        × eligible_drugs_count
        × additional_drug_productivity_factor
```

The `additional_drug_productivity_factor` (0.6) captures that drugs negotiated beyond the first 20 in the IRA generate 60% as much savings per drug (smaller market share and less price room to negotiate).

**Calibration**: IRA negotiation (~$237B/10yr, CBO 2022). Extended negotiation scenarios scaled from this base.

### Part D Redesign

The IRA 2022 also redesigned Part D cost-sharing, capping out-of-pocket costs at $2,000 and shifting more liability to drug manufacturers (catastrophic coverage phase). The model estimates net budget impact from these transfers.

### Insulin Cap

A $35/month insulin cap is a **cost-sharing** cap: it moves a patient's liability
onto the plan, and the federal budget picks up only its share of that shift. The
module scores that share, not the retail-minus-cap differential:

```
Federal effect = ASPE Part D out-of-pocket relief ($734M/yr, 2020)
                 × Medicare's basic-benefit subsidy share (74.5%, statutory)
               + private-market cost shift
                 × marginal income-plus-payroll offset on premiums (32%)
```

Every input is transcribed with document, page and URL to
`fiscal_model/data_files/pharma/drug_pricing_incidence.csv` (HHS ASPE, *Report
on the Affordability of Insulin*; MedPAC, *Report to the Congress: Medicare
Payment Policy*; CBO budget option 58627). The result is a **deficit increase**
of about +$7B over ten years, which agrees in sign with CBO's own score of a
private-market cap — publication 57957 (H.R. 6833) puts it at +$6.566B of
outlays and −$4.793B of revenues, about **+$11.4B**. Not modelled: induced
utilisation, and growth in insulin cost and enrolment across the window (ASPE's
$734M is a single 2020 figure held flat).

*Prior specification, corrected 2026-09-01:* the module booked the whole
`($6,000 − $420) × 8.4M` retail differential as a federal outlay reduction, and
extending the cap to private insurance *raised* the modelled federal saving 2.5×.

### International Reference Pricing

Referencing Medicare drug prices to an international benchmark is scored on a
**net-price, brand-only, federal-share** basis. US unbranded generics are
*cheaper* than the OECD comparison (67% of comparison-country prices) and cannot
contribute savings, so only brand molecules are referenced; and the price ratio
applied is RAND's **net** brand ratio of **3.08** — US brand-name originator
prices at 422% of 33 OECD comparison countries before rebates, less a 37.2%
gross-to-net adjustment (RAND RR-A788-3 / ASPE, *International Prescription Drug
Price Comparisons: Estimates Using 2022 Data*, February 2024). The base is Part D
gross spending net of the 23% manufacturer-rebate share and restricted to the
80% brand share, plus Part B drug spending, each times the federal share of its
program.

*Prior specification, corrected 2026-09-01:* RAND's **gross list-price** all-drug
ratio (2.56) was applied to a **net** Part B + D base with no rebate adjustment
and no brand/generic split.

**Known limitation, unrepaired.** RAND's index is computed on presentations sold
in both markets, and the module applies it to all brand spending; no utilisation,
launch-delay or availability response is modelled on either this row or the
insulin row.

---

## State-Level Modeling

The state-level module (`fiscal_model/models/state/`) computes combined federal + state effective tax rates for the top 10 states by population and income.

### Architecture

```
FederalStateCalculator
    ├── MicroTaxCalculator (federal)        # Full federal tax calculation
    └── StateTaxDatabase → StateTaxProfile  # State rates, deductions, exemptions
```

### State Tax Calculation

State taxable income typically conforms to federal AGI, with state-specific adjustments:

```
State_Taxable_Income = Federal_AGI
                     - State_Standard_Deduction
                     - Personal_Exemptions
                     + State_Add-backs (e.g., bonus depreciation in some states)
```

State income tax is calculated separately using the state bracket schedule and credits, then combined with federal tax for an effective combined rate.

### SALT Interaction

The TCJA SALT cap ($10,000) constrains the federal deductibility of state taxes, making high-state-tax residents effectively double-taxed on state taxes above the cap. The model explicitly computes this interaction:
- At $10,000 cap: High-income taxpayers in CA, NY, NJ, CT, IL face higher effective combined rates
- Without SALT cap: Federal deductibility reduces the after-federal-tax cost of state taxes

### Coverage and Limitations

- **10 states covered**: CA, NY, TX, FL, IL, PA, OH, GA, NC, WA
- **Local taxes**: Not modeled for NYC, Philadelphia, and similar cities; flagged as a caveat
- **State conformity**: Approximated; states differ on bonus depreciation, pension exclusions, and other itemized deductions
- **Synthetic population**: Uses IRS bracket-level data to approximate the population, not a true microsimulation of state returns

---

## Overlapping Generations Model

The `OLGModel` (`fiscal_model/models/olg.py`) is a 30-period Auerbach-Kotlikoff-style model that analyzes the long-run and intergenerational distribution of fiscal policy.

### Production Function

```
Y_t = A_t × K_t^α × L_t^(1-α)
```

Where α = 0.35 (capital share), A_t grows at 1.5%/year (TFP), and L_t grows at 0.7%/year.

Factor prices are set by marginal products:
```
w_t = (1-α) × Y_t / L_t        # Wage per worker
r_t = α × Y_t / K_t - δ        # Net return on capital (δ = 5% depreciation)
```

### Capital Accumulation

```
K_{t+1} = (1-δ)K_t + s × Y_t - G_t
```

Government borrowing (G_t) directly crowds out private capital. The model calibrates to a K/Y ratio of ~3.0 and an initial GDP of ~$29T (2025).

### Generational Accounts

The lifetime fiscal burden for a cohort born in year b:

```
GA_b = Σ_{a=0}^{T-1} [τ_w × w_{b+a} + τ_k × r_{b+a} × (K/L)_{b+a}
                       - SS_{b+a}] / (1+ρ)^a
```

Where τ_w = 0.25 (labor tax rate), τ_k = 0.20 (capital tax rate), SS = Social Security replacement (40% of wages), and ρ = 0.03 (individual discount rate). The sum runs over working years (40) plus retirement years (20).

### Crowding Out

Each dollar of additional government debt is estimated to crowd out ~$0.33 of private capital (CBO), reducing wages for future workers:
```
crowding_out_effect = (debt / GDP) × 0.33 × 100   # % of GDP
```

### Use Cases

The OLG model is used to analyze:
- Social Security reform (payroll tax changes, benefit cuts, retirement age)
- Long-horizon effects of deficit-financed tax cuts (TCJA extension)
- Generational redistribution in Medicare reform

**References**: Diamond (1965), Auerbach, Gokhale & Kotlikoff (1991), CBO (2023) Long-Term Budget Outlook.

---

## Spending Multipliers

### Budget authority → outlays (spend-out)

A spending proposal states **budget authority**; a budget score reports
**outlays**. `SpendingPolicy` keeps the two distinct and converts between them
with a lagged convolution:

```
outlays_t = Σ_k s_k · BA_{t−k}
```

`s` is a first-year/out-year profile keyed by **account class** — the thing that
governs how fast an obligation becomes a disbursement. Pay and benefits disburse
at once; construction and capital take years.

| Account class | What it covers | s₀ | Σs | 10-yr outlay/authority on a level path |
|---|---|--:|--:|--:|
| `personnel_and_benefits` | pay, allowances, medical-care enrolment | 0.921 | 1.000 | 0.991 |
| `mandatory_benefit` | direct benefit payments, outlaid when owed | 0.977 | 1.000 | 0.998 |
| `operations_and_support` | agency operations, O&M, force structure, across-the-board caps | 0.539 | 0.977 | 0.893 |
| `grants_and_procurement` | project and formula grants, student aid, foreign assistance, procurement, R&D | 0.405 | 1.000 | 0.848 |
| `construction_and_capital` | construction, infrastructure and other capital grants | 0.022 | 0.973 | 0.663 |

**Provenance.** The profiles are fitted by non-negative least squares on the
14 options in CBO, *Options for Reducing the Deficit: 2025 to 2034*
([publication 60557](https://www.cbo.gov/publication/60557)) that publish both a
budget-authority row and an outlays row **and are not scored by the validation
battery**; the five that are scored never donate to any profile, and option 44 is
excluded because its outlays exceed its authority in every year. Class assignment
is a classification from the predominant account type each program funds, never
a fit. OMB Circular A-11 publishes no numeric outlay-rate table (see
[VALIDATION_NOTES.md](VALIDATION_NOTES.md) §5a); CBO's account-level spendout
rates (publications 61913 and 62256) are the open external cross-check.

The window truncates the **tail, not the head**: authority whose outlays fall
past the projection end is dropped — the truncation official 10-year totals
embed — while a policy that began before the window still spends its earlier
authority into it. `immediate` (the identity, `s₀ = 1`) remains available as an
explicit choice and is the default for nothing.

### State-Dependent Multipliers

Fiscal multipliers vary with economic conditions:

| Condition | Spending Multiplier | Tax Multiplier |
|-----------|--------------------:|---------------:|
| Normal | 1.0 | 0.5 |
| Recession | 1.5–2.0 | 0.8–1.0 |
| At Zero Lower Bound | 2.0+ | 1.0+ |
| Overheating | 0.5 | 0.3 |

**Sources**: Auerbach & Gorodnichenko (2012) for state-dependent multipliers; Christiano, Eichenbaum & Rebelo (2011) for ZLB amplification; Blanchard & Leigh (2013) for fiscal consolidation evidence.

### Multiplier Decay

```python
year_effect = spending × multiplier × (decay_rate ** years_since_start)
# decay_rate = 0.7/year (standard multiplier decay)
```

---

## Uncertainty Analysis

### Sources of Uncertainty

1. **Baseline Uncertainty**: Economic projections diverge from actual outcomes
2. **Behavioral Uncertainty**: ETI estimates range 0.15–0.50 across the literature
3. **Dynamic Uncertainty**: Macro model predictions diverge significantly
4. **Data Uncertainty**: IRS data is typically 2 years lagged

### Uncertainty Ranges

```python
base_uncertainty = 0.10 + 0.02 × years_out  # Grows with horizon

policy_factor = 1.2 if tax_policy else 0.8  # Taxes more uncertain
dynamic_factor = 1.5 if dynamic else 1.0    # Dynamic adds uncertainty

total_uncertainty = base × policy_factor × dynamic_factor

low_estimate  = central × (1 - total_uncertainty × 0.9)
high_estimate = central × (1 + total_uncertainty × 1.1)  # Asymmetric: costs skew higher
```

---

## Comparison to Official Methods

### vs. CBO

| Feature | CBO | This Model |
|---------|-----|------------|
| Static scoring | ✅ | ✅ |
| ETI behavioral (0.25) | ✅ | ✅ |
| Dynamic macro (FRB/US) | ✅ on request | ✅ FRBUSAdapterLite |
| GDP and employment effects | ✅ | ✅ |
| Revenue feedback | ✅ | ✅ |
| Crowding out | ✅ | ✅ |
| 10-year window | ✅ | ✅ |
| Uncertainty ranges | ✅ | ✅ |
| Return-level microsimulation | ✅ (proprietary) | Bracket-level + synthetic |

### vs. JCT (Joint Committee on Taxation)

JCT is the official congressional scorer for tax legislation, using IRS SOI microdata with proprietary behavioral models.

| Feature | JCT | This Model |
|---------|-----|------------|
| Return-level microsimulation | ✅ | Bracket-level + synthetic |
| Distributional tables | ✅ | ✅ |
| Corporate model | ✅ | ✅ |
| International (GILTI/FDII/Pillar Two) | ✅ | ✅ |
| Public methodology | Partial | ✅ |

### vs. TPC (Tax Policy Center)

| Feature | TPC | This Model |
|---------|-----|------------|
| Microsimulation | ✅ | Bracket-level + synthetic |
| Distributional tables (quintile/decile) | ✅ | ✅ |
| Winners/losers | ✅ | ✅ |
| TCJA component breakdown | ✅ | ✅ |
| Public methodology | ✅ | ✅ |

**Distributional validation** is benchmarked against **seven published CBO/JCT
tables**, not against TPC alone. Mean absolute share errors span **0.00pp to
5.86pp** (`python scripts/run_validation_dashboard.py`; full table in
[VALIDATION.md](VALIDATION.md)). Two of the seven are **circular** and must not be
counted as skill: `distribution_effects.calculate_tcja_effect` builds its decile
tiers *out of* CBO 54796 and CBO 60007, so the 0.00pp against the first and the
0.74pp against the second are bookkeeping — and since Wave 4 the suite also
records that those two rows are scored on a population CBO does not use, because
`TCJAExtensionPolicy` has no microsim path and falls back `household→tax_unit`.
The five non-circular tables run 2.10pp (JCT JCX-68-17) to 5.86pp (JCT JCX-4-24,
SALT-cap repeal). **The ARP row rose 4.76pp → 7.77pp in Wave 3 and then fell to
3.72pp in Wave 4, and both moves are the honest number.** Wave 3 put the
Recovery Rebate on return-level data alongside the CTC and EITC, and the old
4.76 had been ranking one of the three components by IRS return counts and the
other two by CPS tax units, so two universes were partly cancelling; scored
consistently, the gap showed its real size. **Wave 4 then closed it by scoring
the row on the universe its source ranks.** `DistributionalEngine` gained CBO's
own household universe — size-adjusted household income before transfers and
taxes, quintiles containing equal numbers of *people* — and each benchmark is now
registered on the universe its source uses, with the surfaces reporting the
universe **scored** rather than the one registered. The bottom quintile's share
goes 53.4% → **28.6%** against CBO's 34.0%. The tax-unit-versus-household
universe is the open item.

### vs. Penn Wharton Budget Model (PWBM)

| Feature | PWBM | This Model |
|---------|------|------------|
| OLG generational model | ✅ | ✅ |
| 30+ year horizon | ✅ | ✅ (80-year OLG simulation) |
| Generational accounts | ✅ | ✅ |
| Dynamic scoring | ✅ | ✅ FRB/US-calibrated |
| GDP and employment | ✅ | ✅ |
| Crowding out | ✅ | ✅ |
| Full GE microsimulation | ✅ | Reduced-form |

### vs. Yale Budget Lab

| Feature | Yale | This Model |
|---------|------|------------|
| Dynamic macro (FRB/US) | ✅ | ✅ FRBUSAdapterLite |
| GDP and employment effects | ✅ | ✅ |
| Revenue feedback and crowding out | ✅ | ✅ |
| Tax microsimulation | ✅ | Bracket-level + synthetic |
| Distributional analysis | ✅ | ✅ |
| Capital gains realization (semi-log, rate-dependent ε) | ✅ | ✅ |
| Trade/tariff policy | ✅ | ✅ |
| International tax (GILTI, Pillar Two) | ✅ | ✅ |
| Drug pricing | Partial | ✅ |
| State-level modeling | Partial | ✅ (top 10 states) |
| Public methodology | ✅ | ✅ |

### Known Limitations

1. **Bracket-level microsimulation**: Uses IRS bracket aggregates rather than return-level data; CPS-based individual simulation is a planned upgrade
2. **Simplified corporate pass-through**: Pass-through income distribution not fully modeled at the return level
3. **State modeling approximate**: Top 10 states only; synthetic population rather than state-level microsimulation; local taxes (NYC, Philadelphia) not included
4. **Reduced-form dynamic scoring**: FRBUSAdapterLite uses calibrated multipliers rather than structural general-equilibrium equations
5. **Data lag**: IRS SOI data lags ~2 years (currently Tax Year 2023)

---

## Validation Results

Benchmarks fall into **four** epistemically different tiers, plus a separate
distributional number. We report them separately because conflating calibration
with prediction overstates the model's predictive power, and there is **no single
“validated within X%” figure for this model**. Every number below reproduces live
via `python scripts/cold_holdout.py`, `python scripts/run_loo.py` and
`python scripts/run_validation_dashboard.py`; see [`docs/VALIDATION.md`](VALIDATION.md)
for the full matrix.

### Tier 1 — Out-of-sample predictions (uncalibrated, bottom-up from IRS SOI)

No fitting to the official target — the genuine test of predictive accuracy.
Every case is pre-registered in `fiscal_model/validation/preregistered.py`, in a
commit that lands *before* the commit that first scores it.

| Policy | Official | Model | Error | Source |
|--------|---------:|------:|------:|--------|
| Cut international affairs 25% | −$187B | −$187B | 0% | CBO Options 2025–2034 #37 |
| Cut selected nondefense discretionary | −$339B | −$333B | 2% | CBO Options 2025–2034 #42 |
| 1pp all brackets | −$960B | −$920B | 4% | JCT |
| 5pp top rate ($1M+) | −$700B | −$648B | 7% | TPC |
| New 1% payroll tax (all earnings) | −$1,282B | −$1,378B | 8% | CBO Options 2025–2034 #61 |
| Biden top rate 39.6% ($400K+) | −$246B | −$223B | 9% | Treasury (Green Book FY2025) |
| Social Security Fairness Act, WEP/GPO repeal | +$196B | +$215B | 10% | CBO |
| LTCG + qualified dividends +2pp | −$103B | −$93B | 10% | CBO Options 2025–2034 #47 |
| Fiscal Responsibility Act 2023, discretionary caps | −$1,332B | −$1,170B | 12% | CBO |
| Treasury 39.6% + step-up repeal (`.v2`, scored on its own FY2022–2031) | −$322B | −$381B | 18% | Treasury (Green Book FY2022) |
| IIJA 2021, discretionary component | +$415B | +$340B | 18% | CBO |
| Tax accrued gains at death | −$536B | −$428B | 20% | CBO Options 2025–2034 #51 |
| All ordinary rates +1pp | −$1,185B | −$920B | 22% | CBO Options 2025–2034 #45 |
| Biden capital income at ordinary rates | −$289B | −$383B | 33% | Treasury (Green Book FY2025) |
| CBO Option 46 alternative 2 (AGI surtax +2pp, $100K) | −$1,051B | −$658B | 37% | CBO Options 2025–2034 #46 |
| Corporate rate +1pp | −$136B | −$196B | 45% | CBO Options 2025–2034 #64 (a **JCT** estimate) |
| CBO Option 46 alternative 1 (AGI surtax +1pp, $20K) | −$1,440B | −$723B | 50% | CBO Options 2025–2034 #46 |

**26 pre-registered cases, mean absolute error 15.0% (median 10.6%); 17 of 26
within 15%, 22 of 26 within 25%** (`scripts/cold_holdout.py`; full table in
[VALIDATION.md](VALIDATION.md)). Do **not** collapse this into one tolerance.
Ordinary-bracket and AGI-inclusive rate changes at conventional thresholds land
at **1.5–22.4%**; discretionary funding changes, now scored through the
budget-authority-to-outlay spend-out model described above, land at **0–11%**
for the five CBO Options rows and **10–18%** for the three enacted-law
components; the tier's one tax-expenditure cap, CBO Option 56, lands at **13%**
since Wave 4 gave its excess share CBO's own chained-CPI indexation, and what is
left of that row is half a base omission (CBO caps premiums *and* FSA/HRA/HSA
contributions; the repository's premium distribution has no account dimension)
and about a fifth a behavioral offset whose **direction** is sourced and whose
**magnitude** is not — PR #119 cited the direction to CBO Option 56's own text
and PR #128 then settled it per reform across all nine, leaving the five
elasticity values unsourced and two of them with a published figure beside them;
**filing-status thresholds are no longer a cause**, because PR #127 built the
split off IRS SOI Table 1.2 — the four rows whose sources state a per-status
boundary now carry one, two improving (**12.4%** and **9.2%**) and two getting
worse (**37.4%** and **49.8%**), all four exactly as pre-registered, and what
is left on the two Option 46 rows is an AGI-vs-taxable base and a base frozen at
tax year 2023, worth 20 and 36 points and both measured; and a new broad payroll
tax lands at **7.5–8.1%** since Wave 5
priced its base as earnings — CBO's own wage path times the Trustees'
covered-earnings ratio — instead of Medicare receipts divided by a 2.9% rate
that does not raise all of them. **The gains-at-death group moved in Wave 4 and
the capital-gains rate channel moved in Wave 5.** Wave 4 gave the death channel
the six carve-outs a realization-at-death proposal does not tax — spousal,
charitable, the §121 residence exclusion, tangible personal property, a
family-business deferral and the per-donor exclusion applied *after* the others —
plus a semi-log rate response at death: the two step-up-elimination rows went
**218% → 0.2%** and **135% → 17%**, and gains at death itself went **8% → 19%,
worse and pre-registered as a regression**, because its 8% had been bought by
taxing charitable bequests and small decedents' housing gains that no such
regime reaches. **That 0.2% was never accuracy**: its own lane recorded it as two
errors cancelling, one of which was a realizations base frozen at IRS SOI tax
year 2023 and priced unchanged in every year of the window. Wave 5 projected
that base with the accrued-gains stock it is a flow off, so **Option 47 fell
45% → 10.5%** while the two Green Book rows crossed their targets to
**43%** and **31%** — both registered in advance as regressions. **Wave 7 then
closed both of the questions that left open, and neither closed the way the
record predicted.** The FY2022 row is now scored on FY2022–2031, the decade its
own document covers, under the manifest's supersede rule (`.v2`,
`scoring_window_first_year=2022`, target unchanged) — and **the window offset is
28.7 of its 43.3 points, not the "about 17" this file used to state**, because
the old figure discounted only the rate channel where the death channel grows
too and does not grow proportionally. The row reads **18%** on merged main
rather than the memo's 14.6%, because the decedent lane landed in the same wave;
and even 18% is a net of $60.0B under across FY2022–24 against $106.4B over
across FY2025–31, so the accounting artefact is gone and a shape disagreement is
what is left. The **five-class decedent ladder is gone too**, replaced by a
piecewise-Pareto size distribution fitted to the Distributional Financial
Accounts' own group aggregates — and it **disproved the hypothesis it was built
to test**: `max(0, gain − E)` is convex, so a mean-preserving spread *raises*
the taxable excess, and the $1M → $5M step went 82.26 → **85.02**, the wrong
way. What moves that step is the decedent **headcount**, which was Poterba &
Weisbenner's dollar flow of estates used as a headcount rate: 408,532 decedents
against roughly 3.09 million NCHS deaths. **Wave C (PR #151) took it, and neither
of Wave 7's two quantitative hand-offs survived.** The count is now
`death_exit_rate()`'s own 2.647%/yr — **3,384,194** decedents, the level
untouched — and Option 51 went **20% → 35%** as a registered regression, the
FY2025 Green Book row **33% → 27%** and the FY2022 row **18% → 2%**. Wave 7 had
said *about twice* the count would reproduce Treasury's $1M → $5M step of
$33.4B; 8.3× the count takes that step to **$9.40B**, through Treasury's figure
and out the other side. And it had said to *start at the top*, where the implied
count was short by 1.6× against SOI's 7,194; grading the mortality rate by estate
size runs the **wrong way**, because the wealthy are older and so die at a higher
rate (2.8400% at the top against the uniform 2.6468%), taking the implied top
count to 38,908 rather than toward 7,194 — and the SOI comparison needs a unit
before it is a comparison, since SOI counts individual decedents over a gross
estate and the model counts households over net worth. **Read the FY2022 row's
2% as half of a correction**: the count and the level come from the same PW
ratio, only the count moved, and the level that flow implies is **7.1×** below
the module's own death-exit rate. What is left of the
behavioral tail runs **44.5%** (corporate margins, down from 62.3% since PR #121
projected the base off CBO's own receipts path), **35.5%** (CBO Option 51's gains
at death), **31.8%** (the Medicare surcharge) and **27.0%** (the FY2025 Green
Book capital-gains row). The two CBO Option 46 AGI surtaxes, which led this list
until Wave B, read **7.4%** and **−2.9%** once the generic base grew on the
scored vintage and the AGI-stated rows started reading SOI's AGI column.
**Capital gains is no longer the tier's largest error mass** — 4 cases carrying
74.8 of the tier's **376.1** units (19.9%), against 82.0 of 383.3 (21.4%) after
Wave B, 104.5 of 395.1 (26.4%) after Wave 6, 405.6 of 805.8 (50.3%) before Wave 4
and 80.9 of 468.1 (17.3%) after it.
The two AGI-surtax rows lead at **87.2 (22.3%)**, the eight ordinary and
AGI-inclusive bracket rows carry 84.9 (21.7%), the eight spend-out rows 63.4
(16.2%), the three module identities at the margin 60.1 (15.4%) — corporate
alone 44.5 — and the one tax-expenditure cap 13.1 (3.4%). The two payroll rows,
the largest mass after Wave 4 at 109.6, are 15.6 (4.0%).

#### The scoring window is a shape input, and moving it goes through the manifest

A source publishes its total over a stated decade, and Tier 1's default window is
FY2025–2034. Where those differ, `CBOScore.scoring_window_first_year` (PR #126)
scores the case on **its own** decade — and setting it is a **supersede, not an
edit**: ledger entry in one commit, first scoring in the next, `.v1` kept with
`superseded_by`, the target unchanged. **Two rows carry a `.v2` on this rule**:
`iija_2021_discretionary.v2`, whose shape input moved to CBO's own authorization
schedule, and `treasury_capgains_39_plus_stepup_elim.v2`, scored on **FY2022–2031**
because that is the decade Treasury's FY2022 Green Book row covers. Two design
details are pinned by tests — the field moves the **scorer's window and the
policy's start together** (moving only the window truncates the head; the Warren
row would read exactly 6/10 of itself), and `effective_start_year` keeps
precedence where a record sets one.

**What these rows needed is a window, not a vintage.**
`CapitalGainsPolicy.estimate_static_revenue_effect` opens with
`_ = baseline_revenue` and neither FY2022 row reads a baseline *level*, so the
"the repository has no 2021 vintage" line both notes used to carry names a
blocker that was never the binding one — a vintage would have cost an enum
member, an assumptions block, base levels, the app's vintage picker, the
`baseline=` share-link contract and the classroom frozen-link refusal path, and
moved neither row. **The measurement is a re-score, not a discount**, which is
what made the offset measurable: 28.7 of the Treasury row's 43.3 points, against
the "about 17" earlier revisions of this file quoted, because that figure
discounted the rate channel only. The **control** is `biden_capital_gains_39` —
same shape, module and frozen elasticities on an FY2025 target and window —
whose offset is **exactly zero to the cent**. `scripts/window_offset_capgains.py`
prints the decomposition. The same mechanism would take
`iija_2021_discretionary` from 18.2% to **0.3%**; that is a second target
decision with its own `.v3` row and is deliberately left to the owner, with the
number published so the choice is not silently selective.

#### A baseline correction behind the numbers that moved no score

`CBOBaseline`'s corporate receipts line was `base_individual_income_tax × 0.18`
— 18% of the latest IRS SOI *tax year* on file, times a flat historical ratio,
neither term taking a vintage — grown at real GDP growth plus inflation plus an
unsourced 1pp "corporate profits grow faster than GDP" premium, compounding to
**4.88%/yr**. CBO's own February 2024 corporate receipts grow at **1.21%/yr**
over FY2025–2034 and *fall* in FY2026 and FY2027, for reasons its narrative
states. Under `use_real_data=True`, the app's default, all three vintages
therefore started from **$386.62B to the cent**, while `use_real_data=False`
returned three vintage-specific figures — the two modes disagreeing by 8.6% on
February 2026 and 35.5% on January 2025, with the mode named "real data" the one
with no vintage in it. PR #130 made February 2024 **be** CBO publication 59710
Table 1-1 (reproducing its ten printed values exactly), gave the other two
vintages their own base year from one shared map, and added
`CORPORATE_RECEIPTS_SOURCING` grading all three `published_path` /
`published_base_level` / `vintage_estimate`, so a line this module reconstructed
cannot be reported as CBO's. **No validation benchmark reads the series** — the
battery is built on `CBO_FEB_2024` with `baseline_profits_billions` at its
default — so every scored number is byte-identical. What moved is the baseline
the app reports *about* the projection: Ask's ten-year deficit
**$30,020.7B → $29,529.1B**, end-of-window debt/GDP **104.8% → 103.8%**. The
deficit moves further than the revenue does because of the interest feedback —
$433.3B of revenue against $491.6B of deficit, the $58.3B being interest not
paid on debt not issued. **The same override is still live on the individual,
payroll, other-revenue and spending series**, and `other_revenues` is
byte-identical across all three vintages for all ten years — the same defect
with no growth-rule variation to hide it. Closing it needs each vintage's own
published tables, and cbo.gov returns HTTP 403 to this environment.

The mean moved from Phase B's 43.4% on 23 cases to 52.6% on 25 while the median
*fell* from 23.1% to 21.1%: `top_rate_45` was retired in Phase E (its −$420B target
appears in no TPC, CBO or JCT publication), `biden_capital_gains_39` was re-sourced
to the FY2025 Green Book's actual line item and got *worse* (79% → 142%), and three
enacted-law components joined — one of them IIJA at **356%**, which was kept
deliberately as the sharpest available evidence for a missing mechanism.
**Wave 1 then built that mechanism** (2026-09-01/02): the spend-out model took
the mean to 45.3%, and superseding IIJA's shape input with the authorization
schedule CBO's own estimate states — a new manifest row, `.v1` → `.v2`, target
unchanged — took it to 34.4%, with within-15 rising 8 → 12. No tax row moved
and no target was edited. **Wave 2 (2026-09-02, PR #95) then did the same for
capital gains** and the mean fell to **31.3%**, the median to **14.1%** and
within-15 rose to **13**: the realizations base became IRS SOI Table 3.5's
bracket-priced income, the elasticity became the semi-log tax-rate form CRS
R48562 defines, the 5.3× lock-in multiplier became a derived 1.44× price wedge,
and the $54B gains-at-death constant became a decedent-wealth stock. Two rows
improved sharply, one barely moved and one got worse; no target was edited and
no per-case constant survives.

**Wave 3 (2026-09-02, PR #100) added a case rather than moving one.** CBO Option
56 had been excluded for *leakage* — the only expressible path ran through a
tax-expenditure annual fitted to that same reform — and lane L6 removed the
dependency, so a percentile cap is now the published expenditure level times a
share read off a premium distribution. It enters at **−$529.9B against
−$697.0B, 24.0%**, and no existing row moved by a cent: the mean falls to
**31.0%** because the new row is below it, and the median *rises* to **15.1%**
because the new row sits just above the old midpoint. The CI gate was
re-derived by the workflow's own rule to `--max-mean-error 40
--min-within-25pct 18` (PR #102).

**Wave 4 (2026-09-05, PRs #105, #107, #108) took the tier 31.0% → 18.0%**, the
median to **12.6%**, within-15 to **14** and within-25 to **21**, on five rows.
PR #108 did almost all of it, by building the death channel's statutory
carve-outs and its rate response; PR #105 indexed Option 56's excess share
(24.0% → 13.1%); PR #107 moved `biden_high_income_tax`'s target onto the Green
Book's own printed −$245.9B, which moved only the error column (14.1% → 12.0%).
The CI gate was then re-derived again, to `--max-mean-error 25
--min-within-25pct 20` (PR #110) — ceiling `ceil(18.0 × 1.25) = 23`, rounded
up to the nearest 5; floor `21 − 1 = 20`.

**Wave 5 (2026-09-05, PRs #113, #114, #116) took the tier 18.0% → 15.9%**, the
median to **11.4%**, within-15 to **16** and within-25 to **22** — *through* two
pre-registered regressions rather than around them, which is the reading to
keep. **PR #113** rebuilt the new-payroll-tax base and the two Option 61 rows
went 54.1% / 55.5% → **7.5% / 8.1%**, on its own worth more than the two
regressions cost; the plan's scoping was wrong on both halves, because CBO's own
option text says the tax is paid entirely by employees, so the income-tax offset
it named does not exist. **PR #114** rebuilt the corporate rate identity on IRS
SOI Table 11's published statutory base and the 1pp row went 47.1% → **62.3%**,
registered as a regression: the fitted base it replaced was within 3% of the
TY2018 vintage, and what is left is CBO 60557 and Treasury's FY2025 Green Book
pricing a percentage point 42% apart ($135.7B against $192.8B). **PR #116**
projected the capital-gains realizations base with the accrued-gains stock, so
Option 47 fell 44.8% → **10.5%** while the two Green Book rows crossed to
**31.4%** and **43.3%**. The CI gate was re-derived a third time, to
**`--max-mean-error 20 --min-within-25pct 21`** (PR #117) — ceiling
`ceil(15.9 × 1.25) = 20`; floor `22 − 1 = 21`. Both tighten.

**PR #121 (2026-09-05) then took the tier 15.9% → 15.2% on one row.** The corporate
base is no longer aged at a flat 4%/yr: it is CBO's own February 2024 corporate
receipts path (pub. 59710 Table 1-1) times a **4.80133 base-$/receipts-$** ratio
anchored on SOI TY2022 ÷ MTS FY2022, with a §6655 convolution converting tax years
to fiscal years. `cbo_opt64_corporate_rate_1pp` went **62.3% → 44.5%** against a
pre-registered band of 42 ± 4, and every other row is identical to the decimal.
What the lane closed is an inconsistency independent of any target: the flat aging
grew the base 3.4× faster than the receipts it is a share of, so by FY2033 a
percentage point of statutory rate was scored against **more base than the entire
baseline corporate tax implies exists** (window-average marginal share 90.8%, above
1.0 by FY2034). It is now **80.8%**, flat by construction, because numerator and
denominator are the same series. Twenty of the row's sixty-two points were a
vintage problem; the remaining forty-four are credit carryforwards under §38(c) and
§904(c), CAMT (which begins in TY2023, after the last SOI year on file), and the
individual-side dividend interaction — none of which is in this module's power to
close from a published source, and none of which may be asserted as a constant. The
gate re-derives to the same **20 / 21**: `ceil(15.2 × 1.25) = 19`, rounded up to the
nearest 5 is 20; `22 − 1 = 21`.

A note on what the residual is **not**. This document used to say the corporate
residual was "CBO and Treasury pricing a percentage point 42% apart, with the
larger rate change carrying the larger per-point yield". PR #120's memo refuted
that from the documents: per-point dollars are not comparable across statutory rate
levels or scopes, the split is **JCT against Treasury OTA** (every corporate-rate
option in every *Options* volume carries "Data source: Staff of the Joint Committee
on Taxation" verbatim) times a **scope** difference (Treasury's 28% row has bundled
a GILTI step since the FY2023 edition), and on the comparable metric — implied
marginal base ÷ receipts/rate — the record reads Tax Foundation 55.1%, JCT 55.9%,
PWBM 64.4%, Treasury 79.5%, against this model's **80.8%**. Nothing supports a
yield rising with the step: JCT's 14-point cut from 35% and its 1-point increase
from 21% imply marginal bases of $963.2B and $963.0B. Two further claims went with
it: Option 64 carries **no** income-and-payroll offset footnote though the facing
Option 63 does, so JCT applies no such offset either; and the §174 / bonus-
depreciation inflation of the TY2022 anchor is **11.1%** as an upper bound, which
deflating by takes the row to about 46%, not to CBO's figure.

Ordinary-bracket rate changes score on the ordinary-income base (excluding
preferential LTCG/QDIV); AGI-inclusive surtaxes score on the full taxable-income
base — classified from how each source describes its base, never fitted. Treat
uncalibrated custom rate policies as directional, ±15–25%.

### Tier 2a — Calibrated reference models (fitted; low error by construction)

Specialized modules parameterized to reproduce the published decomposition. Useful
as auditable, source-linked reconstructions of official scores, *not* as
independent confirmation. **21 fitted benchmarks, mean absolute error 1.7%, 21 of
21 within 15%, 21 of 21 within 25%.** Seventeen of them reproduce a published
CBO/JCT/Treasury decomposition; the other four are fitted to a target that is
itself a model estimate, so those measure internal consistency only. (Earlier
revisions of this file quoted “≈ 5% across 29 benchmarks”, then 2.7% over 34,
then 2.8% over 33, then 2.2% over 30, then 1.6% over 23;
`scripts/cold_holdout.py` is now the only place this figure should be read from.)

**Quote the 21 with the rows that left it — there are four different reasons and
all are live.** First, `ScorecardSummary.revised_target_entries` is **16**: sixteen
calibrated targets have been corrected through the Tier-2 revision ledger
(`fiscal_model/validation/target_revisions.py`), and a constant fitted to a
superseded figure is not fitted to its replacement — so the revised rows report
in Tier 2b, where a miss is a finding rather than a regression. **Wave 4's
provenance pass took this tier 28 → 23** on exactly that rule, moving
`biden_eitc_childless`, `eliminate_salt`, `extend_enhanced_ptc`,
`ira_enforcement` and `repeal_salt_cap` out mechanically; retuning any of them to
close the new gap would have been the relaxation, and none was touched. Held in
place instead, this tier reads **28 benchmarks at 3.0%, 27 of 28 within 15%**
(the one miss being `eliminate_salt` at 22.3%), or 29 at 5.2% with the revised
TCJA-AMT row held in too — the n=29 reading earlier revisions quoted as 4.3%.
Second, **Wave 2 took
this tier 33 → 30**: deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural
tuples removed the only constants ever fitted to the three capital-gains
scenarios, so they now report in Tier 2b too. Third, **Wave 3's L8 lane took it
30 → 28**: `universal_coverage_rate` became a Census measurement and
`china_effective_coverage` was deleted for an incremental-rate identity, so the
two Trump tariff rows — which had been reading 1.1% and 6.2% off constants
fitted to them — now report in Tier 2b at 42.0% and 44.3%. **Fourth — and this
one is not the ledger's — PR #119's offset-sign sweep took it 23 → 21**:
`trump_corporate_15` and `repeal_ptc` were reclassified `calibrated_to_target=False`
because each annual had been fitted so that *static × (1 + offset share)* landed on
its target, and signing the offset took the score to *static × (1 − offset share)* —
a movement of twice the offset. **A constant that reproduced its target only
through a defect is not a calibration to that target**; neither was retuned and
neither got a readiness exemption. Held in place, this tier reads **23 at 7.7%,
21 of 23 within 15%** (the sweep's own lane doc records 3.4%, which was true before
PR #122 moved `trump_corporate_15`'s target off the model's own output and that row
went 22.3% → 121.6%), 28 at 8.0% with Wave 4's five also held in, and 29 at 10.0%
with the TCJA-AMT row on top. The mean *fell*
2.8% → 2.2% → 2.0% → **1.6%** and then rose to **1.7%**, and the worst row is still
`tcja_no_salt_cap` at 13.9%: every row that left on the first three mechanisms was
one this tier had been carrying, and the two that left on the fourth were below the
mean only by virtue of the bug. Composition, not accuracy.

| Policy | Official Score | Model Score | Error | Status |
|--------|----------------|-------------|-------|--------|
| **TCJA Full Extension** | **$4,600B** | **$4,582B** | **0.4%** | calibrated |
| **Biden Corporate 28%** | **−$1,347B** | **−$1,397B** | **3.7%** | calibrated |
| **Biden CTC 2021** | **$1,600B** | **$1,600B** | **0.0%** | calibrated |
| **Estate: Biden Reform** | **−$450B** | **−$450B** | **0.0%** | calibrated |
| **SS Donut Hole $250K** | **−$1,427B** | **−$2,700B** | **89.2%** | reconstruction |
| **Repeal Corporate AMT** | **$220B** | **$220B** | **0.0%** | calibrated |
| **Cap Employer Health** | **−$450B** | **−$450B** | **0.1%** | calibrated |
| Eliminate mortgage deduction | −$368B | −$270B | 26.5% | reconstruction |
| TCJA extension without the SALT cap | $5,700B | $6,495B | 13.9% | calibrated (worst fitted row) |

*Positive values indicate deficit increase (cost); negative values indicate deficit reduction (savings). All estimates are 10-year totals.*

*Rows this table used to carry that no longer belong in it:* the two Trump
tariff rows left in Wave 3 when L8 replaced their fitted coverage constants with
Census measurements, and report in Tier 2b at **42.0%** and 44.3%; the two PWBM
capital-gains scenarios left in Wave 2 with the constants fitted to them and now
report in Tier 2b at −28.4% and +76.5%; Biden GILTI reform, FDII repeal and IRA
drug negotiation left earlier, in the Phase E provenance pass, and report in
Tier 2b at **38.4%**, **29.9%** and **93.3%**; and **five more left in Wave 4**
(`biden_eitc_childless` 9.5%, `eliminate_salt` 22.3%, `extend_enhanced_ptc`
9.3%, `ira_enforcement` 4.7%, `repeal_salt_cap` 1.2%) when PR #107 moved their
targets, so a constant fitted to a superseded figure is no longer fitted to what
the row is scored against; and **two more left in PR #119** — `trump_corporate_15`
(now 121.6% against a published range) and `repeal_ptc` (18.5%) — when the
offset-sign sweep showed each annual had been fitted so that
*static × (1 + offset share)* hit its target, which is not a calibration to that
target at all. `scripts/cold_holdout.py` prints the live
membership of both tiers and is the only place it should be read from.

### Tier 2b — Unfitted module reconstructions (target never fitted to)

**34 policies, mean absolute error 57.9%, median 34.2%; 9 of 34 within 15%, 12 of
34 within 25%.** **Wave 7's PR #131 moved this tier on accuracy and not on
composition** — the same 34 rows sit in it either side, so 57.6% → 57.9% is
like-for-like and the whole 0.33pp is `repeal_ptc` going **18.5% → 29.6%** when
its fitted $83.0B/yr was replaced by CBO and JCT publication 51298 Table 2's own
annual credit path net of publication 60437's published 19.28% offsetting share.
*Wave D's PR #155 then replaced that single aggregate ratio with a four-channel
composition priced per coverage person-year, taking the window share to
**12.32%** and the row to **23.6%**; the aggregate had been booking CBO's +$21B
of Medicaid and CHIP as a cost rather than a saving, worth $31.39B in the wrong
direction.*
It is a registered regression, and the within-25 count fell 13 → 12 with it.
Everything before that moved on population, in Wave 4 and again in PRs #119 and
#122, so the constant-population comparisons belong beside them: on
the **33 rows the tier held before PR #122** it reads **57.4% / 29.9%**, on the
**31 it held before PR #119** **56.6% / 29.9%** — exactly what it read after
Wave 5 — and on the **26 rows it already held before Wave 4** **65.7% / 40.5%**,
against 61.8% / 38.0% before that. The whole of the 56.6% → 57.4% step is
`trump_corporate_15` going 22.3% → **121.6%** when PR #122 stopped scoring it
against this model's own output and gave it the published PWBM/Tax Foundation
range; the remaining 0.2pp to 57.6% is the new FY2022 corporate benchmark arriving
at 62.9%. **The rise is the honest direction**: this is the tier a row goes to when
nothing is fitted to it, and a row that stops being measured against the model's
own output should be expected to look worse. These are six
populations and must never be read as one number:

- **Fifteen sectoral presets** (international, trade, pharma, IRS
  enforcement, climate) at **82.6% mean / 39.0% median** — twelve of them Phase
  E's, the two tariff rows L8 unfitted, and `ira_enforcement`, which arrived in
  Wave 4 when its target moved; **88.2%** on the constant 14-row population,
  because Wave 4's pharma rebuild moved two rows *away* from their targets
  (expanded negotiation 25.7% → **93.3%**, international reference pricing
  646.2% → **701.0%**) while Wave 4's provenance pass moved seven targets onto
  their documents. The pharma move is a finding rather than a regression, and the
  lane says why: its own negotiation ladder condemned an unsourced $220B Part D
  gross-spending constant that the reference-pricing leg also reads — current
  law's 160 cumulative selections carry $256.8B of gross Part D spending by 2034,
  and CMS's own sentence puts the total at $281B. Keeping the unsourced number
  because it flattered the prediction is what the pre-registration protocol
  exists to stop. They ship in the app
  with an official figure attached and no module constant was ever fitted to any
  of them. Two — the universal insulin cap and international reference pricing —
  diagnosed real federal-incidence bugs in `pharma.py`, and **Wave 1's L7 lane
  repaired both**, taking this subset from 394.1% to 113.8% without fitting a
  parameter to any of the three pharma targets. The insulin *target* was then
  corrected too: CBO publication 57957 scores a private-market insulin cap at
  about **+$11.4B**, i.e. as *adding* to the deficit, against the carried −$15B,
  and the model scores **+$7.0B** — so the row moved from 146.4% with the
  directions disagreeing to **39.0%** with them agreeing, taking this subset to
  104.8% / 40.0%. Reference pricing at −$746B against a −$100B `model_estimate`
  target is the family's largest remaining row; CBO scored H.R. 3's narrower
  international-reference cap at about $456B, which is where a broader policy
  should sit. **Wave 3 then moved two families and neither move was a
  calibration.** L8 took the tariff scores gross → net and the five trade rows
  from a summed 360.8 points of error to **191.9** (auto 152.3% → 82.2%, steel
  73.2% → 11.9%, reciprocal 128.0% → 16.4%, and the two formerly-fitted rows to
  37.1% and 44.3%). L9 gave FDII repeal the base × rate identity the module's
  own rate branch already used, on Treasury OTA's published $130,230M cost, and
  the row went **15.0% → 44.7%** while the package went **41.0% → 49.5%** — both
  pre-registered as regressions before the lane opened a file, because the
  identity moves toward the document and away from a target 54% above it. **Wave
  4's provenance pass then moved seven of this subset's targets onto their
  documents and no model figure at all**: FDII repeal 44.7% → **29.9%** (the
  target came *toward* the model), GILTI reform 17.8% → **38.4%**, the package
  49.5% → **44.1%**, the universal tariff 37.1% → **42.0%**, the auto tariff
  82.2% → **52.8%**, reciprocal tariffs 16.4% → **6.9%** against an in-range
  anchor, and EV credits 14.2% → **25.3%**. Six of the thirteen Wave 4 revisions
  made their row worse, which is the shape a correct provenance pass has.
  **Wave C's PR #150 then moved the five trade rows on the *score* rather than
  the target, and the family got worse by design**: retaliation left the
  conventional figure, where it was a category error against five conventional
  benchmarks, and `Trade` went **34.2% → 43.6%** — universal 42.0% → **36.9%**,
  China 57.2% → **49.1%**, auto 52.8% → **47.2%**, reciprocal 6.9% → **9.5%**
  (and *inside* its published range, distance $3.2B → $0.0B), steel 11.9% →
  **75.3%** on a base that now reaches the Section 232 derivative chapter. On the
  four rows that have a document the family improves **39.7% → 35.7%**; the fifth
  has no document and carries the whole of the net.
- **Eight Phase D P.L. 119-21 line items** (JCT JCX-35-25, transcribed with page
  references to `fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`)
  at **35.8% mean**, 2 of 8 within 15%, scored over JCT's own FY2025–2034 window.
  This is the sharpest available evidence that the calibrated tier is
  reconstruction rather than structure: the TCJA module reproduces CBO's $4.6T
  aggregate to **0.4%** and JCT's own component rows to **36%**, because one
  calibration factor is fitted to the aggregate and no factor is fitted to any
  component.
- **Three capital-gains scenarios** at **39.6% mean** — CBO +2pp −14.0%, PWBM
  39.6% with step-up −28.4%, PWBM 39.6% without step-up +76.5%. They arrived in
  Wave 2, when `fiscal_model/validation/scenarios.py`'s per-case behavioural tuples were
  deleted: those tuples *were* the fit, so once they were gone
  `calibrated_to_target` became simply `False`. Because no per-case constant is
  left, these three figures are **identical** to the same three rows in Tier 2c,
  and `run_loo.py --donor-matrix` prints three identical rows — there is nothing
  to hold out.
- **One revised-target row**, `extend_tcja_amt`, at **66.8%**. Its target moved
  from $450B to CRS R48286's published $1,357.1B and the AMT constant — still
  fitted to the superseded figure — was deliberately not retuned, so it reports
  here rather than in Tier 2a. The module's *derived* path scores $855.3B,
  **−37.0%** against the same row.
- **Five Wave 4 provenance arrivals** at **9.4% mean** — `repeal_salt_cap`
  1.2%, `ira_enforcement` 4.7%, `extend_enhanced_ptc` 9.3%,
  `biden_eitc_childless` 9.5%, `eliminate_salt` 22.3%. They left Tier 2a
  mechanically when PR #107 moved their targets, none was retuned, and they are
  the best-scoring population in this tier — which is the whole reason the pooled
  mean fell while the model did not improve.

- **Three corporate/PTC arrivals** at **67.7% mean** — `trump_corporate_15`
  121.6%, `biden_corporate_28_fy2022` 62.9%, `repeal_ptc` 18.5%. The
  worst-scoring population here, and every bit of it is a *target* moving rather
  than a model moving: two came in from PR #119 when signing the behavioural offset
  showed their constants had been compensating for a defect, and the largest moved
  again in PR #122 when its target stopped being this repository's own output and
  became PWBM's and Tax Foundation's published range. The third is a benchmark that
  did not exist before PR #122: Treasury's **FY2022** Green Book row, the only
  rate-only corporate row any Green Book prints, registered as a second published
  target the corporate module is **not fitted to and never will be**.

Nothing in any of the five Wave 4 arrivals was retuned to close a gap, nothing in
the three corporate/PTC arrivals was either, and every row carries a
`known_limitations` note naming the structural cause.

### Tier 2c — Calibrated modules, held out (leave-one-out)

`python scripts/run_loo.py` refits each calibrated module's mechanism on the
*other* benchmarks in its module and asks it to rebuild the held-out one.
**18 derivable cases, mean absolute error 30.1%, median 19.1%, 8 of 18 within
15%**, plus **4 cases declared not cross-validatable** — no second benchmark to
calibrate on, or a base constant that is the published target restated — which are
reported and never folded into the aggregate.

| Module | Kind | n | Not x-val | LOO mean abs error |
|---|---|--:|--:|--:|
| Payroll | structural | 3 | 1 | 3.8% |
| Estate | structural | 2 | 1 | 10.4% |
| Credits | structural (CPS ASEC per-unit) | 3 | 0 | **18.5%** |
| Expenditures | bottom-up | 5 | 1 | **37.5%** |
| CapitalGains | structural | 3 | 0 | 39.6% |
| AMT | structural | 2 | 1 | 73.9% |

Compare against the 1.7% in Tier 2a: that number measures bookkeeping, this one
measures whether the machinery predicts.

**Wave 7 moved this suite 29.6% → 30.1%, and it is the first move here that is a
derivation rather than a target — registered in advance as a regression.**
PR #128 gave `TaxExpenditurePolicy` a per-reform offset `direction` read off nine
published sources, and the one scored reform whose direction flipped is the
mortgage-interest deduction, on Poterba & Sinai's own $72.4B-without-behaviour
against $61.9B-with. `eliminate_mortgage`'s held-out score went −$315.3B
(**−5.1%**) → −$257.9B (**+14.0%**), taking `Expenditures` **35.7% → 37.5%**;
the median stayed at 19.1% and within-15 at 8/18. **The old −5.1% was two errors
cancelling**: the held-out annual is JCT's $25.0B against the fitted $26.2B, a
static path 4.5% *low*, and magnifying it by 10% put the score 5.1% *high*.
Signing it correctly gives the base error *plus* the offset instead of *netted
against* it — the same shape as Wave 1's Fiscal Responsibility Act spend-out
finding, where a flattering number turned out never to have been evidence. The
leakage guard is untouched, `eliminate_step_up` is still excluded by it, and no
donor-matrix entry moved.

**Wave 4 moved this suite 28.4% → 29.6% without a single derivation moving.**
`run_loo.py --donor-matrix` differs from pre-Wave-4 main in exactly five lines,
and every derived figure in them is identical: PR #107 moved three of the targets
the suite scores against. `biden_eitc_childless` −38.0% → **−32.1%** (derivation
unchanged at 110.4), `repeal_salt_cap` −29.4% → **−33.5%** (777.0),
`eliminate_salt` +10.2% → **+33.5%** (−1,077.9). Per module that is `Credits`
20.5% → **18.5%** and `Expenditures` 30.2% → **35.7%**; the other four are
untouched, no donor-matrix entry moved, and the leakage guard neither fired nor
was touched. **The mean rose while the model was unchanged, in the same wave
that the reconstruction mean fell while the model got worse — read both with
their populations attached.**

**Wave 3 moved two of the six modules, in opposite directions.** `Credits`
**45.1% → 20.5%**: lane L3 replaced `Δcredit × units × participation` with two
statutory parameter sets run through `MicroTaxCalculator` over CPS ASEC tax units
and differenced on final liability, which prices refundability, the tax limit on
the non-refundable leg and the qualifying-age expansions the identity had
nowhere to put. The single largest correction inside it is a **counterfactual**,
not a parameter: IRC §24's $2,000 reverts to $1,000 after 2025, so a window
opening in 2025 is scored against current law for one year and the pre-TCJA
regime for nine — $883B against a fixed baseline, **$1,528B** against the one the
statute specifies. `Expenditures` **28.8% (n=4) → 30.2% (n=5)**, and the rise is
the better state: PR #100 replaced `annual_cost_no_cap = 120.0` — exactly the
carried $1,200B target over ten — with **$89.55B** computed from IRS SOI Table
2.1 at the statutory schedule, `loo.py`'s untouched leakage guard stopped firing,
`eliminate_salt` re-entered at **+10.2%**, and `repeal_salt_cap` moved
**+4.0% → −29.4%** because its old +4.0% was `−(120.0 − 25.0)`, the same leaked
constant under a different benchmark. Held to the 17 cases the suite carried
before the readmission the mean is **29.5%**; the printed 28.4% over 18 is the
honest figure and the difference is composition.

**Wave 2 had moved three of the six, and one case had left the denominator.**
`CapitalGains` **171.2% → 39.6%** on one frozen literature elasticity set
replacing three hand-set tuples; `Estate` **25.8% → 10.4%** on a SOI-fitted
Pareto size distribution replacing a blend that was exactly invariant in the
exemption; `Expenditures` **39.4% → 28.8%** on declared cap units and SOI
benefit distributions, with `eliminate_salt` excluded for the leakage Wave 3
then closed.

**Before Wave 2 this aggregate had moved twice, and neither move was a model
change.** Wave 1
took it 59.3% → 61.7%, entirely on AMT (79.6% → 100.5%), and that rise was the
module becoming more structural rather than less accurate: L5 replaced a flat
steady-state identity (~$73B/yr) with TPC T25-0049's published year-indexed path.
The plan's hypothesis had been that a missing 2026 phase-in biased the derivation
high; the table shows a **cliff** (0.2M AMT payers in 2025, 7.6M in 2026)
followed by *growth* ($71.6B in 2026 to $124.2B in 2035), so the flat level was
the window's early-year value and indexing it by year **raises** the score. Both
rows therefore moved away from their carried $450B targets. Correcting
`extend_tcja_amt`'s target to the published $1,357.1B then took the aggregate to
58.7% and AMT to **73.9%**: the held-out derivation is **unchanged at $855.3B**
and only the figure it is measured against moved, so that row reads **−37.0%**
instead of +90.1%. Wave 2's 58.7% → **32.3%** is the first move that *is* the
model, with the case-count caveat above attached, Wave 3's 32.3% → **28.4%**
is one model change and one provenance fix pulling against each other, and Wave
4's 28.4% → **29.6%** is provenance alone. See
[VALIDATION_NOTES.md](VALIDATION_NOTES.md) §6.

### Reading the tiers

**Report these separately and never collapse them:**

| Tier | What it measures | n | Mean | Median |
|---|---|--:|--:|--:|
| 1 — out-of-sample, pre-registered | prediction | 26 | **15.0%** | 10.6% |
| 2a — calibrated, fitted | bookkeeping (low by construction) | 21 | **1.7%** | 0.0% |
| 2b — unfitted module reconstructions | modules against targets they never saw | 34 | **57.9%** | 34.2% |
| 2c — calibrated, leave-one-out | how much of the calibration is structure | 18 | **30.1%** | 19.1% |

Two of the four changed population in Wave 4 and again in PRs #119 and #122, so the
constant-population readings belong next to them: **Tier 2a is 23 at 7.7%, 21/23
within 15%** with the sweep's two reclassified rows held in place (28 at 8.0% with
Wave 4's five held in too, 29 at 10.0% with the TCJA-AMT row on top) — and, on
the *ledger's* mechanism rather than the sweep's, **27 at 5.6%, 25/27 within
15%**, which `run_validation_dashboard.py` computes since PR #130 gave
`ScorecardEntry` a `declared_calibrated_to_target` beside the effective flag.
**The natural guess there is wrong by a factor of three**: folding in all 16
`revised_target_entries` rows reads 37 at 15.5%, but 10 of those are sectoral
rows no runner ever declared fitted, so they were never in the tier to be moved
out of it. **Tier 2b is 57.4% / 29.9% over the 33 rows it held before PR #122**,
**56.6% / 29.9% over the 31 it held before PR #119**, and **65.7% / 40.5% over
the 26 it held before Wave 4** — *worse* than 61.8% / 38.0% — with its sectoral
subset unmoved throughout at **88.2% over the 14 it held**; Wave 7's step to
57.9% is the exception that has **no** composition reading, because no row
entered or left. Tier 2c was for three waves the mirror case: it *rose* 28.4%
→ 29.6% without a single derivation moving, and then **29.6% → 30.1%** in
Wave 7 with a derivation that did move — registered in advance, on a row whose
old figure was two errors cancelling. A mean that
moves because the population moved has not improved, and a mean that moves
because a target moved has not measured the model. **Wave 5 moved only Tier 1**,
and it is the one tier where a moving mean *does* measure the model: 2a, 2b and
2c are unchanged to the decimal, and `run_loo.py --donor-matrix` is
byte-identical, because all three lanes worked at the out-of-sample margin
without touching a target or retuning a constant. **PR #121 did the same**, moving
one Tier 1 row and leaving 2a, 2b and 2c untouched; **PRs #119 and #122 moved 2a
and 2b by composition and 2c not at all** — `run_loo.py --donor-matrix` is still
byte-identical, checked independently on all four branches. Wave 5 also named a
hole in 2c: the suite has **no `Corporate` row**, so the module whose fitted base
turned out to be a stale vintage has never been cross-validated. **PR #120's memo
answered that `no`, and `loo.py` is not what is stopping it**: the module has one
fitted constant and had two benchmarks, one of them its own output, so re-deriving
the base from it would reconstruct the constant from itself — the leakage the
suite exists to catch, and `not cross-validatable` is the honest outcome.
**PR #122 shipped the substitute instead**: `biden_corporate_28_fy2022`, a second
*published* target the module is not fitted to, reporting in 2b at −62.9%. The
module now has two published benchmarks and one fitted constant and still nothing
cross-validating either — a smaller hole, honestly stated, not a closed one.

Distributional accuracy is a fifth, separate number: **seven published CBO/JCT
tables at 0.00–5.86pp** mean absolute share error, **two of which are circular**
(see [above](#vs-tpc-tax-policy-center)) — and since Wave 4 the suite also reports
the universe each row was **scored** on, so those two circular rows are visibly
scored on a population CBO does not use. There is no single “validated within X%”
figure for this model, and any document that states one is wrong.

---

## References

### Academic Literature

1. **Saez, E., Slemrod, J., & Giertz, S.H. (2012)**. "The Elasticity of Taxable Income with Respect to Marginal Tax Rates: A Critical Review." *Journal of Economic Literature*, 50(1), 3–50.

2. **Auerbach, A.J., & Gorodnichenko, Y. (2012)**. "Measuring the Output Responses to Fiscal Policy." *American Economic Journal: Economic Policy*, 4(2), 1–27.

3. **Christiano, L., Eichenbaum, M., & Rebelo, S. (2011)**. "When Is the Government Spending Multiplier Large?" *Journal of Political Economy*, 119(1), 78–121.

4. **Gruber, J., & Saez, E. (2002)**. "The Elasticity of Taxable Income: Evidence and Implications." *Journal of Public Economics*, 84(1), 1–32.

5. **Dowd, T., McClelland, R., & Muthitacharoen, A. (2015)**. "New Evidence on Long-Run Capital Gains Elasticities." *National Tax Journal*, 68(3), 511–540.

6. **Blanchard, O., & Leigh, D. (2013)**. "Growth Forecast Errors and Fiscal Multipliers." *American Economic Review*, 103(3), 117–120.

7. **Amiti, M., Redding, S.J., & Weinstein, D.E. (2019)**. "The Impact of the 2018 Tariffs on Prices and Welfare." *Journal of Economic Perspectives*, 33(4), 187–210.

8. **Clausing, K.A. (2020)**. "Profit Shifting Before and After the Tax Cuts and Jobs Act." *National Tax Journal*, 73(4), 1233–1266.

9. **Diamond, P.A. (1965)**. "National Debt in a Neoclassical Growth Model." *American Economic Review*, 55(5), 1126–1150.

10. **Auerbach, A.J., Gokhale, J., & Kotlikoff, L.J. (1991)**. "Generational Accounts: A Meaningful Alternative to Deficit Accounting." *Brookings Papers on Economic Activity*, 1991(1), 55–110.

11. **Auerbach, A.J., & Kotlikoff, L.J. (1987)**. *Dynamic Fiscal Policy*. Cambridge University Press.

12. **Ball, L., Leigh, D., & Loungani, P. (2017)**. "Okun's Law: Fit at 50?" *Journal of Money, Credit and Banking*, 49(7), 1413–1441.

### Official Methodology Documents

13. **CBO (2014)**. "How CBO Analyzes the Effects of Changes in Federal Fiscal Policies on the Economy." Congressional Budget Office.

14. **CBO (2022)**. "Estimated Budgetary Effects of H.R. 5376, the Inflation Reduction Act of 2022." Congressional Budget Office.

15. **CBO (2023)**. "The 2023 Long-Term Budget Outlook." Congressional Budget Office.

16. **CBO (2026)**. "The Budget and Economic Outlook: 2026 to 2036." Congressional Budget Office.

17. **JCT (2017)**. "Overview of Revenue Estimating Procedures and Methodologies." Joint Committee on Taxation. JCX-1-17.

18. **Treasury (2024)**. "General Explanations of the Administration's FY2025 Revenue Proposals (Green Book)." U.S. Department of the Treasury.

19. **TPC**. "Tax Model Resources." Tax Policy Center. https://taxpolicycenter.org/resources/tax-model-resources

20. **Yale Budget Lab**. "Methodology and Documentation." https://budgetlab.yale.edu/research

### Data Sources

21. **IRS Statistics of Income**. Individual Income Tax Statistics. Tables 1.1 and 3.3. https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics

22. **FRED**. Federal Reserve Economic Data. Federal Reserve Bank of St. Louis. https://fred.stlouisfed.org

23. **RAND (2021)**. "Prices Paid to US Hospitals by Medicare Advantage Plans." RAND Corporation.

24. **KFF (2024)**. "Medicare Drug Spending Dashboard." Kaiser Family Foundation.

---

## Appendix: Parameter Defaults

### Tax Parameters

| Parameter | Default | Source |
|-----------|---------|--------|
| ETI | 0.25 | Saez et al. (2012) |
| Labor supply elasticity | 0.15 | CBO |
| Capital elasticity | 0.25 | Literature |
| Marginal revenue rate | 0.25 | CBO |
| Corporate tax incidence (capital) | 75% | CBO/TPC |
| Corporate tax incidence (labor) | 25% | CBO/TPC |
| Capital gains elasticity (short-run) | 0.8 | CBO (2012) |
| Capital gains elasticity (long-run) | 0.4 | Dowd et al. (2015) |

### Dynamic Scoring Parameters (FRBUSAdapterLite)

| Parameter | Default | Source |
|-----------|---------|--------|
| Spending multiplier (Year 1) | 1.4 | FRB/US-calibrated (`FRBUSAdapterLite`) |
| Tax multiplier (Year 1) | -0.7 | FRB/US-calibrated (`FRBUSAdapterLite`) |
| Multiplier decay (per year) | 0.75 | FRB/US-calibrated (`FRBUSAdapterLite`) |
| Crowding out (share of cumulative deficit) | 0.15 | FRB/US-calibrated (`FRBUSAdapterLite`) |
| Marginal revenue rate on GDP feedback | 0.25 | `FRBUSAdapterLite`; see **Dynamic Scoring** |
| Monetary offset / annual retention of the demand effect | 0.65 | FRB/US-calibrated (`FRBUSAdapterLite`) |

*This table was truncated mid-row in the repository for some time — it ended at
`| Spending multiplier (Year 1) | 1.4 | FR`. The rows above are read back from
`FRBUSAdapterLite.__init__`'s own defaults in
`fiscal_model/models/macro_adapter_frbus.py` rather than reconstructed from
memory. There is **no supply-side channel**; demand-side GDP effects fade over
roughly five to seven years at the 0.65 retention, and the dynamic surface nets
debt-service costs against revenue feedback.*

