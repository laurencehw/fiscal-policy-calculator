# B5: score the corporate anchor as rate plus a sourced GILTI piece (stopped)

*Opened 2026-11-06 against `main` @ `529efc1`. Plan: `planning/PRIORITY5_AND_CHARTS.md`
§B5. Owner decision recorded 2026-11-04: option (a), score `biden_corporate_28` as
rate plus a sourced GILTI piece. **Result: the lane stopped at its source step,
as the plan's stop rule allows. No scored number moves.***

## 1. What the plan asked for

`biden_corporate_28` (Treasury FY2025 Green Book, −$1,349.9B) is a "rate + GILTI"
row and `create_biden_corporate_rate_only` prices the rate only. The plan read
that as the module's per-point yield absorbing Treasury's GILTI linkage. Under
option (a), the anchor would be scored as rate plus a GILTI piece taken from a
source, so that what was left would calibrate rate-only. Before anything else,
the plan required a sourced GILTI base: "If no source supports a GILTI base, B5
stops and says so."

Two falsification conditions were fixed in the plan:
1. If the sourced GILTI piece is under ~$100B over ten years, the share barely
   moves and the lane reports that.
2. If the share falls below JCT's 55.9%, the GILTI piece is too large and the
   lane stops.

## 2. Starting numbers (`529efc1`)

| quantity | value | source |
|---|--:|---|
| Tier 1, 44 rows | 15.2% mean, 26/44 within 15%, 36/44 within 25% | `scripts/cold_holdout.py` |
| corporate class, 4 JCT rows | 40.3% mean (53, 44, 42, 22) | same |
| `biden_corporate_28`, derived | −$1,292.6B against −$1,349.9B (4.0% under) | `validate_corporate_policy` |
| `trump_corporate_15`, derived | +$1,545.2B | same |
| derived marginal share at +1pp | 0.8084 = 1.0083 base conversion × 0.8240 behavioural | `scripts/corporate_marginal_share.py` |

## 3. The sourced GILTI base

Transcribed to `fiscal_model/data_files/international/soi_gilti_section250_ty2021.csv`
and read by `fiscal_model.international.soi_gilti_base()`:

| item, TY2021 | $B | source |
|---|--:|---|
| GILTI inclusion (Form 8992) | 607 | IRS SOI Pub. 6075 (Rev. 3-2025), Highlights |
| net CFC tested income (725 − 111) | 614 | same |
| section 250 deduction, GILTI (Form 8993) | 311 | IRS SOI Pub. 6076 (Rev. 3-2025), Highlights |
| section 250 deduction, FDII | 111 | same |
| SOI Table 11 foreign deemed income | 744.2 | `soi_table11_corporate_tax_items.csv` |
| SOI Table 11 foreign deemed deductions | 446.3 | same |
| SOI Table 11 income subject to tax | 2,422.1 | same |

These are the publications' printed headline figures. The line-item workbooks
(`21it01gilti.xlsx`, `21it01sec250.xlsx`) could not be read from this
environment, so the GILTI-attributable §78 gross-up and the taxable-income
limitation are not transcribed. The cross-checks still hold. The two section 250
deductions sum to $422B, 94.6% of Table 11's foreign deemed deductions, and
GILTI's $607B sits inside Table 11's $744B of foreign deemed income
(`tests/test_b5_gilti_base.py`).

## 4. Why the lane stops

**(i) The GILTI piece is already in the base the model prices.** The derived
rate channel prices SOI Table 11 "income subject to tax", which is corporate
taxable income. Taxable income includes the GILTI inclusion and its gross-up and
subtracts the section 250 deduction. Net GILTI in that base is at least
$607B − $311B = **$296B, 12.2% of the TY2021 base** (a lower bound, because the
gross-up is non-negative). So a +7pp rate step already raises the tax on net
GILTI by 7pp, which is a 3.5pp rise on gross GILTI at a 50% deduction:
10.5% → 14%, exactly the step Treasury describes. At the average credit
realization, that is roughly **$158B (12.2% of $1,292.6B)** of the current derived
score. It is less if GILTI's marginal realization is below the average, which
the foreign tax credit makes likely.

**(ii) Treasury's "rate + GILTI" is what a rate rise does by itself.** The FY2025
Green Book's corporate-rate proposal (printed p. 3) says only: "The effective
global intangible low-taxed income (GILTI) rate would increase to 14 percent
under the proposal." 14% is 28% × (1 − 50%), the current-law deduction at the
new rate. The GILTI reform proper, which cuts the section 250 deduction to 25%
for a 21% effective rate, is a separate row: "Revise the global minimum tax
regime" (printed pp. 25, 29; $373.9B). So the corporate row's GILTI sentence
describes the linkage, and any rate rise under current law carries it, the
factory's included.

**(iii) Nothing in the derived path is fitted to `biden_corporate_28`.** The 0.8084
share is SOI base ÷ MTS receipts × CBO's receipts path × a literature
semi-elasticity. `BASELINE_TAXABLE_PROFITS_BILLIONS`, the constant fitted to
this row, is read only in `reported` mode, and neither the app
(`CORPORATE_APP_MODE`) nor validation (`CORPORATE_VALIDATION_MODE`) runs that
mode. So re-scoping the anchor cannot move a per-point yield, and it cannot move
the four JCT rows.

Adding a separate GILTI piece would therefore count net GILTI twice. It would
move `biden_corporate_28` from 4.0% under to roughly 8% over, and it would move
none of the 44 held-out rows. The plan's premise (§A item 4) holds for `reported`
mode, which no surface uses since PR #166. It does not hold for `derived`.

**Falsification condition 1 is met in its strongest form.** The incremental
GILTI piece is zero rather than under $100B, because it is already priced. The
share does not move.

## 5. What remains true and open

- The corporate class's 40.3% is still the model's 80.8% marginal share against
  JCT's 52.6–57.1%. GILTI is not the explanation. All four JCT +1pp rows also
  carry the linkage, because a percentage deduction makes it automatic, so the
  model and JCT match in scope there.
- `biden_corporate_28`'s `scope_differs` note and `known_limitations` say the
  factory "sets `gilti_rate_change=0.0`" as though that left GILTI out. In the
  derived mode it does not. Rewording them, and possibly moving the row from
  `line_item_differs` to `line_item`, changes a badge class, so it is left for
  Laurence to decide and is not in this PR.
- After 2025 the current-law deduction falls to 37.5% (13.125%), and a rate rise
  to 28% would carry GILTI to 17.5%, above the 14% Treasury states. Whether
  Treasury's row holds the 50% deduction, or simply quotes the 2024 arithmetic,
  cannot be settled from the text. Either way the gap goes the other direction
  from the one B5 assumed.
- `CorporateTaxPolicy._estimate_international_effects` still prices
  `gilti_rate_change × 250.0`, an unsourced constant. It is read only by the
  full Biden package preset (`gilti_rate_change=0.105`). The SOI figures here
  support replacing it, but that moves a preset and belongs in its own lane.

## 6. Outturn

No scored number moved. `cold_holdout.py` reads 44 rows at 15.2% mean, 26/44
within 15%, 36/44 within 25%, unchanged. Both corporate presets are unchanged:
`biden_corporate_28` (derived) −$1,292.6B and `trump_corporate_15` (rate cut
plus bonus depreciation) +$1,545.2B. The `estimator_ranges` marginal-share test
is unchanged because the share is unchanged (0.8084).
