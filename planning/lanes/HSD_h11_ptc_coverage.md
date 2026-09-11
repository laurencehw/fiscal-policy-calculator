# HSD / H11 — PTC: the coverage response

*Lane of `planning/HIGH_STAKES_ACCURACY.md` §3 H11, Wave D. Branch
`model/hs-d-h11-ptc-coverage`, cut from `main` @ `20e356d`. Sections 1-5 are the
**pre-registration** and are committed before any module code is opened; §6 is
appended after. Every figure in §§1-3 was computed from the transcribed tables
by `scratchpad/h11/arith.py` before `fiscal_model/ptc.py` was edited.*

---

## 1. The mechanism

### 1.1 What is there now, and why one number is the wrong shape

PR #131 (`planning/lanes/W7_ptc_repeal_shape.md`) put the repeal's static path
on CBO and JCT's own projection of the credit — publication 51298 Table 2,
outlays plus revenue reductions, by fiscal year — and netted a **single
transferred share of 19.28%** out of it, taken from publication 60437's
`$415B` gross against `$335B` net for permanently extending the *enhancement*.

That lane said, in its own §5, that the transfer was the part it was not doing:

> The transferred 19.28% is dominated, in CBO's own itemisation, by
> **employment-based coverage**: \$101B of the \$104B revenue offset is
> compensation shifting between taxable wages and tax-favoured insurance. A
> repeal of the *whole* credit reaches a different population … the true
> composition would carry **less** employer-shift revenue and **more** Medicaid
> pickup than the extension's does.

The defect is not that 19.28% is the wrong size. It is that **a ratio is the
wrong object**. The offsetting effects CBO itemises are responses to *people
moving between sources of coverage*; the quantity they scale with is
**person-years**, not credit dollars. Applying a dollar ratio silently asserts
that a repeal moves the same number of people per dollar of credit as an
extension does — and it does not, because the enrollee a repeal removes and the
enrollee an extension attracts receive very different credits. CBO prints both:
the extension's marginal enrollee gets **\$5,370** a year (60437 Table 3), while
the average subsidized enrollee a repeal removes costs, on the February 2026
baseline, **\$8,671** a year (\$959B ÷ 110.6M person-years). The transfer is
therefore wrong by about **44% in the denominator alone**, before any argument
about who the affected population is.

There is a second defect the aggregate hides, and it is a **sign**. CBO's \$80B
contains a **+\$21B Medicaid and CHIP cost**. A single share applied to a repeal
does not reverse the channels; it scales them all together, so the model is
currently booking that \$21B-equivalent in the direction that erodes a repeal's
saving, when the mirror of CBO's own mechanism (employers restore offers, so
fewer people land in Medicaid) is a **saving**. Only a decomposition can see
that, which is the argument for building one.

### 1.2 The composition, transcribed

CBO and JCT, letter to Chairmen Arrington and Smith, *The Effects of Permanently
Extending the Expansion of the Premium Tax Credit …*, publication **60437**
(24 June 2024), read 2026-09-11 from CBO's own PDF through a Wayback mirror
(`https://web.archive.org/web/2024id_/https://www.cbo.gov/system/files/2024-06/60437-Arrington-Smith-Letter.pdf`;
cbo.gov returns HTTP 403 to every non-browser client in this environment, as
four previous lanes have recorded). FY2025-2034, billions.

**(a) The budgetary channels** — report **p. 3** (the deficit sentence and the
credit's two legs) and **p. 4** (every other line, itemised in prose):

| channel | \$B | direction on the **deficit** under the extension | page |
|---|--:|---|---|
| outlays for the premium tax credit | +250 | ↑ | p. 3 |
| revenue reductions from the credit | +164 | ↑ | p. 3 |
| **gross cost of the credit** | **+415** (sums to 414) | | p. 3 |
| Medicaid and CHIP | +21 | ↑ | p. 4 |
| Basic Health Program and §1332 waivers | +17 | ↑ | p. 4 |
| other outlay effects | −13 | ↓ | p. 4 |
| compensation shifting to **taxable wages** | +101 revenue | ↓ | p. 4 |
| employer-mandate penalties | +3 revenue | ↓ | p. 4 |
| **net effect on the deficit** | **+335** | | p. 3, Table 2 p. 9 (335,045) |

The letter's own arithmetic closes: direct spending `250 + 21 + 17 − 13 = 275`
against its printed \$275B, revenues `−164 + 101 + 3 = −60` against its printed
−\$60B, deficit `275 + 60 = 335`. The **offsets itemise to \$79B against a
printed \$80B** — CBO's rounding to the billion, the same one the existing
`cbo_premium_tax_credit_baseline.csv` header already documents — so the
itemised share is **19.036%** against the transferred **19.277%**.

**(b) The coverage lines** — report **p. 5**, average annual change over
FY2025-2034, millions:

| line | M | page |
|---|--:|---|
| more people with health insurance | **+3.4** | p. 5 |
| net marketplace coverage | **+6.9** (subsidized +7.4, unsubsidized −0.6) | p. 5 |
| Medicaid and CHIP | **+0.5** | p. 5 |
| nongroup purchased outside the marketplaces | **−0.5** | p. 5 |
| employment-based coverage | **−3.5** | p. 5 |

These close too: `6.9 + 0.5 − 0.5 − 3.5 = 3.4`, exactly the printed insured
change. (`7.4 − 0.6 = 6.8` against the printed 6.9 is CBO's rounding again; the
five-line identity is the one that holds to the decimal, so **6.9 is the figure
the normalisation uses**.)

**(c) Two per-person rates CBO prints itself** — report **p. 5** and **Table 3,
p. 10**: people who no longer enroll in employment-based coverage "would have
received an average annual tax benefit of **\$4,350**", and the extension's
6.9M additional marketplace enrollees would receive an average annual credit of
**\$5,370**, accounting for \$368.5B — 89% — of the \$415B.

### 1.3 The engine: four channels, priced per person-year

Each channel is divided by **the coverage movement it is a response of**, using
the letter's own denominators over its own ten years:

| channel | \$B | denominator | **rate** |
|---|--:|---|--:|
| ESI exclusion + employer penalties | 101 + 3 = 104 | 3.5M ESI × 10 yr | **\$2,971.43** per ESI person-year |
| Medicaid and CHIP | 21 | 0.5M × 10 yr | **\$4,200.00** per Medicaid person-year |
| BHP/§1332 + other outlays | 17 − 13 = 4 | 6.9M marketplace × 10 yr | **\$57.97** per marketplace person-year |
| uninsured | 0 | — | **\$0.00** — a person who becomes uninsured costs these channels nothing |

**The identity test**: handed 60437's own coverage vector, those rates return
`104.0 − 21.0 − 4.0 = $79.0B` of deficit offset against CBO's itemised \$79B and
printed \$80B — **19.036%**. That is a check on the transcription, not a fit;
no rate is free.

**One measured quantity the reconstruction produces and the letter does not
state**: the ESI rate of **\$2,971.43** is **0.6831** of the letter's own
\$4,350 average annual tax benefit for the same people. The lane records the
ratio and does **not** assert a cause. Candidates it can name but not separate:
Table 2 makes FY2025 a stub (\$171M of \$335,045M, 0.05%), so the *budgetary*
window is about nine effective years against a ten-calendar-year coverage
average; \$37.7B of the revenue is off-budget Social Security; and the \$4,350
is stated per *person* while the exclusion accrues per *policy*. Naming a
mechanism here without a document would repeat the error W7 §6.0 corrected in
itself.

### 1.4 Applying it to a repeal: what is computed and what is transferred

Two of the three inputs become **computed** and one stays **transferred**, and
the lane's whole claim is that separating them is the improvement:

1. **The coverage change is computed** from the scored vintage's own
   publication 51298 **Table 1**, row "Purchased through ACA marketplaces →
   Subsidized" — the table W7 §6.5 identified and left untranscribed. A repeal
   of §36B removes subsidized enrollment, so the affected population is that
   row, year by year, over the policy's own window:
   - **February 2026** (Table 1, page 2 of 5), calendar 2026-2035: 13.4, 10.3,
     9.7, 10.0, 10.3, 11.1, 11.4, 11.3, 11.5, 11.6 → **110.6M person-years**
   - **June 2024** (Table 1, report p. 2), calendar 2025-2034: 21.3, 15.7, 14.1,
     13.8, 13.7, 13.4, 13.4, 13.4, 13.8, 13.9 → **146.5M person-years**
2. **The channel rates are transferred** — 60437 is the only document that
   prices them, for any §36B change, in either direction.
3. **The destination split is transferred**, and is now *visible per channel*
   rather than folded into an aggregate. Per unit of subsidized marketplace
   change (60437 p. 5, normalised on its 7.4M subsidized line): ESI
   **0.472973**, Medicaid/CHIP **0.067568**, uninsured **0.459459**,
   nongroup-outside 0.067568, unsubsidized-marketplace −0.081081.

The resulting share is a **window ratio computed from the scored population**,
in the same shape as CBO's own `335/415`, and it is then applied to the credit's
own annual path exactly as 19.28% is today. No change to `scoring_engine.py` is
needed and none is made.

| | February 2026 (shipped) | June 2024 |
|---|--:|--:|
| subsidized person-years | 110.6M | 146.5M |
| ESI channel (deficit ↑, erodes the saving) | +\$155.44B | +\$205.89B |
| Medicaid/CHIP mirror (deficit ↓) | −\$31.39B | −\$41.57B |
| BHP/§1332 + other (deficit ↓) | −\$5.89B | −\$7.80B |
| **net offset** | **+\$118.16B** | **+\$156.51B** |
| **offsetting share** | **12.321%** | **13.693%** |
| gross credit | \$959.0B | \$1,143.0B |
| **score** | **−\$840.84B** | −\$986.49B |

**Why the share falls, stated as a mechanism rather than an outcome**: the
offsets scale with people and the gross scales with dollars, and a repeal's
average enrollee holds a **\$8,671** credit where the extension's marginal
enrollee holds **\$5,370**. Fewer people per dollar removed ⇒ a smaller share of
the dollar that comes back. That is the whole of the move, it is forced by two
published figures, and nothing in it was chosen.

### 1.5 The extension row sees the same composition, and moves no dollar

`extend_enhanced_ptc` keeps `annual_revenue_change_billions=-30.5` and a **zero**
behavioural offset, so its +\$366.19B does not move. The reason is the one W7
§1.5 recorded and it has not changed: the only published quantity that would
drive a derived extension path is CBO's own score of that same policy —
60437's \$335B, which **is its target**. Deriving it would manufacture a 0% row
out of the leakage `loo.py` exists to catch. What the extension does gain is the
*reverse view*: `estimate_coverage_effect()` returns 60437's own five coverage
lines instead of an uncited "4 million", which is a surface number and not a
score.

### 1.6 `MARKETPLACE_DATA`'s "19 million", replaced

`estimate_coverage_effect()` renders `receiving_ptc_millions = 19.0` and
`coverage_loss_millions = 4.0` on a surface users see, both uncited. They are
replaced by transcribed rows:

| what it said | what it becomes | source |
|---|---|---|
| repeal: **−19.0M** coverage | the scored vintage's own subsidized enrollment, **−13.4M in 2026**, **−11.06M** average over FY2026-2035 | 51298 Feb 2026 Table 1, p. 2 of 5 |
| repeal: **+15.2M** uninsured (19.0 × 0.8, the 0.8 uncited) | **+5.08M** — the subsidized loss times 60437's own 0.459459 uninsured destination share | 60437 p. 5 |
| extension: **+4.0M** insured | **+3.48M** average, 2.0M in 2026 rising to 3.8M in 2035 | CBO/JCT pub. **61734** (18 Sept 2025) **Table 2**, p. 14 |
| `uninsured_increase_millions: 14.0` "by 2034" | read by nothing; kept, marked uncited | — |

61734 Table 2 is on the app's **own** FY2026-2035 window and its average
(**3.48M**) corroborates 60437's 3.4M on the earlier one, which is worth having
as an independent check that the coverage side of the letter has not been
revised out from under the composition.

### 1.7 Two asymmetries measured, declared, and **not** shipped

Both would move the row **toward** the −\$1,100B this repository refuses, which
is exactly why each is printed here and left out of the code.

**(a) The ESI channel is concentrated above 400% FPL, and that population is not
in the app's baseline.** 60437 Table 3 puts **3.5M of the 6.9M** marginal
enrollees above 400% FPL, and the ESI decline is **3.5M**; p. 6 says the
below-400% half is mostly people "already eligible, [who] would enroll because
of the lower maximum contribution" and that the ESI decline "would affect people
with higher incomes". On the February 2026 vintage the enhancement has lapsed,
so §36B eligibility is capped at 400% FPL and **none** of the affected
population is in the band CBO's ESI channel lives in. Setting the ESI channel to
zero gives **−\$996.28B (9.43% from −\$1,100B)** on February 2026 and
−\$1,192.38B (8.40%) on June 2024. **Not shipped**: "most" and "would affect
people with higher incomes" do not license a zero, a repeal also reaches people
whose employer offer is merely *unaffordable* under §36B(c)(2)(C), and a
mechanism that lands the row on the figure the repository has twice refused is
the one that most needs a document behind it.

**(b) The Basic Health Program's tie is statutory, not behavioural.**
42 U.S.C. §18051(d)(3) sets federal BHP payments at 95% of the premium tax
credit and cost-sharing reductions the enrollee would otherwise have received,
so repealing §36B **zeroes** BHP funding rather than reversing 60437's +\$17B.
51298 Feb 2026 Table 1 puts BHP enrollment at 1.0M. **Not shipped**: the
statutory consequence is clear but its dollar size is not published anywhere
this lane found, and it is an additional *saving*, so estimating it would be
estimating in the direction of the refused target.

### 1.8 Searched and not found

- A second published **composition**. CBO/JCT publication **61734** (September
  2025) scores the same extension on the app's own FY2026-2035 window at
  \$349.8B (Table 1, p. 13) and publishes outlays, revenues and the net — **and
  no channel itemisation at all**, so the 19.28% cannot be recomputed on the
  window the app scores. 60437 remains the only document with the decomposition.
- A published **destination split for a repeal**. Still none; PR #122's and lane
  H9's searches stand and are not re-opened here.
- **Differencing 51298 Table 1** as a substitute is refused with a reason: over
  the enhancement's lapse (calendar 2025→2027, February 2026 vintage) Medicaid
  and CHIP *falls* 80.5 → 78.4 and Medicare *rises* 62.8 → 65.6, because the
  2025 reconciliation act and population ageing sit in the same column. A level
  path is not a policy counterfactual and this lane does not treat it as one.

---

## 2. Files

| file | change |
|---|---|
| `planning/lanes/HSD_h11_ptc_coverage.md` | this document, committed alone first |
| `fiscal_model/data_files/ptc/cbo_ptc_offsetting_channels.csv` | **new** — 60437's eight budgetary lines, five coverage lines and two per-person rates, each with document, page and date |
| `fiscal_model/data_files/ptc/cbo_marketplace_enrollment.csv` | **new** — 51298 Table 1 (both transcribed vintages) subsidized / unsubsidized marketplace, uninsured, employment-based, Medicaid-CHIP by calendar year; plus 61734 Table 2's extension coverage path |
| `fiscal_model/ptc.py` | the channel engine, the composition share, `estimate_coverage_effect` off the transcribed tables, `create_repeal_ptc` |
| `fiscal_model/ui/tabs/results_summary.py` | the existing `ptc_repeal_baseline_caption` extended **in place** (Decision 6) |
| `fiscal_model/validation/scenarios.py` | `repeal_ptc`'s `known_limitations` only — no target, no factory, no constant |
| `tests/test_ptc_coverage_composition.py` | **new** |
| `tests/test_ptc_repeal_shape.py`, `tests/test_ptc_extra.py` | the assertions that pin the old aggregate share and the uncited coverage constants |

Nothing else. `scoring_engine.py` is **not** opened — the composition resolves
to a window share, which is the shape the engine already consumes.

---

## 3. Pre-registered outturn

Computed from the transcribed tables before `ptc.py` was edited. A prediction
missed is reported, never adjusted for afterwards.

### 3.1 The two rows

| row | before | **predicted after** | band |
|---|--:|--:|---|
| `repeal_ptc` model | −\$774.13B | **−\$840.84B** | ±\$5B |
| `repeal_ptc` error vs −\$1,100B | 29.62% | **23.56%** | **20 ± 8** ⇒ [12, 28] |
| `repeal_ptc` rating | Poor | **Poor** (>20%) | must not cross |
| `extend_enhanced_ptc` model | +\$366.186B | **+\$366.186B**, unchanged to three decimals | exact |
| `extend_enhanced_ptc` error | 9.31% | **9.31%** | exact |

`repeal_ptc` stays `calibrated_to_target=False`, `secondhand`, target
**−\$1,100B unmoved**, `EXAMINED_NOT_REVISED` still six entries.

### 3.2 Aggregates

| | before | **predicted after** |
|---|---|---|
| Tier 1 out-of-sample | 26 @ 14.5% / 11.5 med / 16 w15 / 22 w25 | **byte-identical, row for row** |
| Fitted calibrated | 16 @ 1.5% | **byte-identical** |
| Unfitted reconstructions | 39 @ **56.669%**, median 36.9, 10 w15, **13 w25** | **39 @ 56.514%**, median **36.9**, 10 w15, **14 w25** |
| LOO | 18 @ 29.6%, donor matrix | **byte-identical** — no PTC constant is in the suite |
| CI gate `--max-mean-error 20 --min-within-25pct 21` | exit 0 | **exit 0** |
| `check_readiness.py --strict` | `ready_with_warnings` | **unchanged**, including `holdout_protocol`'s two documented Poor entries |
| `build_validation_headline.py --check` | exit 0 | **exit 0** |
| `run_validation_dashboard.py` | exit 1, pre-existing | **exit 1** |

### 3.3 Presets — exactly one moves

| preset | before | **predicted after** |
|---|--:|--:|
| 🏥 **Repeal ACA Premium Credits** (`aca-ptc-repeal`) | −\$774.13B | **−\$840.84B** (+8.62% of saving) |
| 🏥 Extend Enhanced PTCs (`aca-ptc-extend-enhanced`) | +\$366.186B | **unchanged** |
| the other 51 | — | **to the cent** |

A Decision 6 caption ships with the moved preset, computed from the scored
result so it cannot drift, by extending the caption PR #131 already added.

---

## 4. Falsification

Each is checked explicitly in §6 and reported whichever way it fires.

1. **The module reproduces −\$1,100B.** The lane is **falsified** if the shipped
   repeal path lands within a few percent of the carried target: that target is
   a baseline projection, and PR #131 demonstrated it by returning \$1,143.0B
   against CBO's own \$1,142B — **0.09%** — on the June 2024 vintage and window
   with no coverage response. **That demonstration is re-run after the change
   and its result reported.** It must still read −\$1,143.0B, because it zeroes
   the offset; if the composition has changed the *gross* path, something has
   gone wrong in a place this lane never intended to touch.
2. **`extend_enhanced_ptc` moves.** Any movement at all is a leakage failure
   (§1.5), not a finding.
3. **Any non-PTC scorecard row moves**, or the Tier 1 JSON or the LOO donor
   matrix differ. Checked by diff, not by summary line.
4. **The transcription does not reproduce CBO's own printed arithmetic** —
   the direct-spending, revenue, deficit and coverage identities of §1.2, and
   the \$79B/19.036% reconstruction of §1.3.
5. **Strict readiness fails**, or `repeal_ptc` crosses a rating threshold.
6. **A channel rate or a destination share is changed after a score is seen.**
   Every one of them is transcribed in §1 above the code; a lane that moved one
   afterwards would be tuning, and §6 would have to say so.

---

## 5. Out of scope

- **The target.** −\$1,100B stands. `EXAMINED_NOT_REVISED` is untouched, and
  PR #122's verdict against adopting \$1,142B is not re-opened.
- **A derived static path for `extend_enhanced_ptc`** (§1.5), and no
  `reported`/`derived` mode.
- **The two asymmetries of §1.7** — the above-400% FPL concentration of the ESI
  channel and the Basic Health Program's statutory tie. Measured, printed,
  carried over.
- **The ESI rate's 0.6831 ratio to CBO's own \$4,350** (§1.3). Recorded as a
  measured quantity with candidate causes and no verdict.
- **A third vintage**, and `BASELINE_PTC_COSTS` / `CBO_PTC_ESTIMATES`, which W7
  §6.5 already recorded as unsourced. `BASELINE_PTC_COSTS` is still read by
  nothing.
- **`scoring_engine.py`**, `app_data.py`, and every file H7 owns.
