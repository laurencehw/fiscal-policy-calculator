# Memo — the FY2022 Green Book row is scored on the wrong decade

*Written 2026-09-06 against `main` @ `a251b32`. A decision memo with the minimal
implementation of its recommendation. **No model code changed.** The additions
are this file, `scripts/window_offset_capgains.py` (which prints every number
below), one `CBOScore` field, one manifest row and the ten lines of
`fiscal_model/validation/core.py` that read the field. **The merge is the
owner's decision: this moves a Tier 1 shape input.***

Scope: `planning/MODELING_IMPROVEMENT.md` §6.2 item 24, opened by
`planning/lanes/W5_preferential_margin.md` §8.3 finding 5. Under §1's principles
and §4's prohibitions. No target is edited, no CI threshold is moved, and the
row's `known_limitations` are untouched — the decedent-ladder lane owns that text.

## 1. The question

`treasury_capgains_39_plus_stepup_elim` carries the FY2022 Green Book's combined
row — 39.6% on gains above $1M **plus** realization at death with a $1M
per-donor exclusion — at **−$322,485M over FY2022–2031** (Treasury, *General
Explanations of the FY2022 Revenue Proposals*, Table of Revenue Estimates,
report p. 105 / PDF p. 111). Every Tier 1 case is scored over **FY2025–2034**
(`DEFAULT_VALIDATION_START_YEAR`), and both of this shape's channels grow with
one constant — `household_net_worth_growth_rate = 0.0580148`, the Financial
Accounts 1998:Q4→2024:Q4 CAGR in `accrued_gains_parameters.csv`, which the rate
channel reads through `realizations_projection_factor` and the death channel
through `gains_at_death_billions`. A window three years later therefore scores
higher mechanically. The row reads **43.3%**. How much of that is the window?

## 2. The offset, measured

`python scripts/window_offset_capgains.py`. The measurement is a **re-score, not
a discount**: the policy is scored again on a scorer whose window opens in the
target's own first year. That is available without a 2021 baseline because
`CapitalGainsPolicy` reads no baseline at all — `estimate_static_revenue_effect`
opens with `_ = baseline_revenue`, and the death channel is priced off Financial
Accounts net worth.

| | total | rate | death | vs −$322.0B |
|---|--:|--:|--:|--:|
| as scored, FY2025–2034 | **−$461.5B** | 359.02 | 102.45 | **43.3%** |
| on its own window, FY2022–2031 | **−$369.0B** | 303.14 | 65.81 | **14.6%** |
| analytic `(1+g)^-3`, both channels | −$389.6B | 303.14 | 86.51 | 21.0% |
| analytic `(1+g)^-3`, rate channel only | −$405.6B | 303.14 | 102.45 | 26.0% |

**28.7 of the row's 43.3 points are the window**, not the ~17 §8.3 finding 5
estimated and `docs/VALIDATION.md`, `CLAUDE.md` and the row's own
`known_limitations` now quote. The 17 came from discounting **only** the rate
channel: `359.02 × 0.844354 + 102.45 = 405.6`, which the script reproduces to
the dollar. Two things were missed.

**First, the death channel grows too.** `gains_at_death_billions` is a share of
household net worth in the year scored, so it carries the same 5.80%.

**Second, it does not grow proportionally, and that is the more interesting
half.** A uniform discount gives $86.5B; the re-score gives **$65.8B**, −35.8%
against proportionality's −15.6%. The $1M per-donor exclusion is a *fixed
nominal* subtraction per decedent, applied to a five-class ladder with no
within-group dispersion (§6.2 item 15), so it is a step function whose bite
moves far faster than the stock it is subtracted from. The window offset and the
ladder finding are the same defect seen twice.

**The control.** `biden_capital_gains_39` is the same shape, module and frozen
elasticity set, sourced to the FY2025 Green Book over FY2025–2034 — the window
the runner already scores. Its offset is **exactly zero**: −$379.2B and 31.4% on
either construction, to the cent. The measurement above is a property of this
row's window, not a claim about the mechanism in general.

## 3. What Treasury's own annual table says

Transcribed from the same row (report p. 105 / PDF p. 111), $M, with the
model's FY2022–2031 path beside it (positive = raises revenue):

| FY | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | total 22–31 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Treasury | 1,241 | 7,656 | 25,451 | 32,906 | 36,303 | 33,947 | 32,252 | 34,276 | 36,064 | 37,937 | 45,693 | **322,485** |
| model | — | −59,750 | 31,360 | 34,450 | 37,750 | 41,260 | 45,960 | 51,030 | 56,430 | 62,170 | 68,290 | **369,000** |

Two facts fall out, and both belong in the decision.

**Treasury's first three years are a ramp, and the model's first year is a
hole.** Over FY2022–2024 Treasury books **−$66.0B** and the model **−$6.1B**;
over FY2025–2031 Treasury books −$256.5B and the model −$362.9B. The model's
enactment year is a **+$59.8B revenue loss** — the transitory elasticity (1.20)
unlocking realizations — where Treasury's is a $7.7B gain on a proposal
effective from April 2021. So **14.6% is itself a net of two errors**, −$60.0B
under across three years against +$106.4B over across seven. That is a finding,
not an objection: the window artifact is removed and a *shape* disagreement is
what is left. It is the honest residual, where 43.3% is a shape disagreement
plus an accounting error and Wave 4's 0.2% was two errors cancelling.

**Treasury's own answer to this proposal is not stable.** The same row across
four consecutive volumes: **$322,485M** (FY2022–31, $1M exclusion), **$174,488M**
(FY2023–32), **$213,855M** (FY2024–33), **$288,583M** (FY2025–34) — non-monotone
and spanning 85%.

## 4. The options

Row error and Tier 1 are measured, not projected. Tier 1 today: n=26, mean
**15.2%**, median 11.4%, 16 within 15%, 22 within 25%.

| | row | Tier 1 (mean / w15 / w25) | manifest | rule it follows |
|---|--:|---|---|---|
| **(a) leave it** | 43.3% | 15.2% / 16 / 22 | none | none — status quo, and the note it rests on is off by 12 points |
| **(b) retire it** | — (n=25) | 14.1% / 16 / 22 | `.v1` `retired=True` + search | `top_rate_45`'s rule, misapplied |
| **(c) supersede, `.v2` on FY2022–2031** | **14.6%** | **14.1% / 17 / 23** | `.v1` `superseded_by` → `.v2`, target unchanged | IIJA `.v2` — a **shape input** moves, the target does not |
| **(c′) supersede, seven-year overlap** | 10.5% | 13.9% / 17 / 23 | `.v2` + a new target (−$256.5B) | `biden_high_income_tax.v2` — a re-transcription |
| **(d) add a 2021 vintage** | 43.3% | 15.2% / 16 / 22 | none | — |
| **(e) re-source to FY2023/FY2024** | n/a | n/a | `.v2` with a new target and a new shape | `biden_capital_gains_39.v2` — a re-sourcing |

**(b) is the wrong rule.** `top_rate_45` was withdrawn because its −$420B is in
no publication — an *unsourceable* target, with the search recorded. This one is
sourced to the page and transcribed to the annual. Retiring it would drop a 43%
row and improve the tier by 1.1 points, which is exactly the "quietly dropped
because it scored badly" failure the manifest exists to make visible.

**(d) buys nothing, and the reason is worth writing down.** Neither FY2022 Tier 1
row reads a baseline *level*: the capital-gains shape ignores `baseline_revenue`
outright, and a discretionary `SpendingPolicy` scores its own source-stated
authority. What both need is a **window**, not a **vintage** — so the manifest's
own prose ("the repository has no 2021 vintage to score the bill on its own
window", on both `iija_2021_discretionary.v1/.v2` and `biden_corporate_28_fy2022`)
states a blocker that is not the binding one. A vintage costs a `BaselineVintage`
member, an assumptions block, base levels, `VINTAGE_SOURCING` and
`VINTAGE_SOURCE_DOCUMENT`, the app's vintage picker, the `baseline=` share-link
contract and the classroom frozen-link refusal path — and would move neither row.

**(e) is dead on the documents.** The FY2023 and FY2024 volumes both carry the
row (\$174,488M over FY2023–2032; \$213,855M over FY2024–2033) and both state a
**\$5 million per-donor exclusion** (FY2023 PDF p. 38; FY2024 PDF p. 87), where
the FY2022 volume states \$1 million. No later Green Book carries the \$1M
design. Re-sourcing would swap the policy, not the window, and would leave two
live rows scoring one prediction against different targets — the incoherence
Phase E resolved when it retired `top_rate_45` and re-sourced
`biden_capital_gains_39`.

**(c′) lands nearer and is worse.** Comparing the model's own FY2025–2031 against
Treasury's printed FY2025–2031 subtotal (−$229.4B vs −$256.5B) gives 10.5% — by
netting a **$106.7B** one-year disagreement (the model's enactment-year hole
against Treasury's fourth-year plateau) against **$79.7B** of over-prediction
across the other six. It fixes the calendar alignment by breaking the
policy-time alignment: Treasury's FY2025 is year four of its proposal and the
model's would be year one of the same one. A lower number bought by a larger
cancellation is what this row's history already has too much of.

### Pre-registration each option needs

Every option is a **new row**; none is an edit. (c) is the only one whose target
column is unchanged, which is why it is the only one that needs no ledger
judgement about a number.

```
(b)  .v1 retired=True, retired_reason=<the search>            # no .v2
(c)  .v1 superseded_by=".v2"; .v2 official_10yr_billions=-322.0 (unchanged),
     entered_commit=FY2022_WINDOW_ENTERED_COMMIT,
     first_scoring_run_commit=FY2022_WINDOW_FIRST_SCORED_COMMIT,
     + FY2022_TARGET_WINDOW_RULE, + CBOScore.scoring_window_first_year=2022
(c') as (c), plus official_10yr_billions=-256.472 and a window_years=7
(e)  .v1 superseded_by=".v2"; .v2 official=-174.5 or -213.9, source_date
     2022-03 or 2023-03, and step_up_exemption=5_000_000 on the record
```

Under (c) the CI gate `--max-mean-error 20 --min-within-25pct 21` **still
passes** (14.1 ≤ 20; 23 ≥ 21), and `test_cold_holdout_gate_thresholds_match_the_live_battery`'s
"no more than ~2× the live mean" check holds at 20 ≤ 28.2. Re-derived by the
workflow's own rule the ceiling is `ceil(14.1 × 1.25) = 18 →` nearest 5 `= 20`,
**unchanged**, and the floor is `23 − 1 = 22`, a tightening from 21. **Stated,
not applied** — the coordinator re-derives after all lanes land.

## 5. Recommendation: (c), and it is implemented

Score the row on the ten fiscal years its own document covers. The target does
not move; the shape input does. This is IIJA `.v2`'s rule exactly — *"**The
target does not change.** This row replaces v1's shape input… Keeping v1 would
have meant scoring a shape the source contradicts because the model used to be
unable to express the one it states."* The window is not a knob: it has been
sitting in the record's own `budget_window="FY2022-2031"` and `baseline_year=2021`
since the row was entered on 2025-12-31, four waves before anything made it
matter, and one rule sets it for every case that ever carries it.

What shipped, in the manifest's two-commit order:

1. **Entry.** `FY2022_TARGET_WINDOW_RULE`, the `.v1` supersede, the `.v2` row,
   and `scoring_window_first_year=2022` on the `KNOWN_SCORES` record — frozen in
   the history *before* the runner can read it. Nothing scores differently.
2. **First scoring.** `create_policy_from_score` and `validate_all` read the
   field: the policy starts in that year and the scorer's window opens there.
   The row moves 43.3% → 14.6%.
3. **Stamping.** Both commit constants replaced with the real shas (a file
   cannot contain its own hash; commits 1 and 2 carried `0`×40 placeholders).

Two design details, both pinned by tests. The field moves the **scorer's window
and the policy's start together**: moving only the window truncates the head
instead of shifting it — `warren_ultramillionaire_surtax_3pp` reads −$283.5B →
−$170.1B, exactly 6/10 of itself, if the policy stays at 2025. And
`effective_start_year` still wins where a record sets one, because that is the
year the *source* says the policy takes effect, which is a different fact.

### Pre-registered outturn

| | before | after |
|---|--:|--:|
| `treasury_capgains_39_plus_stepup_elim` | −$461.5B, 43.3% | **−$369.0B, 14.6%** |
| Tier 1 mean / median | 15.2% / 11.4% | **14.1%** / 11.4% |
| Tier 1 within 15% / 25% | 16 / 22 | **17** / **23** |
| Tier 1 error mass | 395.0 | 366.3 |
| capital-gains mass (4 rows) | 104.5 (26.4%) | 75.8 (20.7%) |
| every other Tier 1 row | — | **unchanged to the dollar** |
| fitted tier, reconstruction tier, `run_loo.py --donor-matrix` | — | **byte-identical** |

Falsified if any second Tier 1 row moves, if either calibrated tier moves, if the
donor matrix moves, or if the row lands outside 14–15%.

## 6. What this does not do

- **It does not touch `known_limitations`.** The row's note still says "about 17
  of the row's 43 points" and quotes $405.6B; §2 supersedes both. The
  decedent-ladder lane owns that text and should carry the correction, and
  `docs/VALIDATION.md` §3, `docs/CHANGELOG.md` and `CLAUDE.md` repeat the same
  figure in a doc-sync PR.
- **It does not move IIJA, which the same mechanism closes.**
  `iija_2021_discretionary` reads 18.2% because $92.6B of its authority path
  outlays in FY2022–2024, outside the window; on FY2022–2031 it scores
  **+$414.3B against +$415.4B, 0.3%**. That is a second Tier 1 target decision
  with its own `.v3` row and its own ledger entry, and this lane may not take it
  by implication. The number is published here so the choice is not silently
  selective.
- **It does not claim a 2021 information set.** The model prices FY2022–2024
  from an SOI TY2023 base and a 2024:Q4 DFA anchor discounted backwards: a
  2026 backcast against a 2021 forecast. What the change fixes is that the ten
  fiscal years priced are the ten the target covers.
- **It does not fix the enactment-year hole.** §3 sizes it at $67B in FY2022
  alone, and it is the same missing receipts lag `W5_preferential_margin.md`
  §8.7 recorded. A shape residual, and the next thing to look at on this row
  after the decedent ladder.
- **It moves no shipped number.** Nothing under `fiscal_model/validation/` is
  reachable from a preset, and no app surface scores on a validation window.
