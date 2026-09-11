# R8 — Tariffs: JCT's offset path and the HS-10 Section 232 base, from CBO's own tariff model

**Lane** R8 of `planning/ROUTE_TO_8_5.md` §1 (Wave F). **Closes** `MODELING_IMPROVEMENT.md`
§6.2 item 64, and the H8 carry-overs that item names. **Branch** `model/r8-tariff-ctam`.
**Owns** `fiscal_model/trade.py`, its data under `fiscal_model/data_files/trade/`,
`fiscal_model/validation/scenarios.py`'s tariff `known_limitations`, `tests/`, and — under
Decision 6 — `tariff_net_caption` in `fiscal_model/ui/tabs/results_summary.py`, extended in
place the way H8 extended it.

**Source repository, pinned.** `https://github.com/US-CBO/conventional-tariff-analysis-model`
(CTAM), commit **`59ea68fd6a6f006ca240bc45100b634b3787c2a2`**, authored 2026-02-17, cloned
read-only 2026-09-11. Public domain. CTAM replicates *CBO's Updated Projections of the
Budgetary Effects of Tariffs as of November 15, 2025* (`cbo.gov/publication/61877`); the model
itself is documented at `cbo.gov/publication/61388`. Every file:line below is at that commit.

Written **before** any file in `fiscal_model/` was opened for editing. Every figure in §3 comes
from `scratchpad/r8/predict.py`, a deliberate **reimplementation** of `trade.py`'s chain that
does not import `fiscal_model` — it reproduces all five BEFORE scores to the cent
(−105.17 / −203.90 / −1369.83 / −331.12 / −1641.98), which is what licenses its AFTER figures
as predictions rather than readings.

---

## 1. Mechanisms

### 1(a) — The income-and-payroll offset is a year path, not a scalar

`trade.py:153` carries `income_payroll_offset_rate = 0.25`, and
`data_files/trade/tariff_scoring_inputs.csv` sources it as "the longstanding CBO/JCT/Treasury
OTA convention", **cited secondhand** through Tax Foundation FF861 p. 3 n. 3 because jct.gov and
cbo.gov both 403 this environment. The primary — JCT's own percentages — is shipped in CTAM:

> `inputs/offset/2025OffsetPostHR1.csv`, eleven rows:
> 2025 **0.244**, 2026 0.247, 2027 0.247, 2028 0.247, 2029 0.245, 2030 0.243, 2031 0.243,
> 2032 0.242, 2033 0.242, 2034 0.242, 2035 **0.241**.

CBO applies it multiplicatively, once per year, at `code/model/add_offset.py:18`
(`df[str(year)] *= (1 - offset_value)`). So the round 0.25 is replaced by JCT's own published
path — **not** by FF861's 26.2%, which `tariff_scoring_inputs.csv` already records as an
`external_check` deliberately not adopted because it is Tax Foundation's own model output for
this window and adopting it would move a parameter toward a benchmark. JCT's path is neither.

**How a year path enters a year-blind call.** `scoring_engine.py:341` calls
`policy.estimate_behavioral_offset(revenue[idx])` with no year, and `TariffPolicy` is not in
`_growth_tax_policy_handlers` (`scoring_engine.py:72-80`) and has no `soi_base_tax_year`, so
`_income_base_projection_factor` returns 1.0 and **the tariff gross is flat across the window**.
For a flat gross the window mean is not an approximation, it is an identity:
`Σ_t g·(1−o_t) = 10·g·(1−ō)`. The module therefore carries the whole path and reads the mean
over **its own** `[start_year, start_year + duration_years)`, which is exactly right today and
would be an approximation only for a phased tariff — stated in the docstring, and a carry-over,
because closing it needs `scoring_engine.py`, which this lane does not own.

Over the validation window FY2025–2034 that mean is **0.2442**; over the app's FY2026–2035
window, **0.2439**. Net-to-gross therefore moves `0.95 × 0.75 = 0.7125` → `0.95 × 0.7558 =
0.71801`, i.e. **+0.773%** on every trade row.

### 1(b) — The Section 232 base at HS-10, replacing two chapter proxies

`trade.py:127-135` already declares the problem: HS-73 whole-chapter is an **upper bound**
"because the Section 232 annexes list articles at HS-10, and Proclamation 10896 taxes a
derivative on its steel *content* rather than its customs value. Neither the annex nor a
content share is transcribed here." CTAM ships both:

| CTAM file | what it is | HS-10 lines |
|---|---|---|
| `inputs/hts_lists/alum_steel.csv` | the primary Section 232 aluminium-and-steel article list | 1,180 |
| `inputs/hts_lists/alst_deriv_h.csv` | derivative articles **deemed high metal content** | 168 |
| `inputs/hts_lists/alst_deriv_l.csv` | derivative articles **deemed low metal content** | 709 |
| `inputs/hts_lists/autos.csv` / `auto_parts.csv` | the Section 232 vehicle and parts lists | 62 / 316 |
| `inputs/base_imports/all_countries_2024_CY_2025-11-12.csv` | Census imports at HS-10 by country, CY2024, pulled 2025-11-12 (`config/default.yaml` `data.pull_date`) | 589,502 rows |
| `inputs/usmca/usmca_utilization_rates.csv` | USMCA utilization by HTS, Canada and Mexico | 12,937 |

The content shares are `config/default.yaml:72-73` — `alum_steel_deriv_high_share: 0.75`,
`alum_steel_deriv_low_share: 0.25` — applied at `code/tariffs.py:256-274` as a **rate blend**,
`new = old·(1−share) + s232·share`. For incremental revenue that is identical to taxing `share`
of the value at the Section 232 rate and leaving the rest at its existing duty, which is
exactly the `(base, incremental rate)` shape `rate_schedule` already takes. CTAM excludes the
auto-parts list from every metal mask (`tariffs.py:246-248`); this lane does the same, and
assigns a code appearing in both derivative lists to the high list only.

**The CTAM file is the same Census series the repository already transcribed, one vintage
later**, which is what makes it usable as a drop-in: aggregated over `CTY_CODE = '-'` it returns
HS-73 at **$49.394B / 5.614%** against the CSV's transcribed "$2.7732B on $49.265B" = 5.63%, and
all chapters at **$76.16B / 2.3425%** against `current_tariff_revenue_billions = 76.6` and
`current_avg_tariff_rate = 0.0236`.

Measured (`scratchpad/r8/ctam_bases2.py`, CON_VAL_YR):

| | base $B | existing duty |
|---|---|---|
| S232 primary, ex auto parts (1,167 lines) | **96.7516** | 4.6416% |
| S232 derivative, content-weighted `0.75·108.755 + 0.25·164.141` | **122.6015** | 3.872% |
| **S232 steel total** | **219.353** | |
| *app today: HS-72+76 "floor"* | *58.217* | *3.11%* |
| *app today: + HS-73 "ceiling"* | *107.611* | |
| S232 autos, less the USMCA US-content carve-out | **214.281** | 1.374% |
| S232 auto parts | **340.670** | 2.183% |
| **S232 auto total** | **554.951** | 1.836% |
| *app today: HS-87 × (1 − 48.42%)* | *198.531* | *1.98%* |

**The declared bracket is wrong at both ends, and this is the lane's headline finding.**
`alum_steel.csv`'s chapter mix is HS-72 508 lines, **HS-73 558**, HS-76 107, HS-87 7 — so most
of HS-73 is *primary* Section 232 scope, not derivative, and the "floor" of HS-72+76 excludes
it. Meanwhile the derivative annex lives in chapters **82, 83, 84, 85, 86, 87, 94, 95** (high)
and **34, 38, 82, 84, 85, 87, 94, 95** (low) — machinery, furniture, appliances — which HS-73
does not contain at all. The measured base is **2.04× the declared ceiling** and 3.77× the
floor, and the ceiling was never a ceiling.

The auto carve-out is CTAM's too: `tariffs.py:186-187` taxes USMCA-qualifying Canadian and
Mexican **vehicles** on their non-US-content share only, `us_content_ca_autos: 0.50` /
`us_content_mx_autos: 0.35` (`default.yaml:77-78`), with the qualifying share taken per-HTS
from `usmca_utilization_rates.csv` (`create_usmca.py:18-19`). That is **$41.02B** of carve-out,
against the roughly $186B the module's whole-value 48.42% removes — and
`tariff_scoring_inputs.csv` already says of its own figure that "the March 2025 proclamation
exempts only the US-content share of USMCA-qualifying vehicles, not the whole import value, so
this over-states the carve-out". This lane stops over-stating it.

**One inconsistency closes on the way.** Today `steel_aluminum_imports_billions = 58.9` is
Census **GEN_VAL_YR** while `steel_aluminum_existing_avg_tariff = 0.0306` divides duty by
**CON_VAL_YR** ($58.2B) — a base and a rate on different denominators. CTAM's file carries
CON_VAL_YR only, so every new figure is CON_VAL_YR and base and rate now share a denominator.

**Declared scope-vintage mismatch.** CTAM's article lists are the Section 232 scope as of
15 November 2025; the preset models the 25% Proclamation 10896 rate, in force 12 March – 3 June
2025. This lane changes the **base**, never the preset's rate, and §3 says what the row can and
cannot tell as a result.

### 1(c) — What CTAM does **not** supply, checked and recorded rather than taken

1. **`import_price_elasticity = −0.997` is not replaced, and the memo's description of the
   replacement is wrong.** `inputs/elasticities/boehm_elasticities.csv`'s `final_path` reads
   0.5517 → 2.0408, but `code/model/CES_time_path.py:14` **normalises it to 1.0 at t+10** and
   then *multiplies* 110 NAICS-4 foreign-to-foreign substitution elasticities by it
   (`:48-50`), with nesting divisors 1.0 / 1.5 / 2.0 (`:53-55`). It is a **time shape on a CES
   nest**, not an import-demand elasticity, and it cannot be dropped into `-0.997`'s slot.
   Route-doc move 3 is therefore **refused with a reason**, not deferred for time.
2. **`tariff_avoidance_rate = 0.05` stays unsourced.** CTAM has no avoidance or noncompliance
   parameter at all. Its `exporter_absorption: 5` (`default.yaml:84`) is a different object —
   incomplete border pass-through — and contradicts `border_pass_through_rate = 1.00`, which is
   sourced to Amiti–Redding–Weinstein and Fajgelbaum et al. Swapping a sourced constant for a
   conflicting one is not an upgrade; both are recorded in the CSV as declared disagreements.
3. **The calendar-to-fiscal conversion the module has no concept of.** `add_offset.py:24`
   books `FY_y = CY_{y−1}·0.2976 + CY_y·0.7024`. The app books a tariff's full calendar duty in
   its first fiscal year. Carry-over — it needs the same year-indexed hand-off as 1(a).

---

## 2. Files

| File | Change |
|---|---|
| `fiscal_model/trade.py` | JCT offset path + window mean; Section 232 steel and auto bases from the article lists; docstring and `TRADE_BASELINE` rewritten |
| `fiscal_model/data_files/trade/tariff_scoring_inputs.csv` | new rows for every figure above, each with the CTAM path, the pinned commit SHA and the Census vintage |
| `fiscal_model/data_files/trade/section232_hts_bases.csv` | the article-level transcription itself: one row per CTAM list, with line counts, CON_VAL, calculated duty and the content share applied |
| `fiscal_model/validation/scenarios.py` | `known_limitations` on `steel_tariff_25` and `auto_tariff_25` only |
| `fiscal_model/ui/tabs/results_summary.py` | `tariff_net_caption` extended in place (Decision 6) |
| `tests/test_trade_net_scoring.py`, `tests/test_trade_section232_base.py` | pinning the CSV against `TRADE_BASELINE`, the offset path, and the article-level arithmetic |

Out of my ownership and **not touched**: `policies_core.py` (R4), `corporate.py` (R5),
`scoring_engine.py`, and every planning/docs file except this one.

---

## 3. Pre-registered outturns

On the validation window FY2025–2034. `(a)` and `(b)` are each stated **alone**, so a
mis-prediction can be attributed.

| row | target $B | before | **(a) alone** | **(b) alone** | **predicted after** |
|---|---|---|---|---|---|
| `steel_tariff_25` | −60.0 *(untraceable)* | 75.28% | 76.64% | 255.35% | **258.10%** |
| `auto_tariff_25` | −386.2 | 47.20% | 46.80% | −48.09% | **−49.23%** |
| `trump_universal_10` | −2,171.1 | 36.91% | 36.42% | — | **36.42%** |
| `trump_china_60` | −650.0 | 49.06% | 48.66% | — | **48.66%** |
| `reciprocal_tariffs` | −1,500.0 *(range)* | −9.47% | −10.31% | — | **−10.31%** |

Scores: steel −105.17 → **−214.86**; auto −203.90 → **−576.33**; universal −1,369.83 →
**−1,380.43**; china −331.12 → **−333.68**; reciprocal −1,641.98 → **−1,654.68**.

**Trade sub-population mean 43.58% → 80.54%**, median 47.20% → 49.23%, within-15 1/5 → 1/5.
**This is a pre-registered regression** and three quarters of it is one row.

**On the four rows that have a document: 35.66% → 36.16%.** That is the number to quote, and
the route doc says why: `steel_tariff_25`'s target is **untraceable and examined-and-left
twice** (§6.2 item 65; `target_revisions.EXAMINED_NOT_REVISED`). The 25% Section 232 rate was in
force for ten weeks and **no scorekeeper published a ten-year estimate of it**. So:

- **What the row can tell**: whether the base is the one the statute reaches. It now is,
  measured at HS-10 off CBO's own annex transcription, where before it was two chapter proxies
  that between them missed most of the derivative annex and mis-classified most of HS-73.
- **What the row cannot tell**: whether the score is right. Its target is a repository
  artefact, not a published figure. A movement from 75% to 258% against it is a movement
  against nothing, and **must not be quoted as this lane's accuracy outturn**.

**The one external control that does exist, declared in advance and predicted to fail.**
Tax Foundation's tariff tracker scores the **50%** steel/aluminium regime (copper folded in) at
**−$341.4B** conventional over 2026–2035. Run at 50% the module returns **−$190.95B** on the new
base against **−$94.32B** on the old: the new base halves the gap, from 72% below to 44% below,
and **is still well short**. Copper does not explain it — CTAM's copper list is $15.32B of
imports. The residual is the ad-hoc high-rate device: at a 46pp increment
`high_tariff_elasticity_multiplier` leaves a volume factor of **0.379**, i.e. the module asserts
imports fall 62% in year one. That is the unsourced trio at `trade.py:172-174`, and this control
is registered here precisely so that the carry-over in §5 is evidenced rather than asserted.

**Presets that move** (Decision 6; app boundary, FY2026 open):
🏭 25% Steel/Aluminum Tariff **−$94.65B → ≈ −$193.4B**; 🏭 25% Auto Tariff **−$183.51B →
≈ −$518.7B**; 🏭 Trump Universal 10% −$1,232.85B → ≈ −$1,242.4B; 🏭 Trump 60% China −$298.01B →
≈ −$300.3B; 🏭 Reciprocal Tariffs −$1,477.79B → ≈ −$1,489.2B. The other 48 presets must score
to the cent what they score today. A caption ships with the five, computed from the scored
result, never hard-coded.

Both re-based rows are predicted to land near a **different** published estimator than the one
they are scored against — auto at −$576B against Yale Budget Lab's $600–650B for the tariff as
announced (already recorded in `auto_tariff_25`'s own limitations), steel as above. Neither is
adopted as a target: constructing a target from whichever document the model lands near is the
selection the revision ledger exists to prevent.

---

## 4. Falsification

1. **Tier 1 byte-identical.** No tariff row is in the out-of-sample tier and no Tier 1 shape
   reads `TRADE_BASELINE`. `cold_holdout.py --json` must be byte-identical to `before/`.
   If any Tier 1 figure moves, this lane has touched something it does not own.
2. **`run_loo.py --donor-matrix` byte-identical.** No trade constant is fitted to any target
   and `Trade` is not a LOO module.
3. **48 of 53 presets byte-identical**, and the 12 non-trade reconstruction sub-populations,
   the fitted tier and the held-in-place tier all unchanged.
4. **No constant is chosen to land a row.** Every figure in §1(b) is an aggregation of CBO's
   shipped Census file over CBO's shipped article lists at CBO's shipped content shares; the
   offset is JCT's published path. **If any row lands closer to its target than §3 predicts,
   that is a failure to be reported, not a result** — the predictions are arithmetic, not
   hopes. Specifically: `steel_tariff_25` landing anywhere near −$60B would mean the base was
   fitted, and the lane would be reverted.
5. **The identity test.** With the offset path forced flat at 0.25 and the old bases restored,
   every row must return its BEFORE figure to the cent.

---

## 5. Out of scope / carry-overs

1. **The elasticity as a path** — refused on the merits, §1(c)1. What CTAM supplies is a
   normalised CES time shape over 110 NAICS-4 elasticities, not a scalar import-demand
   elasticity. Taking it means building the CES nest.
2. **`high_tariff_threshold` / `_multiplier` / `min_volume_factor` (`trade.py:172-174`) — no
   CSV row, no citation, and now a measured symptom.** The CSV cites Boehm et al. for the
   doubler, but Boehm is a **horizon** result and the module applies it on the **rate level**;
   the 50% control above sizes the consequence at a 62% year-one import collapse. Closing this
   needs year-indexed scoring (`scoring_engine.py`) and interacts with the 0.20 floor, which
   binds hard once the elasticity rises. **Own lane.**
3. **The CY→FY conversion** (§1(c)3) — same year-indexed hand-off.
4. **`tariff_avoidance_rate = 0.05`** — still unsourced; CTAM has nothing to offer.
5. **CBO's own Nov-2025 tariff score ($2,380.58B, FY2026–2035, `outputs/replication/
   fy_revenue_summary.csv`) as a Tier 1 row** — rejected on principle in the tax memo's §4 and
   repeated here: it is a stack of overlapping Section 232 actions, reciprocal rates, USMCA
   carve-outs, country caps and article-level exemptions `TariffPolicy` cannot construct, so the
   row's error would measure inexpressibility. The tractable fragment CBO also publishes — the
   implied import decline, **16.49%** over the period and 25.57% for China
   (`cy_implied_import_decline_pct.csv`) — is a check on carry-over 2, not on this lane.
6. **`steel_tariff_25`'s target** — stays untraceable and stays `EXAMINED_NOT_REVISED`. This
   lane found no published ten-year estimate of the ten-week 25% regime either, and a lane may
   not take a target decision by implication.

---

## 6. Outturn (2026-09-11)

**Every one of the five scores landed on its §3 prediction to the cent.** Not to within a band —
to the cent: steel −214.86, auto −576.33, universal −1,380.43, china −333.68, reciprocal
−1,654.68, against §3's −214.86 / −576.33 / −1,380.43 / −333.68 / −1,654.68. That is what the
reimplementation in `scratchpad/r8/predict.py` was for, and it is the only claim in this section
that needed a check rather than a measurement.

### 6.1 Rows

| row | target $B | before | (a) alone | (b) alone | **after** | predicted |
|---|---|---|---|---|---|---|
| `steel_tariff_25` | −60.0 *(untraceable)* | 75.28% | 76.64% | 255.35% | **258.10%** | 258.10% ✓ |
| `auto_tariff_25` | −386.2 | 47.20% | 46.80% | −48.09% | **−49.23%** | −49.23% ✓ |
| `trump_universal_10` | −2,171.1 | 36.91% | — | — | **36.42%** | 36.42% ✓ |
| `trump_china_60` | −650.0 | 49.06% | — | — | **48.66%** | 48.66% ✓ |
| `reciprocal_tariffs` | −1,500.0 *(range)* | −9.47% | — | — | **−10.31%** | −10.31% ✓ |

`reciprocal_tariffs` stays **inside** its published range [−$1,800B, −$1,400B] at −$1,654.7B,
`within_published_range` True, distance $0.0B — so its 10.31% remains a distance from one
modeller's point rather than a measurement of accuracy, exactly as before.

**Trade 43.58% → 80.54%**, a pre-registered regression, and **three quarters of it is one row**.
Median 47.20% → **48.66%** (§3 predicted 49.23%; the prediction mis-ordered the sorted list —
the middle row is `trump_china_60`, not `auto_tariff_25`. The only figure in this lane that
missed, and it is a sorting slip in a summary statistic, not a model figure). Within-15 1/5 → 1/5.

**On the four rows that have a document: 35.66% → 36.16%**, as predicted. That is the number to
quote. `steel_tariff_25`'s target is untraceable and examined-and-left twice, so a movement from
75% to 258% against it measures nothing about the score, and the row's own `known_limitations`
now open with that sentence in capitals rather than leaving a reader to infer it.

Tier-wide: reconstructions **37.5% → 42.4%** (n=38, median 30.1% unchanged, within-15 11/38
unchanged), retired-held-in 55.5% → 60.1%.

### 6.2 Falsification — all five passed

1. **Tier 1 byte-identical.** `cold_holdout.py --json`'s `out_of_sample` block compares equal,
   key for key: 22 rows, mean 11.6%, median 8.9%, 18 within 15%, 19 within 25%.
2. **The fitted tier is byte-identical too**, which §4 did not even ask for:
   `calibrated_reference` compares equal, and `retired_targets` with it. Only
   `uncalibrated_reconstruction` moved.
3. **`run_loo.py --donor-matrix` byte-identical** — not one line. No trade constant is fitted to
   any target and `Trade` is not a leave-one-out module.
4. **48 of 53 presets byte-identical**, the five that moved are the five tariff presets, and the
   twelve non-trade reconstruction sub-populations are unchanged in the dashboard diff.
5. **No constant was chosen to land a row.** `tests/test_trade_section232_base.py::
   TestNothingWasChosenToLandARow` asserts it rather than claiming it: the steel score must stay
   **above $200B**, i.e. nowhere near the −$60B it is measured against, and the test's message
   says that a score drifting toward that target is a reason to revert the lane.

### 6.3 Presets moved (Decision 6)

| preset | before | after |
|---|---|---|
| 🏭 25% Steel/Aluminum Tariff | −$94.65B | **−$193.45B** |
| 🏭 25% Auto Tariff | −$183.51B | **−$518.90B** |
| 🏭 Trump Universal 10% Tariff | −$1,232.85B | **−$1,242.88B** |
| 🏭 Trump 60% China Tariff | −$298.01B | **−$300.43B** |
| 🏭 Reciprocal Tariffs | −$1,477.79B | **−$1,489.81B** |

The caption is extended in place and computed from the scored result. It now prints the offset
to one decimal (**24.4%**, the policy's own window, not a module constant) and says it is JCT's
published year path rather than the round 25%; and for the two Section 232 presets it adds one
sentence naming the base — *"the Section 232 article list itself — CBO's own HS-10 annex, $219B
of imports — rather than the whole HS chapter it used to stand in for"* — because for those two
the base moved far more than the offset did and the base is what a user needs told.

### 6.4 Findings

1. **The declared upper bound was 2.5× too small, and the bracket was wrong at both ends.**
   H8 shipped whole-chapter HS-73 as a ceiling on the Section 232 derivative base *because* it
   knew the annexes list articles at HS-10. Read at HS-10 the annex is **$122.60B** of
   content-weighted base, not $49.5B — and the primary list is **$96.75B**, above the $58.9B
   "floor", because **558 of `alum_steel.csv`'s 1,180 lines are in HS-73**. The chapter proxy
   and the article list are not nested at all: the derivative annex lives in chapters 82–95,
   machinery and furniture and appliances, which HS-73 does not contain, while most of HS-73 is
   primary scope. **A bracket built from the wrong dimension is not conservative in either
   direction.**
2. **The ordering of the collected duties flips, and that is the tell.** HS-73 collects 5.63%
   against HS-72+76's 3.06%; CBO's derivative annex collects **3.87%** against its primary
   list's **4.64%**. If these were the same articles the ordering could not reverse. Pinned by a
   test.
3. **CTAM's Boehm `final_path` is not an import-demand elasticity, so route-doc move 3 is refused
   on the merits rather than deferred.** `code/model/CES_time_path.py:14` normalises the column
   to 1.0 at t+10 and `:48-50` *multiplies* 110 NAICS-4 foreign-to-foreign substitution
   elasticities by it, with nesting divisors 1.0 / 1.5 / 2.0 at `:53-55`. The published 0.5517 →
   2.0408 is a **time shape on a CES nest**. Dropping it into `import_price_elasticity`'s slot
   would be a category error. The tax memo's §3 row 11 describes it as a "time-varying
   import-demand elasticity"; that description should be corrected.
4. **The one external steel control halves its gap and does not close it, and it diagnoses the
   elasticity rather than the base.** Tax Foundation's tracker scores the 50% regime (copper
   folded in) at −$341.4B; the module returns **−$190.95B** on the new base against **−$94.32B**
   on the chapter proxies. Copper is $15.3B of imports and cannot be the residual. What is left
   is `high_tariff_threshold` / `_multiplier` / `min_volume_factor` — no CSV row, no citation —
   which at a 46pp increment leaves a volume factor of **0.379**: the module asserts imports fall
   **62% in year one**. Registered in §3 in advance, and now a regression test.
5. **The unsourced trio cites Boehm on the wrong axis.** `tariff_scoring_inputs.csv` sources
   `high_tariff_elasticity_multiplier` to Boehm et al. — but Boehm is a **horizon** result
   ("elasticities roughly double over the medium run") and the module applies it on the **rate
   level**. The app encodes a time phenomenon as a rate phenomenon. That is finding 3 and finding
   4 meeting: CTAM has the right object for it and it is not a scalar.
6. **A base and its rate stood on different denominators.** `steel_aluminum_imports_billions` was
   Census GEN_VAL_YR ($58.9B) while `steel_aluminum_existing_avg_tariff` divided duty by
   CON_VAL_YR ($58.2B). Every new figure is CON_VAL_YR, so they share one — and CON_VAL is the
   value duty is actually assessed on.
7. **CBO's file is the repository's own Census series, one vintage on, and that is checkable.**
   Aggregated the same way it returns HS-73 at **5.614%** against the 0.0563 this repository
   transcribed independently in February 2025, and all chapters at **$76.16B / 2.3425%** against
   its `76.6` and `0.0236`. Three cross-checks ship as `external_check` rows with a test.
8. **The auto carve-out was 4.5× too large, and the repository had already said so.**
   `tariff_scoring_inputs.csv`'s source note for `auto_usmca_exempt_share` read "the March 2025
   proclamation exempts only the US-content share of USMCA-qualifying vehicles, not the whole
   import value, so this over-states the carve-out". CBO's own rule removes **$41.0B** where the
   whole-value 48.42% removed about **$186B**. A defect can sit in a file, correctly described,
   for a wave and more.
9. **A year path can be read through a year-blind engine call, exactly, and the reason is worth
   keeping.** `scoring_engine.py:341` passes no year; `TariffPolicy` is in no growth handler and
   has no `soi_base_tax_year`, so the gross is flat and `Σ_t g(1−o_t) = n·g·(1−ō)` is an
   identity. No engine change, no approximation — and a test asserts the identity rather than
   the docstring claiming it. It would become an approximation for a *phased* tariff, which is
   why that is a carry-over rather than a silence.
10. **CTAM carries no avoidance parameter at all.** `tariff_avoidance_rate = 0.05` stays
    unsourced and stays a "Retained module default". Its `exporter_absorption: 5` is incomplete
    border pass-through, a different object, and it *contradicts* the app's sourced 1.00; both
    are now recorded as declared disagreements rather than quietly swapped.

### 6.5 Gates

Full suite **4150 passed, 7 skipped, 0 failed** (`ANTHROPIC_API_KEY=` unset, to a file). `ruff
check` at the CI scope, ruff 0.15.8: **All checks passed**. `check_readiness.py --strict`: exit 2
on this branch and on `main`, **and the output text is byte-identical** — which is the check that
matters, per PR #119 §7.5, because Python 3.14 fails the runtime component first and masks
everything after it. `build_validation_headline.py --check`: **OK, 73 published of 77**,
unchanged. Both CI gate commands as the workflow runs them: `cold_holdout.py --max-mean-error 15
--min-within-25pct 19` **exit 0**, `--max-class-mean-error …` **exit 0**, and both read a Tier 1
block byte-identical to `main`'s. `tests/test_offset_sign_contract.py` green (86 passed, 6
skipped). `scripts/smoke_ask_assistant.py`: **3/3 PASS**, $0.0436.

### 6.6 Carry-overs

1. **The elasticity trio** (`high_tariff_threshold`, `high_tariff_elasticity_multiplier`,
   `min_volume_factor`) — unsourced, on the wrong axis, and now **sized**: a 62% year-one import
   collapse at 46pp, and the whole of the residual in the one external steel control. Needs
   year-indexed scoring (`scoring_engine.py`, not this lane's file) and a decision about the 0.20
   floor, which binds hard once the elasticity rises. **Own lane, and it is the tariff module's
   largest remaining unsourced object.**
2. **The CY→FY conversion** — `add_offset.py:24` books `FY_y = CY_{y−1}·0.2976 + CY_y·0.7024`;
   the app books a tariff's full calendar duty in its first fiscal year. Same hand-off as 1.
3. **`tariff_avoidance_rate = 0.05`** — CTAM has nothing to offer; needs a different document.
4. **The auto-parts rebate** (`auto_parts_rebate: -5`) and the **USMCA compliance cost**
   (`ca_usmca_cost` / `mx_usmca_cost: 3`, explicitly non-revenue-generating) are shipped CTAM
   parameters this lane did not take, because they belong to the specific November-2025 schedule
   rather than to a generic 25% auto tariff. Recorded so nobody re-derives them from scratch.
5. **`steel_tariff_25`'s target stays untraceable and stays `EXAMINED_NOT_REVISED`.** This lane
   searched again and found no published ten-year estimate of the ten-week 25% regime either. A
   lane may not take a target decision by implication.
6. **The tax memo's §3 row 11 needs correcting** on what `boehm_elasticities.csv` is (finding 3).
   Docs are the docs-sync lane's, not this one's.
