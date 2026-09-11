# Next Steps — Fiscal Policy Calculator

> Roadmap last reviewed April 2026; the validation scorecard below was re-derived 2026-09-11 (post-Wave-C). This file tracks roadmap items beyond the current shipped branch.

For a manuscript-focused path to citation-grade quality, see [MANUSCRIPT_95_PLUS.md](MANUSCRIPT_95_PLUS.md). For repo-grounded go/no-go gates on the two biggest upgrades, see [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md).

For the ranked plan to close the errors the validation expansion exposed - by modelling the mechanism, never by tuning to the held-out targets - see [MODELING_IMPROVEMENT.md](MODELING_IMPROVEMENT.md).

For the plan that re-ranks that work by *who reads the number* - the preset, Tailor, Ask and Build figures a journalist or Hill staffer would quote - see [HIGH_STAKES_ACCURACY.md](HIGH_STAKES_ACCURACY.md); it supersedes §6.2's sequencing, not its rules.

---

## Current state (April 2026)

**Large automated test suite, 85% enforced coverage gate, and a four-tier
validation scorecard.** There is no single "validated within 15%" figure — that
phrasing was on this line until 2026-09-01 and was wrong. Live numbers from
`python scripts/cold_holdout.py`, `python scripts/run_loo.py` and
`python scripts/run_validation_dashboard.py`:

| Tier | What it measures | n | Mean | Median |
|---|---|--:|--:|--:|
| Out-of-sample, pre-registered | prediction | 26 | **14.5%** | 11.5% |
| Calibrated, fitted | bookkeeping (low by construction) | 16 | **1.5%** | 0.1% |
| … fitted, ledger rows held in place | the same tier without the composition move | 27 | **11.9%** | 1.1% |
| Unfitted module reconstructions | modules vs targets never fitted to | 39 | **56.7%** | 36.9% |
| Calibrated, leave-one-out | how much of the calibration is structure | 18 | **35.7%** | 29.1% |

Out-of-sample is **16/26 within 15%, 22/26 within 25%**, and it is itself **eight
policy classes**, each now carrying its own CI ceiling:

| Class | n | mean | mass | ceiling | before Wave A |
|---|--:|--:|--:|--:|--:|
| AGI-inclusive surtax | 6 | **17.6%** | 105.4 | 22 | 20.7% |
| capital gains | 4 | **18.7%** | 74.8 | **24** | 20.5% |
| ordinary rate change | 4 | **14.8%** | 59.3 | 19 | 12.0% |
| corporate | 1 | 44.5% | 44.5 | 56 | 44.5% |
| enacted-law spending | 3 | 13.4% | 40.2 | 17 | 13.4% |
| discretionary spending | 5 | 4.6% | 23.2 | 6 | 4.6% |
| payroll | 2 | 7.8% | 15.6 | 10 | 7.8% |
| tax expenditure | 1 | 13.1% | 13.1 | 17 | 13.1% |

**Wave C of [HIGH_STAKES_ACCURACY.md](HIGH_STAKES_ACCURACY.md) is done**
(2026-09-11, PRs #148-#151), and it is the mirror image of Waves A/B: **no target
moved, no constant was retuned, and the two tiers that moved both moved on
mechanism.** Row 1 fell **14.7% → 14.5%** and row 4 **rose 55.5% → 56.7% on the
same 39 rows** — accuracy, not composition, and registered as worse in advance.
The fitted tier, its held-in-place reading and leave-one-out are byte-identical
across the wave.

**H5 (PR #151) found the module carrying two death rates 8.3× apart.**
`estate_flow_rate` is Poterba & Weisbenner's *dollar* flow of estates used as a
*headcount* rate — 408,532 decedents against roughly 3.09 million NCHS deaths —
while `death_exit_rate()` has priced the lock-in wedge off a **2.647%/yr**
mortality-weighted rate since Wave 2. The count is now **3,384,194**, the level
is untouched, and a fixed per-donor exclusion bites 8.3× harder:
`cbo_opt51_gains_at_death` **20.3% → 35.5%** (registered regression),
`biden_capital_gains_39` **32.8% → 27.0%**, `treasury_capgains…v2` **18.4% →
1.8%**, the class **20.5% → 18.7%** — the first class to reach its §5 target.
**Read the 1.8% as half of a correction, not as accuracy**: the count and the
level come from the same ratio, only the count was authorised to move, and the
level that flow implies is **7.1× below** the module's own death-exit rate, which
points the other way (§6.2 item 55). **The plan's instruction to grade the rate
by estate size was refuted in sign** — the wealthy are older, so a size-graded
rate is *higher* at the top (2.84% vs 2.65%) and takes the implied top count
*further* from SOI's.

**H8 (PR #150) found the plan's residual cause for the whole trade block
backwards, and said so before opening a file.** All five tariff targets are
*conventional* estimates and the model sat below every one, so the GDP-feedback
drag the plan prescribed would have moved every row **further** out; the
0.60–0.66 vs 40–50% net/gross comparison was a **denominator mismatch** besides.
The channel is built and **reported beside** the score; what moved the rows is
that **retaliation left the conventional score**, which the repository's own
knowledge file had already described as the right convention while every scenario
and preset ran the other way. `Trade` **34.2% → 43.6%**, registered as worse,
with `steel_tariff_25` (11.89% → **75.28%**) carrying the whole of the net against
an untraceable target and the **four documented rows improving 39.72% → 35.66%**.
Five shipped presets moved with a Decision 6 caption.

**H4 (PR #149) and the label lane (PR #148) moved no scored number.** The
accuracy band on a result is now its own policy class's Tier 1 spread rather than
a fixed proportion of the point estimate — **31 of 56 surfaces had been printing
the whole Tier 1 tier's ±14.7% for policies with no Tier 1 row** — and **35 of 53
presets now print no band and the reason**, with their own row's error and tier
beside the absence. Six preset labels moved onto their row's current published
target, and the invariant runs against all **40** figure-carrying labels with no
exemptions; one of the six had been printing **the model's own output** where a
published score belongs.

**Waves A and B of [HIGH_STAKES_ACCURACY.md](HIGH_STAKES_ACCURACY.md) are done**
(2026-09-10, PRs #140-#146), and they moved all four rows for three different
reasons that must not be run together.

**Row 1 moved 15.0% → 14.7% by way of 15.6%, and the intermediate figure is the
honest part.** PR #144 grew the generic base on the scored vintage — a tax-year
2023 SOI aggregate had been answering an FY2026-2035 question on Tailor, Ask,
Build and seven presets — and the tier mean **rose**, firing the plan's own
falsification condition, because six rows had been under-predicting by *less*
than a decade of the baseline's own nominal growth is worth. The lane reported it
and tuned nothing. PR #146 then gave the AGI-stated rows SOI's **AGI column**,
which is where the tier's 14.7% comes from. **The plan's stated endpoints for
those two rows, 9.1% and 1.0%, were unreachable as written**: §1.3(c) attributed
them to a *preset* flag that cannot move a validation row, and the missing step
was the column. The measured chain is 49.8% → 34.1% → **7.4%** and 37.4% →
17.9% → **-2.9%**. Only two classes moved: AGI-inclusive surtax 20.7% → 17.6%,
and ordinary rate change 12.0% → **14.8%**, where all four rows crossed from
under-prediction to over-prediction.

**Rows 2, 3 and 4 all moved on targets, and not one derivation moved with them.**
PR #145 judged eighteen calibrated benchmarks one at a time, revised six,
recorded twelve as examined-and-left, and left **all 81 `model_10yr_billions`
byte-identical**. The fitted tier fell 1.73% → 1.51% *while nothing improved*,
because the five rows that left it averaged 2.42% — above its own mean; the
reconstruction tier fell 57.88% → 55.46% *while nothing improved*, because the
five arrivals average 36.42%, and **on a constant population it got worse,
57.88% → 58.26%**. The single honest number for what the new targets did to the
model's measured error is that **0.38pp**, against 2.42pp of composition. And the
one reading that is not composition at all: **the 21 rows the fitted tier held
before Wave B, scored on the targets it leaves behind, read 9.82%** rather than
1.73%. Leave-one-out is the same story again — `run_loo.py --donor-matrix`
differs in six lines and every *derived* figure in them is unchanged, with
`Payroll` going 3.8% → **32.3%** and `Expenditures` 37.5% → **40.6%** purely
because two targets moved underneath them.

**Seven shipped presets moved, and every one moved onto its own source's base or
decade**: Warren Ultra-Millionaire Surtax -\$134.6B → **-\$456.0B**, High-Earner
Medicare Surcharge -\$166.5B → **-\$426.6B**, Progressive Millionaire Tax
-\$354.6B → **-\$878.8B**, and four generic presets by a uniform +35.60% (Flat
Tax Reform +\$4,601.5B → **+\$6,239.4B**, Middle Class Tax Cut +\$1,029.4B →
**+\$1,395.9B**, Top Rate to 45% -\$724.4B → **-\$982.2B**, Biden 2025 Proposal
-\$216.5B → **-\$293.5B**). The other 45 score to the cent what they scored
before. Build package totals moved for seven *more* presets with no scored
number moving at all, because Build quotes list prices and a Build package
inherits the **target's** provenance.

**Two things the waves closed that are not accuracy.** Badges went **24 → 44**,
so no preset prints an official figure with nothing checking it, and each badge
names the tier its row sits in (16 fitted / 25 reconstruction / 3 out-of-sample);
six presets now carry a badge saying they are more than 50% from their published
target, and five of them said nothing at all before. And the two OCACT payroll
targets are now described rather than asserted: OCACT publishes E2.1 and E2.5 as
percent of payroll and **no ten-year dollar amount at any horizon**, -\$2.7T
traces to a Peter G. Peterson Foundation sentence describing a *different*
provision, and -\$3.2T matches nothing either body prints.

**Wave 7, the round before, moved three of the four rows and every move is
stated with its mechanism.** The first row fell **15.2% → 15.0%** while **six of its seven moved
rows got worse**, all pre-registered — and no lane's branch figure is the merged
one, because PRs #126 and #132 move the same Treasury row in opposite directions
(#126 alone gave 14.1%, #127 alone 15.9%, #132 alone 15.4%). The third row moved
**57.6% → 57.9% on accuracy, not composition**: the same 34 rows sit in it either
side and the whole 0.33pp is `repeal_ptc` going 18.5% → 29.6% when PR #131
replaced a fitted annual with CBO's own published credit path. The fourth moved
**29.6% → 30.1%**, also registered: PR #128 gave the expenditure module a
per-reform offset direction and `Expenditures` went 35.7% → 37.5%, because the
old −5.1% on the held-out mortgage row was two errors cancelling. The fitted row
did not move, and `run_validation_dashboard.py` now prints its **held-in-place**
reading too — **27 at 5.6%** on the six rows a target revision moved out, not the
37 at 15.5% that folding in all 16 revised rows would give, since 10 of those
were never declared fitted.

**Wave 5 moved only the first row, which is the one tier where a moving mean
measures the model, and PR #121 did the same again.** Wave 5's three lanes all
worked at the out-of-sample margin: no target moved, no constant was retuned, and
0 of the 23 fitted rows and 0 of the 31 reconstruction rows changed, with
`run_loo.py --donor-matrix` byte-identical — a falsification test each lane
registered in advance and each passed. **PR #121's corporate base projection then
moved one Tier 1 row and nothing else** (0 of 21 fitted, 0 of 33 reconstructions,
LOO byte-identical), taking the first row **15.9% → 15.2%**. **PRs #119 and #122
moved the second and third rows by composition and neither by accuracy**, which is
the reading below.

Wave 5 named a hole in the fourth row: the leave-one-out suite holds Payroll,
Estate, AMT, Credits, Expenditures and CapitalGains and has **no `Corporate`
row**, so the module whose fitted base turned out to be a stale TY2018 vintage
has never been cross-validated. **PR #120's memo answered that carry-over `no`**:
the module has one fitted constant and had two benchmarks, one of them the model's
own output, so re-deriving the base from it would reconstruct the constant from
itself — `loo.py` is not what is stopping it and `not cross-validatable` is the
honest outcome. **PR #122 shipped the substitute the memo named**, a second
*published* corporate target the module is not fitted to (`biden_corporate_28_fy2022`,
Treasury's FY2022 Green Book row, reporting at −62.9% among the reconstructions).
The hole is smaller and honestly stated; it is not closed.

**Two of those four changed population in Wave 4 and again in PRs #119 and #122,
and no mean that moved did so for an improvement, so the like-for-like readings
belong beside them**: the fitted tier is **23 at 7.7%, 21/23 within 15%** with the
offset-sign sweep's two reclassified rows held in place (28 at 8.0% with Wave 4's
five held in too, 29 at 10.0% with the TCJA-AMT row on top), and the reconstruction
tier is **57.4% / 29.9% over the 33 rows it held before PR #122**, **56.6% / 29.9%
over the 31 it held before PR #119** — exactly what it read after Wave 5 — and
**65.7% / 40.5% over the 26 it held before Wave 4**, *worse* than the 61.8% /
38.0% before that, with its sectoral subset unmoved throughout at **88.2% over the
14 it held**. The whole of the 56.6% → 57.4% step is `trump_corporate_15` going
22.3% → **121.6%** when PR #122 stopped scoring it against this model's own output;
the remaining 0.2pp is the FY2022 corporate benchmark arriving at 62.9%. Leave-one-out is the mirror case: it *rose*
28.4% → 29.6% without a single derivation moving, because three of its targets
did. A mean that moves because the population moved has not improved, and a mean
that moves because a target moved has not measured the model.

**The fitted tier has lost eighteen rows, and every reason must be quoted with the
number.** `ScorecardSummary.revised_target_entries` is **22**: a constant fitted
to a superseded figure is not fitted to its replacement, so a revised row reports
among the reconstructions, where a miss is a finding rather than a regression.
**Wave 4's provenance pass took the tier 28 → 23** that way, moving
`biden_eitc_childless`, `eliminate_salt`, `extend_enhanced_ptc`,
`ira_enforcement` and `repeal_salt_cap` out mechanically — retuning any of them
to close the new gap would have been the relaxation, and none was touched. The
revised TCJA-AMT row had left the same way earlier. Three more left in Wave 2,
when deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural
tuples removed the only constants ever fitted to the capital-gains scenarios.
Two more left in Wave 3, when L8 turned `universal_coverage_rate` into a Census
measurement and deleted `china_effective_coverage` outright, so the two Trump
tariff rows stopped reading 1.1% and 6.2% off constants fitted to them and now
read 42.0% and 44.3%. **Two more left in PR #119, on a mechanism that is not the
ledger's**: the offset-sign sweep reclassified `trump_corporate_15` and
`repeal_ptc` to `calibrated_to_target=False`, because each annual had been fitted
so that *static × (1 + offset share)* hit its target and signing the offset took
the score to *static × (1 − offset share)* — a constant that reproduced its
target only through a defect is not a calibration to that target. Neither was
retuned and neither got a readiness exemption. The fitted mean *fell*
2.8% → 2.2% → 2.0% → **1.6%** because every row that left on the first three
mechanisms was one it had been carrying, then rose to **1.7%** on the fourth
because the two that left were below the mean only by virtue of the bug — both
moves are **composition, not accuracy**. The reconstruction tier is itself six
populations — 15 sectoral presets at 82.6%, 8 P.L. 119-21 line items at 35.8%, 3
capital-gains scenarios at 39.6%, the revised TCJA-AMT row at 66.8%, Wave 4's
five arrivals at 9.4% and the 3 corporate/PTC rows PRs #119 and #122 moved in at
67.7% — and must not be quoted as one number. Distributional
accuracy is separate again: 7 published CBO/JCT tables at **0.00-5.86pp**, two
of which are circular, with the ARP row falling **7.77 → 3.72pp** because Wave 4
scored it on CBO's own household universe. See
[`docs/VALIDATION.md`](../docs/VALIDATION.md).

*Re-derived 2026-09-05, after Wave 5 (PRs #111-#117). Tier 1 moved 52.6% → 34.4%
on the eight spending rows in Wave 1, 34.4% → 31.3% on the four capital-gains
rows in Wave 2, 31.3% → 31.0% in Wave 3 by *adding* CBO Option 56 at 24.0%,
31.0% → 18.0% in Wave 4 on five rows, **18.0% → 15.9%** in Wave 5 on five
more, and **15.9% → 15.2%** in PR #121 on exactly one — reached through two pre-registered regressions rather than around them,
because PR #113's payroll correction (54.1% / 55.5% → **7.5% / 8.1%**) was worth
more than PR #114's corporate regression (47.1% → **62.3%**) and PR #116's two
Green Book rows (16.7% → **31.4%**, 0.2% → **43.3%**) cost, while PR #116 also
took CBO Option 47 44.8% → **10.5%**. Wave 7 then took it **15.2% → 15.0%**
while making six of its seven moved rows worse. The CI gate went to
`--max-mean-error 20 --min-within-25pct 21` (PR #117), and neither PRs #119-#122
nor Wave 7 moved it: on the post-Wave-7 battery the workflow's own rule
**re-derives it to itself** — ceiling `ceil(15.0 × 1.25) = 19`, rounded up to the
nearest 5 is 20, and floor `22 − 1 = 21`. (PR #126's memo stated a floor of 22 on
its own branch, where within-25 read 23; the merged tree reads 22, so that
tightening does not apply.) PR #121's one row is `cbo_opt64_corporate_rate_1pp`,
**62.3% → 44.5%**, which took corporate out of first place; Wave 7 then rewrote
the tail around it. The largest rows are now `cbo_opt46_agi_surtax_1pp_20k` at
**49.8%**, corporate at **44.5%**, `cbo_opt46_agi_surtax_2pp_100k` at **37.4%**
and `biden_capital_gains_39` at **32.8%**, with the FY2022 Treasury row down to
**18.4%** on its own decade. **Capital gains is no longer the tier's largest
error mass** — the two AGI-surtax rows are, at 87.2 of 390.7 units (22.3%)
against capital gains' 82.0 (21.0%).

Wave 4's own five rows, for the record: PR #108's death-channel carve-outs and
rate response did almost all of it (the two step-up rows 218% → 0.2% and
135% → 17%, gains at death 8% → 19% **worse and pre-registered as a
regression**), PR #105 indexed Option 56's excess share (24.0% → 13.1%) and
PR #107 moved the Biden top-rate target onto its document (14.1% → 12.0%). The
CI gate went to `--max-mean-error 25 --min-within-25pct 20` (PR #110).
Leave-one-out rose 59.3% → 61.7% on the two AMT rows, fell to 58.7% when the AMT
extension's target was corrected, fell to 32.3% in Wave 2 on three rebuilt
modules, fell to 28.4% in Wave 3 on one more rebuilt module pulling against one
provenance fix, and **rose to 29.6%** in Wave 4 on three moved targets and no
moved derivation — credits 20.5% → 18.5%, expenditures 30.2% → 35.7% — and
**did not move at all in Wave 5 or in PRs #119-#122**, all five of whose
`--donor-matrix` outputs are byte-identical. The
reconstruction tier went 250.8% → 82.6% on two pharma rows, then to 21 rows at
76.7% on two target corrections, then to 24 rows at 72.1% when the capital-gains
scenarios arrived, then to 26 rows at 61.8% on L8 and L9, and then to **31 rows
at 56.6%** in Wave 4 — a fall that is entirely composition, since on a constant
population it is **65.7%**, worse, because PR #109's pharma rebuild moved
expanded negotiation 25.7% → 93.3% and international reference pricing
646.2% → 701.0% while PR #107's five arrivals came in at 9.4%; it was unchanged
after Wave 5, which moved no calibrated row, then went to **33 rows at 54.4%** in
PR #119 and **34 at 57.6%** in PR #122 — a fall and a rise that are both
composition again. See
[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) §§5.1, 5.2, 5.3, 5.4, 5.5 and
5.6.*

### Completed work

**Foundation + Sprints 1–5 (March–April 2026)**
- CBO February 2026 baseline with vintage selector (Feb 2024 / Jan 2025 / Feb 2026)
- Sprint 1: Tariff scoring — 5 presets, consumer price impact display, 45 tests
- Sprint 2: Microsimulation hardening — MFJ brackets, SALT, AMT, EITC, NIIT
- Sprint 3: FastAPI endpoints (`/health`, `/presets`, `/score`, `/score/preset`, `/score/tariff`)
- Sprint 4: Test coverage 57% → 72% (131 new tests)
- Sprint 5: `scripts/update_data.py`, `scripts/batch_score.py`

**Horizon features (April 2026)**
- Feature 1: OLG model — 30-period Auerbach-Kotlikoff-style, SS/Medicare reform, generational accounting
- Feature 2: Classroom Mode — 7 assignments (intro → advanced), OLG exercises, PDF export, relative validation
- Feature 3: State-Level Modeling — top 10 states, SALT interaction, combined rate curves
- Feature 4: Real-Time Bill Tracker — congress.gov pipeline, LLM provision extraction, SQLite storage, Streamlit UI

## Modelling plan: Waves 1-7 complete, plus the sign sweep and the corporate follow-through (2026-09-06)

[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) Wave 1 landed 2026-09-01/02
(PRs #83, #85, #86, #87, #88): the budget-authority-to-outlay spend-out model
(L2), the AMT live exemption branch and published year-indexed path (L5), pharma
federal incidence (L7), IIJA's superseding authorization-path row, and spend-out
for the app's own spending presets. §5.1 of that file has the outturn and the
three findings.

**The AMT / insulin target provenance lane closed two of its three targets**
(PR #90, 2026-09-02). `extend_tcja_amt` moved $450B → **$1,357.1B** (CRS R48286
Table 1, transcribing CBO 60114/60271) and `universal_insulin_cap` −$15B →
**+$11.4B** (CBO pub. 57957), both through a new Tier-2 supersede ledger,
`fiscal_model/validation/target_revisions.py`, which mirrors `preregistered.py`'s
rule: ledger entry in one commit, first scoring in the next, old figure kept as a
`superseded_by` row. **No constant was retuned and no threshold moved.**
`KNOWN_TARGET_SIGN_INVERSIONS` is now empty, and the emptiness is the assertion.
`AMT_APP_MODE` and `AMT_SCORECARD_MODE` both stay `reported` — 22.3% reported
against 54.2% derived across the three AMT benchmarks, which is Decision 1's own
rule — so nothing a user sees changed.

**Wave 2 landed 2026-09-02** (PRs #93, #94, #95): L4 estate replaced a
two-point taxable-estate blend that was *exactly invariant* in the exemption with
a SOI-fitted Pareto size distribution; L6 tax expenditures made every cap declare
its unit and gave each expenditure a transcribed benefit distribution; L1 capital
gains rebuilt the realizations base (IRS SOI Table 3.5), the elasticity (the
semi-log **tax-rate** form CRS R48562 defines — the frozen 0.8 had been applied
as a net-of-tax elasticity and was an effective 0.25), lock-in (a derived 1.44×
price wedge in place of the 5.3× multiplier) and gains at death (a
decedent-wealth stock in place of a flat $54B/yr). Tier 1 **34.4% → 31.3%**, LOO
**58.7% → 32.3%**. §5.2 of that file has the outturn, the four findings and the
three missed bands.

**Wave 3 landed 2026-09-02** (PRs #98, #99, #100, #101, #102) and completes the
plan.

- **L9 international** (PR #98) added a jurisdiction-level base-overlap term and
  gave FDII repeal the same base × rate identity the module's rate branch already
  used. **Two rows got worse on purpose and the lane registered both before
  opening a file**: `fdii_repeal` 15.0% → **44.65%** and the package
  41.0% → **49.47%**, because the identity is built on Treasury OTA's published
  $130,230M cost and the carried −$200B is 54% above it. The double count the
  plan named turned out not to exist — the UTPR reads foreign-parented profits
  and GILTI reads US-parented CFC income, so the overlap term nets exactly zero
  for every shipped factory — and the package's real residual is a **level**: a
  $15B UTPR against Treasury's own $136,313M row and JCT's implied $133.9B.
- **L8 tariffs** (PR #99) took the score **gross → net**: duty avoidance, the 25%
  income-and-payroll offset CBO/JCT/Treasury apply to any indirect tax, and the
  receipts lost to retaliation, on Census 2024 levels and a tax-inclusive rate.
  The three unfitted rows fell from a summed 353.5 points of error to **110.5**
  (auto 152.3% → 82.2%, steel 73.2% → 11.9%, reciprocal 128.0% → 16.4%), the two
  *fitted* coverage constants were re-derived or deleted so both Trump rows left
  the fitted tier and now read 37.1% and 44.3%, and the lane found and fixed a
  **sign defect** that made a tariff *cut* raise the deficit. Per **Decision 6**
  every shipped preset moved 28–49% and the user-facing caption shipped in the
  same PR.
- **L3 credits / microsim** (PR #101) replaced `Δcredit × units × participation`
  with two statutory parameter sets run through `MicroTaxCalculator` over CPS
  ASEC tax units and differenced on final liability: module LOO
  **45.1% → 20.5%**. Per **Decision 4** the raw 148 MB ASEC archive is fetched by
  script (`scripts/fetch_cps_asec.py`, SHA-256 verified) into a cache outside the
  repository and never vendored, with five dependent age bands added and every
  pre-existing column byte-identical; per **Decision 5** the three tautological
  credit benchmarks now carry a per-case declaration. The **ARP distributional
  benchmark got worse, 4.76pp → 7.77pp**, and that is the finding: the old figure
  was ranking one of three components by IRS return counts and the other two by
  CPS tax units, and the two universes were partly cancelling.
- **PR #100** (target provenance) moved five targets onto their documents:
  **CBO Option 56 promoted into Tier 1** at 24.0% now that L6 removed the leakage
  its only path ran through; **Pillar Two re-benchmarked as JCT's published
  range** [−$102.6B, +$56.5B], which the model sits inside; the leaked
  `annual_cost_no_cap = 120.0` replaced by **$89.55B** computed from SOI Table
  2.1; the **estate** target examined and deliberately left, with both errors
  recorded under a new `EXAMINED_NOT_REVISED` state; and the **Treasury FY2022**
  combined-row reading confirmed.
- **PR #102** re-derived the Tier 1 CI gate by the workflow's own rule after the
  battery grew: `--max-mean-error 40 --min-within-25pct **18**`.

**Every Wave 3 module keeps `reported` as its app default under Decision 1.**
The only shipped numbers that moved are the five tariff presets, and they moved
because the *score* changed rather than because a default did.

**Wave 4 landed 2026-09-05** (PRs #104, #105, #106, #107, #108, #109, #110). It
was not in the plan as a wave — it is six of §6.2's carry-over items, taken in
parallel lanes, each pre-registered with an outturn appended in
[`planning/lanes/`](lanes/).

- **Gains at death** (PR #108, `W4_gains_at_death.md`) built the death channel's
  missing behaviour: the six carve-outs a realization-at-death proposal does not
  tax — spousal transfers, charitable bequests, the §121 residence exclusion,
  tangible personal property, a family-owned-business deferral, and the per-donor
  exclusion applied *after* the others — plus a semi-log rate response at death
  (`exp(−2.2660 × 0.196)` = 0.641 on the decedents a rate change reaches, exactly
  1.0 on Option 51, which changes no rate). **Tier 1 31.0% → 18.5% on this PR
  alone**, and the capital-gains error mass **405.6 → 81.0**, from half the
  tier's mass to a sixth; the two payroll rows are now the largest single mass.
  `treasury_capgains_39_plus_stepup_elim` 217.5% → **0.2%**,
  `biden_capital_gains_39` 134.9% → **16.7%**, `cbo_opt51_gains_at_death`
  8.4% → **19.3%, worse by design and pre-registered as a regression** because
  its 8.4% had been bought by taxing charitable bequests and small decedents'
  housing gains that no such regime reaches. **The 0.2% must always be quoted
  with the lane's own caveat that it is two errors cancelling**: the mechanism
  removes 87.2% of that row's death channel where the pre-registered hand path
  said 92.8%. A falsification test fired — the two Green Book rows land on
  opposite sides of their targets — and its diagnosis is *not* the mis-ordering
  it was written to catch but the **five-class decedent ladder having no
  within-group dispersion**, which is now a carry-over. Decision 6 caption
  shipped in the same PR.
- **Distributional households** (PR #104, `W4_distributional_households.md`)
  gave `DistributionalEngine` CBO's own household universe — size-adjusted
  household income before transfers and taxes, quintiles containing equal numbers
  of *people* — registered each benchmark on the universe **its source ranks**,
  and made the surfaces report the universe **scored** rather than the one
  registered. **ARP 2021 7.77pp → 3.72pp**; the seven tables now span
  **0.00-5.86pp**; six of the seven are unmoved to the hundredth, including the
  microsim control. Two findings: **3 of the 7 fall back `household→tax_unit`**
  because `TCJAExtensionPolicy` and the corporate policy have no microsim
  reform mapping — which is now visible rather than latent, and says that the two
  *circular* rows are also scored on a population CBO does not use — and a
  per-household **dollar column was wrong by a factor of three** and invisible to
  every gate, because the error metric scores shares.
- **Option 56 excess share** (PR #105, `W4_option56_excess_share.md`) asked the
  excess share what year it is: **24.0% → 13.1%**, from CBO's own chained-CPI
  indexation rather than a fitted parameter, with the pre-registered escape hatch
  (5%/yr premium growth, landing the row at 0.6%) declared in advance and **not
  taken**. Two findings on the remainder: about half is a **base omission** (CBO
  caps premiums *and* FSA/HRA/HSA contributions and the repository's premium
  distribution has no account dimension) and about a fifth is an **unsourced
  behavioural offset whose sign convention is the reverse of `TaxPolicy`'s** —
  the expenditure module *magnifies* where the tax module erodes, worth +20% on
  this row, module-wide, and an owner decision rather than a lane's.
- **AMT phase-outs** (PR #106, `W4_amt_phaseouts.md`) transcribed statutory
  §55(d)(2) from eleven IRS inflation Revenue Procedures. **No benchmark moved,
  by design**, and every registered row landed where it was registered. What it
  bought: a threshold reform stops scoring exactly zero (a −$200,000 MFJ
  threshold change is now +$300.1B over ten years where every value used to
  return 0.0), the module can now represent P.L. 119-21's design as distinct from
  a naive TCJA extension (it scores it 6.4% cheaper, the sign a reader of the
  statute would expect), and nothing clamps at a year any more. The finding worth
  keeping: two schedule rows were **20% wrong and it never showed**, because both
  benchmarks sit on anchors where only the row matters — so "the benchmarks did
  not move" is weaker evidence about this module than it looks.
- **Pharma Part D** (PR #109, `W4_pharma_part_d.md`) built the three federal
  channels the 2023 aggregate had been standing in for (direct subsidy 0.37269,
  reinsurance 0.10470, low-income subsidy 0.29864, federal total 0.77603), a
  negotiation ladder fitted to all three published CMS cycles, and a
  RAND-sourced coverage base. **The reconstruction rows got worse and the lane
  reports it**: expanded negotiation 25.7% → **93.3%**, international reference
  pricing 646.2% → **701.0%**, insulin unchanged at 39.0%. The cause is that the
  lane's own ladder condemned an unsourced $220B Part D gross-spending constant
  the reference-pricing leg also reads — CMS's own sentence puts the total at
  **$281B** — and keeping an unsourced number because it flattered the prediction
  is what the pre-registration protocol exists to stop. Presets moved by design:
  negotiation −$371.5B → **−$33.5B**, reference pricing −$746.2B → **−$801.0B**,
  comprehensive −$573.5B → **−$150.5B**, insulin unchanged.
- **Provenance** (PR #107, `PROVENANCE_wave4.md`) moved **thirteen targets onto
  their documents** — twelve through the Tier-2 ledger and
  `biden_high_income_tax.v2` (−$245.9B) through the Tier-1 manifest — and
  recorded **four more as examined-and-left**. **No modelling change at all**:
  every `model_10yr_billions` is byte-identical and every LOO *derivation* is
  unchanged. Two targets were not merely unsourced but the wrong *kind* of
  number: the auto tariff's −$100B was a **per-year** claim in a ten-year column,
  and the reciprocal-tariff target was **Tax Foundation's dynamic score in a
  conventional column** — a tier error no rescaling would have found, now the
  second **range** revision, [−$1,800B, −$1,400B], on which CRFB, Tax Foundation
  and Yale disagree by 29%. **Six of the thirteen got worse**, which is the shape
  a correct provenance pass has. `line_item_differs` went 13 → **5**, and all
  five now carry a written verdict.
- **PR #110** re-derived the Tier 1 CI gate by the workflow's own rule after the
  death channel halved the tier: `--max-mean-error **25** --min-within-25pct
  **20**` (ceiling `ceil(18.0 × 1.25) = 23`, rounded up to the nearest 5; floor
  `21 − 1 = 20`).

**Every Wave 4 module keeps `reported` as its app default under Decision 1.**
The shipped numbers that moved are the three drug-pricing presets (by design,
with a Decision 6 caption), and the insulin preset's description string, which
had still been quoting the −$15B target PR #90 superseded.

**Wave 5 landed 2026-09-05** (PRs #111, #113, #114, #115, #116, #117). Three
modelling lanes at the Tier 1 margin plus two blue-tier PRs and the gate, each
lane pre-registered with an outturn appended in [`planning/lanes/`](lanes/).
**Tier 1 18.0% → 15.9%**, median 12.6% → **11.4%**, within-15 14 → **16**,
within-25 21 → **22** — and it got there *through* two pre-registered
regressions, not around them. Neither calibrated tier moved at all.

- **Payroll at the margin** (PR #113, `W5_payroll_margin.md`) took the two CBO
  Option 61 rows **54.1% / 55.5% → 7.5% / 8.1%**, the largest single move of the
  wave, and reproduced its hand arithmetic to the decimal. **The plan's own
  scoping was wrong on both halves**: §2.1 scoped it as "employer-share
  incidence + income-tax offset", and CBO's option text says the tax "would be
  paid entirely by employees" — adding the offset would have moved the model
  *away* from the target, for a reason the source explicitly rules out. The real
  defect was `$400B / 2.9% = $13,793B`: Medicare receipts divided by a rate that
  does not raise all of them, because `additional_medicare_billions: 15.0` — the
  0.9% surtax on a far smaller base — sits four lines above it in the same dict.
  The base is now CBO's own February 2024 wage path × the Trustees'
  covered-earnings ratio. Six findings, of which two are carry-overs: the
  module's "elasticities" are flat shares of the revenue effect rather than
  responses to the size of the change, and **the behavioural offset returned the
  opposite sign to the static effect** — the second module found with that
  defect after `trade.py` in Wave 3, and invisible to every gate because both
  modules' calibrated factories zero the elasticity. No shipped number moved, so
  no Decision 6 caption was owed.
- **Corporate at the margin** (PR #114, `W5_corporate_margin.md`) was
  **pre-registered as a regression and landed as one, to the decimal**:
  `cbo_opt64_corporate_rate_1pp` **47.1% → 62.3%**. The derived path now prices a
  percentage point on IRS SOI Table 11's published income subject to tax
  ($2,879.1B, TY2022), realized at SOI's own after/before-credits ratio and
  settled on IRC §6655's calendar. **The fitted $1,900B it replaced was not a
  wrong concept but a stale vintage** — within 3% of SOI's TY2018 figure — and
  the offsetting error was two errors: a base 34% too small and a flat 12.5%
  offset well below what the published semi-elasticity implies at 7pp, which
  very nearly cancel at 7pp and do not at 1pp. What is left is a disagreement
  between documents: CBO 60557 prices a point at $135.7B over the window,
  Treasury's FY2025 Green Book at $192.8B, and the *larger* rate change carries
  the *larger* per-point yield. Re-running with only the SOI anchor year varied
  gives 4.2% at TY2019 and 62.3% at TY2022 — which is why the anchor is fixed as
  "latest published" rather than chosen. `CORPORATE_APP_MODE` stays `reported`
  under Decision 1 (1.92% against derived's 9.67%), so nothing shipped moved.
  Two findings are carry-overs: **`corporate.py`'s behavioural offset returns
  `abs(static_effect)`**, so a shipped rate-cut preset books a behavioural
  response that makes the cut *more* expensive (the third module with an offset
  defect, now pinned by a test in both behaviours), and **the corporate module
  has no leave-one-out row at all** — the one module self-documented as
  calibrated has never been cross-validated, and adding it needs a `loo.py` edit
  no modelling lane may make.
- **Preferential rate at the margin** (PR #116, `W5_preferential_margin.md`)
  projected the realizations base with the accrued-gains stock it is a flow off
  (`R(t) = h · A(t)`, no new constant), taking **CBO Option 47 44.8% → 10.5%** —
  34.3 of its 44.8 points, with no elasticity, bracket, threshold or rule
  touched. The obvious hypothesis was **refuted**: SOI Table 3.5's preferential
  columns exceed the whole year's realized gains in both vendored years (1.046
  and 1.189), so they already contain qualified dividends, and adding a column
  would have double-counted $313-336B by being wrong twice. The same projection
  was registered as a **net Tier 1 regression** on the two Green Book rows and
  landed inside both bands: `biden_capital_gains_39` 16.7% under → **31.4%
  over**, `treasury_capgains_39_plus_stepup_elim` 0.2% → **43.3% over**. **The
  0.2% was two errors cancelling and this lane removed the first** — Wave 4's own
  lane doc had already said so — and about **17 of the FY2022 row's 43 points are
  the window** it is scored on (target FY2022-2031, model FY2025-2034, no
  `effective_start_year` on the record), a manifest question and a carry-over.
  Four Tailor capital-gains rows moved 26-110%, so a Decision 6 caption ships
  with them; the reconstruction scenarios and the CapitalGains LOO are
  byte-identical, because a projection is a property of the base's vintage and
  those rows carry 2018 and 2021 vintages.
- **Frozen assignment links** (PR #111, blue tier) put `frozen=1` beside the
  existing `baseline=&engine=&spec=&mode=` stamps on `/explore` and `/tailor`,
  pinning vintage, engine, dynamic and policy so a class hands in one set of
  numbers. A link frozen on a vintage this deployment does not serve **refuses to
  score** and names both vintages, rather than falling back quietly; `?classroom=1`
  reveals the control that emits one. Two carry-overs, both stated in the PR:
  **Build packages are not freezable** (freezing one would mean disabling the
  checklist that also owns the target slider and the exports, so `frozen=1` on
  `/build` does nothing rather than claiming a lock it is not holding), and the
  **Data & methodology options are not pinned**, per the owner's stated scope.
- **App default window** (PR #115, blue tier) introduced
  `fiscal_model.baseline.APP_DEFAULT_START_YEAR = 2026`, so every app surface and
  the API's `budget_window` read **FY2026–FY2035** — the window the CBO February
  2026 baseline projects, and the one the app already defaults to. The library
  defaults stay at 2025, because each benchmark is scored over the window its own
  document used and moving one would be a target revision with its own ledger.
  Exactly one validation path read a default — the five sectoral runners pinned
  their scorer but not their policy — and it was fixed in a separate first commit
  that leaves all five scripts byte-identical. Two pharma presets moved by one
  calendar year, correctly: negotiation −$33.5B → **−$41.8B**, comprehensive
  −$150.5B → **−$158.9B**.
- **PR #117** re-derived the Tier 1 CI gate by the workflow's own rule:
  `--max-mean-error **20** --min-within-25pct **21**` (ceiling
  `ceil(15.9 × 1.25) = 20`; floor `22 − 1 = 21`). Both tighten.

**Every Wave 5 module keeps `reported` as its app default under Decision 1.**
The only shipped numbers that moved are the four Tailor capital-gains rows (with
their Decision 6 caption) and the two pharma presets the window change carried
forward a year.

**The sign sweep and the corporate follow-through landed 2026-09-05** (PRs #119,
#120, #121, #122): one cross-cutting sweep, one research memo, one modelling lane
and one provenance pass. **Tier 1 15.9% → 15.2%** on a single row; the fitted tier
23 → **21 at 1.7%** and the reconstructions 31 → **34 at 57.6%**, both by
composition and neither by accuracy; leave-one-out byte-identical on all four
branches; distributional unchanged; the CI gate re-derives to the same 20 / 21.

- **The behavioural-offset sign sweep** (PR #119, `SWEEP_offset_sign.md`) closed
  §6.2 item 22 and subsumed item 8. The engine adds the offset to the static
  deficit effect, so an offset must carry the **same sign as the static revenue
  effect** to erode it; **7 of the 15 implementations did not**. Three were
  **inverted** (`AMTPolicy`, `EstateTaxPolicy`, `PremiumTaxCreditPolicy` — all
  three carrying the *identical* comment pair above a `return -total_offset`, one
  copy-paste in three files) and four were **`abs()`-ed** (`CorporateTaxPolicy` in
  `reported`, the `TaxCreditPolicy` fallback, `IRSEnforcementPolicy`,
  `InternationalTaxPolicy`). AMT booked **25% more** than its own static in both
  directions. Six were signed with `math.copysign`; `TaxExpenditurePolicy` is kept
  as a **sourced convention**, cited to CBO Option 56's own text, and its size is
  now measured (+5% on a SALT elimination, +20% on Option 56). Two shipped presets
  moved with a Decision 6 caption — **Trump Corporate 15% +$1,690.6B →
  +$1,314.9B** and **Repeal ACA Premium Credits −$966.2B → −$790.5B** — and the
  other 51 score to the cent. Strict readiness then failed on CI, and the owner's
  decision was **reclassify, don't retune, don't exempt**: `trump_corporate_15` and
  `repeal_ptc` became `calibrated_to_target=False`. **The §7.5 lesson is the one to
  carry**: the CI failure was invisible locally because Python 3.14 fails the
  runtime check *first* and masks everything after it, so `check_readiness.py
  --strict` exited 2 on both trees and a byte diff showed nothing — *"identical to
  main" is only evidence when the check being compared can distinguish them*.
- **The corporate per-point memo** (PR #120, `CORPORATE_PER_POINT_YIELD.md`)
  changed no code and refuted three claims sitting in `cbo_opt64`'s
  `known_limitations`. 18 published corporate-rate estimates across 10 vintages,
  transcribed with page references and annual paths. The split is **JCT vs Treasury
  OTA**, not CBO vs Treasury; Treasury's 28% row has bundled a GILTI step since
  FY2023; on the comparable metric the record is Tax Foundation 55.1%, JCT 55.9%,
  PWBM 64.4%, Treasury 79.5% and **this model 90.8%**, above every published
  estimator; and Option 64 carries **no** income-and-payroll offset footnote though
  the facing Option 63 does, which refutes the old "largest unmodelled channel"
  claim.
- **The corporate base projection** (PR #121, `W6_corporate_base_projection.md`)
  built the memo's §7(i) mechanism in `derived` only: base = CBO's Feb-2024
  receipts path (pub. 59710 Table 1-1) × a 4.80133 base-$/receipts-$ ratio anchored
  on SOI TY2022 ÷ MTS FY2022, with a §6655 convolution. `cbo_opt64` **62.3% →
  44.5%** against a registered band of 42 ± 4; **Tier 1 15.9% → 15.2%**, only that
  row moving; derived `biden_corporate_28` **−7.81% → +4.04%**. The marginal share
  fell 90.8% → **80.8%**, closing an inconsistency independent of any target. App
  default untouched, no caption owed. **Its finding**: `CBOBaseline.generate()
  .corporate_income_tax` grows at 4.88%/yr — faster than the 4% constant this
  lane removed and 3.4× CBO's own 1.44% — and under `use_real_data=True` returns
  an *identical* path for all three vintages. Nothing scored reads it today; it is
  a green-tier defect and a carry-over.
- **The corporate/PTC provenance pass** (PR #122, `PROVENANCE_corporate_ptc.md`)
  opened neither module and moved no model output. `biden_corporate_28` →
  `line_item_differs` through the new **`scope_differs`** kind (figures agree to
  0.2%; the scope bundles GILTI); `biden_corporate_28_fy2022` registered as the
  module's second published and **never-to-be-fitted** target (−62.9%);
  `cbo_opt64`'s estimator corrected to JCT and its `known_limitations` rewritten;
  `trump_corporate_15` superseded to the published range **[+$595.0B, +$673.1B]**
  (22.3% → 121.6%, model $818.7B outside, a third of the residual measured as
  bonus depreciation); `repeal_ptc` **examined and left** with its origin found
  (CBO/JCT pub. 51298 Table 2's $1,142B, a baseline projection in a repeal-score
  column, 3.8% away — adopting it would make the row worse). Published targets
  73 → **75**, `model_estimate` rows 7 → **6**.

**`CORPORATE_APP_MODE` stays `reported` on `main` by owner decision, although
Decision 1's rule now points the other way.** Measured on the merged tree where
both the base projection and the moved targets apply, the corporate module reads
**reported 62.75% against derived 61.43%** on three published targets — derived
leads, narrowly, by winning the FY2022 rate-only row and losing a little on the
other two. The flip was built and pre-registered as PR #124 and **closed unmerged
on 2026-09-05**: the mean cannot discriminate on this set (one row of three won;
two rows are the same reform 57% apart; the third missed by more than 100% in
both modes), and flipping would leave a fitted row scored by an unfitted path.
Revisit when a rate-only published 28% score on a carried vintage exists. Neither figure is small, and the honest summary is that a
module whose implied marginal base is above every published estimator's misses both
published corporate targets in the same direction and misses the third by more.

### Wave 7 landed (2026-09-06, PRs #126-#135)

Seven green/🟡-tier lanes and three blue-tier ones. **Four of the seven were
pre-registered regressions and landed as regressions**, and the tier figures
below are the merged tree's, which are not any lane's before/after: PRs #126 and
#132 move the same Treasury row in opposite directions.

**#126 FY2022 target window** (`planning/memos/FY2022_TARGET_WINDOW.md`) gave
`CBOScore` a `scoring_window_first_year` and scored
`treasury_capgains_39_plus_stepup_elim` on **FY2022–2031**, the decade its own
document covers — target unchanged at −$322.0B, shape input superseded to `.v2`,
which is `iija_2021_discretionary.v2`'s rule exactly. **The window offset is 28.7
of the row's 43.3 points, not the "~17" every doc quoted**: the old figure
discounted only the rate channel, and the death channel both grows and does not
grow proportionally. The control (`biden_capital_gains_39`, same shape on its own
window) has an offset of exactly zero. The row reads **18.4%** on merged main
rather than the memo's 14.6%, because #132 landed in the same wave. **The same
mechanism would take IIJA 18.2% → 0.3%**, published as an owner `.v3` decision
rather than taken.

**#127 filing-status split** (`planning/lanes/W7_filing_status_split.md`) closed
§6.2 item 25, the tier's oldest tail row, by transcribing IRS SOI **Table 1.2**
and taking only its *composition* onto the Table 1.1 base. `opt46_1pp`
44.7% → **49.8%**, `opt46_2pp` 16.1% → **37.4%**, `opt45_top4` 17.9% → **12.4%**,
`biden_high_income` 12.0% → **9.2%**, every figure landing on its pre-registered
value. **Finding: `opt46_2pp`'s 16.1% was two errors cancelling a third** —
split + AGI base + baseline growth would take it to **1.0%**, but the latter two
move rows with no filing-status boundary, so each is its own lane. And the
single-threshold approximation was **not** uniformly generous: the Green Book
row's married-filing-separately floor is $175,000 *below* the amount the model
applied.

**#128 expenditure offset convention**
(`planning/lanes/W7_expenditure_offset_convention.md`) settled §6.2 item 8 by
reading nine sources one reform at a time: **magnify** where CBO names the
channel (Option 56, the charitable rate ceiling, SALT elimination, SALT-cap
repeal), **erode** otherwise (mortgage on Poterba–Sinai, step-up, retirement,
like-kind). Only `eliminate_mortgage` moved, −$330.4B → **−$270.3B**,
10.1% → **9.9%**; **zero presets moved**. Expenditures LOO **35.7% → 37.5%**, a
pre-registered regression, because the old −5.1% was two errors cancelling. A
sixth sign defect was fixed in `estimate_expenditure_revenue()`, and
`CONVENTION_EXCEPTIONS` is now per-policy rather than per-class. **Magnitudes
remain unsourced** — item 8 is closed on direction, open on magnitude.

**#131 PTC repeal shape** (`planning/lanes/W7_ptc_repeal_shape.md`) replaced a
fitted $83.0B/yr — which is the carried target run backwards through the engine's
growth factor — with CBO/JCT publication 51298's own annual credit path times
(1 − 19.28% of offsets from publication 60437). `repeal_ptc` −$896.9B →
**−$774.1B**, 18.5% → **29.6%**, a **pre-registered regression** whose whole
$326B decomposes into three published steps. **The gross June-2024 path scores
0.09% against $1,142B** — the proof that the target is a baseline projection. The
Repeal ACA PTC preset moved with a Decision 6 caption.

**#132 decedent ladder** (`planning/lanes/W7_decedent_ladder.md`) replaced the
five-class ladder with a fitted piecewise-Pareto SOI/DFA estate-size
distribution: `opt51` 19.3% → **20.3%**, `biden_capgains` 31.4% → **32.8%**,
Treasury 43.3% → 45.4% on that branch — all pre-registered. **Finding: the
$1M→$5M exclusion-step gap is the decedent HEADCOUNT, not the ladder.**
`max(0, gain − E)` is convex, so a sharper schedule makes an exclusion cost
*more*; the step went 82.26 → **85.02**, the wrong way. The model's decedent
count is short **7.6×** overall and only **1.6×** at the top, so a uniform
scaling would overshoot. `.gitignore`'s bare `data/` line makes ruff skip
`fiscal_model/data/` entirely.

**#130 baseline corporate path + dashboard means**
(`planning/lanes/FIX_baseline_corporate_path.md`) gave `CBOBaseline` a per-vintage
corporate receipts line — February 2024 is now CBO publication 59710 Table 1-1 —
where it had been 18% of individual income tax regardless of vintage, grown
4.88%/yr against CBO's own 1.21%. **Nothing scored moved**; the Ask baseline's
ten-year deficit went $30,020.7B → **$29,529.1B** and debt/GDP 104.8% → **103.8%**.
The dashboard gained a calibrated-tier block and `declared_calibrated_to_target`,
so the honest held-in-place reading (**27 @ 5.6%**, not 37 @ 15.5%) is computed
rather than asserted.

**Three blue-tier PRs.** **#129 cold-start measurement**
(`planning/memos/COLD_START.md`) took first paint **1.59s → 0.02s** by import
ordering in `app.py` and found the real cost was the footer's scorecard —
**8.7 of 9.4s** on a cold landing page. Community Cloud sleeps after 12 hours and
needs a click to wake; no app-side fix touches that. **#135 footer scorecard**
closed it with a test-pinned artifact: landing first run **8.40s → 0.67s**. A
registry count cannot be exact, because runners drop rows that fail to score.
Scored `/explore` is still ~10.6s through `get_validation_badge → _scorecard_index`
— carry-over. **#133 Plotly dark mode** themed 20 of 21 chart sites, with light
mode pinned byte-identical and WCAG contrast measured. **#134 Build frozen links**
closed PR #111's carry-over: `/build?policies=&target=&metric=` plus the shared
lock, values links freezable, exports still live, and a test comparing frozen and
open scoreboards bar by bar.

### Next: the carry-over list, sequenced by the owner

What is left is a single list of open items at
[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) **§6.2**. Wave 4 closed
nine of them; **Wave 5 closed three more** — payroll at the margin, corporate at
the margin, and the preferential-rate base — and opened six; **PRs #119-#122
then closed three of those six and struck a fourth as answered**.

**Closed since:** the **behavioural-offset sign sweep** (item 22, PR #119 — seven
implementations found and six signed, with the expenditure convention now the only
exception and its size measured, which also folds in item 8's outstanding half);
the **corporate base's flat 4%/yr aging** (PR #121); and the **corporate and PTC
targets nobody could check** (PR #122). **Struck as answered rather than closed:**
the corporate module's missing leave-one-out row (item 23) — PR #120's memo
answered it `no`, because the module has one fitted constant and had two
benchmarks, one of them its own output, so a LOO row would reconstruct the constant
from itself; the substitute that *was* built is a second published, unfitted
corporate target.

**Wave 7 closed seven more**: the FY2022 target window (#126), the filing-status
threshold row (#127), the expenditure convention's *direction* half (#128), the
`repeal_ptc` shape (#131), the decedent ladder (#132), `CBOBaseline`'s corporate
receipts path and the dashboard's blindness to the calibrated tiers (#130). Two
of those closed by being **disproved rather than fixed** — the decedent ladder
was not the cause of the exclusion-step gap, and the filing-status split made
three of its four rows worse — which is why the list below is longer than the
seven items it lost.

**Wave 7's new items**, each with a lane pointer: the **IIJA `.v3` window
decision** (owner; #126 publishes 18.2% → 0.3% and declines to take it); **Option
46's AGI base and baseline-growth terms** (#127 finding 1 measures both, and both
move rows with no filing-status boundary); the **decedent headcount** (#132 —
`estate_flow_rate` is a dollar flow used as a headcount rate; the candidate is
`mortality_weighted_net_worth_share` at 2.65%, and the top of the distribution is
short by only 1.6× where the total is short by 7.6×); the **expenditure
elasticity magnitudes** (#128 — all five unsourced, two now with a published
figure beside them); **`_scorecard_index`'s badge cost on scored routes** (#135 —
6.6s of a 10.6s scored `/explore`, and it needs per-row figures, so the artifact
cannot serve it); the **preset-sweep script's window** (#131 finding 5 — it
scores FY2026–2034 while its own lane docs say FY2026–2035); **`.gitignore`'s
bare `data/` line** (#132 — ruff silently skips `fiscal_model/data/`); and the
**stale `known_limitations` text on the Treasury row** (#126 — still says "about
17 of the row's 43 points" and quotes $405.6B, and the record's `notes` still
claim the row necessarily gets the same prediction as `biden_capital_gains_39`).

What remains from before, with the newest first: **the corporate module's implied
marginal base still 80.8% of the vintage average against JCT's 55.9%** (new,
PR #120 §4b and PR #121's own "what the lane did not do" — the remaining 44 points
of `cbo_opt64` are credit carryforwards under §38(c)/§904(c), CAMT and the
individual-side dividend interaction, none available from a source this module
reads, and none to be asserted as a constant); **Decision 1's corporate override**
(decided — reported 62.75% vs derived 61.43% on the merged tree; the flip, PR #124,
was closed unmerged on 2026-09-05 and `reported` kept, revisit trigger recorded in
§6.2 item 33); **a `retire` state for `target_revisions.py`**
(new, PR #122 §3 — deliberately *not* built, because a mechanism with no user is
dead code and the row that would have used it turned out to have a document;
recorded so the next lane does not re-derive the question); **the Data &
methodology options still not pinned by a frozen link** (PR #111 — *Build
packages became freezable in PR #134*, so only the options half is left); payroll's two flat-share "elasticities" and
its unexplained base-growth gap (W5-A findings 4 and 5); and the engine's
two year-indexed policy classes with no general concept behind them (W5-A
finding 6). Carried from before: the holdout-protocol re-lock;
`repeal_individual_amt`'s unsourced $450B; Option 56's two payroll alternatives
and its FSA/HRA/HSA base; the expenditure module's behavioural sign convention
(W4-3a finding 3 and §6.2 item 8 — **the sweep's single remaining exception**,
now sourced to CBO Option 56's own text and sized at +5% of the static effect on a
SALT elimination and +20% on Option 56, and still an owner decision because
choosing it module-wide moves every fitted expenditure row and the whole
leave-one-out column together); re-basing the UTPR on
OECD CbCR aggregates and GILTI's two calibration constants; a GDP-feedback
channel for tariffs; the estate growth lever; CBO's account-level spend-out rates
as the L2 cross-check; the alternatives CSV's revenue sub-row sign artifact;
pharma's utilisation response, Part B/D split and cost-sharing re-split (W4-3b
§5.9); and §55(b)(1)'s 26/28% AMT bracket (W4-3c). The cold-start measurement in
[`redesign/FOLLOWUPS.md`](redesign/FOLLOWUPS.md) is also still open, partially
done rather than closed. **Sequencing is an owner call**, which is why they are
one list rather than a wave.

## Immediate next moves (next 2-3 weeks)

Before committing to the full CPS microsimulation build or the full multi-model platform, run the feasibility gates first.

Starter commands:
- `python scripts/run_feasibility_audit.py --json`
- `python scripts/run_feasibility_audit.py --include-model-pilot`
- `python scripts/run_feasibility_audit.py --include-model-pilot --strict`
- `python scripts/run_feasibility_audit.py --include-model-pilot --use-synthetic-cbo`
- `python scripts/run_feasibility_audit.py --include-model-pilot --no-top-tail-augmentation`
- `python scripts/run_feasibility_audit.py --include-model-pilot --include-experimental-pwbm --strict`

### CPS microsimulation feasibility sprint
- [ ] Audit current `fiscal_model/microsim/` inputs, tax-unit construction, and weighting assumptions
- [ ] Confirm whether `tax_microdata_2024.csv` is reproducible from source CPS files
- [ ] Wire one interaction-heavy benchmark through the microsim path
- [ ] Decide whether the current stack is strong enough for a full CPS migration

### Multi-model feasibility sprint
- [ ] Audit the current `BaseScoringModel` / `ModelResult` abstractions
- [ ] Wrap one microsim-style engine and one PWBM-style path behind a common comparison contract
- [ ] Run one preset policy through 2-3 engines outside the current static-vs-dynamic UI
- [ ] Resolve any PWBM blockers from `scripts/run_feasibility_audit.py --include-model-pilot --include-experimental-pwbm --json`
- [ ] Decide whether the repo is ready for a true side-by-side comparison feature

### Go/no-go memo
- [ ] Write a short memo covering risks, effort, reproducibility, and recommended sequencing
- [ ] Use that memo to choose whether CPS or multi-model work starts first

## Genuine next priorities

### Multi-model comparison platform
Run the same policy through distinct CBO-style, TPC-style (microsim), and FRB/US/PWBM-inspired engines side by side. This remains a roadmap item; the current UI only compares the existing conventional and dynamic scoring paths.

### CPS microsimulation
Replace IRS bracket-level aggregates and synthetic tax units with CPS ASEC microdata for distributional analysis. This remains the highest-leverage methodological upgrade for AMT + SALT + CTC interaction accuracy.

### Additional policy modules
- **Climate/energy** — IRA clean energy credits, carbon pricing, EV incentives
- **Immigration** — Workforce effects on payroll tax base and GDP
- **Housing** — Mortgage deduction reform, first-time buyer credits

### Data freshness
- ~~IRS SOI 2023 data~~ — **done.** Tables 1.1 and 3.3 for tax years 2021, 2022
  and 2023 ship in `fiscal_model/data_files/irs_soi/`, and auto-population takes
  the latest available year, so production scoring runs on **tax year 2023**.
- CBO baseline auto-loader from `cbo.gov` instead of hardcoded values

### Production hardening
- Docker containerization
- `requirements-lock.txt` with `pip-compile`-managed pinned transitive runtime versions
- Structured logging, data freshness monitoring

---

## Priority matrix

| Feature | Impact | Effort | Recommended |
|---------|--------|--------|-------------|
| CPS microsimulation feasibility sprint | High | Medium | Do now |
| Multi-model feasibility sprint | High | Medium | Do now |
| Full multi-model comparison | High | High | Start after feasibility gate |
| Full CPS microsimulation | High | High | Start after feasibility gate |
| Climate module | Med-High | Medium | Good standalone sprint |
| ~~IRS SOI 2023~~ | Medium | Low | **Done** — shipped and in use |
| Docker/lock file | Medium | Low | Interleave with above |

---

## Bill Tracker: committee filter + JCX crosswalk (pipeline work, from the 2026-08 UI review)

Both need new data before any UI ships — a filter or crosswalk built on
what the database holds today would be silently wrong:

- **Committee filter**: the ingestor does not fetch committee referrals;
  committee names appear only incidentally inside `latest_action` text for
  ~20% of bills (and vanish once a bill moves past referral). Requires the
  congress.gov `/bill/{congress}/{type}/{number}/committees` endpoint in
  `bill_tracker/ingestor.py`, a `committees` column, and a pipeline run
  (CONGRESS_API_KEY).
- **JCX crosswalk**: no JCT publication data exists in the pipeline.
  Requires scraping/curating jct.gov publication listings (JCX number,
  title, bill reference) into a small table keyed by bill_id, refreshed by
  the update pipeline; render beside the CBO score for revenue titles.
