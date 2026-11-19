# Bet 4: a second package total on Build, on one window

Pre-registered 2026-11-19, before any code. Source: the 16 Nov site review, bigger bet 4
("Score Build packages jointly through the engine instead of adding list prices from different
windows and years"), and `planning/PRIORITY5_AND_CHARTS.md` B7/C6.

## What is wrong now

Build's total adds published list prices. They come from different documents, windows and
baselines (2021 to 2026), so the sum describes no single decade. Under it the page prints one
fixed sentence, "Interactions between these policies are not measured", which is false for the
one pair the microsim does measure (the top rate with SALT-cap repeal) and says nothing specific
about any other pair.

## What the engine can actually do jointly

Read before designing, so the lane does not promise more than exists:

- `FiscalPolicyScorer.score_package` sums standalone scores and multiplies by an
  `interaction_factor` that defaults to 1.0. It is a sum, not a joint model.
- `package_interactions.joint_tax_change` runs reforms together on the CPS microsim. Only three
  Build rows have a microsim reform (`MICROSIM_MEASURABLE_IDS`: `top-rate-39-6`,
  `salt-cap-repeal`, `eitc-childless-expansion`). The microsim's levels sit 3-4x below list
  prices, so its dollars are not shown; only shares are (the module's own rule).
- 42 of the 48 Build rows have a calculator score on FY2026-2035 in `site_data/presets/`. The six
  without one are the mortgage deduction and five score-only rows (SALT elimination and the four
  P.L. 119-21 deduction extensions).

So "jointly through the engine" can honestly mean: every row the calculator scores, on one window
and one baseline, plus the measured overlap where the microsim measures one. It cannot mean a
joint model of corporate, payroll, estate, tariffs or the TCJA composite, and the page must say so.

## Design

1. **Static, not a live call.** Build's choices are a fixed catalog of 48 rows and the only
   nonzero measured overlap is among three of them, so `scripts/export_static.py` precomputes
   everything and the page needs no engine call, no cold start and no API key. Tailor calls the
   engine because its inputs are free; Build's are not. (B7 asked the PR to pick one and say why.)
2. **Export** a `site_data/package-joint.json`: each row's interaction channels, the channel
   labels, and every measurable pair's measured share and reference member, from
   `measure_reforms` / `measured_interaction_share` as they stand. No new constant.
3. **Headline unchanged.** The big figure stays the list-price sum (`total()`), as B7 says, until
   Laurence decides otherwise.
4. **Second total**, in the `secondTotal` slot U5 left: "Calculator total, FY2026-2035". It is
   the sum of the calculator's conventional scores for ticked rows that have one, plus, for each
   measured pair both ticked, `-share x |calculator score of the reference member|` (a negative
   share means less revenue, so the deficit is higher). It names the ticked rows it leaves out
   and their list prices, and says which tiers it mixes (from each preset's `own_row_tier`). It
   is shown when at least two policies are ticked and at least one has a calculator score.
5. **The interaction sentence** under the total is built from the selection: the measured pair
   with its share, "additive by construction in this model" for rate x credit (never "no
   interaction"), named shared channels for overlaps with no joint model, and a plain "not
   modelled" otherwise. The PNG and CSV exports carry the same sentence instead of the fixed one.

## Predictions (fixed now)

- Exported share for `top-rate-39-6` x `salt-cap-repeal` equals `measured_interaction_share` to
  the last digit: -16.35% of the top-rate item's yield (reference `top-rate-39-6`). B7's "13.7%
  and 20.2% with the sign flip" predate R6c's calibrated population and statutory AMT; the
  repository's own test already moved to the current band, and this lane does not reopen it.
- `top-rate-39-6` x `eitc-childless-expansion` exports as structurally additive, interaction 0.
  `eitc-childless-expansion` x `salt-cap-repeal` exports as no overlap, interaction 0 (to 1e-9).
- The three-way microsim interaction equals the sum of the pairwise ones to within $0.01B a year,
  so applying pairs is exact for the measurable set. A test asserts it.
- Ticking the top rate and SALT-cap repeal: list-price sum **+$923.1B**; calculator total
  **+$481.2B** (-$309.8B + $740.3B + $50.6B overlap).
- Adding the childless EITC: list-price sum **+$1,085.7B**; calculator total **+$659.2B**.
- No scored number anywhere moves. `cold_holdout.py --json`, the validation dashboard and every
  `site_data/presets/*.json` are byte-identical (bar the known float-noise files).

## Acceptance

- Web tests: a supported set (top rate + SALT repeal: overlap applied, nothing excluded), an
  unsupported set (two corporate rows: summed, overlap named as not modelled), and a mixed set
  (one scored row plus a score-only row: the score-only row is named as left out).
- Python test pins the export to `package_interactions` so it cannot drift.
- The fixed sentence "Interactions between these policies are not measured." no longer appears
  for a selection that contains a measured pair.

## Outturn (2026-11-19)

Laurence chose the one-window calculator total over B7's microsim-only version on the decision
card, so the lane shipped as designed above.

- **Every prediction landed.** The exported share is `measured_interaction_share` to 1e-12
  relative (to the last digit on one machine; Python 3.10 CI differs in the final binary digit,
  so the test compares at 1e-12), -16.35% of the top-rate item's yield; rate x childless EITC exports as structurally
  additive and EITC x SALT as no overlap. The three-way microsim interaction equals the sum of the
  pairwise ones within $0.01B, so applying pairs is exact for the measurable set
  (`tests/test_package_joint_export.py`). Top rate + SALT-cap repeal: list-price sum +$923.1B,
  calculator total **+$481.2B**; adding the childless EITC: +$1,085.7B and **+$659.2B**
  (`web/lib/packageJoint.test.ts`).
- **No scored number moved.** No Python model file changed; the only new export is
  `site_data/package-joint.json`, and every preset, view and validation file is untouched.
- **What shipped.** `export_static.package_joint_payload` writes the channels, channel labels and
  measurable pairs. `web/lib/packageJoint.ts` computes the calculator total (scored rows only,
  measured overlap applied, rows left out named with their list prices, tiers counted from each
  preset's `own_row_tier`) and the selection's interaction sentences. `PackageSummary` shows both
  under the list-price headline, which is unchanged; on a phone the notes open with the policy
  list. The CSV now carries the notes and a `calculator_total` row; the PNG's caveat is the
  selection's sentences. The fixed "Interactions between these policies are not measured" is gone
  everywhere; the list-price sum's own tag now says it "does not adjust for interactions".
- **What it is not.** Apart from the one measured pair it is still a sum, of the calculator's own
  scores instead of published ones. It fixes the window and baseline, not the joint modelling of
  corporate, payroll, estate, tariff or TCJA items, and the page says so pair by pair. Fitted rows
  carry a published figure through a calibrated constant, so for those the "one window" is the
  constant's window; the tier sentence is how a reader sees that.
- **Not done.** The Streamlit app's `inconsistent_list_price` finding (a bundle beside a sibling of
  something it contains) is not ported; Build's exclusive-group rules already stop the common
  cases. Six rows (mortgage deduction and five score-only rows) have no calculator score and are
  always named as left out.
