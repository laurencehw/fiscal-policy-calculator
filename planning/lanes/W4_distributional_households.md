# Lane W4-1 — Distributional pipeline: a household universe

*Pre-registered 2026-09-02 against `origin/main` @ `5deef17`, before any code
change. Outturn appended at the end of the file, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §6.2's carry-over — the tax-unit
versus household universe that lane L3 named but could not close from inside a
credits lane. L3's finding, in one sentence: putting the ARP Recovery Rebate on
return-level data removed a cancellation and took the ARP distributional table
from 4.76pp to 7.77pp, because the model's bottom quintile is CPS **tax units**
ranked by AGI against CBO's **households** ranked by size-adjusted income before
transfers and taxes, so the model books 53% of the bundle where CBO books 34%.

---

## 1. Starting numbers

All from the branch point, `5deef17`.

### The seven distributional tables

`python -c "from fiscal_model.validation.cbo_distributions import
run_full_cbo_jct_validation; from fiscal_model.validation.benchmark_runners
import default_model_runner; ..."` — the same call `readiness.py`,
`run_validation_dashboard.py` and `api.py` all make.

| # | Benchmark | Source doc | Grouping | Engine path | Err (pp) | Rating |
|---|---|---|---|---|--:|---|
| 1 | Tax Cuts and Jobs Act, calendar 2018 | CBO 54796 | decile | **synthetic** | 0.00 | excellent |
| 2 | TCJA conference agreement, calendar 2019 | JCX-68-17 | AGI class | **synthetic** | 2.10 | good |
| 3 | **American Rescue Plan refundable credits, 2021** | CBO 56952 | quintile | **microsim** | **7.77** | acceptable |
| 4 | SALT cap repeal, 2024 | JCX-4-24 | AGI class | **microsim** | 5.86 | acceptable |
| 5 | Corporate rate 21% to 28%, 2022 | JCX-32-21 | AGI class | **synthetic** | 2.51 | good |
| 6 | TCJA individual-provisions permanent extension, 2026 | CBO 60007 | decile | **synthetic** | 0.74 | excellent |
| 7 | P.L. 119-21 tax and cash-transfer provisions, 2026 | CBO 61367 | decile | **synthetic** | 3.96 | good |

The "engine path" column is the first thing this lane had to establish and it
is not in any existing document. `policy_to_microsim_reforms` returns a
non-empty reform dict for **two** of the seven: the ARP bundle's three
components (`create_biden_ctc_2021`, `create_biden_eitc_childless`,
`create_arp_recovery_rebate`) and `create_repeal_salt_cap`. The other five —
every `TCJAExtensionPolicy` and the `CorporateTaxPolicy` — return `{}` and take
the synthetic bracket-aggregate path, which aggregates **IRS SOI return counts**
and has no household layer to build on at all. Section 3 draws its predictions
from that fact and not from the brief's expectation that four tables move.

### The ARP table, row by row

| quintile | model share | CBO share | err (pp) | model avg | CBO avg |
|---|--:|--:|--:|--:|--:|
| Lowest | 53.4% | 34.0% | **19.42** | −$892 | −$2,800 |
| Second | 20.0% | 28.0% | 8.03 | −$954 | −$3,150 |
| Middle | 14.1% | 20.0% | 5.86 | −$949 | −$2,450 |
| Fourth | 11.9% | 12.0% | 0.13 | −$1,030 | −$1,620 |
| Highest | 0.6% | 6.0% | 5.40 | −$55 | −$920 |

### The SALT table, row by row (the microsim control)

| AGI class | model share | JCT share | err (pp) |
|---|--:|--:|--:|
| $100k–$200k | 3.0% | 5.5% | 2.54 |
| $200k–$500k | 26.6% | 28.1% | 1.48 |
| $500k–$1M | 39.8% | 27.9% | 11.87 |
| $1M+ | 30.6% | 38.2% | 7.56 |

### The other batteries (this lane must not move any of them)

| battery | command | value |
|---|---|---|
| Tier 1 out-of-sample | `cold_holdout.py` | **26 cases, 31.0% mean, 13/26 within 15%, 19/26 within 25%** |
| Calibrated fitted | `cold_holdout.py` | **28 policies, 2.0% mean, 28/28 within 15%** |
| Unfitted reconstructions | `cold_holdout.py` | **26 policies, 61.8% mean, 5/26 within 15%, 9/26 within 25%** |
| Tier 2 leave-one-out | `run_loo.py --donor-matrix` | **18 cases, 28.4% mean, 16.5% median, 9/18 within 15%, 4 not x-val** |
| LOO per module | | Payroll 3.8% (n=3) · Estate 10.4% (n=2) · AMT 73.9% (n=2) · Credits 20.5% (n=3) · Expenditures 30.2% (n=5) · CapitalGains 39.6% (n=3) |

### The microdata, as it stands

`fiscal_model/microsim/tax_microdata_2024.csv`, 78,727 rows, 25 columns, 7.0 MB.
Rebuilt from the cached CPS ASEC 2024 extract with
`python -m fiscal_model.microsim.data_builder --data-dir <cache>/extracted`,
the output is **byte-identical** to the committed file
(SHA-256 `bbd92b66a43bed0d25d8bfbb3d372ef92d6265b99c8ee955a085d3dec4c24bca`),
so the by-script rebuild L3 established is reproducible and this lane can add
columns to it without a provenance argument.

Facts established from the branch point's own data, before any code:

| quantity | value |
|---|--:|
| weighted tax units | 191,113,962 |
| distinct households in the file | 56,251 |
| weighted households, `HSUP_WGT / 100` | **132,391,925** |
| weighted persons, `HSUP_WGT/100 × H_NUMPER` | **320,890,854** |
| households where `Σ member_count == H_NUMPER` | **56,251 of 56,251** |
| tax units with AGI ≤ 0 | 33.8M (17.7% of units) |
| tax units with AGI < $35,000 — the engine's "Lowest Quintile" | **96.8M (50.6% of units)**, mean AGI $8,062 |

Two of those matter more than the rest.

**The tax-unit construction partitions every person exactly once.** `Σ
member_count` equals the CPS household roster count `H_NUMPER` in all 56,251
households, so aggregating tax units back to households is exact arithmetic, not
an imputation.

**The engine's "quintiles" are not quintiles.** They are the fixed 2024 dollar
thresholds `$35k / $65k / $105k / $170k` in
`distribution_grouping.get_group_thresholds`, and on the CPS tax-unit universe
the lowest of them holds **50.6% of tax units**, not 20%. The 7.77pp is
therefore two errors compounded — the wrong universe *and* a bucket boundary
that was set for a different population — and this lane separates them by
leaving the tax-unit path's fixed thresholds untouched and computing the
household path's cut points from the ranking, as CBO does.

---

## 2. The mechanism (CBO's published methodology, not a fit)

Four definitions, all CBO's, none tuned to a benchmark.

**Unit.** A household is the people sharing a housing unit, whatever their
relationship. The CPS `H_SEQ`/`PH_SEQ` household sequence number is that unit,
and it is already carried in the derived microdata as `household_id`.

**Ranking income.** CBO: *"Income before transfers and taxes is market income
plus social insurance benefits."* Market income is *"labor income, business
income, capital gains (profits realized from the sale of assets), capital income
excluding capital gains, income received in retirement for past services, and
other nongovernmental sources of income"*; social insurance benefits are
*"Social Security and Medicare benefits, regular unemployment insurance ... and
workers' compensation"* (CBO, *The Distribution of Household Income*,
[publication 60706](https://www.cbo.gov/publication/60706); methodology working
paper [58508-WP](https://www.cbo.gov/system/files/2022-12/58508-WP.pdf)).

On the columns this file carries, that is exactly
`agi + social_security` — the file's `agi` is
`wages + interest + dividends + capital_gains + unemployment`, so the sum is
market income (wages, interest, dividends, realized gains) plus social insurance
(regular UI, Social Security). Three CBO components the CPS extract does not
carry are named as the gap rather than proxied: business income, retirement
income for past services other than Social Security, and the value of Medicare
benefits.

**Size adjustment.** CBO: *"CBO calculates adjusted household income by dividing
household income by the square root of the number of people in the household,"*
and *"CBO adjusts income for household size only for the purpose of ranking
households and assigning them to income groups. All other income measures in the
agency's distributional analyses are unadjusted."* So the exponent is ½, it is
applied only to the ranking key, and every reported dollar stays unadjusted.

**Group formation.** CBO ranks *individuals* by their household's adjusted
income before transfers and taxes and cuts that ranking into groups *"each
containing roughly an equal number of people"*; *"the quintiles contain equal
numbers of people, but because households vary in size, quintiles generally
contain unequal numbers of households."* Reported averages are then per
household.

Computed on the branch point's microdata, that ranking gives size-adjusted
income before transfers and taxes cut points of **$20,514 / $38,162 / $60,527 /
$97,946**, and a bottom people-quintile of **29.9M households / 64.2M people**,
mean size 2.15, mean income before transfers and taxes $13,366. Against the
current path's 96.8M tax units at mean AGI $8,062, that is the whole lane in two
lines.

---

## 3. What the lane changes

1. **Data.** `data_builder.py` emits two more columns — `household_weight`
   (`HSUP_WGT / 100`, the CPS household supplement weight) and
   `household_persons` (`H_NUMPER`, the roster count). Both come from
   `hhpub24.csv`, which the builder already reads and already merges; neither is
   derived or imputed. The tax-unit construction rules do not change, so the
   existing 25 columns must stay byte-identical and every existing summary
   statistic must be unmoved. The provenance sidecar is rewritten by the same
   builder.
2. **Engine.** A household layer aggregates tax units to households by
   `household_id`, ranks by size-adjusted income before transfers and taxes,
   forms people-weighted groups, and reports per-household averages and shares.
   `DistributionalEngine` gains `unit="tax_unit"` (default, unchanged behaviour)
   vs `unit="household"`, and `DistributionalAnalysis` records which universe
   actually produced the table — so a synthetic fallback reports `tax_unit`
   honestly instead of claiming a household ranking it never did.
3. **Registration.** Each benchmark declares the universe its source ranks on,
   with the source's own sentence quoted: CBO's four tables (54796, 56952,
   60007, 61367) on `household`; JCT's three (JCX-68-17, JCX-4-24, JCX-32-21) on
   `tax_unit`, because JCT reports by AGI class of tax-filing units.
4. **One arithmetic correction on the way past.**
   `_combine_distributional_results` reports a merged component's per-group
   dollar average as the *mean* of the components' averages
   (`tax_change_avg_sum / avg_weight`, `avg_weight` counting components) where it
   should be the *sum* — three components, so the ARP row's dollar column reads
   a third of what it should, which is exactly the −$892 against CBO's −$2,800
   above. It is a display quantity: `compare_distribution` scores shares, and
   the shares are already dollar-weighted and correct. Fixing it must move no
   pp error at all, and that is asserted, not assumed.

Nothing else. No constant is fitted to a benchmark, no target is edited, no
threshold in the rating rule moves, and the tax-unit path's fixed dollar
thresholds are left exactly as they are.

---

## 4. The prediction

**Headline: one table moves, and it is the ARP table. The brief expected the
four CBO-universe tables to move; three of them cannot, because they run on the
synthetic bracket path where no household layer exists. Registering those three
on `household` is therefore a declaration about the source, not a change to a
number, and I am pre-registering that as the lane's main negative result.**

### Rows I expect to move

| Row | Now | Predicted band | Point | Direction |
|---|--:|--:|--:|---|
| **ARP 2021 distributional** | **7.77pp** | **1.5pp to 6.0pp** | **3.5pp** | much better; back into `good` |
| ARP lowest-quintile share | 53.4% vs 34.0% | **26% to 40%** | 33% | the whole of the 19.42pp row |
| ARP highest-quintile share | 0.6% vs 6.0% | **1% to 6%** | 3% | better; households pool a rebate-eligible earner with an ineligible one |
| ARP per-household dollar column | −$892 … −$55 | roughly ×3, then reranked | ≈ −$2,700 … −$700 | the merge fix plus the universe |

The reasoning. Under a household universe the bottom people-quintile is 29.9M
households — 22.6% of all households — holding 64.2M people, against the current
path's 96.8M "lowest quintile" tax units, 50.6% of the universe. The 33.8M tax
units at AGI ≤ 0 are dependent filers, students and secondary units that a
household ranking never separates from the household that supports them; under
full refundability they currently collect the whole ARP credit inside the bottom
bucket. Folding them into their households, and letting Social Security count in
the ranking so retirees stop sorting to the bottom on AGI alone, has to move mass
upward. A flat $1,400-per-person rebate paid into people-weighted quintiles is
20% per quintile before phase-outs; the CTC's refundable leg and the childless
EITC then tilt it down-income, which is how CBO gets 34/28/20/12/6. Landing
between those two shapes is what the band describes.

**If it lands above 6.0pp the household universe is not the binding constraint,
and that — not the ARP number — is the lane's finding.** The candidates would
be the missing CBO income components (business income, retirement income,
Medicare's value), the absence of means-tested transfers from the CPS extract,
or the component-merge approximation standing in for one combined reform.

### Rows I expect NOT to move

- **Tables 1, 2, 5, 6, 7 — unmoved to the hundredth.** Five of the seven run on
  the synthetic bracket path, which this lane does not touch. Tables 1, 6 and 7
  are registered on `household` and will *say* so; their numbers stay
  0.00 / 0.74 / 3.96 because `calculate_tcja_effect` still builds its decile
  tiers out of CBO 54796 and CBO 60007 directly. Tables 2 and 5 are registered
  on `tax_unit`, which is what they already are.
- **Table 4, SALT cap repeal — unmoved to the hundredth, and this is the real
  control.** It is the *other* microsim benchmark. It is registered on
  `tax_unit` because JCT reports by AGI class of filing units, so the household
  code must be reachable, exercised by ARP, and completely inert here. **5.86pp
  to the hundredth.** Anything else means the tax-unit path was changed by
  accident.
- **Tier 1 — 26 cases, 31.0%, 13/26, 19/26.** No pre-registered out-of-sample
  case runs the distributional engine at all; the battery scores revenue.
- **Calibrated fitted tier — 28 policies, 2.0%, 28/28.** Same reason.
- **Unfitted reconstructions — 26 policies, 61.8%, 5/26, 9/26.** Same reason.
- **Leave-one-out — 18 cases, 28.4% mean, 16.5% median, 9/18, 4 not x-val**, and
  every per-module figure. LOO scores revenue through `credits_core.py`,
  `amt.py`, `payroll.py` and friends; the household layer is downstream of all
  of them.
- **The rating rule and the CI gate.** `compare_distribution`'s
  2/5/10pp rating thresholds, `cold_holdout.py --max-mean-error 40
  --min-within-25pct 18`, `run_loo.py --max-mean-error 75`, the
  anti-leakage invariant and `tests/test_preregistration.py` are all untouched.
- **The app default.** `DistributionalEngine()` with no argument is
  `unit="tax_unit"`, which is byte-for-byte today's behaviour, so no preset, no
  share link and no rendered table changes.

### Two things that could move and I am naming in advance

1. **The microdata file is rebuilt.** Every consumer —
   `soi_calibration.py`, `filing_threshold.py`, `top_tail.py`, `/health`'s
   microdata component, the state calculator, the multi-model TPC pilot — reads
   the rebuilt file. The construction rules are unchanged and the 25 existing
   columns must be byte-identical, so nothing downstream may move. **If a
   summary statistic moves, the rebuild is the finding, not the distributional
   numbers.** The file grows by two columns; it must stay close to 7.0 MB and
   well under 8.
2. **The merge fix changes a displayed dollar column.** The ARP row's
   `tax_change_avg` triples. No pp error may move as a result, and the lane
   asserts that separately from the universe change so the two are not
   confounded.

Anything that moves outside these lists is a finding, and goes in §5.

---

## 5. Outturn

*Appended in the last commit, after the code.*
