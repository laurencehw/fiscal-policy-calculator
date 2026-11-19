# Bet 3b: the four P.L. 119-21 deduction extensions as Build list prices, and the PTC preset on its own window (pre-registration)

Pre-registered 2026-11-19, before any code in this lane is written. The outturn
is appended below the line at the end, in the same commit series, and the
predictions above it are not edited after the first code commit.

## Why

The 16 November site review asked for presets that match 2026 debates. Two of
the live questions are whether to keep P.L. 119-21's temporary individual
deductions past 2028 and whether to restore the lapsed enhanced premium tax
credits. Neither could be sourced from this environment (cbo.gov is refused by
the proxy). The figures below were read on Laurence's own machine on 18 November
and are saved at `/mnt/project-files/sources/fpc-sources-2026-11-18.md`
(sections 1 and 3). Laurence approved this PR on 19 November.

## Scope

### 1. Four score-only Build options

CBO/JCT's letter to Senator Merkley of 4 August 2025 (publication 61466, data
file Table 2) prices extending each provision beyond 2028. Conventional, CBO's
January 2025 baseline, FY2025-2034, $ billions, positive = adds to the deficit:

| P.L. 119-21 section | Provision | Cost of extension |
|---|---|--:|
| 70201 | No tax on tips | 52 |
| 70202 | No tax on overtime | 137 |
| 70103 | Senior deduction | 129 |
| 70203 | Car-loan interest deduction | 66 |

They become `CBO_SCORE_MAP` entries with **no** `PRESET_POLICIES` row, the
pattern `salt-deduction-eliminate` and `mortgage-deduction-eliminate` already
use: Build quotes the figure as a list price and the engine never runs it.
The engine has no income base for tips, overtime or car-loan interest, so a
scored version is a separate lane.

* Ids, frozen once shipped: `tips-deduction-permanent`,
  `overtime-deduction-permanent`, `senior-deduction-permanent`,
  `car-loan-interest-deduction-permanent`.
* Area: "Individual rates" is wrong (they are deductions, not rates);
  "Tax expenditures" is right and is where the two existing score-only rows sit.
* Interaction channel: one new channel, `pl119_21_deductions`, shared by all
  four, so Build's package classifier says that picking two of them is not a
  clean sum. CBO prints no combined figure for the four (they add to $384B, which
  is my addition), and Tax Foundation's interaction-adjusted combination exists
  on a different window, so the honest disclosure is "interacting, not
  measured".
* The note on each row says the window (FY2025-2034, so six years of
  extension, 2029-2034) and that other houses differ by a lot: Tax Foundation's
  *Options 3.0* prices overtime at $372.4B over 2027-2036, almost three times
  CBO's figure on an overlapping window. This is quoted as context, not as a
  second target.

### 2. "Restore ACA Enhanced PTCs" moves from $335B to $350B

CBO's letter of 18 September 2025 (publication 61734, p. 1): permanently
extending the enhanced credits would increase "the deficit by $350 billion from
2026 to 2035". FY2026-2035 is the app's own window, and the enhancements lapsed
at the end of 2025, so this is the figure for the question the preset asks.

This goes through the calibrated-tier ledger, not an edit:

* `extend_enhanced_ptc.v3`, $350.0B, CBO/JCT publication 61734, window
  FY2026-2035. `.v2` ($335B, publication 60437, FY2025-2034) gets
  `superseded_by="extend_enhanced_ptc.v3"`.
* The figure equals `.v1`'s. That is not a reversal of the Wave 4 revision.
  `.v1` was rejected because its declared window (FY2025-2034) and its figure's
  window (FY2026-2035) disagreed and the source was unnamed. `.v3` declares the
  figure's own window and names the document, which is what Wave 4 asked for.
* Finding before any code: the validation runner already scores this row from
  FY2026. `validate_ptc_policy` builds the scorer at `policy.start_year`, and
  `create_extend_enhanced_ptc` defaults to `start_year=2026`. So `.v2` compared a
  FY2026-2035 run against a FY2025-2034 figure, and `.v3` fixes that. Nothing
  else about the run changes: the module prices a flat annual grown from the
  policy's own start year, so its total is +$366.19B on either window.
* Label becomes "🏥 Restore ACA Enhanced PTCs ($350B)". The slug
  `aca-ptc-extend-enhanced` stays and the old label goes into
  `LEGACY_LABEL_ALIASES`.

## Predictions

* **No engine score moves.** The PTC preset's model score is unchanged at
  +$366.19B. `cold_holdout.py --json` and `run_loo.py --donor-matrix` are
  byte-identical. Every other preset's `site_data` score file is unchanged apart
  from label text.
* **`extend_enhanced_ptc` goes from 9.31% to 4.62%** (366.19 / 350 − 1). This is
  the target moving, not the model improving. The module's −$30.5B annual was
  originally tuned toward "~$350B", so part of the closer fit is that constant's
  own history. The row **stays in the unfitted-reconstruction tier**: a revised
  target forces `calibrated_to_target=False`, and the constant is not re-labelled
  as fitted.
* **The reconstruction tier's mean falls by about 0.12pp** (one row of 39 moving
  by 4.69 points). Its held-in-place line (41 rows) falls by about 0.11pp. The
  fitted tier, Tier 1 and leave-one-out do not move. I regenerate
  `current_evidence.json` and fix whatever doc sentences its test names.
* **Build:** four new rows, all in the adds-to-deficit section under Tax
  expenditures, with list prices +52, +137, +129, +66. The PTC row's list price
  goes from +335 to +350.
* **Values composer:** no starting package changes. The composer picks revenue
  raisers for a deficit target, the four new rows and the PTC row all add to the
  deficit, and score-only rows carry no values tags.

## Falsification

* Any engine score moving, or any Tier 1 row moving, means something beyond a
  target and four list prices changed.
* A starting package changing means the composer reads cost rows in a way this
  document did not expect.
* If the ledger refuses `.v3` (for example a rule against returning to a
  superseded figure), I stop and report rather than work around it.
