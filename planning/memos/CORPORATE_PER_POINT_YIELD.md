# Memo — what a percentage point of corporate rate is worth, and why the published answers differ

*Written 2026-09-05 against `main` @ `790caff`, after Wave 5. A research memo
with a lane recommendation at the end. **No model code changed**; the additions
are `fiscal_model/data_files/validation/corporate_rate_scores.csv` (18 published
estimates, transcribed with page references and annual paths) and
`scripts/corporate_yield_reconciliation.py`, which prints every table below.
Nothing here is a promise of attainment.*

Scope: `planning/lanes/W5_corporate_margin.md`'s parting question, and
`planning/MODELING_IMPROVEMENT.md` §6.2 items 22 and 23. Under §1's principles
and §4's prohibitions.

## 1. The question, and what the lane left standing

`cbo_opt64_corporate_rate_1pp` reads **62.3%** — CBO Option 64 prices +1pp at
−$135.7B over FY2025-2034 and the model says −$220.3B. After Wave 5 closed the
two payroll rows and the preferential-rate row, it is the **largest single row
in Tier 1**: 62.3 of the tier's 412.9 error units, **15.1%**, ahead of the AGI
surtax at 10.8%.

W5-B closed with a claim now sitting in the row's own `known_limitations` —
"CBO's option is $135.7B per percentage point … and Treasury's FY2025 Green Book
row is $192.8B, a 42% gap in which the LARGER rate change carries the LARGER
per-point yield" — and called it "a fact about the documents, not a repair".
**It is not a fact about the documents.** It compares two rows that price
different reforms, on a metric that is not comparable across statutory rate
levels, without normalising for the base each was written on. Three corrections,
each sourced in §2:

1. **Every corporate-rate option in every CBO *Options* volume is a JCT
   estimate** — all five carry "Data source: Staff of the Joint Committee on
   Taxation" verbatim. This is JCT against Treasury OTA, and `cbo_opt64`'s
   `ScoreSource.CBO` names the publisher rather than the estimator.
2. **Treasury's row is not a rate-only row.** From the FY2023 Green Book onward
   the chapter states the GILTI effective rate moves with the statutory rate —
   "The effective global intangible low-taxed income (GILTI) rate would increase
   to 14 percent under the proposal" (FY2024 and FY2025, report p. 2) — while
   the factory scored against it, `create_biden_corporate_rate_only`, sets
   `gilti_rate_change=0.0` and says "No international changes - just rate".
   **The only rate-only Green Book row is FY2022's.**
3. **Per-point dollars are the wrong metric.** A point off 35% is 1/35 of the
   base; a point off 21% is 1/21. The comparable quantity is the **implied
   marginal base**, `|total| / Δτ / 10`, invariant to the rate level.

On that metric the record is not two documents in disagreement but four
estimators on one window, and Treasury is the high one: Tax Foundation 55.1%,
JCT 55.9%, PWBM 64.4%, Treasury 79.5% — of each vintage's average base. The
model reads **90.8%**, and is fitted to the 79.5%.

## 2. The published record

Eighteen rows, all read from the issuing body's own document (cbo.gov returns
HTTP 403 here, so the CBO volumes came through Wayback mirrors of cbo.gov's own
files — primary documents, mirrored delivery). The eleven official rows are
below; the seven non-government ones are in §4b. `B_marg` and `share` are §4's
metric, carried here so the record reads as one table: the implied marginal base
`|10yr| / Δτ / 10`, and that base as a share of the vintage's own average base
from §3. Italicised shares are not clean readings — the 2020 volume's
denominator is a COVID outlier, JCX-42-21 is graduated.

| Source | Est. | Date | Window | Scope | Step | 10yr $B | per pp | B_marg | share |
|---|---|---|---|---|--:|--:|--:|--:|--:|
| Budget Options 2016, Opt 25 | JCT | 2016-12 | FY2017-2026 | graduated, 35% | +1pp | −100.3 | −100.30 | 1,003.0 | 88.0% |
| JCX-67-17 (TCJA conference) | JCT | 2017-12 | FY2018-2027 | rate only, 35% | −14pp | +1,348.5 | −96.32 | 963.2 | 86.3% |
| Options 2018, Opt 24 | JCT | 2018-12 | FY2019-2028 | rate only | +1pp | −96.3 | −96.30 | 963.0 | **52.6%** |
| Options 2020, Opt 19 | JCT | 2020-12 | FY2021-2030 | rate only | +1pp | −99.3 | −99.30 | 993.0 | *66.1%* |
| JCX-42-21 (BBB markup) | JCT | 2021-09 | FY2022-2031 | graduated | +5.5pp | −540.1 | −98.20 | 982.0 | *53.5%* |
| Options 2022 Vol. II, Opt 50 | JCT | 2022-12 | FY2023-2032 | rate only | +1pp | −129.3 | −129.30 | 1,293.0 | **57.1%** |
| **Options 2024, Opt 64** | JCT | 2024-12 | FY2025-2034 | rate only | +1pp | **−135.7** | **−135.70** | **1,357.0** | **55.9%** |
| Green Book FY2022 | Treasury | 2021-05 | FY2022-2031 | **rate only** | +7pp | −857.8 | −122.55 | 1,225.5 | **66.7%** |
| Green Book FY2023 | Treasury | 2022-03 | FY2023-2032 | rate + GILTI | +7pp | −1,314.6 | −187.79 | 1,877.9 | 82.9% |
| Green Book FY2024 | Treasury | 2023-03 | FY2024-2033 | rate + GILTI | +7pp | −1,325.8 | −189.39 | 1,893.9 | 78.1% |
| **Green Book FY2025** | Treasury | 2024-03 | FY2025-2034 | rate + GILTI | +7pp | **−1,349.9** | **−192.85** | **1,928.5** | **79.5%** |
| *model `derived`, +1pp* | *repo* | — | FY2025-2034 | rate only | +1pp | *−220.3* | *−220.28* | *2,202.8* | ***90.8%*** |

Four things this settles before any modelling question is asked.

**Two rows are graduated schedules and are not per-point observations.** The
2016 option's title says "Rates" plural because it moves every bracket at a 35%
top rate; JCX-42-21 is H.R. 5376 §138101 — 18% to $400,000, 21% to $5,000,000,
26.5% above, plus a recapture over $10,000,000 — so dividing by 5.5 understates
the top tranche's base, and it bundles a dividends-received-deduction change JCT
gives no separate line. **And the House-*passed* Build Back Better Act contains
no corporate rate change at all**: JCX-45-21 and JCX-46-21 contain the strings
`26.5` and `tax rate` zero times, the increase having been replaced by CAMT and
the buyback excise rather than rescored.

**Treasury's per-point yield jumps 53% between the FY2022 and FY2023 editions**
($122.55 → $187.79) and is then flat for two more. Two things change in that one
edition and the documents do not separate them: the GILTI bundling, and a BBBA
baseline ("a baseline that incorporates all revenue provisions of Title XIII of
H.R. 5376 … except Sec. 137601", NOTES p. iii). The FY2024 edition returns to
current law and the level does *not* fall back, which rules the baseline out as
the driver and leaves scope and the profit revision.

**No Green Book states a behavioural or macro assumption anywhere.** The words
*macroeconomic*, *static*, *dynamic scoring*, *behavioral response* and
*conventional* (in the scoring sense) appear in none of the four volumes. Treat
"Treasury's estimates are conventional" as an external convention about OTA
practice, not something these documents assert.

## 3. The baseline each score was priced against

Corporate income tax receipts, fiscal years, from each vintage's own recurring
supplemental budget-projections workbook (script table 2).

| Vintage | Pub | Window | Rate | Receipts 10yr $B | Avg base/yr $B |
|---|---|---|--:|--:|--:|
| Mar 2016 Updated Projections | 51384 | FY2017-2026 | 35% | 3,987.7 | 1,139.3 |
| Jun 2017 Update (pre-TCJA) | 52801 | FY2018-2027 | 35% | 3,907.2 | 1,116.3 |
| Apr 2018 Outlook | 53651 | FY2019-2028 | 21% | 3,846.6 | 1,831.7 |
| Sep 2020 Update | 56517 | FY2021-2030 | 21% | 3,152.4 | 1,501.1 |
| Jul 2021 Update | 57218 | FY2022-2031 | 21% | 3,856.5 | 1,836.4 |
| May 2022 Outlook | 57950 | FY2023-2032 | 21% | 4,754.9 | 2,264.2 |
| Feb 2023 Outlook | 58848 | FY2024-2033 | 21% | 5,089.4 | 2,423.5 |
| **Feb 2024 Outlook** | **59710** | **FY2025-2034** | 21% | **5,094.0** | **2,425.7** |

`Avg base/yr` is `receipts / statutory rate / 10` — the base which, taxed at the
statutory rate, reproduces the receipts the vintage projects. It already nets
credits, NOLs and shifting, which is what makes it the right denominator. The
script also carries Jan 2025 (60870) and Feb 2026 (61882) for the CRFB and Tax
Foundation rows. Two caveats: **the September 2020 vintage is a COVID outlier**
(FY2021 receipts projected at $122.8B against an actual of $371.8B), so any
share against it is far too large; and **Treasury, Tax Foundation and PWBM state
no baseline in CBO terms**, so their rows are normalised against the nearest CBO
vintage on the same window and flagged `(proxy)` — only the JCT rows put
numerator and denominator in the same house.

## 4. The implied marginal base, and the implied offset

The `share` column of §2 is the comparable metric, and `1 − share` is the
**implied offset** — the fraction of the average base a statutory point does not
reach, whatever the reason. Script table 3 prints both, with the seven
non-government rows summarised in §4b.

**Each estimator has a stable marginal share, and the estimators differ.** JCT's
three clean post-TCJA rows read **52.6%, 57.1%, 55.9%** — a 4.5-point spread
across six years and three baselines. Treasury's three rate-plus-GILTI rows read
**82.9%, 78.1%, 79.5%**; its one rate-only row reads **66.7%**. The
normalisation removes the baseline level entirely and what is left is not noise.

**The pre-TCJA rows agree with each other, which is the check that the metric
works.** At a 35% rate the two JCT readings are 88.0% and 86.3%; at 21% they are
52.6-57.1%. That break is arithmetic, not behaviour: `receipts / τ` is itself a
function of `τ`, because a higher rate buys more shifting and more credit use,
so the denominator is depressed at 35%. Within a rate regime the metric is
exact; no comparison below crosses that line.

## 4b. The same window, four estimators

| Source | Estimator | Scope | B_marg/yr | share |
|---|---|---|--:|--:|
| Biden Budget Tax Proposals (Jun 2024) | Tax Foundation | rate only | 1,336.9 | **55.1%** |
| **Options 2024, Opt 64** | **JCT** | rate only | 1,357.0 | **55.9%** |
| FY2025 Budget Proposal (May 2024) | PWBM | rate only | 1,561.4 | **64.4%** |
| **Green Book FY2025** | **Treasury OTA** | **rate + GILTI** | 1,928.5 | **79.5%** |
| *model `reported`, any step* | *this repository* | rate only | *1,996.0* | *82.3%* |
| *model `derived`, +1pp* | *this repository* | rate only | *2,202.8* | ***90.8%*** |

CRFB's Budget Offsets Bank publishes the only per-point figure in the record —
**"$140 billion/pt"**, FY2026-2035, normalising to 61.7% — but it is CRFB's own
calculation off CBO, so read it as a restatement of the JCT line.

**The model's marginal share is higher than every published estimate on the
record, and the benchmark it is fitted to is the second highest.** Three
estimators price a point at 55-64% of the average base; Treasury prices 79.5%
and is the only one of the four whose scope is not rate-only.
`biden_corporate_28` is the outlier of its own literature and the module was
tuned to it. Two limits: the proxy denominators mean the three non-JCT shares
carry a forecast difference as well as a modelling one, and **the shares
drift** — on FY2022-2031 the same three houses cluster tightly and high
(Treasury rate-only 66.7%, Tax Foundation 68.9%, PWBM 69.4%) and by FY2025-2034
two have fallen while Treasury has risen, as CBO's projected receipts rose 32%
between those windows.

### The check that this is a structure and not a coincidence

Year by year, against CBO's own February 2024 receipts path (script table 4):

| FY | B_avg | Opt 64 share | GB FY2025 share | model derived share |
|---|--:|--:|--:|--:|
| 2025 | 2,352.9 | 31.9% | 74.4% | 60.3% |
| 2026 | 2,340.0 | 54.3% | 76.4% | 83.2% |
| 2027 | 2,305.2 | **59.0%** | 79.4% | 87.8% |
| 2028 | 2,336.7 | **58.6%** | 78.6% | 90.1% |
| 2029 | 2,385.2 | **59.1%** | 76.9% | 91.9% |
| 2030 | 2,431.4 | **59.2%** | 76.0% | 93.7% |
| 2031 | 2,470.0 | **58.7%** | 79.8% | 95.9% |
| 2032 | 2,472.4 | **59.1%** | 83.7% | 99.7% |
| 2033 | 2,540.0 | **58.7%** | 84.4% | **100.9%** |
| 2034 | 2,622.9 | **59.9%** | 84.4% | **101.6%** |

**JCT's Option 64 is 0.59 × (CBO's own baseline corporate receipts ÷ 21%) × Δτ,
in every year from FY2027 to FY2034, flat to 2.1%** — FY2025 and FY2026 being
the tail of a January 2025 effective date. That is not a behavioural response
with a shape; it is a level. The model's column runs 0.83 in FY2026 to **1.016**
in FY2034: by FY2033 it scores a percentage point of statutory rate against
*more* base than the entire baseline corporate tax implies exists. No marginal
base can exceed the average base it is part of, so that is an internal
inconsistency independent of any target.

## 5. Diagnosis

**(a) Baseline profit level explains most of the drift within each estimator and
none of the gap between them.** JCT's per-point yield went $96.30 → $135.70
between the 2018 and 2024 volumes, +40.9%; its baseline's average base went
1,831.7 → 2,425.7, +32.4%; its marginal share went 52.6% → 55.9%, +6.3%.
1.324 × 1.063 = 1.407 — the drift is the base, to a decimal, on the one series
where numerator and denominator come from the same house. Treasury's FY2022 →
FY2025 move has a profits boom in it too — NIPA pre-tax corporate profits rose
2020 → 2021 from $2,522.9B to $3,366.8B, +33%, and SOI's income subject to tax
from $1,780.3B (TY2020) to $2,422.1B (TY2021), +36% — but its move is
confounded with the FY2023 scope change and cannot be attributed the same way.
**Normalising by the vintage removes the level and the gap survives**: on the same
window and the same Feb 2024 baseline, Option 64 reads 55.9% and the FY2025
Green Book 79.5%. So the vintage story W5-B's anchor-year sensitivity suggested
— TY2019 → 4.2%, TY2022 → 62.3% — is a level coincidence: TY2019's
credit-realized base ($1,163.7B) happens to sit near JCT's marginal base
($1,357.0B). The lane's decision to fix "latest published" in advance is
vindicated by exactly this arithmetic.

**(b) Direction and size: not identified, and the apparent effect is
confounded.** The lane's anomaly compares a 2024 rate-only 1pp JCT row with a
2024 rate-plus-GILTI 7pp Treasury row. On rows that share a scope the ordering
reverses: Treasury's rate-only 7pp row implies $1,225.5B and JCT's
contemporaneous 1pp options imply $993.0B (2020) and $1,293.0B (2022) — the 7pp
row sits between them. Where the same estimator prices a big step and a small
one, JCT's 14-point cut from 35% implies $963.2B and its 1-point increase from
21% a year later implies $963.0B. **Nothing in the record supports a per-point
yield that rises with the step.**

There is exactly one published *direction* comparison and it goes the way theory
says. Tax Foundation's *Options 2.0* prices both directions in one edition, one
model, one window: Option 36 raises 21% → 28% for $886.3B, **$126.6B per
point**; Option 11 cuts 21% → 15% for $978.9B, **$163.2B per point**. A point of
cut costs 29% more than a point of increase yields — what a base that expands
when the rate falls produces, and what `reported` mode gets backwards for the
wrong reason, since `abs(static_effect)` makes a cut cost more by discarding a
sign (§6.2 item 22). `derived` signs it correctly, returning $252.36B per point
on a 14-point cut against $220.28B on a 1-point increase: a 15% asymmetry in the
right direction, about half the published one. That is the closest thing to a
validation this module's behavioural channel has, and it rests on one pair.

**(c) Stated behavioural assumptions are the residual, and nobody publishes
enough to measure them.**

- **CBO's 2018 Option 24 is the only volume with a narrative**, and it names one
  channel as included: "An increase in the corporate tax rate would increase
  corporations' ability to use tax credits, rather than carrying them forward to
  a future year … That use of credits would reduce revenues", plus unspecified
  "strategies to reduce the amount of taxes they owe". Profit shifting and form
  shifting appear only under "Other Effects", as arguments about the option; the
  capital-investment channel is explicitly excluded. Option 64 itself has no
  narrative at all.
- **Option 64 carries no income-and-payroll-tax offset footnote**, though the
  facing Option 63 does. The individual-side offset the row's
  `known_limitations` calls "the largest single unmodelled channel" is **not in
  JCT's estimate either**. Refuted, not unmeasured.
- **JCT's corporate model has five published behavioural margins** (JCX-46-11,
  p. 10) — dividends and retained earnings, capital structure, equity
  valuations, repatriations, entity choice, "in all cases … estimated within the
  fixed GNP constraint" — but **no official estimator publishes a parameter**:
  JCT's only elasticity monographs are capital gains and the individual ETI,
  PWBM defers to unstated "estimates of profit shifting elasticities from JCT
  staff", and Treasury publishes nothing.
- **One house states a parameter and it is the module's own.** Tax Foundation
  (Feb 2021) uses a **0.8** profit-shifting semi-elasticity — Heckemeyer &
  Overesch, the same source and value as `PROFIT_SHIFTING_SEMI_ELASTICITY`.
  Respectable company, not a validation: their 0.821 is a semi-elasticity of
  *multinational affiliate* pre-tax profit with respect to the **tax-rate
  differential** between jurisdictions, and both the module and Tax Foundation
  apply it to the whole domestic base with respect to the **own statutory
  rate**. The algebra around it is right — `B₁ = B₀(1 − βΔτ)` valued at the new
  rate gives an offset in the rate *level*, which is what `corporate.py:212`
  computes — but the parameter covers more base than it was estimated on.

So the 1.42× between JCT's 55.9% and Treasury's 79.5% decomposes into a **scope**
factor and an **estimator** factor that multiply: Treasury rate-only 66.7%
against rate-plus-GILTI 79.5% is 1.19×, and JCT 55.9% against Treasury rate-only
66.7% is 1.19×; 1.19 × 1.19 = 1.42. The first has a document behind it. The
second does not — but §4b shows it is not a two-house quarrel: Tax Foundation
lands on JCT's side and PWBM in between, on the same window.

**In this order: (a) sets the level and is closable; (c) sets the wedge and is
not; (b) is not there.**

## 6. Where the model sits

`fiscal_model/corporate.py`, `derived` mode:

```
Δτ × [SOI income subject to tax, TY2022 = 2,879.1] × 1.04^(t−2022)
     × [credit realization = 0.7085]          # SOI after/before credits
     × (1 − 0.8 × (τ₀ + Δτ))                  # Heckemeyer & Overesch
     × [IRC §6655 phase: 0.75, then 0.99038]
```

Three separable defects, in descending size:

1. **The base outgrows the vintage.** 4%/yr against CBO's own Feb 2024 corporate
   receipts at 1.43%/yr over FY2026-2034, and against both estimators' implied
   marginal bases at 2.69% (JCT) and 2.72% (Treasury) — figures that agree with
   each other to three basis points. This drives the model's share past 1.0.
2. **The level is above every published estimate**, 90.8% at 1pp against
   Treasury's 79.5%, PWBM's 64.4% and JCT's/Tax Foundation's 55-56%.
3. **β and a marginal share are not separable.** JCT's 0.59 already contains
   whatever behaviour JCT applies; a lane that keeps `β = 0.8` and adds a
   realization share double-counts.

A fourth, smaller: the model's §6655 first-year factor is 0.757, where JCT's
options run 0.591-0.732 first-to-second-year and Treasury's FY2022/FY2023 rows
run 0.593/0.601. Treasury's is a *statutory blend* (21% plus 7% times the 2022
share of the taxable year), which the module has no concept of; JCT's is
unexplained, because no volume mentions payment timing anywhere.

**The counterfactual** (script table 5): projecting the base off the scored
vintage's own receipts — `receipts_t × Δτ / 0.21`, already credit-realized so
the 0.7085 ratio drops out — and keeping everything else:

| | +1pp vs −135.7 | +7pp vs −1,347.0 |
|---|--:|--:|
| today (`derived`) | −220.28, **62.3%** | −1,452.14, **7.81%** |
| vintage-projected base | −193.29, **42.4%** | −1,274.22, **5.4%** |

Hand arithmetic on published inputs, to be checked by any lane that builds it.
It closes 20 points of the Tier 1 row and 2.4 of the calibrated row, and does
**not** close the residual, because the residual is not a vintage problem.

The number that *would* close it is printed in the script and named here so
nobody arrives at it by accident: the total factor reproducing Option 64 is
**0.5785**, and JCT's own steady-state share is **0.590**. Adopting 0.59 is
reading JCT's answer backwards, and §4 forbids it.

## 7. Recommendation — (iii), both, target side first

### (ii) Target side: three records to correct, no target to move

None of these changes a number. All three are provenance-lane work; a modelling
lane may not open `preregistered.py`, `benchmark_sources.py` or `cbo_scores.py`.

1. **`biden_corporate_28` is `line_item_differs`, not `line_item`.** Its
   `BenchmarkSource` calls the FY2025 Green Book row a clean line item; the
   row's own chapter says the estimate carries GILTI 10.5% → 14%, and the
   factory scored against it sets `gilti_rate_change=0.0`. **The figure is right
   and the reform it names is broader than the thing the model builds** —
   exactly the class `PROVENANCE_wave4.md` created `line_item_differs` for, and
   it is the only corporate benchmark with a document behind it, so the 3.73%
   the fitted path reports is measuring a scope mismatch as well as a fit. **The
   row is also an outlier in its own literature**: on its own window Tax
   Foundation prices the same reform 31% lower and PWBM 19% lower. The
   `alternatives` field should mark the FY2022 figure as the rate-only one.
2. **`cbo_opt64_corporate_rate_1pp`'s estimator is JCT, not CBO** — CBO's own
   page and table say "Data source: Staff of the Joint Committee on Taxation".
   A distinct provenance class from the JCX-35-25 line items, worth one field.
   (Also undocumented: Table 1-1 gives 136.0 in `cbo_options_2025_2034.csv`
   where the alternatives CSV and the target carry 135.7 — CBO's own rounding.)
3. **Rewrite the row's `known_limitations`.** Its first entry states the
   42%-gap-with-inverted-size claim this memo refutes; its second names the
   individual-side interaction as the largest unmodelled channel when Option
   64's own table shows JCT applies no such offset. Replace both with the scope
   difference and the estimator difference in the marginal share. The third
   entry, on §174 and bonus depreciation inflating the TY2022 anchor, can now be
   **sized**: SOI's income subject to tax was 71.8% of NIPA pre-tax corporate
   profits on average over TY2019-2021 and 79.8% in TY2022, so TY2022's base is
   **11.1% above** what the prior ratio gives — an upper bound, since it charges
   the whole ratio move to the timing items. Deflating by it takes the row to
   46.1%, not to CBO.

### (i) Model side: a lane with one mechanism, and a named thing it will not do

**Lane C — project the corporate base off the scored vintage.** The mechanism is
the one Wave 5 C used on the realizations base, and the precedent for reading a
vintage path in an *uncalibrated* shape is W5-A's payroll base, "CBO's own
February 2024 wage path times one covered-earnings ratio measured on completed
history": the ratio is measured, the path is the vintage's. The tension that
creates belongs in the lane's own §1 — `validation/cbo_options.py` claims every
uncalibrated shape is vintage-independent and `_derived_rate_effect`'s docstring
says it deliberately reads no baseline level, so that claim needs re-scoping to
"reads no level *fitted to a benchmark*", which is what it was protecting.

Files: `fiscal_model/corporate.py` (the `derived` branch,
`CORPORATE_BASE_GROWTH`, the §6655 closed form — which assumes a constant growth
rate and stops being closed-form on a path), `tests/test_corporate_derived.py`,
and the four lines of `validation/core.py`'s `corporate_rate` shape if the mode
pin changes. Nothing else. `reported` is untouched, so no shipped preset moves
and no Decision 6 caption is owed.

| Row | Now | Predicted |
|---|--:|---|
| `cbo_opt64_corporate_rate_1pp` | −220.28, 62.3% | **−193 ± 5, 42 ± 4%** |
| `biden_corporate_28` **reported** | −1,397.21, 3.73% | **unchanged** |
| `biden_corporate_28` **derived** | −1,452.14, 7.81% | **−1,274 ± 20, 5.4 ± 1.5%** |
| `trump_corporate_15` reported | +1,917.98, 0.11% | unchanged |
| `trump_corporate_15` derived | +1,698.57, 11.53% | moves; not predicted — 20% of it is a depreciation constant this lane does not open |
| Decision 1 means | 1.92% / 9.67% | reported unchanged; derived improves, does not win |
| Tier 1 mean | 15.9% | **15.1 ± 0.2%** |
| Fitted tier, LOO, every shipped preset | — | unchanged |

**And the thing the lane may not do.** It may not assert a marginal-realization
ratio. The only component of the JCT-Treasury wedge with a published mechanism
behind it is the one CBO's 2018 option text names — credit carryforwards, which
§38(c) and §904(c) unlock as the rate rises, so *marginal* absorption exceeds the
*average* ratio the module applies. SOI Table 11 publishes claimed credits, not
the carryforward stock; the stock is in the Form 3800 and Form 1118 statistics,
which is a data-acquisition item, not a constant. CAMT — which begins in TY2023,
after every SOI year the module reads — is a second such item. **A lane that
asserts a share instead of deriving one has failed even if the row lands.**

### (iii) Leave-one-out — §6.2 item 23, answered

**The corporate module cannot be given an honest leave-one-out row today, and
`loo.py` is not what is stopping it.** LOO holds out one benchmark's fitted
constant and asks whether the machinery calibrated on the *others* can put it
back. The module has one fitted constant, `BASELINE_TAXABLE_PROFITS_BILLIONS`,
and two benchmarks — and one of those, `trump_corporate_15`, has provenance
`model_estimate`: its target is the model's own output, so re-deriving the base
from it reconstructs the constant from itself, which is the leakage
`LEAKAGE_TOLERANCE` exists to catch. The honest outcome is
`not cross-validatable`.

**What would change that is on this memo's own table.** The FY2022, FY2023 and
FY2024 Green Books publish the *same 7pp reform* on three further windows and
vintages, each with a full annual path, all transcribed in the new CSV.
Registering the **FY2022 row** as a second calibrated benchmark — with its own
`effective_start_year=2022` and window, under the manifest's rules — would give
the module a second published target, make it cross-validatable for the first
time, and test precisely this memo's hypothesis, because FY2022 is the
**rate-only** row and its implied marginal base is 36% below FY2025's. A base
anchored on a vintage reproduces that difference; a fixed base cannot. A
yardstick decision, and the owner's.

## 8. What could not be verified

- **The size of the GILTI leg inside Treasury's corporate-rate row.** Never
  printed, and not obtainable by differencing editions: FY2022 excludes it (the
  global minimum tax was a separate $533,503M row), FY2023 is on a BBBA baseline
  with a 20% GILTI rate, and FY2024/FY2025 route 21% → 14% through the corporate
  row and 14% → 21% through a separate $373,919M international row. §5's 1.19×
  is inferred from the FY2022 rate-only share, not read.
- **Option 64's text beyond its four sentences.** There is none; the 2020, 2022
  and 2024 volumes are short-form.
- **Treasury's, Tax Foundation's and PWBM's baselines in CBO terms.** All
  non-JCT shares are computed against a proxy vintage. Relatedly, March 2016's
  `51135-2016-01` economic workbook is not archived, so that vintage has
  receipts but no profits or GDP.
- **Tax Foundation's two 2024 readings** (−$935.8B in June with a stated window,
  −$1,045B in August with none) do not reconcile; §4b uses the first, and the
  second moves the share 55.1% → 61.5% without changing the ordering. Its
  *Options 3.0* edition carries the same sign on its 28% and 15% rows where
  *Options 2.0* carries opposite signs, so no cut-versus-increase comparison is
  drawn from it.
- **Dowd, Landefeld & Moore (2017)** and **Gruber & Rauh (2007)** are paywalled;
  their figures reach this memo only secondhand and neither is used above.

## 9. Sources

**Every score in §§2-4b, with its URL, table, page and annual path, is in
`fiscal_model/data_files/validation/corporate_rate_scores.csv`**, and
`scripts/corporate_yield_reconciliation.py` recomputes every table. Documents
cited here but not scored in that file:

- **JCT method**: JCX-46-11, *Summary of Economic Models and Estimating
  Practices* (2011), p. 10 (the five corporate margins); JCX-69-17, pp. 6-7
  (profit shifting is inside conventional estimates); JCX-14-13, p. 8 (75/25
  capital/labour); *Revenue Estimating Process* (Jan 2025), slides 18 and 20
  (stacking; conventional ≠ static). JCX-45-21 and JCX-46-21 are the negative
  result on the House-passed BBB.
- **CBO baselines**: pubs 51384, 52801, 53651, 56517, 57218, 57950, 58848,
  59710, 60870, 61882 — recurring supplemental workbooks
  `51118-<yyyy>-<mm>-budgetprojections.xlsx`, read through Wayback mirrors of
  cbo.gov's own files.
- **Data**: IRS SOI *Corporation Income Tax Returns Complete Report* Table 11,
  TY2019-2022, as transcribed in
  `fiscal_model/data_files/corporate/soi_table11_corporate_tax_items.csv`;
  actual FY corporate receipts from Treasury MTS Table 4 via the Fiscal Data
  API, cross-checked digit-for-digit against OMB *Historical Tables* Table 2.1
  (FY2027 Budget); NIPA pre-tax corporate profits from BEA Table 1.12 via FRED
  `A053RC1A027NBEA`.
- **Heckemeyer & Overesch**, ZEW DP 13-045 (2013); *Canadian Journal of
  Economics* 50(4), 2017 — the module's `β = 0.8`, discussed in §5(c).
