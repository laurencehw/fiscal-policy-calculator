# Next Steps — Fiscal Policy Calculator

> Roadmap last reviewed April 2026; the validation scorecard below was re-derived 2026-09-05. This file tracks roadmap items beyond the current shipped branch.

For a manuscript-focused path to citation-grade quality, see [MANUSCRIPT_95_PLUS.md](MANUSCRIPT_95_PLUS.md). For repo-grounded go/no-go gates on the two biggest upgrades, see [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md).

For the ranked plan to close the errors the validation expansion exposed - by modelling the mechanism, never by tuning to the held-out targets - see [MODELING_IMPROVEMENT.md](MODELING_IMPROVEMENT.md).

---

## Current state (April 2026)

**Large automated test suite, 85% enforced coverage gate, and a four-tier
validation scorecard.** There is no single "validated within 15%" figure — that
phrasing was on this line until 2026-09-01 and was wrong. Live numbers from
`python scripts/cold_holdout.py`, `python scripts/run_loo.py` and
`python scripts/run_validation_dashboard.py`:

| Tier | What it measures | n | Mean | Median |
|---|---|--:|--:|--:|
| Out-of-sample, pre-registered | prediction | 26 | **15.9%** | 11.4% |
| Calibrated, fitted | bookkeeping (low by construction) | 23 | **1.6%** | 0.1% |
| Unfitted module reconstructions | modules vs targets never fitted to | 31 | **56.6%** | 29.9% |
| Calibrated, leave-one-out | how much of the calibration is structure | 18 | **29.6%** | 19.1% |

**Wave 5 moved only the first row, which is the one tier where a moving mean
measures the model.** Its three lanes all worked at the out-of-sample margin: no
target moved, no constant was retuned, and 0 of the 23 fitted rows and 0 of the
31 reconstruction rows changed, with `run_loo.py --donor-matrix` byte-identical
— a falsification test each lane registered in advance and each passed. Wave 5
also named a hole in the fourth row: the leave-one-out suite holds Payroll,
Estate, AMT, Credits, Expenditures and CapitalGains and has **no `Corporate`
row**, so the module whose fitted base turned out to be a stale TY2018 vintage
has never been cross-validated.

**Two of those four changed population in Wave 4, and both means fell for
reasons that are not improvements, so the like-for-like readings belong beside
them**: the fitted tier is **28 at 3.0%, 27/28 within 15%** with Wave 4's five
revised rows held in place (29 at 5.2% with the TCJA-AMT row held in too), and
the reconstruction tier is **65.7% / 40.5% over the 26 rows it already held** —
*worse* than the 61.8% / 38.0% it read before Wave 4 — with its sectoral subset
**88.2% over the 14 it held**. Leave-one-out is the mirror case: it *rose*
28.4% → 29.6% without a single derivation moving, because three of its targets
did. A mean that moves because the population moved has not improved, and a mean
that moves because a target moved has not measured the model.

**The fitted tier has lost eleven rows, and every reason must be quoted with the
number.** `ScorecardSummary.revised_target_entries` is **15**: a constant fitted
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
read 42.0% and 44.3%. The fitted mean *fell* 2.8% → 2.2% → 2.0% → **1.6%**
because every row that left was one it had been carrying, which is
**composition, not accuracy**. The reconstruction tier is itself five
populations — 15 sectoral presets at 82.6%, 8 P.L. 119-21 line items at 35.8%, 3
capital-gains scenarios at 39.6%, the revised TCJA-AMT row at 66.8% and Wave 4's
five arrivals at 9.4% — and must not be quoted as one number. Distributional
accuracy is separate again: 7 published CBO/JCT tables at **0.00-5.86pp**, two
of which are circular, with the ARP row falling **7.77 → 3.72pp** because Wave 4
scored it on CBO's own household universe. See
[`docs/VALIDATION.md`](../docs/VALIDATION.md).

*Re-derived 2026-09-05, after Wave 5 (PRs #111-#117). Tier 1 moved 52.6% → 34.4%
on the eight spending rows in Wave 1, 34.4% → 31.3% on the four capital-gains
rows in Wave 2, 31.3% → 31.0% in Wave 3 by *adding* CBO Option 56 at 24.0%,
31.0% → 18.0% in Wave 4 on five rows, and **18.0% → 15.9%** in Wave 5 on five
more — reached through two pre-registered regressions rather than around them,
because PR #113's payroll correction (54.1% / 55.5% → **7.5% / 8.1%**) was worth
more than PR #114's corporate regression (47.1% → **62.3%**) and PR #116's two
Green Book rows (16.7% → **31.4%**, 0.2% → **43.3%**) cost, while PR #116 also
took CBO Option 47 44.8% → **10.5%**. The CI gate went to `--max-mean-error 20
--min-within-25pct 21` (PR #117).

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
**did not move at all in Wave 5**, whose output is byte-identical. The
reconstruction tier went 250.8% → 82.6% on two pharma rows, then to 21 rows at
76.7% on two target corrections, then to 24 rows at 72.1% when the capital-gains
scenarios arrived, then to 26 rows at 61.8% on L8 and L9, and then to **31 rows
at 56.6%** in Wave 4 — a fall that is entirely composition, since on a constant
population it is **65.7%**, worse, because PR #109's pharma rebuild moved
expanded negotiation 25.7% → 93.3% and international reference pricing
646.2% → 701.0% while PR #107's five arrivals came in at 9.4%; it is unchanged
after Wave 5, which moved no calibrated row. See
[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) §§5.1, 5.2, 5.3, 5.4 and
5.5.*

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

## Modelling plan: Waves 1-5 complete (2026-09-05)

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

### Next: the carry-over list, sequenced by the owner

What is left is a single list of open items at
[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) **§6.2**. Wave 4 closed
nine of them; **Wave 5 closed three more** — payroll at the margin, corporate at
the margin, and the preferential-rate base — and opened six.

What remains, with the newest first: **the behavioural-offset sign sweep** (new,
and the wave's sharpest finding — three modules have now been found with an
inverted or `abs()`-ed offset, `trade.py` in Wave 3, `payroll.py` in W5-A and
`corporate.py` in W5-B, plus the `tax_expenditures` convention W4-3a named, and
**every one of them was invisible to the fitted tier and to leave-one-out**
because the calibrated factories zero the elasticity; the remaining modules have
not been swept); **the corporate module's missing leave-one-out row** (new,
W5-B finding 5 — a `loo.py` edit, so not a modelling lane's to make); **the
FY2022 Green Book target's window offset** (new, W5-C §8.3 finding 5 — worth
about 17 of that row's 43 points, and a shape input under the manifest's
supersede rule); **Build packages not freezable and the Data & methodology
options not pinned** (new, PR #111); payroll's two flat-share "elasticities" and
its unexplained base-growth gap (new, W5-A findings 4 and 5); and the engine's
two year-indexed policy classes with no general concept behind them (new, W5-A
finding 6). Carried from before: the five-class decedent ladder's lack of
within-group dispersion (W4 gains-at-death §8, and still the diagnosis behind
both Green Book rows); the AGI-surtax filing-status threshold row, unchanged at
**44.7%** and now the tier's second-largest; the holdout-protocol re-lock;
`repeal_individual_amt`'s unsourced $450B; Option 56's two payroll alternatives
and its FSA/HRA/HSA base; the expenditure module's behavioural sign convention
(W4-3a finding 3, now one instance of the sweep above); re-basing the UTPR on
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
