# Corporate class accuracy — why four Options editions of +1pp blow up, and what is left after the receipts vintage

*Diagnosis 2026-09-13. No constant retuned, no elasticity invented, no score
moved. The tables below are printed by
`python scripts/corporate_options_vintage_gap.py` on this tree; they are
arithmetic on inputs already in the repository, not a new estimate.*

Scope: Tier 1's `corporate` class after lane R3 (PR #169) grew it from one row
to four editions of one reform — 21% → 22%, JCT-estimated, published in CBO's
2018 / 2020 / 2022 / 2024 *Options for Reducing the Deficit* volumes. The class
is **4 @ 71.6%**, error mass **286.5**, **36.1% of the 44-row tier**. R5 / PR
#166 flipped `CORPORATE_APP_MODE` to `derived`, refused CBO's loss-firm haircut,
and acquired the credit-carryforward stocks without pricing them. This note
answers what that left standing, and ranks the next moves by measured
error-mass reduction.

It revises one sentence of R3's carry-over 6. That carry-over is still the
highest-value next install. The *leftover it predicted* was the first-year MTS
diagnostic, not the contemporaneous-Outlook counterfactual a lane would
actually wire.

---

## 1. How corporate +1pp is scored

Out-of-sample corporate rows never read the fitted profits aggregate. That is
load-bearing.

| layer | what it does | where |
|---|---|---|
| Shape | `create_policy_from_score` builds a `CorporateTaxPolicy` with `mode=CORPORATE_VALIDATION_MODE` | `fiscal_model/validation/core.py` (`corporate_rate`) |
| Mode pin | `CORPORATE_VALIDATION_MODE = derived` so an OOS row cannot leak `BASELINE_TAXABLE_PROFITS_BILLIONS` (fitted to `biden_corporate_28`) | `fiscal_model/corporate.py` |
| App default | `CORPORATE_APP_MODE = derived` since PR #166. Same identity the battery scores; Decision 1, not a validation leak | same |
| Window | `scoring_window_first_year` opens the decade the *source* published (FY2019 / 2021 / 2023 / 2025) | `CBOScore`; PR #126's rule |
| Vintage stamp | all four rows carry `scoring_vintage="cbo_feb_2024"` — the oldest `BaselineVintage` this repository serves, not the Outlook the option was priced on | R3 §1.4 |
| Rate identity | `Δτ × projected_statutory_base(year)` | `CorporateTaxPolicy._derived_rate_effect` |
| Base | `cbo_corporate_receipts(year) × 4.80133` | `projected_statutory_base`; `BASE_PER_DOLLAR_OF_RECEIPTS` = SOI TY2022 credit-realized base / Treasury FY2022 MTS receipts |
| Receipts path | **one block**: February 2024 Outlook (pub. 59710 Table 1-1), FY2025–2034. Years before FY2025 continue the nearest observed growth (FY2026/FY2025 = −0.546%/yr) *backwards* | `cbo_corporate_receipts.csv`; `cbo_corporate_receipts()` |
| Phase | IRC §6655: 0.75 in `start_year`, then `0.75 + 0.25 × B(t−1)/B(t)` | `get_phase_in_factor` |
| Offset | `static × 0.8 × (τ₀ + Δτ)` = 17.6% of phased static at +1pp. Heckemeyer & Overesch, one frozen value | `PROFIT_SHIFTING_SEMI_ELASTICITY` |
| Engine | asks for the year and applies **no** 4%/yr growth — the path already carries CBO's | `scoring_engine.py` (`uses_projected_base`) |
| Reported mode | `Δτ × $1,900B`, grown at 4%/yr, flat 12.5% offset. **Not on these four rows.** Still what `validate_corporate_policy(..., mode="reported")` prints for Decision 1 | `CORPORATE_MODE_REPORTED` |

A window is not a vintage, and R3 said so. The four rows sit on the right
*decades*. They do not sit on the right *receipts paths*. `cbo_corporate_receipts`
has no April 2018, September 2020 or May 2022 block; `cbo_receipts_by_fiscal_year`
raises rather than silently substituting, and the only vintage it can return is
`cbo_feb_2024`. Everything before FY2025 is an extrapolation of that nearly-flat
line, not a clamp and not CBO's then-current Outlook.

`reported` vs `derived` is not this class's residual. All four rows are pinned
to `derived`. The app default matching that pin is a presentation fact, not an
accuracy claim: `derived` still sits at 80.8% of the vintage's average base
against a published 55.1–79.5%.

---

## 2. The four rows

Targets are JCT estimates that CBO publishes. Every corporate-rate option in
every *Options* volume carries "Data source: Staff of the Joint Committee on
Taxation" verbatim (`planning/memos/CORPORATE_PER_POINT_YIELD.md` §2; each
`CBOScore.source` is `JCT`).

| row | volume | pub. | report p. | window | Outlook the option names | target $B | live $B | live err |
|---|---|--:|--:|---|---|--:|--:|--:|
| `cbo2019_opt24_corporate_rate_1pp` | 2018 | 54667 | 266 | FY2019–2028 | Apr 2018 Outlook, pub. 53651 | −96.3 | −192.3 | **99.7%** |
| `cbo2021_opt19_corporate_rate_1pp` | 2020 | 56783 | 293 | FY2021–2030 | Sep 2020 Update, pub. 56517 | −99.3 | −191.8 | **93.1%** |
| `cbo2023_opt50_corporate_rate_1pp` | 2022 | 58163 | 115 | FY2023–2032 | May 2022 Outlook, pub. 57950 | −129.3 | −192.9 | **49.2%** |
| `cbo_opt64_corporate_rate_1pp` | 2024 | 60557 | 75 | FY2025–2034 | Feb 2024 Outlook, pub. 59710 | −135.7 | −196.1 | **44.5%** |

CBO/JCT's four answers for the identical reform span **41.0%**. The model's
four answers span **2.2%**. That is R3 §5.4, and it is still the sharpest
statement of the class.

The annual Outlook paths those four options were priced on are **already
transcribed** as `BASELINES` in `scripts/corporate_yield_reconciliation.py`
(Apr 2018 Table 4-1, Sep 2020 Table 1, May 2022 Table 1-1, Feb 2024 Table 1-1).
They were never copied into `cbo_corporate_receipts.csv`. The February 2024
block is the only one scoring reads.

### 2.1 Shipped path vs contemporaneous Outlook vs first-year MTS

`scripts/corporate_options_vintage_gap.py` rebuilds the derived identity on
each receipts path and matches the live scores to the dollar ($0.000B).

| row | live err | on that edition's own Outlook path | first-year MTS deflation (R3 diagnostic) |
|---|--:|--:|--:|
| 2018 | 99.7% | **53.4%** (−$147.8B) | 10.0% (−$86.7B) |
| 2020 | 93.1% | **21.8%** (−$120.9B) | 42.2% (−$141.2B) |
| 2022 | 49.2% | **41.6%** (−$183.1B) | 25.3% (−$162.0B) |
| 2024 | 44.5% | **44.5%** (−$196.1B) | 32.2% (−$179.4B) |
| **class mean / mass** | **71.6% / 286.5** | **40.3% / 161.3** | — |

Receipts 10-year totals, shipped (Feb 2024, back-extrapolated) over
contemporaneous:

| row | shipped $B | contemporaneous $B | ratio | FY1 shipped / MTS actual |
|---|--:|--:|--:|---|
| 2018 | 4,982.4 | 3,846.6 | **1.295×** | 510.6 / 230.2 = **2.218×** |
| 2020 | 4,975.5 | 3,152.6 | **1.578×** | 505.0 / 371.8 = **1.358×** |
| 2022 | 5,006.1 | 4,754.9 | **1.053×** | 499.5 / 419.6 = 1.191× |
| 2024 | 5,093.9 | 5,093.9 | **1.000×** | 494.1 / 452.1 = 1.093× |

Three things this settles.

**The hypothesis is right about the 2018/2020 blow-ups and wrong about the
leftover.** Back-projection of the February 2024 path *is* most of 99.7% and
93.1%. Installing the Outlook each option names — the thing a lane would
actually do — takes those rows to **53.4% and 21.8%**, not to R3's 10.0% and
42.2%. The 10% figure applies the FY2019 MTS ratio (2.218×) to a ten-year
score whose last four years are already on the transcribed block; the
window-mean receipts ratio is 1.295×. The 42.2% figure uses FY2021 *actuals*
($371.8B) where JCT scored against CBO's September 2020 *projection*
($122.8B). That Outlook is a COVID outlier and the memo already flags its
denominator; it is still the right path for that row, because it is the path
the target was priced on.

**The 2022 row is already almost on its own path.** FY2023–2024 sit before the
transcribed block (1.053× over the window). R3 listed back-projection as a
limitation on the 2018 and 2020 rows only; the 5.3% overstatement is real and
small. Wiring May 2022 is cheap while the file is open and is not the prize.

**The 2024 row has no vintage problem.** FY2025–2034 *is* the transcribed
block. Deflating it by FY2025 MTS actuals ($452.1B against a projected
$494.1B) is answering a different question — how CBO's projection missed that
year — and is not a scoring defect. 44.5% is the structural residual.

MTS actuals are a diagnostic for "how wrong is walking February 2024
backwards." They are **not** a scoring path. JCT scored against CBO's then-
current Outlook, not against realized receipts.

### 2.2 After the vintage is right, every leftover is one number

JCT's implied marginal share of each vintage's own average base
(`CORPORATE_PER_POINT_YIELD.md` §2 / §4):

| edition | JCT share | model share (derived, on that path) | `0.808 / share − 1` | contemporaneous error |
|---|--:|--:|--:|--:|
| 2018 | 52.6% | 80.8% | 53.6% | **53.4%** |
| 2020 | 66.1%* | 80.8% | 22.2% | **21.8%** |
| 2022 | 57.1% | 80.8% | 41.5% | **41.6%** |
| 2024 | 55.9% | 80.8% | 44.5% | **44.5%** |

\*COVID-outlier denominator; the 21.8% leftover is the module's usual level
measured against a depressed base, not a more accurate score.

The four residuals are four readings of **one** gap: this module reaches
~81% of the credit-realized statutory base a receipts path implies, and JCT
reaches 53–57% on a clean post-TCJA baseline (66% on the COVID one). No
edition-specific mechanism is required to explain what is left. That is why
CAMT is a weak candidate for the 2022/2024 leftover: after the vintage is
right those two sit at 41.6% and 44.5%, next to 2018's 53.4% on a window that
is mostly pre-CAMT. A CAMT-sized hole would have opened a gap *between*
editions, and it does not.

The 80.8% is W6's number (PR #121): February 2024 receipts × 4.80133, after
the 17.6% offset and the §6655 phase. It replaced a 90.8% that had been aging
SOI at 4%/yr against a 1.2%/yr receipts path. The memo's published span on
the same window is Tax Foundation 55.1%, JCT 55.9%, PWBM 64.4%, Treasury OTA
(rate + GILTI) 79.5%. The model is above all four at +1pp. Haircut ×0.85
would have taken the 2024 row to 22.8% and was refused: it adjusts a
*statutory rate* in a user-cost expression, and this path multiplies a *base*
that already nets loss firms (`planning/lanes/R5_h3b_corporate.md` §1.1;
`tests/test_corporate_loss_firm_haircut.py`).

---

## 3. What is still unknown

These are open because a source is missing, not because nobody looked.

1. **The share of the base held by taxpayers who are both §38(c)-capped and
   holding general-business-credit carryforward.** The stock is transcribed
   (`credit_carryforward_stocks.csv`): Form 3800 carryforward into 2022 is
   $124.47B against $72.17B of claims (1.72 years). `credit_absorption_bounds`
   puts the average substitution already in use at **29.15%** of a marginal
   pre-credit dollar and the §904 upper bound at **28.85%** — a third of a
   point apart — so the foreign-tax-credit channel is essentially booked and
   the §38(c) channel is **entirely unbooked**. CBO's 2018 Option 24 is the
   only volume with a narrative and it names exactly this channel ("An
   increase in the corporate tax rate would increase corporations' ability to
   use tax credits … That use of credits would reduce revenues"). SOI's
   excess-position tables stop at TY2010. A chosen share is forbidden; a
   reinstated table, a Treasury tabulation, or microdata is not.

2. **CAMT's regular-tax base.** Book minimum began in TY2023, after the last
   SOI Complete Report on file. Treasury JY2574 gives ~100 payers and a 2.6%
   counterfactual effective rate; JCT's 2022 Wyden letter gives 175–200
   corporations averaging $8.2B of 2019 book income. Neither is a base. Worth
   re-opening when the TY2023 Complete Report publishes. Not the separator
   between these four editions (§2.2).

3. **Why JCT's first-year factor runs 0.591–0.732** against this module's
   0.757. No *Options* volume mentions payment timing. Treasury's 0.59/0.60
   on the Green Book rows is a *statutory blend* of the rate, which this
   module has no concept of. Untouchable without a source.

4. **The 1.19× JCT-vs-Treasury-rate-only estimator gap.** Documented, not
   closed. Nobody publishes a parameter that would let this module land inside
   JCT's 55.9% without reading JCT's answer backwards. The total factor that
   reproduces Option 64 is **0.5785**; JCT's own steady-state share is
   **0.590**. Both are printed in `scripts/corporate_marginal_share.py` so a
   lane can see how close it got without aiming.

5. **Whether `US-CBO/cbo-data` will ever grow a pre-2024 `ten_year_budget`
   block.** It currently ships `2024-06`, `2025-01`, `2026-02` only. The
   April 2018 / September 2020 / May 2022 annuals in `BASELINES` were read
   from those Outlooks' own tables (Wayback mirrors of cbo.gov; the
   environment 403s `cbo.gov` directly). They are primary documents, mirrored
   delivery — the same standard the yield memo used. A later lane that
   prefers a CBO GitHub CSV should take it if one appears, and should not
   wait for one.

---

## 4. Recommended next actions

Ordered by expected error-mass reduction. Each is an install of a published
input or a bounded search, not a retune. The class mean after (1) is still
~40%; that is the honest remaining problem, and (2)–(4) are what is left of
it.

### 1. Wire the three Outlook paths that are already transcribed — expected mass −125

Copy the `cbo_apr_2018`, `cbo_sep_2020` and `cbo_may_2022` annuals from
`scripts/corporate_yield_reconciliation.py` `BASELINES` into
`cbo_corporate_receipts.csv` as additional `vintage` blocks. Teach
`projected_statutory_base` / the `corporate_rate` shape to read the Outlook
each `CBOScore` names (the documents are already in
`corporate_rate_scores.csv` `baseline_vintage` and in each row's notes). Do
not invent a `BaselineVintage` member for 2018 unless a scored *budget* path
needs one; a receipts-file key is enough.

This is R3 carry-over 6, with the leftover restated. The two older blocks do
almost all of the work (−117.6 of −125.2). May 2022 is a 7.6-point tidy-up
that belongs in the same commit because the file is open. The 2024 row must
stay byte-identical.

**Verify.** `python scripts/corporate_options_vintage_gap.py`: the
`contemporaneous_*` columns become the live scores; 2018 53.4%, 2020 21.8%,
2022 41.6%, 2024 44.5% to one decimal; reconstruction gap stays $0.00B;
`run_loo.py --donor-matrix` byte-identical; both calibrated tiers
byte-identical; zero presets move (no module constant changes). Pre-register
those four figures before opening `corporate.py`. Quote the 21.8% with the
COVID-denominator clause or do not quote it.

**Do not** substitute MTS actuals, and do not deflate the 2024 row by FY2025
actuals. Those are diagnostics.

### 2. Keep hunting a §38(c) constrained-base share — remaining class ~40%

The only named channel that points the leftover *down* and is not already
booked. Stocks and bounds exist; the share does not. A lane that finds one
(TY2010 SOI excess-position tables as a historical cross-check, a later SOI
release, Treasury OTA) should bound the 2024 row's movement *before*
applying anything, and should refuse a number that lands Option 64 on 0.5785.

**Verify.** `credit_absorption_bounds()` still reports average substitution
≈ §904 upper bound (29.15% vs 28.85%) after any change; a new share is a new
row in `credit_carryforward_stocks.csv` with a document; `cbo_opt64` moves
only by the product of that share and the unused 75% §38(c) cap, printed
beside the forbidden 0.5785.

### 3. Re-open CAMT when TY2023 SOI exists — expected mass small, sign unknown

Blocked on a publication, not on a modelling idea. After (1) the 2022 and
2024 leftovers agree to three points, so a large CAMT term would have to be
offset by something else of the same size. Worth a CHECK-ONLY pass the week
the Complete Report lands; not worth inventing a payer count.

**Verify.** A transcribed TY2023 `income subject to tax` for CAMT-liable
corporations, or an explicit "cell suppressed"; no score movement without
that cell.

### 4. Do not do these

| action | why |
|---|---|
| Apply CBO's 0.85 / 0.80 haircut | Refused on the merits, PR #166. Wrong object; CBO divides it back out to avoid double-counting |
| Adopt 0.5785 or JCT's 0.590 as a "realization share" | Reading the target backwards. `corporate_marginal_share.py` prints both so the failure mode is visible |
| Age SOI at a fitted rate, or pick TY2019 because it sits near JCT's $1,357B | The coincidence the yield memo already retired |
| Retune `PROFIT_SHIFTING_SEMI_ELASTICITY` or `BASELINE_TAXABLE_PROFITS_BILLIONS` | One is literature-frozen, one is the fitted constant `derived` exists to ignore |
| Use MTS actuals as the scoring path | JCT scored a projection |
| Collapse the four rows into one "validated within X%" after (1) | 21.8% and 53.4% are the same mechanism on two denominators |

---

## 5. What this note is not

It is not a pre-registration. A lane that opens `corporate.py` to do §4.1
still owes R3's two-commit rule and this note's four predicted leftovers,
written down before the file is touched.

It is not an accuracy claim about `derived`. Wiring three Outlooks takes a
class of four from 71.6% to 40.3% by giving each row the receipts path its
own document used. The 40.3% that remains is the same 80.8-versus-JCT gap
the 2024 row has been reporting since PR #121. Removing the back-projection
does not make the module a better estimator of a statutory point; it stops
reporting a 99.7% row as if the module had failed a test it was never given.
