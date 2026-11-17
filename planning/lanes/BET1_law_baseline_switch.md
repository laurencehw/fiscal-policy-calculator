# Bet 1: law-baseline switch (pre-registration)

Pre-registered 2026-11-17, before any code in this lane is written. The outturn
is appended below the line at the end, in the same commit series, and the
predictions above it are not edited after the first code commit.

## The question

A score is a difference from a baseline. The site scores against CBO's
February 2026 Outlook (publication 61882), which already contains P.L. 119-21.
Eight presets were built to answer the 2024-25 question, "what does extending
or repealing this cost against the law as it stood before July 2025?" Since
PR #248 they carry a "pre-2025 law" chip and Build leaves them out, but Explore
still prints their pre-2025 number as the headline and gives no current-law
answer at all.

This lane gives each of the eight presets its answer on current law and shows
it first, above the stored pre-2025-law figure, on the preset page and in the
Explore list. It takes the classification in Cursor's PR #257
(`fiscal_model/law_baselines.py`) and rebuilds it on main against #248's
`pre_2025_law` flag. It does not take #257's `?law=` toggle: the pages are
static, and showing both answers side by side needs no client-side state and
cannot leave a reader on the wrong yardstick by accident. Three further changes
from #257:

1. **The no-SALT-cap TCJA variant is scored, not left blank.** Against current
   law, TCJA is already in the baseline, so "extend TCJA without the SALT cap"
   is exactly "repeal the SALT cap on the current-law path". That is the
   existing `salt-cap-repeal` preset, scored on `SaltCapBaseline.CURRENT_LAW`
   (PR #161). No new modelling.
2. **The IRA repeal shows what P.L. 119-21 already ended**, sourced to JCT
   JCX-35-25 (subchapter A, $542.7B over FY2025-2034, already transcribed in
   `pl119_21_jct_line_items.csv`). The remainder is not computed, because the
   preset's −$851B target is Tax Foundation's and the terminations are JCT's;
   subtracting one estimator from another is not a score.
3. **Publication numbers are corrected.** #257 cites CBO publication 62105 for
   the February 2026 Outlook; the Outlook is 61882 (as `baseline.py` and
   CLAUDE.md already say). Its $4.7T dynamic figure is cited to CRFB's reading
   of that Outlook instead.

## Predictions

Current-law view (the default). The stored (pre-2025-law) figure stays on every
page beneath it. No other preset's number changes in any view.

| Preset | Stored (pre-2025 law) | Current law | Why |
|---|--:|--:|---|
| tcja-full-extension | +$4,581.9B | **$0** | JCX-35-25 Ch.1 items 1-7: already law |
| tcja-rates-only | +$3,114.7B | **$0** | JCX-35-25 item 1 |
| estate-extend-tcja | +$167.0B | **$0** | item 6 ($15M, indexed, more generous) |
| amt-extend-tcja-relief | +$450.5B | **$0** | item 7 |
| ctc-extension | +$600.0B | **$0** | item 4 ($2,200 indexed, more generous) |
| ev-credit-repeal | −$228.4B | **$0** | credits end for vehicles after 30 Sep 2025 |
| tcja-extension-no-salt-cap | +$6,494.5B | **+$740.3B** | = salt-cap-repeal on the current-law cap path, to the cent |
| ira-clean-energy-repeal | −$783.0B | **not computed** | JCT: $542.7B of the credits already ended |
| salt-cap-repeal | +$740.3B | +$740.3B | unchanged; already scored on current law |

Where the enacted law is more generous than the preset (CTC, estate), the
$0 is the extension having happened. The preset's own design would be a cut
against current law; that difference is named on the page and not scored.

## Falsification tests

- `scripts/cold_holdout.py --json`, `run_validation_dashboard.py` and
  `run_loo.py --donor-matrix` are byte-identical. No model code is opened.
- Every `site_data/presets/<id>.json` and `views/*.json` file is byte-identical
  (apart from the export's known run-to-run noise in `salt-cap-repeal` and
  `states.json`, which is reverted as usual). Only `presets/index.json` and
  `build-catalog.json` change, by gaining a `current_law` field on each status.
- The no-SALT-cap current-law figure equals `salt-cap-repeal`'s stored
  conventional score to the cent, asserted by a test that reads both.
- A test fails if a preset carries `pre_2025_law=True` without a current-law
  role, or the reverse.

## Out of scope

- Rescoring any preset on January 2025 current law (the pre-2025 view keeps
  the February 2026 figure for the 52 live presets and says so).
- The `?law=` toggle and the "temporaries extended" yardstick from #257. The
  second is the live 2026 question and deserves its own lane with scored
  presets (tips, overtime, the senior deduction, the $40,000 SALT cap), not a
  label over the current-law scores.
- Build. Starting packages already leave the eight out.

---

## Outturn

*(appended after implementation)*
