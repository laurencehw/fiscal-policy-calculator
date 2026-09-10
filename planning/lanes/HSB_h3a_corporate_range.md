# HSB / H3a — Corporate: show the estimator range

*Lane of `planning/HIGH_STAKES_ACCURACY.md` Wave B, §3 H3, the **H3a** paragraph. Presentation
only. H3b — the mechanism, the §38(c)/§904(c) carryforwards and CAMT — is Wave E and is not this
lane's; `fiscal_model/corporate.py` is not opened here.*

*Pre-registered 2026-09-09 on `ui/hs-b-h3a-corporate-range` @ `fdb9f8b`, branched from
`origin/model/hs-a-h1-base-rule` (H1, PR #142, awaiting the owner's merge). This section was
committed **before** any code changed.*

---

## 0. The measurement this lane starts from

| Run | Command | Artifact |
|---|---|---|
| Tier 1 | `python scripts/cold_holdout.py --json` | `before_holdout.json` |
| Dashboard | `python scripts/run_validation_dashboard.py` | `before_dashboard.txt` |
| Preset sweep | 53 presets × static/dynamic through `composer._build_preset_policy` → `_scorer_for` → `score_policy`, per-year path included | `before_sweep.json` |

`run_validation_dashboard.py` exits **1 at the branch point already** — the health gate trips on
`runtime [degraded] Python 3.14.0` and the SOI microdata warning. Both are pre-existing and neither
is this lane's; the exit code is not a signal here, the printed blocks are.

The two figures the lane exists to caption, measured on that sweep:

| Preset | App \$B (static) | Δ rate |
|---|--:|--:|
| 🏢 Biden Corporate 28% (CBO: −\$1.35T) | **−1,397.2107** | +7.0pp |
| 🏢 Trump Corporate 15% | **+1,491.7588** | −6.0pp |

Both reproduce `HIGH_STAKES_ACCURACY.md` §1.2 rows 2 and 2b (−1,397.2 / +1,491.8) to the decimal,
which is the condition for proceeding.

---

## 1. What is displayed, and how the dollar range is derived

### 1.1 The defect, stated as the plan states it

> A user told "−\$1.4T" with no range is being told the model agrees with everyone, when it agrees
> with the highest.

`biden_corporate_28` reads **3.7%** against Treasury's FY2025 Green Book row and the app prints a
green "Excellent" badge beside it. Three facts the badge hides, all already in the repository:

1. Treasury's row is **not the same reform**. `benchmark_sources.py` carries a `scope_differs`
   verdict on it: from the FY2023 edition the Green Book chapter moves the GILTI effective rate with
   the statutory rate, while `create_biden_corporate_rate_only` sets `gilti_rate_change=0.0`.
2. Treasury is the **outlier of its own literature**. On the same window and the same baseline,
   JCT prices a point at 55.9% of the vintage's average corporate base, Tax Foundation at 55.1%,
   PWBM at 64.4%; Treasury at 79.5% and it is the only one of the four whose scope is not rate-only
   (`CORPORATE_PER_POINT_YIELD.md` §4b).
3. The model is **above all four** — 82.3% in `reported`, the app's default;
   80.8% in `derived` at +1pp since PR #121.

So the single number is not wrong so much as unaccompanied. This lane ships the accompaniment.

### 1.2 The conversion rule

For a run whose policy is a `CorporateTaxPolicy` with a non-zero `rate_change`, each of the four
published estimators on the memo's window contributes one converted figure:

```
converted_e = rate_change_pp × per_point_billions_e
```

`per_point_billions` is a **column of the CSV** — `ten_year_billions / rate_change_pp`, arithmetic
on the figure the source printed, never a figure the source printed itself. No new transcription is
made and no figure is re-derived: the four rows are selected by `window == "FY2025-2034"`, which on
`corporate_rate_scores.csv` selects exactly the four rows §4b tabulates and nothing else.

The identity that makes this the memo's own arithmetic rather than a second one:

```
marginal_share_e = |per_point_billions_e| × 10 / average_base_per_year
average_base_per_year = receipts_10yr / statutory_rate / 10 = 5094.0 / 0.21 / 10 = 2425.7143
```

— `receipts_10yr` being CBO's February 2024 baseline corporate receipts over FY2025–2034
(publication 59710 Table 1-1), the vintage `BaselineVintage.CBO_FEB_2024` names and the one the
memo normalises against. **The shares are computed, not transcribed**, and §4 pins them against the
memo's printed table.

The model's own position is computed **from the run at hand**, so it cannot drift from the headline
above it:

```
model_per_point = headline_billions / rate_change_pp
model_share     = |model_per_point| × 10 / average_base_per_year
```

and the sentence saying where the model sits **counts** how many published shares it exceeds rather
than asserting "above every published estimator", because that claim is mode- and step-dependent:
`reported` returns 82.3% at every step, `derived` 80.8% at +1pp and 76.1% at +7pp — above four,
four and three of the four respectively.

### 1.3 What the surface says

Three captions under the headline, rendered by `render_headline_block` — the one function the
Explore preset result, the Tailor corporate run and every other surface's
`render_score_surface` → `render_results` → `render_headline` all pass through.

**(a) The range.** The four converted figures, low to high, with each estimator named and its scope
marked, and one clause saying whether the model sits inside, above or below.

**(b) The conversion and its limits.** Where the figures come from, on what window and baseline, and
one sentence on why this is a range and not a consensus: **direction asymmetry** (Tax Foundation's
*Options 2.0* is the only document pricing both directions in one edition and one model, and a point
of cut costs 29% more than a point of increase yields, so an increase's per-point yield run backwards
does not give a cut's cost), **GILTI bundling** (Treasury's row is `rate_plus_gilti`), and **bonus
depreciation** (`create_republican_corporate_cut` sets `extend_bonus_depreciation=True`; none of the
four published figures includes it). Plus the model's own share, against the four.

**(c) The scorecard row's own published range or scope verdict**, when the run matches one — read
live from `target_revisions.live_target_for` and `benchmark_sources.source_for`, never re-typed:

* `trump_corporate_15` carries the published range **[+595.0, +673.1]** (PWBM's *2024 Trump Campaign
  Policy Proposals* Table 1 and Tax Foundation's Watson & York Table 2, anchored on the latter), and
  a `scope_differs` naming the bonus-depreciation leg.
* `biden_corporate_28` carries the **scope verdict** — the figures agree to 0.2% and the reforms do
  not.

### 1.4 What is deliberately not done

* **No number moves.** `fiscal_model/corporate.py` is not opened; `CORPORATE_APP_MODE` stays
  `reported` by the owner's explicit override (§6.2 item 33). This lane has no opinion on Decision 1
  it can act on, only evidence to hand back (§5).
* **No figure is transcribed.** Every published dollar comes from `corporate_rate_scores.csv` or
  from the validation registries. Where the record has no figure for something the caption would like
  to say, the caption does not say it.
* **The per-point extrapolation is not offered as a score of a cut.** For Trump 15% it is shown
  *beside* the two direct published scores of that cut precisely so the reader can see that the two
  do not agree — see §3.
* **Build, Ask and the Methodology page are out of scope** (§6): Build quotes `CBO_SCORE_MAP` list
  prices rather than model output, and Ask's corporate answers live in `assistant/tools.py`, a
  sibling lane's file.

---

## 2. Files

| File | Change |
|---|---|
| `fiscal_model/ui/estimator_ranges.py` | **new.** The pure helper: `EstimatorEstimate`, `EstimatorRange`, `PublishedRange`, `corporate_estimator_range()`, `published_range_for()`. No Streamlit import, no I/O beyond reading the CSV, deterministic, cached |
| `fiscal_model/ui/tabs/results_summary.py` | `corporate_estimator_range_captions()` + three calls in `render_headline_block`, additive to the existing caption chain |
| `components/results.py` | expected **untouched** — every surface already renders the headline through `results_summary.render_headline_block`; recorded either way in §4 |
| `tests/test_corporate_estimator_range.py` | **new.** Helper arithmetic, the §4b pin, and render-level assertions |
| `planning/lanes/HSB_h3a_corporate_range.md` | this doc |

Sibling lanes: H2 owns `policies_core.py` / `scoring_engine.py`, H9 owns `validation/*` +
`docs/VALIDATION.md` + `app_data.py` target text. This lane **reads** `validation/*` at runtime and
writes none of it.

**Reusability, because Wave C's H4 generalises this.** `EstimatorRange` is a frozen dataclass over
a tuple of `EstimatorEstimate`, with the subject, the window, the basis sentence and the caveat
sentence as data rather than f-strings buried in a caption. `published_range_for(policy_id)` is
already policy-agnostic — it answers for `pillar_two_adoption` [−102.6, +56.5] and
`reciprocal_tariffs` [−1,800, −1,400] today, with no corporate knowledge in it.

---

## 3. Expected outcome — pre-registered

**Every number moves by zero.** This lane touches no scoring path.

| Artifact | Prediction |
|---|---|
| `cold_holdout.py --json` | **byte-identical** |
| `run_validation_dashboard.py` | **byte-identical** |
| 53-preset × 2-mode sweep, per-year paths included | **byte-identical** |
| Scorecard rows, both calibrated tiers, LOO | untouched (not re-run; the dashboard prints all three) |
| Decision 6 caption | **not owed** — no shipped number moves |

**What the two shipped corporate presets will say**, computed in advance from
`corporate_rate_scores.csv` and the before-sweep:

| | Biden Corporate 28% | Trump Corporate 15% |
|---|--:|--:|
| headline (unchanged) | −1,397.2 | +1,491.8 |
| step | +7.0pp | −6.0pp |
| Tax Foundation (rate only) | −935.8 | +802.1 |
| JCT (rate only) | −949.9 | +814.2 |
| PWBM (rate only) | −1,093.0 | +936.9 |
| Treasury OTA (rate + GILTI) | −1,349.9 | +1,157.1 |
| **converted range** | **−1,349.9 … −935.8** | **+802.1 … +1,157.1** |
| model position | **above the widest, by 47.3** | **above the widest, by 334.7** |
| model share of the average base | **82.3%** | *suppressed — bundled* |
| scorecard's own published range | — (scope verdict instead) | **[+595.0, +673.1]**, model outside by 818.7 |

**The Trump row is the one to read twice, and it is pre-registered as an *unflattering* display.**
Converting the four increase-scored per-point yields to a 6-point cut gives **+802.1 … +1,157.1**;
the two houses that scored *this cut directly* print **+595.0 … +673.1**. The extrapolation is above
the direct scores at both ends, and the model is above the extrapolation. Showing both is the point:
if per-point dollars were comparable across direction and scope the two bands would overlap, and
they do not. The lane does **not** reconcile them and does not pick one.

**The model's share is suppressed for a bundled run**, and Trump 15% is the case that forces the
rule: computed naively its per-point is +248.6, or **102.5%** of the vintage's average base — a
figure that reads as a base defect and is mostly `extend_bonus_depreciation=True`, which none of the
four published rows prices. The registry's own `scope_differs` already measures that leg at
+\$294.15B, leaving a rate leg of +\$1,197.6B; the caption names the bundled provisions and declines
to print a share rather than printing a misleading one or re-deriving the split here.

---

## 4. Falsification

The lane is **falsified** if any of the following holds.

1. **Any scored number moves.** `cmp` on the three artifacts, before against after. A single
   differing byte in `before_holdout.json`, `before_dashboard.txt` (modulo nothing — it is
   deterministic) or `before_sweep.json` falsifies the lane's central claim.
2. **The computed shares do not reproduce the memo.** A test asserts the four
   `marginal_share` values land on `CORPORATE_PER_POINT_YIELD.md` §4b's printed 55.1% / 55.9% /
   64.4% / 79.5% to within 0.05pp, and that the model's `reported` +7pp share lands on the same
   table's 82.3%. If the helper's arithmetic and the memo's disagree, the helper is wrong.
3. **The range does not appear for a corporate result**, or **appears for a non-corporate one**.
   Render-level tests drive `render_headline_block` through a recording stub for: the Biden 28%
   preset (range appears, both bounds present), the Trump 15% preset (range appears **and** the
   published `[+595.0, +673.1]` appears), a `TaxPolicy` income-tax run (nothing appears), a
   `SpendingPolicy` run (nothing appears), and a `CorporateTaxPolicy` with `rate_change=0.0` — the
   `⚖️ Repeal Corporate AMT` shape — where nothing appears, because a policy with no statutory rate
   step has no per-point yield to be compared against.
4. **The helper is not pure.** A test imports `fiscal_model.ui.estimator_ranges` and asserts it
   pulls in neither `streamlit` nor `fiscal_model.validation` at module scope, and that two calls
   with the same arguments return equal objects.
5. **A figure is invented.** A test asserts every dollar figure the helper emits is traceable to a
   row of `corporate_rate_scores.csv` or to a `CalibratedTarget`, by reconstructing each from its
   source and comparing.

Gates that must stay green: `ANTHROPIC_API_KEY= python -m pytest tests/ -q`, `ruff check .`,
`python scripts/check_readiness.py --strict` (read past the Python 3.14 runtime line, which fails
first locally), `python scripts/check_streamlit_boot.py`.

No `scripts/smoke_ask_assistant.py` run is owed: the assistant quotes the engine, no engine number
moves, and `assistant/tools.py` is not opened.

---

## 5. The owner question this lane is asked to inform

> ⑤ Does a shipped corporate **range** change Decision 33's `reported` default?

The lane does **not** answer it and may not — `CORPORATE_APP_MODE` is the owner's explicit override.
What it adds is stated in §6 once the code is in.

---

## 6. Outturn

*Appended 2026-09-09 at `7dddff6`, after implementation. Nothing below was edited into §1-§4.*

### 6.1 Falsification: every prediction held

| Artifact | Prediction | Result |
|---|---|---|
| `cold_holdout.py --json` | byte-identical | **identical** (`cmp` clean, 119,989 bytes) |
| `run_validation_dashboard.py` | byte-identical | **identical** (`cmp` clean; exit 1 before and after, on the same two pre-existing health warnings) |
| 53-preset × 2-mode sweep, per-year paths | byte-identical | **identical** (`cmp` clean, 47,127 bytes) |
| Shares reproduce the memo's §4b | 55.1 / 55.9 / 64.4 / 79.5 | **all four within 0.05pp**, computed |
| Range appears for a corporate rate run, not otherwise | — | **held**, five cases |
| Decision 6 caption owed | no | **none owed** |

Suite: **3,783 passed, 7 skipped** with `ANTHROPIC_API_KEY` unset (25 of them new).
`ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py` — CI's own
invocation — clean; bare `ruff check .` reports 9 errors, all in `api.py`, and **the identical 9
are on `origin/main`**, which is why CI's step names paths rather than `.`.
`check_readiness.py --strict` exits **0** at `ready_with_warnings`, the same four warnings as the
branch point. `check_streamlit_boot.py` passes all 14 routes. No smoke test owed: no engine number
moved.

The diff is four files and touches nothing outside the lane's list — `components/results.py`
was **not** edited, as §2 expected, because every surface already renders its headline through
`results_summary.render_headline_block`.

### 6.2 What the two shipped presets now say

**🏢 Biden Corporate 28%**, headline unchanged at −\$1,397.2B:

> **Estimator range.** Four houses have scored a corporate statutory-rate change on FY2025–2034.
> Converted to this policy's +7.0pp step they span **\$-1,349.9B to \$-935.8B** — Treasury OTA
> \$-1,349.9B (rate + GILTI), Penn Wharton Budget Model \$-1,093.0B, JCT \$-949.9B, Tax Foundation
> \$-935.8B. This run's \$-1,397.2B prices it **larger than any of the four**, by \$47.3B.
>
> **How that range is built.** […] On the metric that removes the baseline level — the share of the
> vintage's average corporate base one statutory point reaches — this run sits at **82.3%**, above
> every published estimator on the record (79.5% Treasury OTA, 64.4% PWBM, 55.9% JCT, 55.1% Tax
> Foundation).
>
> **Scope: the benchmark and this run price different reforms.** […] the printed \$1,349,941M prices
> a statutory-rate increase AND a GILTI effective-rate step, while `create_biden_corporate_rate_only`
> sets `gilti_rate_change=0.0` […]

**🏢 Trump Corporate 15%**, headline unchanged at +\$1,491.8B: the same two lines over
**\$+802.1B to \$+1,157.1B**, "larger than any of the four, by \$334.7B", the model share
suppressed and the bundled provision named; then

> **This benchmark carries a published range.** Its scorekeepers — Tax Foundation (anchor); Penn
> Wharton Budget Model — scored this exact reform and printed \$+595.0B to \$+673.1B; this run's
> \$+1,491.8B is \$818.7B outside it. That band and the converted one above do **not** overlap […]

plus the registry's bonus-depreciation scope verdict. A Tailor custom corporate run gets the first
two lines and neither of the last two, which is correct: no benchmark scores it.

### 6.3 Findings

**1. The record's own `per_point_billions` column is rounded, and it shows.** The helper first read
that column; converting Treasury's row back to its own +7.0pp step then returned **−1,349.943**
against a printed **−1,349.941**. Immaterial in dollars and material in trust — a display that
cannot reproduce its own source's figure invites the question of what else was rounded. The helper
computes `ten_year_billions / rate_change_pp` instead, which is what the column *is* (and what
`corporate_yield_reconciliation.py` already recomputes as `per_point_check`), keeps the column as
`published_per_point_billions`, and a test asserts the two agree to 0.001. Caught by the round-trip
test, not by inspection.

**2. `fiscal_model/ui/__init__.py` imports the whole validation package, eagerly.** Importing
*anything* under `fiscal_model.ui` — `styles` as readily as `dependencies` — puts all **22**
`fiscal_model.validation.*` submodules in `sys.modules`, via the package `__init__`'s
`from .app_controller import …` re-export chain. So this module's lazy import is a property of the
file and not of its package, and the purity test had to move from `sys.modules` to the module's own
AST. `test_ui_package_init_is_the_eager_one` records the fact separately so the AST test cannot be
quietly satisfied by the package doing the import instead. **Carry-over**, adjacent to
`planning/memos/COLD_START.md`: it is a cold-start question with a different owner, and this lane
may not edit that file.

**3. The two corporate bands do not overlap, and the asymmetry runs the *opposite* way to the one
the ledger cites.** `trump_corporate_15`'s ledger note quotes Tax Foundation's *Options 2.0*, the
only document pricing both directions in one edition and one model: 21%→28% at \$126.6B per point,
21%→15% at \$163.2B per point, so **a point of cut costs 29% more than a point of increase yields**.
On this window's record the direct cut scores run the other way — \$595.0B and \$673.1B over 6
points is **\$99.2B–\$112.2B per point**, against **\$133.7B–\$192.8B per point** for the four
increase rows. Both cannot be a property of the same reform in the same direction, so at least one
of scope (bonus depreciation), vintage (2021 against 2024) or package-stacking (PWBM's row sits
inside a whole-campaign table) is doing the work. **The lane does not resolve it and the caption
does not either** — it prints both bands, says they do not overlap, and says neither is adjusted
onto the other. That is the display doing its job: a single number here would have had to pick.

**4. "Above every published estimator" cannot be hard-coded, and the measurement is the finding.**
Run through the engine in both modes, all four figures reproducing the memo to the dollar:

| mode | step | total \$B | share of average base | position in the converted range |
|---|--:|--:|--:|---|
| `reported` | +1pp | −199.60 | 82.3% | outside by 6.75 |
| `reported` | +7pp | −1,397.21 | 82.3% | outside by 47.27 |
| `derived` | +1pp | −196.08 | 80.8% | outside by 3.23 |
| `derived` | +7pp | −1,292.62 | **76.1%** | **inside** |

`reported` is above all four estimators at every step; `derived` is above all four at +1pp and above
**three** at +7pp, where it falls below Treasury's 79.5%. A caption asserting the sentence would be
wrong on the last row, so it counts instead.

**5. A bundled run's naive per-point share is 102.5% of the average base, and that is not a base
defect.** Trump 15% divided by its 6-point step gives \$248.6B per point, or 102.5% of the vintage's
average corporate base — a figure no marginal base can be, and the same shape as the internal
inconsistency lane W6 removed. Here it is almost entirely `extend_bonus_depreciation=True`: the
registry's own `scope_differs` measures that leg at **+\$294.15B** of the +\$1,491.8B, leaving a
rate leg of +\$1,197.6B, or **82.3%** — exactly `reported`'s figure, as it must be. The caption
suppresses the share for any bundled run and names the provisions rather than printing a number
that reads as a defect it is not.

**6. Unpredicted, small: the model's `reported` share is exactly step-invariant and this makes the
display self-checking.** `reported` prices every step against the same fitted profits aggregate, so
its share is 82.3% at +1pp, +3pp and +7pp alike; `derived` is mildly concave (80.8% → 76.1%). A
reader who runs Tailor at three steps sees one mode assert the same marginal base at every dose and
the other bend. Nothing is asserted about which is right — but the display now shows it, where the
scorecard's single row per benchmark never could.

### 6.4 The owner question ⑤, with what this lane adds

> Does a shipped corporate **range** change Decision 33's `reported` default?

**Still the owner's, and still not answered here.** What the lane adds is a *second, independent*
metric pointing the same way as the first:

* PR #122 measured Decision 1's own comparison on three published targets and found it **reversed** —
  `reported` **62.75%** against `derived` **61.43%**, derived narrowly ahead.
* This lane measures the same two modes against the published *record* rather than against a target,
  and finds the same ordering more sharply: at the +7pp step every shipped preset uses, **`derived`
  lands inside the published span and `reported` lands outside it** (finding 4). On the marginal-share
  metric `derived` is 76.1% against a published 55.1–79.5% and `reported` is 82.3%, above all of it.

So a shipped range makes the `reported` default *more* visibly the outlier, not less — the caption
will read "larger than any of the four" on every corporate run the app serves, for as long as the
default stands. That is an argument for the flip and it is not a decision: `CORPORATE_APP_MODE` is
the owner's explicit override (§6.2 item 33), the two metrics are 1.3pp and one-step-apart
respectively, and H3b (Wave E) moves `derived` again. The lane's recommendation is only that the
question be taken **with these two readings side by side**, and that whichever way it goes, the
caption above is what a user sees meanwhile.

### 6.5 Carry-overs

1. **Build quotes list prices, not model output.** `deficit_target.build_catalog` is driven by
   `CBO_SCORE_MAP`'s `official_score` (`ui/tabs/deficit_target.py:218-232`), so a Build package
   inherits the *target's* provenance. A range belongs there too — `trump_corporate_15`'s
   [+595.0, +673.1] most obviously — but the surface shows a target rather than a score, so the
   sentence it needs is a different one and the file is not this lane's.
2. **Ask's corporate answers are out of scope.** `assistant/tools.py`'s
   `score_hypothetical_policy` and `benchmarks.candidate_anchors` produce corporate numbers with no
   range beside them; `candidate_anchors` in particular interpolates across `KNOWN_SCORES`
   corporate-rate records, which is where a per-point yield most obviously belongs. Sibling lane's
   file.
3. **`fiscal_model/ui/__init__.py`'s eager validation import** (finding 2).
4. **Wave C's H4** should build its estimator-disagreement bands on `published_range_for`, which is
   already policy-agnostic and tested against `pillar_two_adoption` and `reciprocal_tariffs`; the
   per-point conversion is corporate-only and deliberately so.
