# Lane REVIEW-6: re-admit estate repeal to the leave-one-out suite (pre-registration)

Pre-registered 2026-11-25, before `fiscal_model/validation/loo.py` is edited on
this branch and before the derived figure for this case has been run. The
predictions below are not edited after the first code commit; the outturn is
appended under the line at the end.

Owner decision (2026-11-25, project thread): "please make these fixes", on the
open list of `planning/memos/GEMINI_REVIEW_2026-11-23_FOLLOWUPS.md`. This is
proposal 6.

## 1. What is wrong

`ESTATE_UNPUBLISHED_TARGET_CASES = ("eliminate_estate_tax",)` keeps estate repeal
out of the leave-one-out aggregate because "the $350B target is sourced 'Model
estimate', not a published score". That stopped being true at the H9 target
revision (`target_revisions.eliminate_estate_tax.v2`): the row's target is Tax
Foundation, *Options for Reforming America's Tax Code 3.0* (July 2026), Option
83, +$407.2B over CY2027-2036. The exclusion's stated reason no longer holds, so
the suite reports 18 cross-validated cases where it should report 19, and the
note printed beside the case still says $350B.

## 2. What this lane does

- Empties `ESTATE_UNPUBLISHED_TARGET_CASES`, so `derive_estate_annual` derives
  repeal from the SOI-fitted size distribution like the other two estate cases.
- Removes the exclusion branch's stale note.
- Regenerates `current_evidence.json` and fixes whatever sentences
  `tests/test_current_evidence.py` pins to the leave-one-out figures.

No constant is introduced or moved, and no module's scoring path changes. The
only number that can move is the leave-one-out suite summary.

## 3. Predictions

Today's suite: 18 cases, mean 36.3%, median 30.8%, 6 within 15%, 4 not
cross-validatable.

1. The suite goes to **19 cases** and **3 not cross-validatable**.
2. The derived ten-year figure for repeal is a **cost** (positive deficit
   effect), between **$350B and $600B**. The loo.py note records the machinery's
   2026 baseline at about $47.6B a year, which over a decade with growth is
   above the $407.2B target; the target is on the post-P.L. 119-21 exemption
   ($15M) and a later window, which the scenario states rather than adjusts.
3. So the case's error is **under 50%**, and more likely an over-statement than
   an under-statement.
4. The suite mean therefore **moves by less than 2 points** in either direction
   and stays far under the CI ceiling of 75 (`run_loo.py --donor-matrix
   --max-mean-error 75`). The ceiling is not touched.
5. The other 18 cases are byte-identical.

## 4. What would falsify it

- The derived figure has the wrong sign or is outside $350-600B.
- Any other leave-one-out case moves.
- The out-of-sample tier or either calibrated tier moves at all (they should
  not: nothing they read is edited).

---

## Outturn

Run 2026-11-25 with `python scripts/run_loo.py --donor-matrix --json`, before and
after the edit, on the same tree.

| Prediction | Outturn |
|---|---|
| 19 cases, 3 not cross-validatable | 19 and 3 |
| Derived repeal is a cost of $350-600B | +$471.3B (window average $47.1B a year) |
| Error under 50%, more likely over | 15.7%, an over-statement against +$407.2B |
| Suite mean moves by less than 2 points | 36.3% -> 35.3% (median 30.8% -> 28.4%; 6 of 19 within 15%, the new row at 15.7% just outside) |
| Other 18 cases byte-identical | identical, compared case by case |

None of the falsification conditions fired. The CI ceiling (75) is untouched.

