# Priority 5 and the proposal charts: review of the November feedback, and the plan

*Written 2026-11-04 against `main` @ `e03cec5`. This is a sequencing plan under
[`ROUTE_TO_9.md`](ROUTE_TO_9.md), which stays the active plan. It is addressed to
whoever implements it (Cursor or Claude). It promises nothing about attainment:
the figures marked **(illustrative)** are arithmetic on today's rows, written so a
lane can pre-register against them, not targets.*

The rules that bind every lane still apply, and are restated because Part B leans
on them:

- Pre-register every modelling lane in `planning/lanes/` **before** the module is
  opened; append the outturn after. First commit = pre-registration, last commit =
  outturn.
- Never retune a constant to a held-out target. A regression is reported as one.
- Never collapse the tiers (out-of-sample / fitted / fitted-held-in-place /
  reconstruction / LOO) into one number.
- Lanes do not edit shared docs, yardstick scripts or CI gates. A docs-sync PR
  follows each wave, and it runs `scripts/build_current_evidence.py` and fixes
  pinned sentences.
- Before every push: `ANTHROPIC_API_KEY= python -m pytest tests/ -q`, `ruff check .`,
  the blocking mypy gate (`mypy $(grep -v '^#' mypy.gate.txt | grep -v '^[[:space:]]*$')`),
  and for `web/` changes `npm run typecheck && npm test && npm run layout` in `web/`.

---

## Part A: what the feedback gets right, wrong, or out of date

Every claim was checked against the tree and against a fresh
`scripts/cold_holdout.py --json` run on `e03cec5`. The figures below are from that
run and from `site_data/`.

| # | Claim | Verdict | What the tree shows |
|---|---|---|---|
| 1 | Fitted tier 15 rows at 1.6% (median 0%); 12.4% over 26 with corrected targets held in place | **Right** | `evidence.json` → `calibrated.fitted` 1.6 / 0.0 / n=15; `fitted_held_in_place` 12.4 / n=26 |
| 2 | Out-of-sample: 15.2% mean, 12.3% median, 26/44 within 15%, 36/44 within 25% | **Right** | Same figures from `cold_holdout.py --json` |
| 3 | Class means: ordinary 15.3 (n=11), corporate 40.3 (n=4, 0 within 15), payroll 18.6 (n=8), capital gains 14.4 (n=7), spending 4.6 and 7.4 | **Right** | Error mass: ordinary 168.8, corporate 161.3, payroll 149.0, capital gains 101.1 out of 668.6 |
| 4 | "Those three tax classes are about three-quarters of the error" | **Roughly right** | Ordinary + corporate + payroll = 71.7%. Add capital gains and it is 86.8% |
| 5 | Halving the corporate miss alone takes 15.2% to about 13% | **Right** | (668.6 − 80.7) / 44 = 13.4% |
| 6 | The 9/10 bar: ~10% pooled, no class above 20%, at least five cases per class | **Right, and it has a consequence the feedback does not draw** | `ROUTE_TO_9.md` priority 5. Four classes are **below five cases today**: corporate 4, AGI surtax 4, enacted-law spending 3, tax expenditure 2. No modelling change meets the bar until the battery grows. See B1 |
| 7 | Ordinary income is grown from a 2023 IRS total by a nominal-GDP index | **Right** | `ScoringEngine._income_base_projection_factor` → `BaselineProjection.nominal_income_index`. The docstring records why GDP was chosen: it was the only series transcribed for all three vintages |
| 8 | CBO publishes AGI and taxable income year by year; `rev_iit_agi` ≈ $18.8T (2026) to $25.8T (2035) | **Right** | `US-CBO/cbo-data` @ `284a956` (the commit this repo already pins), `data/budget/revenue_detail/annual_cy_iit_2026-02.csv`: 18,810.4 and 25,817.9. It also carries taxable income, ordinary and preferential taxable income, and **taxable income by statutory bracket** (`rev_iit_bracket_1..7`) |
| 9 | Using that file "is not fitting to a score" and should be pre-registered expecting a few rows to get worse | **Right in principle, wrong about which way the rows move**. See B2 | All 11 ordinary rows **over-predict** (model larger than published, every one). Which way they move depends on the series and the vintage, and the effect differs between the battery and the live site |
| 10 | Corporate: a point is priced on ~81% of the base; TF 55%, JCT 56%, PWBM 64%, Treasury 80%; the loss-firm haircut was tried and refused | **Right** | `W6_corporate_base_projection.md` outturn: 80.8%. `CORPORATE_PER_POINT_YIELD.md` §4b. `R5_h3b_corporate.md` §7: haircut sourced and refused |
| 11 | Next corporate step: split the 81% into named pieces (domestic/foreign, credits, GILTI) | **Partly out of date** | R5 §7.2 already did the credits and CAMT part. It found the §38(c) and §904(c) carryforward stocks but **not the share that would price them** (SOI discontinued the excess-credit tables after TY2010), and found no published CAMT base. The piece that *is* still open and actionable is GILTI, see B5 |
| 12 | The homepage pair (−$1,311B vs Treasury −$1,347B) is the fitted, bundled row; the four unfitted corporate rows average 40% | **Right** | `web/lib/home.ts` `WORKED_PRESET_IDS`; `biden_corporate_28` is fitted; Treasury's FY2025 row is rate + GILTI while `create_biden_corporate_rate_only` sets `gilti_rate_change=0`. All four held-out corporate rows are JCT and all over-predict (53.5, 44.5, 41.6, 21.8) |
| 13 | Social Security donut on the homepage: −$2,700B vs CBO −$1,427B; flat $270B/yr; not one of the 44 | **Right** | `fiscal_model/payroll.py` `create_ss_donut_hole`: `annual_revenue_change_billions=270.0`. The flat path is a **deliberate record of a superseded target**, left in place so the 89.2% gap stays visible. Fixing it is a mechanism change, not a refit, and must be written up as such. See B3 |
| 14 | CBO's donut option rises from ~$122B to ~$192B as the taxable maximum climbs toward $250K | **Not checked here** (cbo.gov is blocked from this environment) | The shape is plausible: the donut closes as the cap rises. The plan does not use CBO's annual path as a target either way |
| 15 | Gains-at-death level and the death rate disagree by about 7× | **Right** | `fiscal_model/data/capital_gains.py`: the flow is Poterba & Weisbenner's 1998 estates over net worth; the exit rate is the NCHS-weighted 2.65%. The module's own docstring measured the old headcount version at 8.3× |
| 16 | `cbo_opt51_gains_at_death` under-predicts; the Treasury row is two errors cancelling | **Right** | Model −345.9 vs −536.1 (35.5% under). `biden_capital_gains_39` over-predicts by 27.0%, `treasury_capgains_39_plus_stepup_elim` reads 1.8% |
| 17 | Feedback is 25 cents per dollar of GDP; debt service is a flat 4% | **Right, and incomplete** | `FRBUSAdapterLite`: `marginal_tax_rate=0.25`, `interest_cost = cumulative_deficit * 0.04`. It also hard-codes `baseline_gdp = 28_000.0` (a $28T GDP for every year of every vintage), which sets the GDP percentages and the rate channel. TCJA reads +$4,582B conventional and +$5,239B dynamic |
| 18 | CBO publishes "nine marginal tax rates by income type" and a debt-service matrix | **Half right** | `cbo-data`'s `tax_parameters` carries CBO's **effective** marginal rates: labour (income tax, payroll, combined) and capital by asset and financing type. Those are the wrong object for revenue feedback (see B6). A debt-service matrix is not in `cbo-data`. Net interest and debt held by the public are already transcribed per vintage, which is enough for a vintage-specific effective rate |
| 19 | Build adds list prices; top rate + SALT repeal is ~14% less jointly; a $1M surtax + repeal can flip sign | **Right** | `web/lib/package.ts` `total()`. `ROUTE_TO_9.md` 2026-10-03 status: 13.7% and 20.2% with a sign flip. `fiscal_model/package_interactions.py` already has `joint_tax_change` |
| 20 | Cell weights match IRS 2023 (100% returns, 100.9% AGI); TCJA who-pays is an approximate bracket method; eight 2025-law line items reconstruct at ~36% | **Right** | `evidence.json` data_vintages; `web/components/WhoPays.tsx`; the eight `pl119_21_*` rows average 35.8% |
| 21 | econvitals.org/fiscal description | **Not checked** (not reachable from here) | It does not affect the plan |
| 22 | Homepage "how to read a figure" teaches a fitted TCJA row, a fitted corporate row, and an 89% miss | **Right** | `web/lib/home.ts`: `tcja-full-extension`, `corporate-28pct`, `ss-donut-250k` |
| 23 | Ten-year baseline deficit is $23.1T | **Right** | `cbo_budget_baseline.csv`, `cbo_feb_2026`, FY2026-2035 `deficit_total` sums to −23,143.3 |
| 24 | The corporate multi-house range is measured and not on the page | **Right for the new site; out of date for the code** | `fiscal_model/ui/estimator_ranges.py` already builds it (and `published_range_for` covers three more presets) for the frozen Streamlit app. The Next.js site never got it. This is a port, not new work |

### Where I disagree with the ordering

1. **The battery comes before the models, not after.** The bar needs five cases in
   every class and four classes have fewer. `ROUTE_TO_9.md` already says benchmark
   design should start before the modelling it evaluates. New rows also change the
   denominators the modelling lanes pre-register against. So lock them first (B1).
2. **Step 1 is right, but the expected sign is wrong.** It is not "a few rows get
   worse". Every ordinary row over-predicts today, so the direction is set by the
   ratio of CBO's base growth to nominal-GDP growth on each row's vintage, and
   that ratio differs between the battery's vintage and the live site's
   (illustrative, from `cbo-data`, window average over the 2023 level):

   | Edition | Window | Nominal GDP (in use) | AGI | Taxable income | Top bracket income |
   |---|---|--:|--:|--:|--:|
   | 2024-06 (nearest to the battery's Feb 2024) | CY2025-34 | 1.312 | 1.301 | 1.230 | 1.461 |
   | 2026-02 (the live site) | CY2026-35 | 1.356 | 1.438 | 1.431 | 1.569 |

   On the battery, a taxable-income index would shrink ordinary scores by about
   6% and **help** every over-predicting row. On the live site the same switch
   **raises** Tailor's ordinary scores by about 6%, and top-bracket scores by more.
   Both are honest consequences, and both must be pre-registered. The series
   choice (AGI vs taxable income vs taxable ordinary income) has to be fixed in
   the pre-registration on conceptual grounds before anyone sees which one helps
   the battery. That is the main risk of quiet fitting in this lane.
3. **Vintage matching is the bigger lever, and it reaches payroll too.** Eight of
   the 44 rows come from the 2018, 2020 and 2022 Options volumes and are scored on
   the February 2024 path projected backwards. The payroll rows' own
   `known_limitations` already say the residual grows with that distance (20.1% on
   the 2018 volume, 33.7% on 2020, 12.1% on 2022, 7.5% on 2024). `cbo-data` starts
   at the 2024-06 edition, so the older volumes need CBO's archived
   *Revenue Projections, by Category* and economic-projections workbooks (earlier
   lanes fetched cbo.gov files through Wayback). That is one data lane that feeds
   both the ordinary and the payroll fix, so B2 is scoped that way.
4. **Corporate has one actionable lever, and it is the anchor's scope, not the
   base.** The fitted anchor (`biden_corporate_28`, Treasury FY2025) prices rate
   *plus* GILTI, and the factory prices rate only. So the module's per-point yield
   carries the GILTI piece. Treasury's one rate-only row (FY2022) normalises to
   66.7%, against 79.5% for its rate + GILTI rows. If the rate-only share fell to
   about 67%, the four JCT rows would read about 27, 19, 17 and 1%, a class mean
   near 16% **(illustrative)**. That would be the largest single move available
   in the battery. But it changes how a fitted row is scored, so it is an owner
   decision, and the GILTI piece has to come from a source and not from the
   residual (B5).
5. **The donut fix is the most visible error, but it is not a modelling-tier
   lane.** It moves no out-of-sample row. Do it early, as a mechanism replacement
   with its own pre-registration (B3). The homepage example swap (C1) should not
   wait for it.
6. **Agreed: charts that change no score go first.** The baseline-vs-policy chart
   and the house strip run in parallel with B1. The waterfall ships in the same PR
   as the dynamic parameters (B6), as proposed.

---

## Part B: modelling lanes, in order

### B1. Lock the battery expansion before any modelling lane opens

**Goal.** Bring every class to n ≥ 5 with agency rows, and add a separate dynamic
tier. Do this before B2–B6, so they pre-register against a fixed denominator.

**Files.** `fiscal_model/validation/cbo_scores.py` (new `CBOScore` records),
`fiscal_model/validation/policy_classes.py` (classification only, no rule
changes), `fiscal_model/validation/core.py` (`_KNOWN_LIMITATIONS_BY_POLICY_ID`),
`fiscal_model/validation/benchmark_sources` (provenance), new lane
`planning/lanes/B1_battery_expansion.md`.

**Candidate rows (agency first; a research house only where no agency scored the policy):**
- *Corporate (needs ≥1):* an official rate-only row on a 21% regime that is not
  already in a tier. Check JCT's JCX tables for any 2025–2026 rate bill first. If
  none exists, record the search and leave the class at n=4 with that stated.
  Pre-TCJA 35%-regime rows do not count: the memo shows the share metric breaks
  across regimes.
- *AGI surtax (≥1), enacted-law spending (≥2), tax expenditure (≥3):* CBO
  *Options 2024* and the 2022 volume still hold unscored options in these
  families. Enacted-law cost estimates for 2023–2025 laws are also candidates.
- *Dynamic tier (new, separate, never pooled):* JCT's macroeconomic analysis of
  the TCJA conference agreement (JCX-69-17) and PWBM's dynamic TCJA table.
  Record what each includes (feedback only, or feedback plus debt service) so
  the model's matching quantity is scored.

**Pre-registration.** Write down each new row, its source and page, and its
class before the model is run on it. Then run it once and record the error. That
first number is the out-of-sample result and is never re-run against a changed
model as if fresh. Disclose the membership change in the cohort table (old 44,
new N, both reported).

**Acceptance.** Every new row has `provenance="line_item"` and a page
reference. `cold_holdout.py --json` reports both the fixed 44-row cohort and the
expanded cohort. No existing row moves (byte-identical on the 44). The dynamic
tier is in `evidence.json` under its own key and is not pooled.

### B2. Vintage-matched CBO income and wage paths (ordinary income, then payroll)

**Goal.** Replace the nominal-GDP projection of the SOI income base with CBO's
own projection of that base, on each record's own vintage. Then apply the same
vintage matching to the payroll covered-earnings path.

**Data (B2a).**
- `US-CBO/cbo-data` @ `284a95665f9f2f74ed1f482feb629b43fce323da`:
  `data/budget/revenue_detail/annual_cy_iit_{2024-06,2025-01,2026-02}.csv`.
  Variables: `rev_iit_agi`, `rev_iit_taxable_income`, `rev_iit_taxable_ordinary`
  (absent in 2024-06; check before relying on it), `rev_iit_bracket_1..7`.
- For the 2018, 2020 and 2022 Options volumes: CBO publication 51138 archived
  editions (Revenue Projections by Category, Sheet 3 Individual Income Tax
  Details) from the matching baseline. Pin each by URL and SHA-256 as
  `scripts/fetch_cbo_baseline.py` does. Where an edition cannot be found, grade
  the row `nearest_vintage` exactly as `cbo_tax_parameters` does, and say so in
  `known_limitations`.
- New script `scripts/fetch_cbo_income_detail.py`, writing
  `fiscal_model/data_files/cbo_income_detail/cbo_income_detail.csv` verbatim (long
  format: `vintage,calendar_year,variable,value`) plus `PROVENANCE.csv`. Model it
  on `scripts/fetch_cbo_tax_parameters.py`.

**Code.**
- `fiscal_model/baseline.py`: add `BaselineProjection.income_base_index(year,
  series)` beside `nominal_income_index`. Return 0.0 when the vintage has no
  series, so callers fall back to the GDP index *and log that they did*.
- `fiscal_model/scoring_engine.py`: `_income_base_projection_factor` and
  `_threshold_deflator` both go through `_nominal_income_ratio`. Keep that single
  choke point so the base projection and the threshold deflator stay one unit
  conversion. Swap the index inside it, not in either caller.
- Do **not** use `rev_iit_bracket_k` as a growth index: in the 2024-06 and
  2025-01 editions the bracket numbering changes meaning in CY2026 (TCJA expiry),
  and the per-bracket series jump (bracket 6 falls to 0.37×, bracket 5 rises to
  3.1×). Use bracket income only for the check below.

**A decomposition to add, separate from the index switch.** CBO's bracket-income
series gives a published **static** base for a bracket-rate change: 1pp on the
top four brackets is 0.01 × Σ `rev_iit_bracket_4..7`. On the 2024-06 edition,
CY2025-34, that is about $396B per point, against JCT's $285B per point for
*Options 2024* option 45, and the model's ~$336B. Print, per ordinary row:
model static, CBO-implied static, model behavioural offset, and the published
total. This separates base error from behavioural error before anyone touches
the ETI. Put it in `scripts/ordinary_base_decomposition.py`. It reports, it does
not change scores.

**Pre-registration (`planning/lanes/B2a_cbo_income_path.md`), written before the module is opened.**
1. The series, chosen on concept and fixed here. My recommendation: **taxable
   income** for a rate change on taxable income, and AGI only for AGI-based
   surtaxes. Give the reason in the doc. Do not run both on the battery and pick.
2. For each of the 11 ordinary rows, the predicted factor (scratch script output)
   and the predicted error. **Illustrative**, if the 2024-06 taxable-income ratio
   acted as a pure scalar (0.938): the class goes from 15.3% to about 11%; the
   largest row from 40.6% to about 32%; the three rows now at 0.8–1.3% go to about
   5%. Three rows getting worse is the expected cost, and they are kept.
3. The AGI-surtax rows, if they read the same base: predicted factor and error
   per row.
4. Tailor and the live presets (Feb 2026 vintage): the predicted movement in the
   ordinary-income presets (about +5.5% on taxable income, +16% on top-bracket
   shapes, before thresholds). This is a change to the public number, and it
   goes in the PR body.
5. Rows that must stay byte-identical: everything outside ordinary-rate,
   AGI-surtax, and SOI-based credit paths. List them.

**B2b (payroll vintage) pre-registration.** Same structure. The data is CBO's
fiscal-year wages and salaries and its taxable-payroll path per vintage, from the
matching *Budget and Economic Outlook* economic workbook, into
`fiscal_model/data_files/payroll/covered_earnings_base.csv` (a vintage column)
and `fiscal_model/payroll.py` `covered_earnings`. Prediction: the 2018/2020/2022
volume rows (20.1, 33.7, 20.3, 34.6, 12.1, 12.6) fall, and the 2024-volume rows
(7.5, 8.1) are byte-identical, because they are already on their own vintage. If
the 2024 rows move, the lane has a bug.

**Acceptance.** Pre-registration merged before the module is opened (first
commit). Outturn table with predicted vs actual per row (last commit). A row that
misses its band is reported as a miss. Fitted tier unchanged, or every movement
explained. The 44-row cohort and the expanded cohort are both reported.
`build_current_evidence.py` is rerun in the docs-sync PR, not in the lane.

### B3. Social Security donut: replace the flat $270B with the mechanism

**Goal.** The proposal page and homepage stop showing −$2,700B for a design CBO
scores at −$1,426.8B. No ten-year dollar target is built from CBO's option.

**Code.** `fiscal_model/payroll.py`:
- `create_ss_donut_hole` stops passing `annual_revenue_change_billions=270.0`, so
  `PayrollTaxPolicy.estimate_static_revenue_effect` prices the donut from
  `covered_wages_above(threshold)` against the **year's** taxable maximum. The
  donut is wages above `max(threshold, cap_t)`, so it narrows as the cap rises
  toward $250,000. The cap path comes from CBO's own `tp_ss_max_earnings` in
  `cbo_tax_parameters.csv` (already transcribed), not from the option.
- `SSA_COVERED_WAGES_ABOVE_BILLIONS` has a $250K point (2,177) that was **fitted
  to the superseded $2.7T**. It cannot stay as an input to the new mechanism.
  Replace it with a source-derived level: SSA's *Wage Statistics* (counts and
  amounts of net compensation above $250K) for the anchor year, grown with B2b's
  covered-earnings path. Record the replacement in the module docstring and in
  `validation/scenarios.py`, which records the decision to keep the old error.

**Pre-registration (`planning/lanes/B3_ss_donut_mechanism.md`).** Expected ten-year
total as a band, computed in scratch from SSA wage statistics before the module is
touched. The donut row is in the fitted-held-in-place group (target revised), so
the pre-registration also states how that tier moves. The old 89.2% stays in the
record as the *superseded-target* finding with its date. It is not deleted.

**Acceptance.** `ss-donut-250k` conventional total changes, with the year path
rising as the cap closes the gap. The tier tables report the move. The Social
Security page's OCACT-based figures are untouched (they come from
`fiscal_model/social_security/`, a different path, and must stay byte-identical).

### B4. Capital gains at death: measure the level, then decide

**Goal.** A memo, not a model change: is the flow of gains at death (Poterba &
Weisbenner 1998, held as a share of net worth) too small by the factor implied by
the 2.65% death rate used elsewhere?

**Sources to check the level against.** SCF 2022 with NCHS life tables, which
repeats P&W's method on current data. IRS SOI *Estate Tax Returns* (the top tail
only). IRS SOI *Sales of Capital Assets* (the share of sold assets acquired by
inheritance, and their basis). JCT's and Treasury's tax-expenditure estimates for
step-up at death, as a plausibility range only, never a target.

**Output.** `planning/memos/GAINS_AT_DEATH_LEVEL.md` and
`scripts/gains_at_death_level.py`. If the memo concludes the level is wrong, a
follow-up lane pre-registers both `cbo_opt51_gains_at_death` (predicted to
improve) **and** `treasury_capgains_39_plus_stepup_elim` (predicted to get
worse, because its 1.8% is two errors cancelling). Report both. Also write down
before the lane what fixes the other half of that cancellation: the 27.0%
over-prediction in `biden_capital_gains_39`.

**Acceptance.** A memo with a stated conclusion and every source pinned. No score
moves in this step.

### B5. Corporate: make the fitted anchor score the reform it is fitted to (owner decision first)

**Goal.** Stop the rate-only per-point yield from absorbing Treasury's GILTI
linkage.

**Open decision for Laurence.** `biden_corporate_28` is fitted to Treasury FY2025
(rate + GILTI 10.5% → 14%), while the factory prices rate only. There are two
honest repairs:
(a) score the anchor as rate **plus** a sourced GILTI piece, so that what is left
calibrates rate-only, or
(b) re-anchor on Treasury's rate-only FY2022 row and move that row out of
whatever tier it now sits in, with the cohort change disclosed.
Both change a fitted row, and so both need sign-off. I recommend (a), because it
keeps the anchor, and it makes Cursor's "name the GILTI piece" a mechanism instead
of a residual.

**The GILTI piece must come from a source, not from the gap.**
`fiscal_model/corporate.py` prices GILTI as `gilti_rate_change × 250.0`, an
unsourced constant. Before B5 runs, `fiscal_model/international.py` needs a
sourced GILTI base (SOI Form 8992 / Form 5471 aggregates for GILTI inclusions,
net of the §250 deduction), validated against an international-class row where
one exists. If no source supports a GILTI base, B5 stops and says so.

**Pre-registration (`planning/lanes/B5_corporate_anchor_scope.md`).** Predicted
rate-only marginal share, and predicted error on each of the four JCT rows and on
`trump_corporate_15`. **Illustrative:** at a 66.7% share the four rows read about
27, 19, 17 and 1 (a class mean near 16%). Two falsification conditions are fixed
in advance: if the sourced GILTI piece is under ~$100B over ten years, the share
barely moves and the lane reports that; and if the share falls below JCT's 55.9%,
the GILTI piece is too large and the lane stops.

**Acceptance.** Owner decision recorded in the lane. `biden_corporate_28` still
within its fitted band, or the move reported. All four held-out rows reported,
predicted vs actual. `estimator_ranges` marginal-share test updated to the new
model share.

### B6. Dynamic: sourced feedback and debt-service parameters, plus the waterfall

**Goal.** The second number on every proposal page stops resting on three round
constants.

**Code.** `fiscal_model/models/macro_adapter_frbus.py` `FRBUSAdapterLite` (and
`SimpleMultiplierAdapter`, which carries the same 0.25 and 0.04):
- `baseline_gdp = 28_000.0` → the scored vintage's own `nominal_gdp` by year.
- `interest_cost = cumulative_deficit * 0.04` → each year's effective rate,
  `net_interest_t / debt_held_by_public_{t-1}`, from `cbo_budget_baseline.csv`
  (both are already transcribed per vintage). Include interest on interest.
- `revenue_feedback = gdp_change * 0.25` → revenue per dollar of GDP **by income
  type**: the baseline's own revenue-to-income ratios (individual income tax over
  AGI, payroll over wages, corporate over profits), weighted by how the GDP change
  splits between labour and capital income. CBO's effective marginal rates in
  `tax_parameters` (`tp_emtr_labor_*`, `tp_emtr_capital_*`) measure incentives,
  not revenue per dollar of income. Use them only for the labour-supply and
  investment responses, if those channels are modelled.
- Check whether CBO's *How Changes in Economic Conditions Might Affect the Federal
  Budget* workbook for the matching vintage (with its debt-service and rules-of-
  thumb tables) is fetchable. If it is, use its debt-service relationship in
  place of the derived effective rate and record which one was used.

**Web.** `web/app/explore/[id]/page.tsx`: a waterfall, in the **same PR**, with
static, behavioural, revenue feedback, debt service and dynamic total, read from
`file.dynamic`. `scripts/export_static.py` already exports all five fields.

**Pre-registration (`planning/lanes/B6_dynamic_parameters.md`).** Predicted
TCJA dynamic total, and predicted change on the five largest presets. The B1
dynamic tier rows are scored once after the change and reported. They are never
used to set a parameter. The out-of-sample tier must be byte-identical (it is
conventional). If it moves, the lane has a bug.

**Acceptance.** No literal 0.25, 0.04 or 28,000 left in either adapter.
Per-vintage tests. The dynamic tier is reported separately. The waterfall renders
in `npm run layout` on desktop and phone.

### B7. Joint scoring in Build (ordinary rates, SALT, AMT, CTC)

**Goal.** Build shows two bars when every selected row in the jointly scorable set
can run through the microsimulation: the sum of list prices, and the joint
microsimulation total.

**Code.** `fiscal_model/package_interactions.py` `joint_tax_change` and
`measure_package` already exist. Export a `joint` block per scorable combination
from `scripts/export_static.py`. Precompute every pair and the common triples, or
call `/api/score` for arbitrary sets. Pick one in the PR and say why. Then
`web/components/PackageBuilder.tsx` and `web/lib/package.ts`. The headline stays
`total()` (the sum of list prices) until Laurence decides the joint figure is the
one to stand behind. Corporate, estate, payroll and tariffs stay a labelled sum.

**Pre-registration.** The two measured pairs (13.7% and 20.2% with the sign flip)
are reproduced exactly. Rate × AMT, rate × credits and CTC × EITC stay labelled
"structurally additive in this model", never "no interaction".

**Acceptance.** Two bars appear only for supported sets. Web tests cover a
supported set, an unsupported set, and a mixed set.

### B8 (after B2). One tax-unit population for revenue, the TCJA breakdown and who-pays

Agreed with the feedback, and it waits until the B2 income base is the one it
calibrates to. It needs its own plan document. It is not scoped here.

---

## Part C: web lanes (no score moves; can run alongside B1)

Each is one PR against `web/` (plus `scripts/export_static.py` where noted). Each
passes `npm run typecheck && npm test && npm run layout`, and adds a test in
`web/lib/*.test.ts` for any new pure function.

### C1. Fix the homepage examples (first, smallest)
`web/lib/home.ts` `WORKED_PRESET_IDS`: replace the three rows with **out-of-sample**
rows. For example, one within 5% (`cbo_opt45_all_rates_1pp`, if a preset maps to
it), one near the class mean, and one honest miss that is labelled as out of
sample. Add a `tier` to each worked row (fitted / out-of-sample) and print it on
the line. Keep the "36 of 44" stat. Acceptance: no fitted row is presented
without the word "fitted"; `home.test.ts` asserts it.

### C2. The proposal drawn on the baseline
`scripts/export_static.py`: add `site_data/baseline.json` (deficit, debt held by
the public, nominal GDP, by fiscal year, `cbo_feb_2026`, from
`cbo_budget_baseline.csv` and `cbo_economic_baseline.csv`). On
`web/app/explore/[id]/page.tsx`, add a new `BaselineChart` component: deficit
under current law and under the policy, then debt-to-GDP under each, with a
$ / % of GDP switch. Policy debt is the baseline debt plus the cumulative
conventional effect, and the dynamic version is shown only if B6 has shipped.
Label it "conventional, no feedback". Acceptance: FY2026–2035 ten-year deficit
reads $23.1T on the baseline line, and the chart's sums equal the page's
headline to the cent (test).

### C3. Where this score sits among the houses
Export `fiscal_model/ui/estimator_ranges.py` output per preset
(`corporate_estimator_range` for corporate rate presets, `published_range_for`
for `trump_corporate_15`, `pillar_two_adoption` and `reciprocal_tariffs`) into
`site_data/views/<id>.json` or a new `ranges.json`. Draw a horizontal strip:
each house as a labelled dot, this model as a distinct mark, and the fitted
target ringed. On `/methods`, add a scatter of the out-of-sample rows (model vs
published, log-scaled magnitude, the 45° line, ±15% and ±25% bands, coloured by
class), from a new `out_of_sample_rows` array in `evidence.json`. That field is
added in `scripts/build_current_evidence.py` in its own docs/yardstick PR, not
inside a lane. Acceptance: the strip's numbers equal `estimator_ranges` output
(test). The scatter shows 44 points (or the expanded cohort, labelled).

### C4. A ribbon only where a class has a record
On the year chart, show a band only if the preset maps to an out-of-sample class
with n ≥ 5. The inner band is the class mean absolute error, and the outer band
is the class's worst row. Otherwise print the current "no pre-registered row of
this kind" text. Read the classes from `evidence.json` `out_of_sample_classes`,
with the mapping via `policy_classes.classify_policy_object` exported per preset.
Acceptance: TCJA shows no band; a payroll preset shows one; and corporate shows
none until it reaches n ≥ 5 (the band would be built on four rows).

### C5. PNG and a link on the proposal chart
A "Download PNG" button (serialize the chart SVG to canvas client-side, no new
dependency) and a "Copy link" button, beside the existing CSV link. Acceptance:
the PNG includes the title, source line and vintage. Layout check passes.

### C6. Build, as two bars (ships with B7)
See B7.

---

## Suggested order and parallelism

| Wave | In parallel | Gate before the next wave |
|---|---|---|
| 1 | **C1**, **C2**, **C3** (strip half), **C5**; **B1** pre-registration and new rows; **B4** memo | B1 merged (denominators locked) |
| 2 | **B2a** (ordinary income path), **B3** (donut mechanism), **C3** scatter (after the `evidence.json` field lands) | B2a outturn merged, then the docs-sync PR |
| 3 | **B2b** (payroll vintage), **B6** + waterfall; **B5** if Laurence picks (a) or (b) | docs-sync PR, then a re-score against the 9/10 bar |
| 4 | **B7** + C6; **C4**; B4's follow-up lane if the memo says the level is wrong | — |
| Later | **B8** | its own plan |

**What would reach the bar, honestly.** Illustratively, B2a takes the ordinary
class from 168.8 to about 122 units of error mass (about 11%), and B5 takes
corporate from 161.3 to about 64 (about 16%). If B2b halves the older-volume
payroll miss (133.4 units on six rows), payroll goes to about 10%. Together, the
pooled mean on today's 44 rows would be about 10.4%, with no class above 20%. Each
of those three is a pre-registered prediction that can miss, B5 needs an owner
decision, and B1's new rows will move the mean in a direction nobody knows yet.
**The bar is within reach of this plan but not in hand**, and the docs should keep
saying so until the outturns are in.
