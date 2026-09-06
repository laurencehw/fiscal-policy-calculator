# Lane W7 — A filing-status dimension for the generic income-tax path

*Pre-registered 2026-09-06 against `main` @ `a251b32`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §2.1's row **"Filing-status-specific
thresholds"**, restated as carry-over item 25 of §6.2 — *"The AGI-surtax
filing-status threshold row is now the tier's largest, at 44.7%, and nothing
since Wave 4 has touched it… Together with `cbo_opt45_top4_brackets_2pp` at
17.9% this is 62.6 units, 15.8% of the tier. Closing it needs SOI by filing
status, which is why §2.1 scoped it 'medium, not in scope below'; it has now
outlasted five waves and the corporate follow-through."*

The lane gives `TaxPolicy` a threshold that may be stated per filing status, and
gives `IRSSOIData` a base split the same four ways, from IRS SOI **Table 1.2**
(TY2023) — the table that reports returns, AGI, taxable income and tax by size
of AGI **and by marital/filing status**, which the repository has never read.

It touches `fiscal_model/data/irs_soi.py`, `fiscal_model/policies_core.py`,
one new data file and one new build script, the three rows' shape inputs in
`fiscal_model/validation/cbo_scores.py`, the shape rule and four
`known_limitations` blocks in `fiscal_model/validation/core.py`, the Option 45
and 46 notes in `fiscal_model/validation/cbo_options.py`, and the tests. It
adds **no Tier-1 row**, edits **no target**, no manifest, no CI threshold, and
no behavioural parameter.

**It is registered as a lane that makes the battery's mean worse.** §3 says by
how much, in which direction, and why the improvement it does produce is a
decomposition rather than a headline.

## 1. Starting numbers

All measured on the branch point, `a251b32`, from `python
scripts/cold_holdout.py --json`, `python scripts/run_loo.py --donor-matrix` and
`python scripts/run_validation_dashboard.py`.

### 1.1 The four cases this lane is about

Three are CBO, *Options for Reducing the Deficit: 2025 to 2034* (pub. 60557,
Dec 2024), report pp. 55–56 / PDF pp. 61–62; the estimates are JCT's (*"Data
source: Staff of the Joint Committee on Taxation"*). The fourth is Treasury's
FY2025 Green Book, report p. 78 / PDF p. 86.

| policy_id | official | model | err | the boundary its source states |
|---|--:|--:|--:|---|
| `cbo_opt46_agi_surtax_1pp_20k` | −1,440.1 | −796.6 | **44.7%** | $20,000 single / $40,000 joint |
| `cbo_opt45_top4_brackets_2pp` | −569.5 | −671.6 | **17.9%** | the 24% bracket floor: $206,700 joint, $103,350 otherwise |
| `cbo_opt46_agi_surtax_2pp_100k` | −1,051.0 | −881.7 | **16.1%** | $100,000 single / $200,000 joint |
| `biden_high_income_tax` | −245.9 | −216.5 | **12.0%** | $450,000 joint / $425,000 HoH / $400,000 unmarried / $225,000 MFS |

Together **91.7 units of Tier 1's 395.1**, 23.2% of the tier — a larger share
than §2.1's pre-Wave-1 accounting gave the mechanism, because
`biden_high_income_tax` was never counted in it.

**Every other Generic row was checked for a filing-status boundary and does not
have one.** The two that look as if they might:

- `medicare_surcharge_2pp` — the Green Book proposal it cites (report p. 76–77;
  PDF pp. 84–85) states one number for every return: *"increase the additional
  Medicare tax rate by 1.2 percentage points for taxpayers with more than
  $400,000 of earnings … also increase the NIIT rate by 1.2 percentage points
  for taxpayers with more than $400,000 of income."* Current law's $200,000 /
  $250,000 split is quoted in the same proposal's *Current Law* section and is
  explicitly **not** carried into the proposal. No boundary; row must not move.
- `cbo_opt45_all_rates_1pp` — threshold 0. There is no boundary to split.

`illustrative_top_rate_5pp`, `illustrative_500k_2pp` and
`warren_ultramillionaire_surtax_3pp` are TPC illustrative or secondhand targets
whose sources state a single amount; nothing in the record distinguishes
statuses, and inventing one would be a shape input with no document behind it.

### 1.2 What the generic path does today

`TaxPolicy.estimate_static_revenue_effect` → `_should_use_irs_data()` →
`_estimate_from_irs_data()` (`policies_core.py:181-322`), which is four lines of
arithmetic on one pooled SOI aggregate:

```python
bracket_info   = irs_data.get_filers_by_bracket(year, self.affected_income_threshold)
marginal_income = max(0, bracket_info["avg_taxable_income"] - self.affected_income_threshold)
ordinary_share  = self._ordinary_income_share(marginal_income * bracket_info["num_filers"], year=year)
revenue_change  = self.rate_change * marginal_income * ordinary_share * bracket_info["num_filers"] / 1e9
```

`get_filers_by_bracket` (`data/irs_soi.py:88-136`) reads **Table 1.1**, which
has no filing-status dimension at all: it sums returns, AGI, taxable income and
tax over the AGI size classes at or above one threshold, interpolating linearly
inside the class that straddles it. The aggregate marginal income is therefore
`Σ TI − threshold × Σ N` over **every** return above **one** floor.

Three consequences, all of them live in the four rows above:

1. **One floor for four populations.** At `cbo_opt46_agi_surtax_1pp_20k` the
   model taxes 46.1M joint returns from $20,000 up, where JCT's estimate starts
   them at $40,000. That single leg over-counts **$839.8B of base — 9.2% of the
   whole**, and the row still under-predicts by 44.7%.
2. **`affected_income_threshold` is a scalar** (`policies_core.py:127`), with no
   place to put a second number even when the source prints one.
3. **The score is the same in every year** — plain `TaxPolicy` is not in
   `_growth_tax_policy_handlers` (`scoring_engine.py:66-75`), so
   `revenue[idx] = static_annual × phase` repeats one TY2023 number ten times.
   That is not this lane's defect to fix, but §3 measures how much of the
   residual it is, because the answer decides how the lane's result is read.

### 1.3 What the sources actually say

**Option 45** (60557, report p. 55; PDF p. 61) names both the filing-status
dimension and the 2026 revert in its own narrative:

> "Tax rates vary depending on the tax bracket, or income range, in which a
> taxpayer's income falls. **(Tax brackets vary by taxpayers' filing status** and
> are adjusted, or indexed, each year to include the effects of inflation.)"

> "Through calendar year 2025, taxable ordinary income earned by most
> individuals is subject to the following seven statutory rates: 10 percent, 12
> percent, 22 percent, 24 percent, 32 percent, 35 percent, and 37 percent. At
> the end of 2025, the rates and brackets will revert to those in effect under
> pre-2018 tax law. Specifically, beginning in 2026, the rates will be 10
> percent, 15 percent, 25 percent, 28 percent, 33 percent, 35 percent, and 39.6
> percent."

> "Under the second alternative, tax rates on ordinary income in the top four
> brackets would increase by 2 percentage points. **Under both alternatives, the
> scheduled changes to the underlying tax brackets and rates would still take
> effect in 2026.**"

So the four highest brackets in 2025 are 24/32/35/37, whose floor is the 24%
bracket. IRS **Rev. Proc. 2024-40** §2.01, tables 1–4 (2025 rate tables under
§1(j)(2)(A)–(D)):

| Filing status | 24% bracket begins at taxable income over |
|---|--:|
| Married filing jointly and surviving spouses (§1(j)(2)(A)) | **$206,700** |
| Heads of households (§1(j)(2)(B)) | **$103,350** |
| Unmarried, other than surviving spouses and HoH (§1(j)(2)(C)) | **$103,350** |
| Married filing separately (§1(j)(2)(D)) | **$103,350** |

The record already carries $103,350 as its single threshold, sourced to that
Rev. Proc. This lane adds the other number the same table prints.

**Option 46** (60557, report p. 56; PDF p. 62) states its thresholds in the
alternative's own label, which is what
`data_files/validation/cbo_options_2025_2034_alternatives.csv` rows `46.1` and
`46.2` already carry verbatim:

> "Under the first alternative, a surtax of 1 percentage point would be imposed
> on AGI above **$20,000 for single filers and $40,000 for joint filers**. Under
> the second alternative, a surtax of 2 percentage points would be imposed on
> AGI above **$100,000 for single filers and $200,000 for joint filers**. After
> 2025, the thresholds for the surtax would be adjusted, or indexed, to include
> the effects of inflation."

The option names **two** amounts and SOI publishes **four** statuses, so a rule
is needed for heads of households and married-filing-separately. §2.2 states it
before any code, and §3 discloses what the alternative reading would have given.

**The Green Book** (FY2025, report p. 78; PDF p. 86) needs no rule — it prints
all four:

> "The top marginal tax rate would apply to taxable income over **$450,000** for
> married individuals filing a joint return and surviving spouses, **$400,000**
> for unmarried individuals (other than surviving spouses and head of household
> filers), **$425,000** for head of household filers, and **$225,000** for
> married individuals filing a separate return."

Note the direction: the MFS threshold is **below** the single threshold the
model uses today, so this row's base *grows* under the split while the other
three shrink.

**The data.** IRS SOI **Table 1.2**, *All Returns: Adjusted Gross Income,
Deductions, and Tax Items, by Size of Adjusted Gross Income and by Filing
Status, Tax Year 2023* — `https://www.irs.gov/pub/irs-soi/23in12ms.xls`,
Publication 1304, March 2026. Five blocks of twelve columns (all returns; joint
and surviving spouses; separate; heads of households; single) over the same 19
AGI size classes Table 1.1 uses. Returns and AGI agree with Table 1.1 **class by
class, to the unit**, on all 19 classes bar one 1-return rounding difference in
`$2,000,000 under $5,000,000`; taxable income does not, because Table 1.1
column 11 is taxable income on **taxable returns** ($11,625.3B) and Table 1.2 is
taxable income on **all returns** ($11,944.4B), a 2.7% difference concentrated
below $50,000. §2.1 says what this lane does about that, and it is the single
most important design choice in it.

### 1.4 The rows this lane must not move

Leave-one-out (`python scripts/run_loo.py --donor-matrix`):

| Module | n | not x-val | mean |
|---|--:|--:|--:|
| Payroll | 3 | 1 | 3.8% |
| Estate | 2 | 1 | 10.4% |
| AMT | 2 | 1 | 73.9% |
| Credits | 3 | 0 | 18.5% |
| Expenditures | 5 | 1 | 35.7% |
| CapitalGains | 3 | 0 | 39.6% |

Aggregate **18 derivable, 29.6% mean / 19.1% median, 8/18 within 15%, 4 not
cross-validatable.**

`get_filers_by_bracket` has exactly one caller in the model
(`policies_core.py:278`) and one in `scripts/batch_score.py`;
`get_bracket_distribution` has five more (`amt.py:620`, `baseline.py:423`,
`distribution_engine.py:89`, `microsim/soi_calibration.py:222`,
`microsim/top_tail.py:166`). **The lane adds a method and changes neither**, so
no calibrated module, no LOO derivation, no distributional benchmark and no
microsim calibration can see it. That is asserted in §4, not assumed.

### 1.5 Battery aggregates

- **Tier 1 (out-of-sample): 26 cases, 15.2% mean, 11.4% median, 16/26 within
  15%, 22/26 within 25%.**
- Fitted calibrated references: **21 policies, 1.7% mean**, 21/21 within 15%.
- Unfitted module reconstructions: **34 policies, 57.6% mean**, 9/34 within 15%.
- Distributional benchmarks: 7, spanning 0.00–5.86pp.
- Shipped presets: 53, plus the Tailor form at its defaults.
- Tests: **3518 passed, 7 skipped** (`python -m pytest tests/ -q`).
- CI gate in force: `cold_holdout.py --max-mean-error 20 --min-within-25pct 21`.
- `run_validation_dashboard.py` **already exits 1** on the branch point, on
  `runtime [degraded] Python 3.14.0 (supported >=3.10,<3.14)`. That is the
  interpreter, not the model, and it is recorded here so the after-run is
  compared against it rather than read as a regression.

## 2. What the lane changes

One dimension — **a threshold that may be stated per filing status, applied to a
base split the same way** — and nothing else.

### 2.1 The base: Table 1.1's level, Table 1.2's composition

The obvious construction is to read Table 1.2 wholesale. **It is rejected**,
because Table 1.2's taxable-income column sits on a different universe from the
one the model reads today (§1.3), so a lane that switched tables would move the
four rows for two reasons at once and could not say which. The Option 46 rows
would shift by 3.5% before a single threshold changed.

So: **Table 1.2 supplies the within-class composition; Table 1.1 supplies the
level.** For each of the 19 AGI size classes and each of the four statuses,

    field_status = field_table_1_1_class × (field_status_table_1_2 / Σ_status field_status_table_1_2)

for returns, AGI, taxable income and total income tax alike. The shares sum to
one by construction, so the four statuses sum back to the Table 1.1 class total
exactly, and — because the aggregate marginal income is linear in both terms —

    Σ_status (Σ TI_status − T · Σ N_status)  =  Σ TI − T · Σ N

**a split evaluated at one uniform threshold reproduces the pooled score to the
cent.** That identity is the lane's control, and §4 asserts it as a test rather
than describing it here. (It holds for any threshold below $10,000,000; above
that the open-ended top class's share depends on a per-status average AGI, and
the identity is only approximate. No case in the repository goes near it.)

### 2.2 The threshold: `threshold_by_filing_status`

`TaxPolicy` gains one optional field, a partial mapping over the four SOI
statuses. Missing statuses fall back to `affected_income_threshold`, which is
exactly the shape of the sources: Option 46 names two amounts, so
`{"joint": 40_000}` against `affected_income_threshold=20_000` **is** the option
text. When the field is `None` the pooled path runs unchanged, byte for byte.

**The rule for the statuses Option 46 does not name**, fixed here before any
code and applied identically to both of its alternatives:

> A return takes the joint amount if and only if it is a joint return (SOI's
> *"Returns of married persons filing jointly and returns of surviving
> spouses"*, the population that uses the §1(j)(2)(A) schedule). Every other
> return — separate, head of household, single — takes the single amount.

This is the two-way split the option's own sentence makes, and it is the
structure of the one enacted broad-income surtax: IRC §1411(b) sets $250,000 for
a joint return, $125,000 for married filing separately — *half* the joint
amount, which is the single amount whenever joint is twice single, as it is in
both Option 46 alternatives — and $200,000 "in any other case", which is single
and head of household together. §3 discloses what the alternative reading
(heads of household at the joint amount) would have given, and it is *not* the
reading that flatters the lane.

Option 45's boundary and the Green Book's are printed per status and need no
rule at all.

### 2.3 The preferential-income share stays where it is measured

`preferential_income_share` (`policies_core.py:22-53`) divides capital gains
above a threshold by the marginal income above the same threshold, and the
capital-gains data behind it (`data/capital_gains.py`) has **no filing-status
dimension**. Two readings are available and they differ materially:

- **(a) recompute on the split base.** The numerator stays "gains above the
  single floor across all returns" while the denominator shrinks, so the
  preferential share rises — on `cbo_opt45_top4_brackets_2pp` from 21.6% to
  29.1%. This is **wrong**, and not merely approximate: the joint returns
  between $103,350 and $206,700 have already been removed from the base once,
  and their gains are then removed from what is left a second time.
- **(b) freeze it at the policy's own `affected_income_threshold`, on the
  pooled marginal income at that threshold** — i.e. compute exactly the number
  the code computes today, and apply it to the split base. Numerator and
  denominator stay on one population. It assumes the split base has the same
  preferential composition as the pooled base, which is an approximation, but
  it double-counts nothing.

**The lane ships (b).** The argument is the double-removal, and it was settled
before the numbers were run; §3 prints both columns anyway, because (b) is also
the friendlier of the two on both affected rows and that has to be visible.

Both Option 46 rows are `agi_inclusive_base=True`, so their ordinary share is
1.0 and the choice cannot touch them.

### 2.4 The 2026 schedule change is not modelled, and the lane says so

Option 45's own text says the pre-2018 brackets return in 2026, so alternative 2
applies to the 28/33/35/39.6 brackets for nine of the window's ten years, at a
28%-bracket floor that is materially *higher* in real terms than the 24% floor
and is **not** twice the single amount for joint returns (the pre-TCJA schedule
carried a marriage penalty at that bracket). Modelling it needs two things this
lane does not have:

1. **A year-indexed threshold.** Plain `TaxPolicy` scores one number ten times
   (§1.2). Making the threshold a path means opting `TaxPolicy` out of the flat
   branch — the third `isinstance` special case in `scoring_engine.py`, which
   §6.2 carry-over 27 already names as the point at which a general
   `Policy.scores_by_year()` should exist instead. That is an engine change
   and it would move every row in the battery.
2. **A published post-2025 rate table.** There is none. The 2026 pre-TCJA
   brackets would have to be constructed by indexing 2017's, which is derivation
   rather than transcription, and the rule for this lane is that every threshold
   comes from a document.

So the shipped threshold is the 2025 schedule's, per status, from Rev. Proc.
2024-40 — the same document and the same year the record already cites — and
the 2026 revert stays in `known_limitations` with its direction stated: it would
raise the single/HoH/MFS floor by roughly 20% and take the row further under,
not closer.

### 2.5 Where the code goes

- **`scripts/build_filing_status_data.py`** — fetches `23in12ms.xls` from
  `irs.gov/pub/irs-soi` (or reads it from the data directory), and writes
  `fiscal_model/data_files/irs_soi/table_1_2_2023.csv` as a faithful dump of the
  sheet, the way `table_1_1_*.csv` are faithful dumps of theirs. The `.xls` is
  gitignored (`*.xls`), so the CSV is the tracked artefact and the workbook is
  the local provenance the script names.
- **`fiscal_model/data_files/irs_soi/table_1_2_2023.csv`** and a README section
  giving the source table, year, publication and URL.
- **`fiscal_model/data/irs_soi.py`** — `FILING_STATUSES`, a Table 1.2 reader
  that locates the five column blocks from the sheet's own status headings
  rather than by hard-coded offsets, `get_bracket_distribution_by_status(year)`
  and `get_filers_by_status_thresholds(year, thresholds)`. `get_filers_by_bracket`
  and `get_bracket_distribution` are **not touched**.
- **`fiscal_model/policies_core.py`** — the `threshold_by_filing_status` field,
  its validation, the split branch in `_estimate_from_irs_data`, and a private
  cache so years 2–10 reproduce year 1 (the pooled path stores its answer in
  `affected_taxpayers_millions` / `avg_taxable_income_in_bracket` and recomputes
  from them on later years, which would silently fall back to the pooled formula
  for a split policy). The cache is populated **only** when a split is declared,
  so the pooled path's arithmetic is untouched to the last bit.
- **`fiscal_model/validation/cbo_scores.py`** — one new shape field,
  `income_threshold_by_filing_status`, set on the three records from the
  documents quoted in §1.3. **No `ten_year_cost` is touched.**
- **`fiscal_model/validation/core.py`** — `FILING_STATUS_THRESHOLD_RULE` (the
  §2.2 rule, written where `GREEN_BOOK_DEATH_DESIGN_RULE` lives), the
  `ordinary_rate` shape passing the mapping through, and the four rows'
  `known_limitations` rewritten to what is actually left.
- **`fiscal_model/validation/cbo_options.py`** — the Option 45.2, 46.1 and 46.2
  notes.
- **`tests/test_filing_status_split.py`** and additions to the SOI and policy
  tests.

**A manifest note.** Under `preregistered.py`'s own convention a *shape* input
that changes gets a new `.v2` row (that is how `iija_2021_discretionary` was
handled). A modelling lane may not open `preregistered.py`, so this document is
the pre-registration for these three shape inputs: entered in a commit before
the commit that first scores them, with the document and page for every number.
Whether the manifest should also carry a row is an owner call and goes to §6.2.

## 3. The prediction

**Headline: three of the four rows get worse, one gets better, and the Tier 1
mean rises 15.2% → 15.9%.** Every figure below was computed by hand from Table
1.2 and the four documents before a line of module code was written.

| policy_id | official | today | **predicted** | today err | **predicted err** |
|---|--:|--:|--:|--:|--:|
| `cbo_opt46_agi_surtax_1pp_20k` | −1,440.1 | −796.6 | **−723.1** | 44.7% | **49.8%** |
| `cbo_opt46_agi_surtax_2pp_100k` | −1,051.0 | −881.7 | **−657.5** | 16.1% | **37.4%** |
| `cbo_opt45_top4_brackets_2pp` | −569.5 | −671.6 | **−498.7** | 17.9% | **12.4%** |
| `biden_high_income_tax` | −245.9 | −216.5 | **−223.3** | 12.0% | **9.2%** |

The split base, status by status (marginal income above each status's own floor,
in billions of TY2023 dollars):

| case | joint | separate | head of household | single | total |
|---|--:|--:|--:|--:|--:|
| `cbo_opt46_..._1pp_20k` | 5,853.8 | 220.7 | 338.7 | 1,850.8 | **8,264.1** |
| `cbo_opt46_..._2pp_100k` | 2,792.5 | 121.9 | 130.8 | 712.1 | **3,757.3** |
| `cbo_opt45_top4_2pp` | 2,709.1 | 119.2 | 123.8 | 682.2 | **3,634.3** |
| `biden_high_income_tax` | 1,495.0 | 92.6 | 38.2 | 229.1 | **1,854.9** |

against pooled bases of 9,103.9, 5,038.0, 4,894.5 and 1,797.9 at the same single
floors. Three shrink by 9.2%, 25.4% and 25.7%; `biden_high_income_tax` **grows**
by 3.2%, because the Green Book's $225,000 married-filing-separately floor is
$175,000 below the single floor the model applies to those returns today.

**Tier 1 aggregate, predicted:**

| | before | predicted |
|---|--:|--:|
| mean | 15.2% | **15.9%** |
| median | 11.4% | **10.7%** |
| within 15% | 16/26 | **17/26** |
| within 25% | 22/26 | **21/26** |

`cbo_opt45_top4_brackets_2pp` **enters** the within-15 set and
`cbo_opt46_agi_surtax_2pp_100k` **leaves** the within-25 set, which puts the CI
gate exactly on its floor: `--max-mean-error 20` passes with 4.1 points of room,
`--min-within-25pct 21` passes with **none**. That is registered here, in
advance, as the tightest constraint in the lane. If the outturn lands at 20 the
lane has failed its own gate and says so rather than moving the threshold.

**The decomposition, which is the actual result.** Taken alone the split makes
both Option 46 rows worse. Taken as the first of three terms it is what makes
them right:

| `cbo_opt46_agi_surtax_1pp_20k` | score | err |
|---|--:|--:|
| today (pooled floor, taxable-income base, flat TY2023) | −796.6 | 44.7% |
| + filing-status floors (**this lane**) | −723.1 | 49.8% |
| + AGI in place of taxable income | −1,016.1 | 29.4% |
| + base grown at the CBO Feb-2024 baseline's own nominal GDP, 3.878%/yr | **−1,309.0** | **9.1%** |

| `cbo_opt46_agi_surtax_2pp_100k` | score | err |
|---|--:|--:|
| today | −881.7 | 16.1% |
| + filing-status floors (**this lane**) | −657.5 | 37.4% |
| + AGI in place of taxable income | −824.2 | 21.6% |
| + base grown at 3.878%/yr | **−1,061.8** | **1.0%** |

So `cbo_opt46_agi_surtax_2pp_100k`'s **16.1% today is two errors cancelling a
third**: a base measured on taxable income rather than AGI (−22%), held flat
across a decade in which CBO's own baseline grows it 29% (−22%), against a floor
applied to 11.1M joint returns that JCT starts $100,000 higher (+34%). Removing
the third one first is what a correct mechanism does; it is also what makes the
row read worse. This is the `fra_2023_discretionary_caps` finding again —
"the old number measured the cancellation, not the fit" — and the lane expects
to be told so.

**Neither of the other two terms is in scope, and the reason is a falsification
test, not a preference.** `agi_inclusive_base` is set on
`medicare_surcharge_2pp` (1.5%), `illustrative_top_rate_5pp` (7.4%),
`illustrative_500k_2pp` (8.9%) and `warren_ultramillionaire_surtax_3pp` (19.0%)
as well, none of which has a filing-status boundary, so switching that base
would move four rows this lane has promised not to touch. Growing the base
touches every Generic row there is. Both go to §6.2 as carry-overs with the
arithmetic above attached.

**The anti-fitting disclosures.**

1. **The §2.2 rule for the statuses Option 46 does not name.** All three
   defensible readings were computed before the rule was fixed, and the shipped
   one is the **middle** of the three on both rows:

   | reading | 46.1 | 46.2 |
   |---|--:|--:|
   | shipped — HoH and MFS take the single amount | −723.1 / **49.8%** | −657.5 / **37.4%** |
   | HoH takes the joint amount | −712.9 / 50.5% | −649.1 / 38.2% |
   | MFS takes half the single amount (the literal §1411(b) half-of-joint under a joint ≠ 2× single reading) | −725.9 / 49.6% | −664.1 / 36.8% |

   The spread is **0.9 and 1.4 points** against levels of 49.8% and 37.4%: the
   rule for the two unnamed statuses is not what decides this row, and no
   reading of it rescues either. It is shipped on the §1411(b) argument, not
   because it is the best of the three — it is not.
2. **The preferential-share rule.** §2.3(b) ships. Rule (a) would have given
   20.8% on `cbo_opt45_top4_brackets_2pp` (against 12.4%) and 6.7% on
   `biden_high_income_tax` (against 9.2%) — better on one row, worse on the
   other, so neither reading is uniformly self-serving, and the double-removal
   argument decides it.
3. **No behavioural parameter moves.** ETI stays 0.25 with the standard 0.5
   factor on all four rows, so the 12.5% erosion is identical before and after
   and every predicted figure above is `rate × base × ordinary_share × 10 ×
   0.875` on a base that changed and nothing else.
4. **No constant in this lane equals a target over ten.** −1440.1/10 = −144.01,
   −1051.0/10 = −105.10, −569.5/10 = −56.95 and −245.9/10 = −24.59 appear
   nowhere; every number introduced is a threshold from a rate table or an
   option label, or an SOI cell.

**What does not move, and why it cannot.**

- **The fitted tier (21 @ 1.7%) and the reconstructions (34 @ 57.6%).** Every
  calibrated module reaches SOI through `get_bracket_distribution`, which this
  lane does not touch, and none of them constructs a `TaxPolicy` with a
  per-status threshold. Predicted: **0 rows change**.
- **Leave-one-out (18 @ 29.6% / 19.1% / 8).** `loo.py`'s derivations read module
  constants and factories, not `get_filers_by_bracket`. Predicted:
  **byte-identical output**, `--donor-matrix` included.
- **The 7 distributional benchmarks.** `distribution_engine.py` reads
  `get_bracket_distribution`. Predicted: unchanged.
- **Every shipped preset and the Tailor form.** No preset carries a per-status
  threshold and Tailor's `who` field takes one enum or one amount, so
  `threshold_by_filing_status` is `None` on all 53 presets and on the Tailor
  default. **Decision 6 is not expected to be triggered.** If a shipped number
  moves anyway, the lane adds the caption in its own commit and records here
  that the prediction was wrong.

## 4. Falsification tests

Written before the code; each fails the lane rather than being adjusted.

1. **The uniform-threshold control is exact.** For a range of thresholds
   ($0, $20,000, $103,350, $400,000, $1,000,000),
   `get_filers_by_status_thresholds(2023, {s: T})` must reproduce
   `get_filers_by_bracket(2023, T)` on `num_filers_millions`,
   `total_agi_billions`, `total_taxable_income_billions` and
   `total_tax_billions` to within 1e-9 relative. (Those four are unrounded; the
   pooled helper's `num_filers` passes through `int(round(...))`, so it is
   compared to within one return rather than exactly.) If the control fails, the
   apportionment is not neutral and the split's movement cannot be attributed to
   the floors.
2. **Table 1.2 agrees with Table 1.1 where it must.** Returns and AGI, class by
   class, to within one return and $1M; the status shares sum to 1.0 in every
   class. The taxable-income *disagreement* is asserted too, at the known
   $319B, so the reason for §2.1's construction is pinned in a test rather than
   only in prose.
3. **Only the four named Tier-1 rows move.** Every other row identical to the
   dollar, `medicare_surcharge_2pp` and `cbo_opt45_all_rates_1pp` included.
4. **No fitted-tier, reconstruction or LOO row moves at all**, and
   `run_loo.py --donor-matrix` output is byte-identical to §1.4.
5. **`threshold_by_filing_status=None` is byte-identical.** A frozen numeric
   assertion on a pooled policy, plus the 53-preset sweep and the Tailor
   default diffing clean.
6. **A split policy scores the same in every year of the window.** Years 2–10
   must equal year 1 to the cent — the test that the cache in §2.5 works and
   that a split policy does not silently fall back to the pooled formula after
   the first year.
7. **The split is monotone in the joint floor.** Raising the joint threshold
   above the single threshold must strictly shrink the base; lowering it below
   must grow it. A split that ignored its mapping would pass every other test.
8. **The `biden_high_income_tax` direction.** Its base must *grow*, because one
   of its four floors is below the pooled one. A lane that only ever shrinks
   bases has hard-coded the wrong relation.

## 5. What this lane will not do

- Not open `preregistered.py`, `holdout.py`, `loo.py`'s guards,
  `target_revisions.py`, any `KNOWN_SCORES` or `CBO_SCORE_MAP` **value**, any CI
  threshold, `tests/test_cold_holdout.py`'s anti-leakage invariant, or
  `tests/test_offset_sign_contract.py`.
- Not touch `fiscal_model/ptc.py`, `fiscal_model/tax_expenditures_core.py`,
  `fiscal_model/baseline.py`, `fiscal_model/data/capital_gains.py` or
  `scripts/run_validation_dashboard.py` — four other lanes are live on those.
- Not switch the AGI-inclusive rows from taxable income to AGI, and not grow the
  generic base across the window. Both are named in §3 with the arithmetic, both
  would move rows with no filing-status boundary, and both go to §6.2.
- Not make the threshold year-indexed, and so not model Option 45's 2026 revert
  (§2.4).
- Not give any preset or the Tailor form a per-status threshold. The field
  exists for a source that states one; no shipped surface does.
- Not touch the shared docs (`README.md`, `CLAUDE.md`, `docs/VALIDATION*.md`,
  `docs/METHODOLOGY.md`, `planning/MODELING_IMPROVEMENT.md`,
  `planning/NEXT_STEPS.md`, `CHANGELOG.md`). §2.1 of the modelling plan, its
  §6.2 item 25 and the Tier-1 paragraph of `CLAUDE.md` will all be stale after
  this lane, and a docs pass owns them.

Anything that moves outside this list is a finding, and gets written into §6.
