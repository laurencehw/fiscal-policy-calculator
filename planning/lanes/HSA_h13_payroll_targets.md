# Lane H13 — Say what the two OCACT payroll targets are

*Pre-registered 2026-09-09 against `main` @ `8964cb1` (= `f3dc042` plus three
nightly bill-tracker commits), before any file in §2 was opened. Outturn
appended at the end of the lane, in the last commit.*

Scope: `planning/HIGH_STAKES_ACCURACY.md` §1.2 row 3 and §3 **H13**. **No model
change.** `ss_donut_250k` (−$2,700.0B) and `ss_eliminate_cap` (−$3,200.0B) are
two of the app's six largest headline figures; both print their target to the
cent because a constant was fitted to it, and both targets are `secondhand`.
The lane says out loud what the two numbers are, beside the held-out figures the
same machinery returns when the fitted constant is taken away.

This lane is **docs plus one caption**. It may not open `fiscal_model/payroll.py`,
`fiscal_model/validation/*` (Wave B's H9 owns provenance), or
`fiscal_model/app_data.py` (Wave A's H1 owns it).

---

## 1. Starting numbers

Measured on the branch point, `8964cb1`, from `python scripts/run_loo.py
--donor-matrix`, `python scripts/cold_holdout.py --json` and `python
scripts/run_validation_dashboard.py`. Nothing below is copied from the plan.

### 1.1 The two rows

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| Payroll | `ss_cap_90_pct` | −800.0 | −800.0 | −749.5 | **+6.3%** |
| Payroll | `ss_donut_250k` | −2,700.0 | −2,700.0 | **−2,664.0** | **+1.3%** |
| Payroll | `ss_eliminate_cap` | −3,200.0 | −3,200.0 | **−3,319.5** | **−3.7%** |
| Payroll | `expand_niit` | −250.0 | −250.0 | — | not cross-validatable |

Payroll module mean **3.8%** (n=3 derivable, 1 excluded). Suite aggregate: **18
derivable, 30.1% mean / 19.1% median, 8/18 within 15%**, 4 not cross-validatable.

The plan quoted −$2,664.0B (1.3%) and −$3,319.5B (3.7%); both re-measure to the
decimal, so the figures the caption pins are these.

### 1.2 Why the by-construction column is 0.0%

`payroll.py`'s `BASELINE_WAGE_DATA` carries its own arithmetic in the comment:

```
"wages_above_cap_billions": 2_581.0,   # 320 / 0.124
"wages_250k_plus_billions": 2_177.0,   # 270 / 0.124
```

and `create_ss_eliminate_cap` / `create_ss_donut_hole` stamp
`annual_revenue_change_billions = 320.0` and `270.0`, each documented as the
"window-average of Trustees $3.2T / $2.7T over 10yr". The target divided by ten,
divided by the statutory rate, is the base; the base times the rate, times ten,
is the score. **A 0.0% row here measures arithmetic, not agreement.**

`SSA_COVERED_WAGES_ABOVE_BILLIONS` reuses the same two numbers as the
$176,100 and $250,000 anchors of the interpolation table every other threshold
is read off, which is why `validation/cbo_options.py` excludes CBO Option 62
from the Tier 1 battery for **leakage** rather than for missing machinery.

### 1.3 What the leave-one-out figures are, and are not

`validation/loo.py`'s `derive_payroll_annual` holds out the case's own anchor
and refits the covered-wage level at its threshold from the **other two**
anchors' Pareto slope. So −$2,664.0B and −$3,319.5B are what the module returns
when it is not told the answer for that row — a real cross-validation of the
band table's *shape*, and still not an independent measurement of the reform,
because two of the three anchors are themselves fitted.

---

## 2. What the lane changes

Files, and nothing else:

1. `planning/lanes/HSA_h13_payroll_targets.md` — this doc.
2. `docs/VALIDATION.md` — one paragraph in the provenance section: what OCACT
   publishes for E2.1 and E2.5, where the two dollar figures actually come
   from, the held-out figures, and the rule that a `secondhand` target
   reproduced by a fitted constant is bookkeeping.
3. `docs/METHODOLOGY.md` — the **payroll section only**, where line 853 reads
   "vs Trustees $2,700B" and that attribution is wrong.
4. `fiscal_model/ui/tabs/results_summary.py` — **one additive caption block**
   (`payroll_fitted_target_caption`) plus one call site in
   `render_headline_block`, following `ptc_repeal_baseline_caption`'s pattern
   exactly. H1 adds its own separate block in the same file; both are additive
   and independent, so the merge is a two-hunk append.
5. `tests/test_payroll_target_caption.py` — the caption's tests, including the
   **drift test**.

### 2.1 The caption's held-out figures are pinned, not computed

`run_payroll_loo()` re-scores three benchmarks through the full runner. Running
that on a page render is the defect PR #129 measured and PR #135 closed — the
footer computing the entire 81-row scorecard to print one clause, 8.68s of a
9.38s first paint. So the caption reads **two module-level constants**, and
`tests/test_payroll_target_caption.py` calls `derive_payroll_annual` and
`run_payroll_loo` and fails if either constant drifts from what the suite
returns. A pinned constant with a drift test is the cheap half of PR #135's
answer, applied to a two-number artifact rather than a JSON file.

### 2.2 The caption fires on the two shipped designs only

Guarded on `(ss_eliminate_cap, ss_donut_hole_start,
annual_revenue_change_billions)` matching one of the two factory outputs, so a
Tailor-built payroll policy at a different threshold — which is **not** the
fitted design and does **not** print the target — gets no caption. The claim
"the shipped figure reproduces the carried target" must be true whenever the
caption is on screen.

---

## 3. The prediction

**Zero numbers move.** This lane changes no constant, no target, no shape and
no registry.

- `python scripts/cold_holdout.py --json` — **byte-identical**.
- `python scripts/run_loo.py --donor-matrix` — **byte-identical**.
- `python scripts/run_validation_dashboard.py` — **byte-identical**
  (it exits 1 on the branch point already; that must not change either).
- All 53 shipped presets score to the cent what they scored before.
- No Decision 6 caption is owed, because no headline number moves. The caption
  this lane adds is not a Decision 6 caption; it is a provenance statement about
  a number that has not changed and never should have been read as evidence.

**Registries the lane must not touch**: `fiscal_model/validation/target_revisions.py`,
`benchmark_sources.py`, `preregistered.py`, `cbo_scores.py`. Anything the
sourcing turns up is written down **for H9**, and registered by H9 or not at all.

---

## 4. Falsification

The lane is falsified if:

1. Any of the three measurement artifacts differs before and after (`cmp`).
2. The two pinned LOO constants do not equal what `run_payroll_loo()` returns.
3. The caption fires on a payroll policy that does not print its carried target.
4. Any file outside §2's list is modified.
5. The sourcing turns up a published ten-year dollar score and this lane
   registers it rather than handing it to H9.

---

## 5. What this lane will not do

- **Not revise either target.** Sixteen targets have moved through
  `target_revisions.py` and every one of them was a ledger commit followed by a
  scoring commit. A docs lane may not take a target decision by implication —
  the same rule PR #126 applied when it published IIJA's 18.2% → 0.3% number
  and left the `.v3` row to the owner.
- **Not retune anything to close the held-out gap.** 1.3% and 3.7% are the
  honest figures and they are good ones; the point of printing them is that
  0.0% is not.
- **Not convert OCACT's percent of payroll into dollars.** A conversion this
  repository performs is a target this repository constructed. The whole finding
  is that the conversion is unpublished.

---

## 6. Outturn

*(appended in the last commit)*
