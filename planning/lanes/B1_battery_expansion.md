# B1 — Lock the battery before any modelling lane opens

**Status: pre-registration. No module opened. No new row scored. The model was
not run on a candidate.**

This is the first commit of the lane in `planning/PRIORITY5_AND_CHARTS.md` §B1.
The rule for the commit that follows, if one does: each row below that is
marked **register** is transcribed with its page, entered with `runnable=False`,
and scored once. That first error is the out-of-sample result. Nothing in this
file is that commit. `cold_holdout.py` is not run here, and no existing row's
`model_10yr_billions` is touched.

The cohort these later lanes pre-register against stays the one on `main` at
the time of this writing (`e03cec5`): **44 rows, 15.2% mean, 12.3% median,
26 within 15%, 36 within 25%.** Both that cohort and any expanded cohort are
reported when a row is actually added. This commit adds none.

## Where the bar is short

From `fiscal_model/data_files/validation/current_evidence.json`, which is the
report `scripts/cold_holdout.py` feeds:

| Class | n | Mean | Needs for n ≥ 5 |
|---|--:|--:|--:|
| Corporate | 4 | 40.3% | 1 |
| AGI-inclusive surtax | 4 | 7.2% | 1 |
| Enacted-law spending | 3 | 7.4% | 2 |
| Tax expenditure | 2 | 7.1% | 3 |
| Ordinary rate change | 11 | 15.3% | 0 |
| Payroll | 8 | 18.6% | 0 |
| Capital gains | 7 | 14.4% | 0 |
| Discretionary spending | 5 | 4.6% | 0 |

A dynamic tier is separate and is not pooled with these.

## Search, one class at a time

The selection rule is the one in §B1 of the plan and the one R3 already bound
itself to: an agency line item, a page, a shape `create_policy_from_score`
already builds, and no constant fitted to that same reform. A research house
only where no agency scored the policy. A pre-TCJA 35% corporate regime does
not count.

### Corporate — leave at n = 4

The four held-out rows are the +1pp statutory-rate options on a 21% regime,
one from each Options volume (2018, 2020, 2022, 2024). They are already in
the tier.

JCT's JCX-35-25 (1 July 2025), transcribed in
`fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`, is the
revenue table for the 2025 reconciliation. It has no statutory corporate-rate
line. The nearest international row, `pl119_21_fdii_cfc_deduction` (PDF p. 3),
changes a deduction percentage. The file marks it out of scope because
`CorporateTaxPolicy` has a GILTI rate and an FDII repeal switch, and neither
is that provision. Mapping one onto the other would be invention.

No other rate-only row on a 21% regime, with a page, was found in the
transcribed options catalogs. The class stays at **4**, and that is the
record, not a gap to be filled with a 35% regime or a fitted row.

### AGI-inclusive surtax — leave at n = 4

R3 registered every expressible AGI alternative in the 2018, 2020 and 2022
volumes. The 2024 volume's option 46 alternatives are already in the tier.
The remaining 2024 revenue options that touch a base (itemized deductions,
charitable giving, the NIIT expansion) are classified out of scope in
`cbo_options.py` because the module that would score them carries a constant
fitted to that reform. Registering one would be leakage. None is registered.

### Tax expenditure — leave at n = 2

The two rows are the income-tax-only employer-health caps (2022 option 6 and
2024 option 56). The 2022 alternatives that also cap the payroll exclusion
are in `cbo_options_multi_volume_alternatives.csv` with `registered=false`:
the expenditure module has no payroll leg, and the reason is recorded there
(2022 option 6, report p. 30). 2024 options 49 and 50 (itemized deductions,
charitable giving) are the calibrated module, not a prediction. None is
registered.

### Enacted-law spending — leave at n = 3

The three rows are IIJA's discretionary component, the Fiscal Responsibility
Act caps, and the Social Security Fairness Act's WEP/GPO outlays. R3 left the
spending options of the older Options volumes out of scope because each needs
its own budget-authority path, transcribed and passed through
`is_level_budget_authority_path`, and discretionary spending is already at
n = 5. That carry-over is not taken here by implication. No further 2023–2025
cost estimate is transcribed in this tree as a shape the spending module can
score without using the outlay total as its own input. None is registered.

### Dynamic tier — not registered

Two documents are the candidates, and neither is transcribed here at page
level:

- JCT, *Macroeconomic Analysis of the Conference Agreement for H.R. 1*,
  JCX-69-17. `tests/test_dynamic_validation.py` cites "0.7% GDP, ~$450B
  feedback" against a flat −$150B scenario. Those are not a table
  transcription, and the tilde is the tell. The row, when it is added, has to
  say whether JCT's revenue effect is feedback only or feedback plus debt
  service, and the model's matching quantity is the one that gets scored.
- PWBM's dynamic TCJA table. `fiscal_model/assistant/knowledge/pwbm_tcja_dynamic.md`
  describes the shape and does not carry a page-pinned ten-year dollar total.
  A knowledge-file sentence is not a line item.

The dynamic tier stays empty until those pages are transcribed. It is never
pooled with the 44.

## What the next commit may do

Nothing in this file licenses a modelling change. A follow-up may add a row
only by naming a document, a page, and a ten-year total that are not already
rejected above, entering it before the model is run on it, and reporting the
44-row cohort beside the new one. `build_current_evidence.py` and the CI gates
are not edited in that commit either. They move in the docs-sync PR after the
wave.
