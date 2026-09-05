# Changelog

Material changes to the Fiscal Policy Calculator. Trivial fixes are captured
in git history, not here.

## 2026 — ongoing

### Modelling Wave 5 — a payroll base that is earnings, a corporate base that is published, a realizations base that grows; plus frozen classroom links and one app scoring window (2026-09-05)

Three modelling lanes on disjoint files, plus two blue-tier PRs and the
coordinator's gate re-derivation. **Wave 5 is not in the plan's sequencing** — it
is three of §6.2's carry-over items taken in parallel. Every lane pre-registered
its expected movement in [`planning/lanes/`](../planning/lanes/) **before**
touching code and appended an outturn afterwards; §5.5 of
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md) carries
the summary and the four findings. PRs **#111** (frozen assignment links),
**#113** (payroll at the margin), **#114** (corporate at the margin), **#115**
(app default scoring window), **#116** (preferential rate at the margin),
**#117** (CI gate).

**Only Tier 1 moved, and that is the point.** No target moved and no constant was
retuned, so 0 of the 23 fitted rows and 0 of the 31 reconstruction rows changed
and `run_loo.py --donor-matrix` is byte-identical — a falsification test each
lane registered in advance and each passed. It is the first wave since Wave 1
with no composition to net out.

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 18.0% / 12.6% median / 14 within 15 / 21 within 25 | **26 @ 15.9% / 11.4% / 16 / 22** |
| Calibrated, fitted | 23 @ 1.6%, 23/23 within 15 | **unchanged — 0 rows moved** |
| Unfitted module reconstructions | 31 @ 56.6% / 29.9% median / 9 within 15 | **unchanged — 0 rows moved** |
| Calibrated, leave-one-out | 18 derivable @ 29.6% / 19.1% median / 8 within 15 | **byte-identical output** |
| Distributional (7 tables) | 0.00–5.86pp (ARP 3.72) | **unchanged** |
| Scorecard rows | 80 (73 published) | **unchanged** |
| `revised_target_entries` | 15 | **15** — no target moved |
| Tier 1 error mass | 468.1 over 26 (payroll largest at 109.6, 23.4%) | **412.9** (capital gains largest at **104.5, 25.3%**; payroll **15.6, 3.8%**) |
| Tier 1 CI gate | `--max-mean-error 25 --min-within-25pct 20` | **`20 / 21`**, both tightening |
| Tests | 3322 passed, 1 skipped | **3415 passed, 1 skipped** (`python -m pytest tests/ -q`) |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt61_new_payroll_tax_1pct` (Tier 1) | −$1,281.5B | −$1,975.0B | **−$1,378.2B** | 54.1% → **7.5%** |
| `cbo_opt61_new_payroll_tax_2pct` (Tier 1) | −$2,540.0B | −$3,950.0B | **−$2,745.0B** | 55.5% → **8.1%** |
| `cbo_opt47_ltcg_qdiv_2pp` (Tier 1) | −$103.3B | −$57.1B | **−$92.5B** | 44.8% → **10.5%** |
| `biden_capital_gains_39` (Tier 1) | −$288.6B | −$240.5B | **−$379.2B** | 16.7% under → **31.4% over** *(pre-registered regression)* |
| `treasury_capgains_39_plus_stepup_elim` (Tier 1) | −$322.0B | −$322.7B | **−$461.5B** | 0.2% → **43.3% over** *(pre-registered regression; the 0.2% was two errors cancelling)* |
| `cbo_opt64_corporate_rate_1pp` (Tier 1) | −$135.7B | −$199.6B | **−$220.3B** | 47.1% → **62.3%** *(pre-registered regression)* |
| 💊 Expand Drug Negotiation (app preset) | — | −$33.5B | **−$41.8B** | one more post-2029 year in the FY2026–2035 window |
| 💊 Comprehensive Drug Reform (app preset) | — | −$150.5B | **−$158.9B** | same |
| Tailor: +2pp all brackets / +5pp all brackets / +5pp above $1M / 39.6% above $1M + step-up repeal | — | −$56.4B / −$110.9B / −$22.3B / −$490.7B | **−$91.4B / −$183.7B / −$46.9B / −$626.9B** | Decision 6 caption ships with them |

- **PR #113: the payroll base is now earnings, not a receipts total divided by
  the wrong rate.** The two CBO Option 61 rows went **54.1% / 55.5% → 7.5% /
  8.1%**, the largest single move of the wave, and reproduced the lane's hand
  arithmetic to the decimal. **The plan's own scoping was wrong on both halves**:
  §2.1 called for "employer-share incidence + income-tax offset", and CBO's
  option text says the tax "would be paid entirely by employees" — adding that
  offset would have moved the model *further* from the target, for a reason the
  source explicitly rules out. The real defect was `$400B / 2.9% = $13,793B`,
  Medicare receipts divided by a rate that does not raise all of them, with the
  0.9% Additional Medicare Tax's own $15B sitting four lines above it in the same
  dict. The base is now CBO's February 2024 wage path × the Trustees'
  covered-earnings ratio. **A second module was found with an inverted
  behavioural-offset sign** — `trade.py` was the first, in Wave 3 — and neither
  was found by a test, because both modules' calibrated factories zero the
  elasticity.
- **PR #114: the corporate rate is priced on a published base, and the row got
  worse on purpose.** `cbo_opt64_corporate_rate_1pp` **47.1% → 62.3%**,
  pre-registered and landed to the decimal along with all fifteen other
  registered rows. The derived path uses IRS SOI Table 11's income subject to tax
  ($2,879.1B, TY2022), realized at SOI's own after/before-credits ratio and
  settled on IRC §6655's calendar. **The fitted $1,900B it replaced was not a
  wrong concept but a stale vintage**, within 3% of SOI's TY2018 figure — and it
  was two errors, a base 34% too small against an offset well below what the
  published semi-elasticity implies at 7pp, which nearly cancel at 7pp and do not
  at 1pp. What is left is a disagreement between documents: CBO 60557 prices a
  point at **$135.7B** over the window and Treasury's FY2025 Green Book at
  **$192.8B**, with the *larger* rate change carrying the *larger* per-point
  yield. `CORPORATE_APP_MODE` stays `reported` under Decision 1 (1.92% against
  9.67%), so nothing a user sees moved. Two findings recorded and not acted on:
  **`corporate.py`'s offset returns `abs(static_effect)`**, so a shipped rate-cut
  preset books a behavioural response that makes the cut *more* expensive (the
  third module with an offset defect, now pinned by a test in both behaviours),
  and **the corporate module has no leave-one-out row at all**.
- **PR #116: the realizations base grows with the stock it is a flow off.**
  `R(t) = h · A(t)` at the module's own 5.8% net-worth CAGR, introducing no new
  constant, closed **34.3 of CBO Option 47's 44.8 points, to 10.5%**, with no
  elasticity, bracket, threshold or rule touched. The obvious hypothesis was
  **refuted** by arithmetic already in the tree: SOI Table 3.5's preferential
  columns *exceed* the whole year's realized gains in both vendored years (1.046
  and 1.189), so they already contain qualified dividends, and adding a column
  would have double-counted $313–336B by being wrong twice. The same projection
  was registered as a **net Tier 1 regression** on the two Green Book rows and
  landed inside both bands. **The FY2022 row's old 0.2% was never accuracy** —
  Wave 4's own lane doc recorded it as two errors cancelling, and this lane
  removed the first — and about **17 of its 43 points are the window** it is
  scored on (target FY2022–2031, model FY2025–2034). Four Tailor rows moved
  26–110%, so a Decision 6 caption ships with them; the reconstruction scenarios
  and the CapitalGains leave-one-out are byte-identical, because a projection is
  a property of the base's vintage and those rows carry 2018 and 2021 vintages.
- **PR #111: frozen assignment links.** `frozen=1` beside the provenance stamps
  a share link already carried (`baseline=&engine=&spec=&mode=`) pins vintage,
  engine, dynamic and policy on `/explore` and `/tailor`, so a whole class hands
  in one set of numbers; the pinned controls render disabled under a "🔒 Frozen
  for this assignment" banner with a provenance line under the number. A link
  frozen on a vintage this deployment is not serving **refuses to score** and
  names both vintages, rather than falling back quietly — as do a `frozen=1` with
  no `baseline=` and an unknown `engine=` token. `?classroom=1` on a result
  surface reveals the instructor control that emits one. Blue tier: no scoring
  change, every existing URL preserved. Deliberately left out: **Build packages
  are not freezable**, and the **Data & methodology options are not pinned**.
- **PR #115: one app scoring window, FY2026–FY2035.** `APP_DEFAULT_START_YEAR =
  2026` now routes through every app surface and the API's `budget_window`; the
  window was never chosen before, it was whatever `Policy.start_year` happened to
  be, so Explore and Tailor could render different windows off the same baseline.
  Presets move with `max(policy.start_year, APP_DEFAULT_START_YEAR)`, so a
  factory stating a later effective year keeps it. **The library defaults stay at
  2025**, because each benchmark is scored over the window its own document used
  and moving one would be a target revision with its own ledger. Exactly one
  validation path read a default — the five sectoral runners pinned their scorer
  but not their policy — and it was fixed in a separate first commit that leaves
  all five scripts byte-identical. Two pharma presets moved by one calendar year,
  correctly.
- **PR #117: the Tier 1 CI gate, re-derived by the workflow's own rule.**
  `--max-mean-error 25 --min-within-25pct 20` → **`20 / 21`** (ceiling
  `ceil(15.9 × 1.25) = 20`; floor `22 − 1 = 21`). Both tighten. A modelling lane
  never touches the yardstick, so the coordinator re-derives it separately.

**Every Wave 5 module keeps `reported` as its app default under Decision 1.** The
only shipped numbers that moved are the four Tailor capital-gains rows, with
their Decision 6 caption, and the two pharma presets the window change carried
forward a year.

### Modelling Wave 4 — the death channel's carve-outs, CBO's household universe, Option 56's indexation, Part D's three channels, statutory AMT phase-outs, thirteen targets onto their documents (2026-09-05)

Six lanes on disjoint files plus a target-provenance lane and the coordinator's
gate re-derivation. **Wave 4 is not in the plan's sequencing** — it is six of
§6.2's carry-over items taken in parallel. Every lane pre-registered its expected
movement in [`planning/lanes/`](../planning/lanes/) **before** touching code and
appended an outturn afterwards; §5.4 of
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md) carries
the summary, the three findings and the five missed pre-registrations. PRs
**#104** (distributional households), **#105** (Option 56 excess share), **#106**
(AMT phase-outs), **#107** (target provenance), **#108** (gains at death),
**#109** (pharma Part D), **#110** (CI gate).

**Validation tiers moved, and two of the four changed population — so the
like-for-like readings are printed beside them, and in this wave both printed
means fell for reasons that are not improvements:**

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 31.0% / 15.1% median / 13 within 15 / 19 within 25 | **26 @ 18.0% / 12.6% / 14 / 21** |
| Calibrated, fitted | 28 @ 2.0%, 28/28 within 15 | **23 @ 1.6%, 23/23** — or **28 @ 3.0%, 27/28** with Wave 4's five revised rows held in place (29 @ 5.2%, 27/29 with the TCJA-AMT row too) |
| Unfitted module reconstructions | 26 @ 61.8% / 38.0% median / 5 within 15 | **31 @ 56.6% / 29.9% / 9** — but **65.7% / 40.5% over the same 26 rows**, i.e. *worse* |
| — sectoral presets | 14 @ 81.0% / 38.0% median | **15 @ 82.6% / 39.0%** (**88.2%** over the 14) |
| — 8 P.L. 119-21 line items | 35.8% | **unchanged** |
| — 3 capital-gains scenarios | 39.6% | **unchanged** |
| — TCJA AMT relief | 66.8% | **unchanged** |
| — Wave 4 provenance arrivals | — | **5 @ 9.4%** |
| Calibrated, leave-one-out | 18 derivable @ 28.4% / 16.5% median / 9 within 15 | **18 derivable @ 29.6% / 19.1% / 8** — every bit of it a *target* movement, no derivation moved |
| — `Credits` | 20.5% | **18.5%** |
| — `Expenditures` | 30.2% | **35.7%** |
| Not cross-validatable | 4 | **unchanged** |
| Distributional (7 tables) | 0.00–7.77pp | **0.00–5.86pp** (ARP 7.77 → **3.72**) |
| Scorecard rows | 80 (73 published) | **unchanged** |
| `revised_target_entries` | 3 | **15** |
| `line_item_differs` (calibrated) | 13 | **5**, each with a written verdict |
| Provenance (calibrated) | 19 / 13 / 15 / 7 / 0 | **30 / 5 / 12 / 7 / 0** |
| Tier 1 CI gate | `--max-mean-error 40 --min-within-25pct 18` | **`25 / 20`** |
| Tests | — | **3322 passed, 1 skipped** (`python -m pytest tests/ -q`) |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `treasury_capgains_39_plus_stepup_elim` (Tier 1) | −$322.0B | −$1,022.3B | **−$322.7B** | 217.5% → **0.2%** |
| `biden_capital_gains_39` (Tier 1) | −$288.6B | −$678.1B | **−$240.5B** | 134.9% → **16.7%** |
| `cbo_opt51_gains_at_death` (Tier 1) | −$536.1B | −$581.2B | **−$432.8B** | 8.4% → **19.3%** *(worse, pre-registered as a regression)* |
| `cbo_opt56_employer_health_income_only` (Tier 1) | −$697.0B | −$529.9B | **−$605.8B** | 24.0% → **13.1%** |
| `biden_high_income_tax` (Tier 1, **target revised**) | −$252.0B → **−$245.9B** | −$216.5B | −$216.5B | 14.1% → **12.0%** |
| `expand_drug_negotiation` (Tier 2b) | −$500.0B | −$371.5B | **−$33.5B** | 25.7% → **93.3%** *(worse, by design)* |
| `international_reference_pricing` (Tier 2b) | −$100.0B | −$746.2B | **−$801.0B** | 646.2% → **701.0%** *(worse, by design)* |
| `universal_insulin_cap` (Tier 2b) | +$11.4B | +$7.0B | +$7.0B | **39.0%**, unchanged to the cent |
| `eliminate_salt` (fitted → Tier 2b, **target revised**) | −$1,200.0B → **−$1,621.0B** | −$1,260.3B | −$1,260.3B | 5.0% → **22.3%** |
| `repeal_salt_cap` (fitted → Tier 2b, **target revised**) | +$1,100.0B → **+$1,169.0B** | +$1,155.6B | +$1,155.6B | 5.1% → **1.2%** |
| `biden_eitc_childless` (fitted → Tier 2b, **target revised**) | +$178.0B → **+$162.6B** | +$178.0B | +$178.0B | 0.0% → **9.5%** |
| `extend_enhanced_ptc` (fitted → Tier 2b, **target revised**) | +$350.0B → **+$335.0B** | +$366.2B | +$366.2B | 4.6% → **9.3%** |
| `ira_enforcement` (fitted → Tier 2b, **target revised**) | −$200.0B → **−$180.4B** | −$188.9B | −$188.9B | 5.5% → **4.7%** |
| `biden_gilti_reform` (Tier 2b, **target revised**) | −$280.0B → **−$373.9B** | −$230.3B | −$230.3B | 17.8% → **38.4%** |
| `fdii_repeal` (Tier 2b, **target revised**) | −$200.0B → **−$158.0B** | −$110.7B | −$110.7B | 44.7% → **29.9%** |
| `biden_full_international` (Tier 2b, **target revised**) | −$700.0B → **−$632.2B** | −$353.7B | −$353.7B | 49.5% → **44.1%** |
| `repeal_ev_credits` (Tier 2b, **target revised**) | −$200.0B → **−$182.3B** | −$228.4B | −$228.4B | 14.2% → **25.3%** |
| `trump_universal_10` (Tier 2b, **target revised**) | −$2,000.0B → **−$2,171.1B** | −$1,258.5B | −$1,258.5B | 37.1% → **42.0%** |
| `auto_tariff_25` (Tier 2b, **target revised**) | −$100.0B → **−$386.2B** | −$182.2B | −$182.2B | 82.2% → **52.8%** |
| `reciprocal_tariffs` (Tier 2b, **target → a range**) | −$1,200.0B → **[−$1,800B, −$1,400B]**, anchor −$1,500B | −$1,396.8B | −$1,396.8B | 16.4% → **6.9%** vs the anchor; $3.2B outside the nearer bound |
| ARP refundable credits (distributional) | — | 7.77pp | **3.72pp** | scored on CBO's own household universe |

- **PR #108: the death channel now knows what a realization-at-death proposal
  does not tax.** Six carve-outs transcribed from the Green Books' own text —
  spousal transfers, charitable bequests, the §121 residence exclusion, tangible
  personal property, a family-owned-business deferral, and the per-donor
  exclusion applied *after* the others — plus a semi-log rate response at death.
  Tier 1 fell **31.0% → 18.5% on this PR alone** and the capital-gains error mass
  **405.6 → 81.0**, from half the tier's mass to a sixth. **The Treasury row's
  0.2% is two errors cancelling and must never be quoted as accuracy**: the
  mechanism removes 87.2% of that row's death channel where the pre-registered
  hand path said 92.8%. Option 51 got **worse by design**, and that was
  registered in advance — its 8.4% had been bought by taxing charitable bequests
  and small decedents' housing gains that no such regime reaches.
- **PR #104: the distributional engine gained CBO's household universe**,
  size-adjusted household income before transfers and taxes with quintiles
  containing equal numbers of *people*, and each benchmark is now registered on
  the universe **its source ranks**, with the surfaces reporting the universe
  **scored**. ARP **7.77pp → 3.72pp**; six of the seven tables unmoved to the
  hundredth. Two findings: **3 of the 7 fall back `household→tax_unit`** because
  `TCJAExtensionPolicy` and the corporate policy have no microsim path — so the
  two *circular* rows are visibly scored on a population CBO does not use — and a
  per-household **dollar column was wrong by a factor of three** and invisible to
  every gate, because the error metric scores shares.
- **PR #105: Option 56's excess share now knows what year it is.** 24.0% →
  **13.1%**, from CBO's own chained-CPI indexation rather than a fitted
  parameter; the pre-registered 5%/yr escape hatch that would have landed the row
  at 0.6% was declared in advance and **not taken**. What is left: a **base
  omission** (CBO caps premiums *and* FSA/HRA/HSA contributions) and an
  **unsourced behavioural offset whose sign convention is the reverse of
  `TaxPolicy`'s**, both named and neither tuned.
- **PR #106: statutory §55(d)(2) transcribed from eleven Revenue Procedures.**
  No benchmark moved, by design. A threshold reform stops scoring exactly zero
  (a −$200,000 MFJ change is now +$300.1B over ten years where every value used
  to return 0.0), and the module can represent P.L. 119-21's design as distinct
  from a naive TCJA extension. Finding worth keeping: two schedule rows were 20%
  wrong and it never showed, because both benchmarks sit on anchors.
- **PR #109: Part D's three federal channels — and the reconstruction rows got
  worse.** Direct subsidy 0.37269, reinsurance 0.10470, low-income subsidy
  0.29864, federal total 0.77603 against the 2023 aggregate's 0.7626; a
  negotiation ladder reproducing all three published CMS cycles to within 2.1%;
  a RAND coverage base. The two pre-registered mechanisms landed within $3B of
  the pre-registered figure, and then the lane's **own** ladder condemned an
  unsourced $220B Part D gross-spending constant the reference-pricing leg also
  reads — CMS's own sentence puts the total at $281B. **The alternative was to
  keep an unsourced number because it flattered the prediction.** Presets moved
  by design, with a Decision 6 caption in the same PR: negotiation −$371.5B →
  **−$33.5B**, reference pricing −$746.2B → **−$801.0B**, comprehensive −$573.5B
  → **−$150.5B**, insulin unchanged.
- **PR #107: thirteen targets onto their documents, and no modelling change at
  all.** Every `model_10yr_billions` byte-identical, every LOO derivation
  unchanged, no constant retuned, no threshold touched. Two of the thirteen were
  not merely unsourced but the wrong *kind* of number: the auto tariff's −$100B
  was a **per-year** claim in a ten-year column, and the reciprocal-tariff target
  was **Tax Foundation's dynamic score in a conventional column** — a tier error
  no rescaling would have found, now the second **range** revision. **Six of the
  thirteen got worse**, which is the shape a correct provenance pass has. Four
  more benchmarks were examined and deliberately left; `line_item_differs` went
  13 → **5**, and all five carry a written verdict.
- **PR #110: the Tier 1 CI gate re-derived by the workflow's own rule** after the
  death channel halved the tier — ceiling `ceil(18.0 × 1.25) = 23` rounded up to
  **25**, floor `21 − 1 = **20**`, a tightening on both.

**Every Wave 4 module keeps `reported` as its app default under Decision 1.** The
shipped numbers that moved are the three drug-pricing presets, by design; the
insulin preset's *description string* was also corrected, having still quoted the
−$15B target PR #90 superseded.

### Modelling Wave 3 — international overlap, net tariffs, credits from CPS microdata, five targets onto their documents (2026-09-02)

Wave 3 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md)
completes the plan: three modelling lanes on disjoint files, a target-provenance
lane alongside them, and the coordinator's gate re-derivation. Every lane
pre-registered its expected movement in `planning/lanes/` **before** touching
code; §5.3 of the plan carries the outturn, the five findings and the three
missed pre-registrations. PRs **#98** (L9 international), **#99** (L8 tariffs),
**#100** (target provenance), **#101** (L3 credits), **#102** (CI gate).

**Validation tiers moved, and three of the four changed population — so the
like-for-like readings are printed beside them:**

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered | 25 @ 31.3% / 14.1% median / 13 within 15 / 18 within 25 | **26 @ 31.0% / 15.1% / 13 / 19** |
| Calibrated, fitted | 30 @ 2.2%, 30/30 within 15 | **28 @ 2.0%, 28/28** — or **29 @ 4.3%, 28/29** with the revised row held in place |
| Unfitted module reconstructions | 24 @ 72.1% / 40.0% median | **26 @ 61.8% / 38.0%** (**63.6%** over the pre-L8 24 rows) |
| — sectoral presets | 12 @ 104.8% / 40.0% median | **14 @ 81.0% / 38.0%** (**87.8% / 32.3%** over the 12) |
| — 8 P.L. 119-21 line items | 35.8% | **unchanged** |
| — 3 capital-gains scenarios | 39.6% | **unchanged** |
| Calibrated, leave-one-out | 17 derivable @ 32.3% / 19.2% median / 8 within 15 | **18 derivable @ 28.4% / 16.5% / 9** (**29.5%** over the 17) |
| — `Credits` | 45.1% | **20.5%** |
| — `Expenditures` | 4 cases @ 28.8% | **5 cases @ 30.2%** |
| Not cross-validatable | 5 | **4** — `eliminate_salt` left the excluded set and re-entered the derivable one |
| Distributional (7 tables) | 0.00–5.86pp | **0.00–7.77pp** (ARP 4.76 → **7.77**) |
| Scorecard rows | 79 (72 published) | **80 (73 published)** |
| `revised_target_entries` | 2 | **3** |
| CBO Options battery | 14 alternatives / 11 options / 65 excluded / 3 leakage | **15 / 12 / 64 / 2** |
| Tier 1 CI gate | `--max-mean-error 40 --min-within-25pct 17` | **`40 / 18`** |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt56_employer_health_income_only` (Tier 1, **new**) | −$697.0B | — | **−$529.9B** | — → **24.0%** |
| `fdii_repeal` (Tier 2b) | −$200.0B | −$170.0B | **−$110.7B** | 15.0% → **44.65%** |
| `biden_full_international` (Tier 2b) | −$700.0B | −$413.0B | **−$353.7B** | 41.0% → **49.47%** |
| `trump_universal_10` (fitted → Tier 2b) | −$2,000.0B | −$2,021.6B | **−$1,258.5B** | 1.1% → **37.1%** |
| `trump_china_60` (fitted → Tier 2b) | −$500.0B | −$531.1B | **−$278.4B** | 6.2% → **44.3%** |
| `auto_tariff_25` (Tier 2b) | −$100.0B | −$252.3B | **−$182.2B** | 152.3% → **82.2%** |
| `steel_tariff_25` (Tier 2b) | −$60.0B | −$103.9B | **−$52.9B** | 73.2% → **11.9%** |
| `reciprocal_tariffs` (Tier 2b) | −$1,200.0B | −$2,736.0B | **−$1,396.8B** | 128.0% → **16.4%** |
| `biden_ctc_2021` (LOO) | +$1,600.0B | +$574.1B | **+$1,528.5B** | −64.1% → **−4.5%** |
| `ctc_extension` (LOO) | +$600.0B | +$432.0B | **+$714.2B** | −28.0% → **+19.0%** |
| `biden_eitc_childless` (LOO) | +$178.0B | +$101.2B | **+$110.4B** | −43.1% → **−38.0%** |
| `eliminate_salt` (LOO, **readmitted**) | −$1,200.0B | *excluded* | **−$1,077.9B** | — → **+10.2%** |
| `repeal_salt_cap` (LOO) | +$1,100.0B | +$1,144.0B | **+$777.0B** | +4.0% → **−29.4%** |
| ARP refundable credits (distributional) | — | 4.76pp | **7.77pp** | worse, and the more correct configuration |

- **L9 (PR #98): the double count the plan named does not exist.** The module's
  UTPR reads profits of foreign-parented groups and its GILTI reads US-parented
  CFC income, so the new `_estimate_base_overlap()` term nets **exactly zero**
  for every shipped factory. What it establishes instead is algebra: with an 80%
  foreign tax credit, a per-country GILTI at 21% claims more than a 15% top-up in
  every jurisdiction, so a policy carrying both raises the larger, never the sum —
  and at 2026's statutory 13.125% the shared-claim share is 0.9916, not 1, so a
  constant would have got one case right and the other wrong. The **FDII
  identity** replaced a flat $20B/yr with Treasury OTA's published $130,230M
  cost, moving the row toward the document and away from a target 54% above it;
  both regressions were pre-registered and landed to two decimal places. The
  package's real residual is a **level**: a $15B UTPR against Treasury's own
  $136,313M row and JCT's implied $133.9B.
- **L8 (PR #99): tariff scores are net, not gross, and every shipped preset
  moved.** `estimate_static_revenue_effect` had no income-and-payroll offset at
  all. It now subtracts duty avoidance, the ~25% offset CBO/JCT/Treasury apply to
  any indirect tax, and the receipts lost to retaliation, on Census 2024 levels,
  a tax-inclusive rate and a border pass-through frozen at 1.00. **The five
  presets moved 28–49%**, with a caption computed from the scored result shipping
  in the same PR under owner Decision 6. Two fitted coverage constants were
  re-derived or deleted, so no `TRADE_BASELINE` constant is fitted to any target
  and both Trump rows left the fitted tier. The lane also found and fixed a **sign
  defect**: `estimate_behavioral_offset` returned an unsigned positive number, so
  a 5pp tariff *cut* on a $1,000B base scored $711B of deficit against a $553B
  gross revenue loss; signed, the same cut scores $394B. No shipped preset moves
  on that fix — all five are increases.
- **L3 (PR #101): credits are computed per unit over CPS ASEC tax units.** Two
  statutory parameter sets run through `MicroTaxCalculator` and differenced on
  final liability, in place of `Δcredit × units × participation`. The largest
  single correction is a **counterfactual**, not a parameter: IRC §24's $2,000
  reverts to $1,000 after 2025, so a window opening in 2025 is scored against
  current law for one year and the pre-TCJA regime for nine — $883B against a
  fixed baseline, **$1,528B** against the one the statute specifies. Three dead
  levers now have readers, and the engine's EITC qualifying-child count moved
  from the CTC's under-17 column to IRC §32(c)(3)'s definition (**79.7M against
  65.0M**). Per owner **Decision 4** the raw 148 MB March 2024 ASEC archive is
  fetched by `scripts/fetch_cps_asec.py` (SHA-256 verified) into a cache outside
  the repository and never vendored; five dependent age bands were added and
  every pre-existing column comes back byte-identical, with the SOI ratios
  (119% / 81%) unmoved. Per **Decision 5** the three tautological credit
  benchmarks carry a per-case declaration. **The ARP distributional benchmark got
  worse, 4.76pp → 7.77pp**, and that is the finding: the old figure ranked one of
  three components by IRS return counts and the other two by CPS tax units, and
  the two universes were partly cancelling. Scored consistently the quintile
  dollar levels move from about a third of CBO's to close to them and the bundle
  totals $485B, within 10% of the three provisions' actual cost, while the share
  error grows because the model's bottom quintile is 38.2M tax units against
  CBO's ~26M households.
- **PR #100: five targets, five judgements, one modelling change.** **CBO Option
  56 promoted into Tier 1** at −$529.9B against −$697.0B (24.0%) — a leakage
  exclusion is not permanent, and L6 had removed the fitted annual its only path
  ran through; only CBO's third alternative is scored, because 56.3 and 56.6 need
  a payroll base the module does not have. **Pillar Two re-benchmarked as a
  published range**, [−$102.6B, +$56.5B] from JCX-22-23 Table 2, with the model
  **inside** it at distance $0.0B — the ledger gained `is_range`, `contains()`
  and `distance_to_range()`, and the scorecard and API gained
  `published_range_low_billions` / `..._high_billions` / `within_published_range`
  / `distance_to_published_range_billions`. **The leaked SALT constant replaced by
  its computation**: `annual_cost_no_cap = 120.0` was exactly the `eliminate_salt`
  target over ten and is now **$89.55B** from IRS SOI Table 2.1 priced at the
  statutory schedule, checked by the identical computation on the *limited* column
  returning $25.0B against the record's own 25.0. **The estate target examined and
  deliberately not moved**, under a new `EXAMINED_NOT_REVISED` state, because
  JCT's −$429.6B totals a ten-section bill the module does not construct. **The
  Treasury FY2022 combined-row reading confirmed**, not superseded.
- **PR #102: the Tier 1 CI gate re-derived by the workflow's own rule** after the
  battery grew — ceiling `ceil(31.0 × 1.25) = 39 → 40`, unchanged; floor
  `19 − 1 = 18`, a tightening from 17.
- **Nothing else a user sees changed.** Every Wave 3 module keeps `reported` as
  its app default under owner Decision 1 (credits: 0.0% reported against 20.5%
  derived — read with Decision 5 in hand, since the fitted annuals *are* their
  targets over ten). No target moved from a modelling branch, no CI threshold was
  touched by a lane, no per-benchmark constant was added, and two were deleted.

### Modelling Wave 2 — estate distribution, tax-expenditure units, capital gains (2026-09-02)

Wave 2 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md),
three lanes on disjoint files. Every lane pre-registered its expected movement in
`planning/lanes/` **before** touching code; §5.2 of the plan carries the outturn,
the four findings and the three missed bands. PRs **#93** (L4 estate), **#94**
(L6 tax expenditures), **#95** (L1 capital gains).

**Validation tiers moved. Report them separately, as always:**

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered (n=25) | 34.4% / 16.1% median / 12 within 15 / 16 within 25 | **31.3% / 14.1% / 13 / 18** |
| Calibrated, fitted | 33 @ 2.8%, 32/33 within 15 | **30 @ 2.2%, 30/30** — or **31 @ 4.2%, 30/31** with the revised row held in place |
| Unfitted module reconstructions | 21 @ 76.7% / 41.0% median | **24 @ 72.1% / 40.0%** |
| — 12 sectoral presets | 104.8% / 40.0% median | **unchanged** |
| — 8 P.L. 119-21 line items | 35.8% | **unchanged** |
| — 3 capital-gains scenarios | *(in the fitted tier)* | **39.6%** |
| Calibrated, leave-one-out | 18 derivable @ 58.7% / 32.5% median / 6 within 15 | **17 derivable @ 32.3% / 19.2% / 8** |
| — `CapitalGains` | 171.2% | **39.6%** |
| — `Estate` | 25.8% | **10.4%** |
| — `Expenditures` | 5 cases @ 39.4% | **4 cases @ 28.8%** |
| Not cross-validatable | 4 | **5** (`eliminate_salt` joined) |
| Distributional (7 tables) | 0.00–5.86pp | **unchanged** |
| Tier 1 error mass | 859.5 | **781.8** (capital gains 479.4 → **405.6**) |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt51_gains_at_death` (Tier 1) | −$536.1B | −$83.7B | **−$581.2B** | 84.4% → **8.4%** |
| `cbo_opt47_ltcg_qdiv_2pp` (Tier 1) | −$103.3B | −$205.7B | **−$57.1B** | 99.1% → **44.8%** |
| `biden_capital_gains_39` (Tier 1) | −$288.6B | −$699.4B | −$678.1B | 142.3% → **134.9%** |
| `treasury_capgains_39_plus_stepup_elim` (Tier 1) | −$322.0B | −$816.6B | **−$1,022.3B** | 153.6% → **217.5%** |
| `cbo_opt45_top4_brackets_2pp` (Tier 1) | −$569.5B | −$716.4B | −$671.6B | 25.8% → **17.9%** |
| `illustrative_1pp_all` (Tier 1) | −$960.0B | −$935.4B | −$920.3B | 2.6% → 4.1% |
| `cbo_opt45_all_rates_1pp` (Tier 1) | −$1,185.3B | −$935.4B | −$920.3B | 21.1% → 22.4% |
| `biden_high_income_tax` (Tier 1) | −$252.0B | −$284.5B | −$216.5B | 12.9% → 14.1% |
| `cbo_2pp_all_brackets` (LOO) | −$70.0B | −$154.3B | **−$79.8B** | −120.5% → **−14.0%** |
| `pwbm_39_with_stepup` (LOO) | +$33.0B | −$89.3B | **+$23.6B** | −370.5% → **−28.4%**, sign restored |
| `pwbm_39_no_stepup` (LOO) | −$113.0B | −$138.6B | −$26.6B | −22.6% → **+76.5%** |
| `biden_estate_reform` (LOO) | −$450.0B | −$244.9B | **−$457.2B** | +45.6% → **−1.6%** |
| `extend_tcja_exemption` (LOO) | +$167.0B | +$176.9B | +$199.0B | +6.0% → **+19.2%** |
| `cap_employer_health` (LOO) | −$450.0B | −$11.5B | −$30.5B | +97.4% → **+93.2%** |
| `cap_charitable` (LOO) | −$200.0B | −$168.5B | −$173.8B | +15.7% → **+13.1%** |
| `eliminate_salt` (LOO) | −$1,200.0B | −$300.9B | −$1,444.4B | +74.9% → **excluded** (−10.9% against the published −$1,621.0B) |

- **L1 (PR #95) found a fifth defect under the plan's four, and it was a unit
  error.** Realization elasticities were applied as **net-of-tax-rate**
  elasticities where CRS R48562 defines them on the **tax rate** (semi-log,
  `R = B·exp(−b·t)`, so `ε = b·t`), which made the frozen 0.8 an effective
  **0.25**. Dowd–McClelland–Muthitacharoen's 0.72 at CRS's 22% reference rate
  gives **b = 3.273** against **JCT's own 3.1** and a revenue-maximizing rate of
  30.6% — so 43.4% sits past the peak and the model reproduces PWBM's
  revenue-*loss* finding with no multiplier at all. The 5.3× lock-in multiplier,
  the residual-avoidance multiplier and `fiscal_model/validation/scenarios.py`'s three
  per-case tuples are **deleted**. The base is now IRS SOI Table 3.5's
  bracket-priced income ($1,107.7B in five buckets, not $1,368B at a blended
  15.5%); lock-in is a derived **1.44×** price wedge from an accrued-gains stock;
  gains at death are **$196.2B in 2025 growing 5.8%/yr** across five estate-size
  classes, not a flat $54B/yr. **Tailor's capital-gains form loses its lock-in
  slider**, its short/long-run elasticity pair, its transition slider and its
  gains-at-death input, and gains persistent/transitory elasticity inputs; its
  scored outputs move (a +2pp all-brackets change goes −$219.2B → −$56.4B). No
  preset moved. What is left undone is the **death channel's behavioural
  response** — no spousal or charitable carve-out, no §121 residence exclusion,
  no family-business deferral — which is the entire residual on the two Treasury
  rows, and the realizations base is still not projected across the window.
- **L4 (PR #93) replaced an estate blend that was *exactly invariant* in the
  exemption.** For any `E ≤ $6.4M` the old machinery's count × average product
  was constant, so lowering the exemption derived **zero** revenue — and the app
  scored "cut the estate exemption to $3.5M" as free. A Pareto size distribution
  of the estate tax base (α = **1.73843**, pooled from seven local estimates
  inside IRS SOI Estate Tax Statistics Table 1 for filing years 2010, 2013 and
  2024) replaces eight fitted constants, anchored on SOI's own FY2024 row and
  lagged one year because a Form 706 is filed the year after death (IRC
  §6075(a)). `create_estate_exemption_change(3.5e6)` now returns **+$35.4B/yr**.
  The extension row got *worse* (+6.0% → +19.2%) because its old 6% was a
  four-times-too-high level cancelling against a zero exemption response, and
  because the object that grows is the distribution rather than revenue. The
  **growth rate is unresolved**: SOI-fitted 6.81%/yr reproduces history but
  projects to figures no published estate estimate supports, so the module ships
  nominal GDP growth (3.82%) and over-states historical collections by 109% on
  2009 decedents; the choice is pinned by a test. Portability/DSUE and the
  graduated rate schedule remain unmodelled, and
  `create_warren_estate_proposal`'s fitted −$2,600B derives at **−$663.6B**
  because PWBM's figure scores a package with a separate wealth tax.
- **L6 (PR #94) made every cap declare its unit, and the leakage guard fired.**
  `CapUnit` distinguishes `BASE_DOLLARS`, `BENEFIT_RATE` and `BENEFIT_DOLLARS`,
  and each expenditure gained a benefit distribution by AGI class from IRS SOI
  Table 2.1 (`jct.gov` returns HTTP 403 to this environment on every URL; SOI is
  the administrative source under JCT's own tables and separates *total* from
  *limited* SALT). Making `eliminate` read `annual_cost_no_cap = 120.0` then
  tripped `loo.py`'s **untouched** leakage guard, because $120.0B is exactly the
  carried −$1,200B target over ten: the case is now not cross-validatable, and
  **part of the LOO improvement is that case leaving the denominator** — 31.7%
  like-for-like over 18 against the printed 32.3% over 17. SOI × statute puts the
  uncapped SALT deduction at **$89.6B/yr**, 25% below the record's $120.0B, while
  reproducing the *capped* $25.0B to a tenth of a percent. `cap_employer_health`
  moved only 4pp because **a $50,000 premium cap is above the entire
  distribution** (CBO's own 75th-percentile family premium is $31,300; the
  carried −$450B corresponds to a cap near **$26,400**) — a miss pre-registered
  before the code was written. **CBO Option 56 is now scorable**: +2.5% in its
  own first year, −12.8% with a year-indexed excess share; not yet promoted.
- **The three capital-gains scenarios left the fitted tier**, because deleting
  the per-case tuples removed the only constants ever fitted to them, so
  `calibrated_to_target` is now `False` and the runner says so. The fitted mean
  *fell* 2.8% → 2.2% while nothing regressed — those rows were what the tier had
  been carrying, and left in place they would have raised it to 6.2%. That is
  **composition, not accuracy**; read it next to the reconstruction tier or not
  at all. `run_loo.py --donor-matrix` now prints three identical rows: there is
  no donor left to be an answer key.
- **Every Wave 2 module keeps `reported` as the app default** under owner
  Decision 1 (estate 0.0% reported against 19.2% / −1.6% / +34.7% derived;
  expenditures 4.2% reported against 26.0% derived), so **no shipped preset
  moved**. `check_readiness.py`'s `holdout_protocol` check went PASS → **WARN**
  rather than FAIL: `pwbm_39_with_stepup` is a locked holdout id that now rates
  Poor with the direction right, and the repository's existing rule — a Poor
  entry carrying a documented `known_limitations` note on a benchmark the module
  is *not* fitted to is a warning — now applies to the holdout check on the same
  terms. The entry stays in the battery. Re-locking the protocol instead is an
  open owner decision, listed with five others in §6.1 of the plan.

### Tier 1 CI gate tightened to 40 / 17 (2026-09-02)

PR **#96**. The out-of-sample gate's own rule — ceiling = `ceil(mean × 1.25)`
rounded up to the nearest 5, floor = the current count within 25% minus one —
derives **40 / 17** from the post-Wave-2 battery (25 cases, 31.3% mean, 18 within
25%), against the **45 / 15** the workflow carried after Wave 1. A tightening,
which the rule says needs no reason. The derivation is recorded in the workflow
comment beside the earlier ones, and the places that quote the command now match.

### Tier-2 target revisions, and a supersede rule for the calibrated tier (2026-09-02)

PR **#90**. Two modelling lanes had referred *target* problems out of Wave 1:
L5 (`amt.py`) found its structural path landing about 1.8× closer to the document
than its fitted constant but could only say so, because the carried target
disagreed with the document; L7 (`pharma.py`) fixed an incidence bug and was
rewarded with a *worse* percentage, because its benchmark pointed the opposite
way. **No modelling change**: no constant retuned, no mechanism altered, no CI
threshold touched.

The calibrated tier had no supersede rule, so this adds the smallest mirror of
`preregistered.py`'s — `fiscal_model/validation/target_revisions.py`. The old
figure stays as a row marked `superseded_by`; the new row carries document,
table, row, page, date and a reason; `target_revision_problems()` fails if the
ledger and the registries the app reads ever disagree. Ledger entry and first
scoring are separate commits, so "the target moved before the model was allowed
to see it" is checkable from `git log`.

| Benchmark | Was | Is | Document |
|---|--:|--:|---|
| `extend_tcja_amt` | $450.0B | **$1,357.1B** | CRS **R48286** Table 1 (transcribing CBO 60114/60271) — "Increased Alternative Minimum Tax Exemption", FY2025–FY2034. The adjacent five-year column prints $466.2B, so $450B was 3.5% from the five-year cost and 66.8% from the ten-year one: a five-year figure in a ten-year column. Corroborated by JCT **JCX-35-25** at $1,362.810B (0.4% away) for P.L. 119-21's AMT provision. |
| `universal_insulin_cap` | −$15.0B (a saving) | **+$11.4B (a cost)** | CBO pub. **57957** (H.R. 6833), table p. 1 — outlays 6,566, revenues −4,793, FY2022–2031. A $35 monthly cap is a *cost-sharing* cap: it moves liability onto the plan and onto the federal subsidy for it. |
| `repeal_individual_amt` | $450.0B | **not moved** | Nothing to move it to — see below. |

**The tiers moved; report them separately, as always.**

| Tier | Before this PR | After |
|---|---|---|
| Out-of-sample, pre-registered (n=25) | 34.4% / 16.1% median / 12 within 15 / 16 within 25 | **unchanged** |
| Calibrated, fitted | 34 @ 2.7%, 33/34 within 15 | **33 @ 2.8%, 32/33** — or **34 @ 4.7%, 32/34** held in place |
| Unfitted module reconstructions | 20 @ 82.6% / 43.1% median | **21 @ 76.7% / 41.0%** |
| — 12 sectoral presets | 113.8% / 57.1% median | **104.8% / 40.0%** |
| Calibrated, leave-one-out | 18 @ 61.7% / 35.6% median | **18 @ 58.7% / 32.5%** |
| Calibrated provenance | 17 `line_item` / 15 `differs` / 15 `secondhand` / 7 `model_estimate` | **19 / 13 / 15 / 7** |
| Sectoral rows disagreeing with their target on **sign** | 1 | **0** |

- **A revised row leaves the fitted tier, and the summary says so.** A constant
  fitted to a superseded figure is not fitted to its replacement, so
  `scorecard.py` derives `calibrated_to_target` from the ledger and
  `extend_tcja_amt` reports among the unfitted reconstructions, where a miss is a
  finding rather than a regression. `ScorecardSummary.revised_target_entries`
  (= **2**) is on the scorecard and on `/validation/scorecard`, so the move can
  never be silent. **Quote "33 at 2.8%" only next to the statement that a 34th
  row moved out**, and never retune the constant to close the 66.8% — that is the
  move a provenance pass is forbidden to make.
- **The LOO fall is a target moving, not a model.** `extend_tcja_amt`'s held-out
  derivation is **unchanged at $855.3B**; its error against the corrected row is
  −37.0% instead of +90.1%, taking the AMT module 100.5% → 73.9% and the suite
  61.7% → 58.7%. No donor-matrix entry moved.
- **`KNOWN_TARGET_SIGN_INVERSIONS` is now an empty set**, and the emptiness is
  the assertion: no scorecard row disagrees with its own target about what a
  policy does.
- **`AMT_APP_MODE` and `AMT_SCORECARD_MODE` stay `reported`.** Across the three
  AMT benchmarks reported means **22.3%** against derived's **54.2%**, which is
  owner Decision 1's own rule, so **no shipped number changes**. Read past the
  mean: both rows on which derived loses are targets a constant was fitted to, so their
  ~0% is bookkeeping — and the one AMT benchmark no constant was fitted to is the
  one derived wins, 37.0% against 66.8%.
- **`repeal_individual_amt` keeps an unsourced, internally incoherent target.**
  No published post-2025 repeal score exists at JCT, CBO or TPC. TPC T25-0049's
  $948.9B is deliberately not adopted: it is a baseline projection rather than a
  scored repeal, *and* it is `amt.py`'s own input, so adopting it would
  manufacture a 0% row out of the leakage `loo.py` guards against. Closing it
  needs a published score or an owner decision to re-register `holdout.py`'s
  locked `revenue-scorecard-post-lock-2026-05-02` protocol — which has no
  re-registration path. `check_readiness.py --strict` is unchanged from the base
  commit.
- **Two user-facing labels moved with their targets** (slugs unchanged, so no
  share link breaks): `⚖️ AMT: Extend TCJA Relief ($450B)` → `($1.36T)`, and
  `💊 Universal Insulin Cap (-$15B)` → `($11B)`. `/validation/scorecard` and the
  Validation tab now carry `target_revision_id`, `superseded_10yr_billions`,
  `target_revision_reason` per entry and a "Target moved from" column.

### Tier 1 CI gate tightened to 45 / 15 (2026-09-02)

PR **#91**. The out-of-sample gate's own rule — ceiling = `ceil(mean × 1.25)`
rounded up to the nearest 5, floor = the current count within 25% minus one —
derives **45 / 15** from the post-Wave-1 battery (25 cases, 34.4% mean, 16 within
25%), against the **55 / 13** the workflow carried. Both are tightenings, which
the rule says need no reason. The derivation is recorded in the workflow comment
beside the earlier ones, and the places that quote the command now match.

### Modelling Wave 1 — spend-out, AMT, pharma incidence (2026-09-02)

Wave 1 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md),
three lanes on disjoint files plus a follow-up, with the owner's six §6 decisions
recorded first. Every lane pre-registered its expected movement in
`planning/lanes/` **before** touching code; §5.1 of the plan carries the outturn
and the three findings. PRs **#83** (decisions), **#85** (L2 spend-out),
**#86** (L5 AMT), **#87** (L7 pharma), **#88** (IIJA authorization path + app
spend-out).

**Validation tiers moved. Report them separately, as always:**

| Tier | n | Before | After |
|---|--:|---|---|
| Out-of-sample, pre-registered | 25 | 52.6% mean / 21.1% median / 8 within 15 / 14 within 25 | **34.4% / 16.1% / 12 / 16** |
| Calibrated, fitted | 34 | 2.7% / 33 within 15 | **unchanged** |
| Unfitted module reconstructions | 20 | 250.8% / 43.1% median | **82.6% / 43.1%** |
| — 12 sectoral presets | 12 | 394.1% / 57.1% median | **113.8% / 57.1%** |
| — 8 P.L. 119-21 line items | 8 | 35.8% | **unchanged** |
| Calibrated, leave-one-out | 18 | 59.3% / 35.6% median / 6 within 15 | **61.7% / 35.6% / 6** |
| Distributional | 7 | 0.00–5.86pp | **unchanged** |

*Two of these Tier 2 figures moved again the same day, in the target-revision
entry above; the numbers here are Wave 1's outturn, not the current ones.*

- **Budget authority and outlays are now distinct quantities (L2).**
  `SpendingPolicy` no longer books a funding level straight into outlays;
  `outlays_t = Σ_k s_k · BA_{t−k}`, with `s` an account-class profile fitted by
  non-negative least squares on the 14 CBO options that publish both an
  authority row and an outlays row **and are not scored by the battery**. The
  five scored options never donate. Class assignment is a classification from
  the account type each program funds, never a fit. **Finding:** owner Decision
  2 named OMB Circular A-11 §32 as the primary source; A-11 §32 is personnel
  compensation and A-11 publishes **no** outlay-rate table in any section, so
  the decision's own fallback governed and the CBO donor options shipped as
  primary. CBO's account-level rates (publications 61913, 62256) are the open
  cross-check, blocked by cbo.gov 403s.
- **IIJA is scored on the schedule its source states (#88).** The shape input
  was superseded under the manifest's own rule — a **new row**, never an edit —
  in two commits, entry before scoring. `iija_2021_discretionary.v1` stays on
  the record (+$1,894B, 356%; +$1,621B, 290.2% after spend-out); `.v2` carries
  CBO's own authorization path and scores **+$340.0B against an unchanged
  +$415.4B target, 18.2%**. What remains is a window mismatch: $92.6B of the
  path's outlays fall in FY2022-2024, before the model's FY2025-2034 window
  opens. Earlier docs saying IIJA "is kept at 356% deliberately, as the sharpest
  evidence for the missing spend-out model" are now history on both halves.
- **The Fiscal Responsibility Act row got worse, as pre-registered** (5.8% →
  12.2%). The old figure was two errors cancelling; a correct spend-out removes
  one and leaves the other, so the total error rises while the path gets more
  right.
- **AMT gained a live exemption branch and a published year-indexed path (L5).**
  The exemption-change branch had been dead code, so no exemption change had
  ever been scored. The path is TPC Table T25-0049, transcribed to
  `fiscal_model/data_files/amt/`. **Finding:** the plan's "missing 2026 ramp"
  hypothesis was **wrong** — T25-0049 shows a *cliff* (0.2M → 7.6M AMT payers,
  2025 → 2026) and then *growth* ($71.6B → $124.2B by 2035), so the flat
  ~$73B/yr was the window's early-year level and indexing it **raises** the
  score. Both AMT LOO rows moved away from their carried $450B targets (+73.2%
  → +90.1%, +86.0% → +110.9%) while the extension moved *toward* the published
  line item ($1,357.1B: −66.8% fitted → **−37.0%** derived). **App default stays
  `reported`**; nothing a user sees changed. `docs/VALIDATION_NOTES.md` §6 was
  corrected rather than deleted.
- **Drug pricing now scores federal incidence (L7).** A $35 insulin cap is a
  cost-sharing cap, so the federal budget picks up only its share of the
  liability shift; and international reference pricing is scored on a net-price,
  brand-only, federal-share basis (US unbranded generics are *cheaper* than the
  OECD comparison and cannot contribute savings). Every input is transcribed
  with document, page and URL to
  `fiscal_model/data_files/pharma/drug_pricing_incidence.csv`. No parameter was
  fitted to any of the three pharma benchmarks. **Still unrepaired:** RAND's
  index is computed on presentations sold in both markets and the module applies
  it to all brand spending; no utilisation, launch-delay or availability
  response is modelled on either row.

**Shipped preset numbers moved.** No preset label and no `CBO_SCORE_MAP` entry
changed — labels carry the official score or an annual funding level, not the
model's ten-year total.

| Preset | Before | After |
|---|--:|--:|
| 💊 Universal Insulin Cap | −$445.3B | **+$7.0B** |
| 💊 International Reference Pricing | −$1,387.9B | **−$746.2B** |
| 💊 Comprehensive Drug Reform | −$1,025.8B | **−$573.5B** |
| 💊 Expand Drug Negotiation | −$371.5B | unchanged |

The insulin cap now reads as a deficit *increase*, which is what CBO scores for
the same policy (publication 57957, +$11.4B); the carried −$15B benchmark is the
thing still pointing the wrong way.

**Every spending program's 10-year outlays now follow a spend-out profile.** The
label still quotes the annual funding level, which is budget authority and is
unchanged; only the ten-year outlay total moved. Each score renders one line
naming its profile and its outlay/authority ratio, computed from the scored
result. `immediate` stays reachable under Economic parameters and is the default
for nothing.

| Program (Tailor) | Account class | 10-yr before | 10-yr after | outlay/authority |
|---|---|--:|--:|--:|
| Custom program | construction and capital | +$1,095.0B | **+$725.4B** | 0.663 |
| Infrastructure Investment ($100B/yr) | construction and capital | +$1,146.4B | **+$749.8B** | 0.654 |
| Defense Spending Increase (+10%) | operations and support | +$985.5B | **+$880.2B** | 0.893 |
| Universal Pre-K ($40B/yr) | grants and procurement | +$458.6B | **+$386.9B** | 0.844 |
| R&D Investment ($50B/yr) | grants and procurement | +$600.3B | **+$503.8B** | 0.839 |
| Discretionary Spending Cut (−$50B/yr) | operations and support | −$547.5B | **−$489.0B** | 0.893 |
| Disaster Relief ($30B one-time) | grants and procurement | +$30.0B | +$30.0B | 1.000 |
| Student Debt Forgiveness ($400B one-time) | benefit payments | +$400.0B | +$400.0B | 1.000 |
| Universal Childcare ($100B/yr) | grants and procurement | +$1,146.4B | **+$967.4B** | 0.844 |
| Medicare Buy-in Age 55+ ($50B/yr) | benefit payments | +$573.2B | **+$571.7B** | 0.997 |
| High-Speed Rail Program ($30B/yr) | construction and capital | +$328.5B | **+$217.6B** | 0.663 |

The two one-time programs are unchanged because their whole spend-out tail lands
inside the window — the timing moves, the total does not. Explore ships no
spending preset.

**Owner decisions recorded (#83).** All six of the plan's §6 questions were
answered on 2026-09-01: keep `reported` and `derived` modes; A-11 as the primary
spend-out source (superseded by finding 1 above, via the decision's own fallback
clause); freeze Dowd–McClelland–Muthitacharoen (2015) capital-gains elasticities;
fetch raw CPS ASEC by script rather than vendoring it; move the three
tautological credit benchmarks to documented exclusion; ship the tariff
gross→net change with its UI note.

**No yardstick was touched.** `preregistered.py`'s targets, `cold_holdout.py`,
`run_loo.py`, `loo.py`'s leakage guard, `tests/test_preregistration.py` and the
CI thresholds are all unchanged. The CI derivation rule now implies a ceiling of
45 and a floor of 15 against the workflow's current 55 and 13; both pass with
room and tightening them is left to whoever lands next. *(Done in PR #91, above.)*

### Documentation honesty sync (2026-09-01)

*Superseded on 2026-09-02 by the Wave 1 entry above: the tier figures below were
correct when written and are kept as the record of that change, not as current
numbers.*

- `docs/METHODOLOGY.md` now reports **four validation tiers separately** and
  states outright that there is no single "validated within X%" figure:
  out-of-sample pre-registered (25 cases, 52.6% mean / 21.1% median, 8/25 within
  15%, 14/25 within 25%), calibrated-and-fitted (34 at 2.7%), unfitted module
  reconstructions (20 at 250.8% mean / 43.1% median — 12 sectoral presets at
  394.1% plus 8 P.L. 119-21 line items at 35.8%), and calibrated leave-one-out
  (18 derivable at 59.3% mean / 35.6% median, 4 not cross-validatable). It
  previously carried a stale 23-case/43.4% Tier 1 and a "29 benchmarks ≈ 5%"
  Tier 2.
- **Step-up lock-in multiplier corrected.** METHODOLOGY printed `5.3×` as the
  current-law setting. The module default is **2.0**
  (`CapitalGainsPolicy.step_up_lock_in_multiplier`), and `5.3` is set only by
  the `pwbm_39_with_stepup` validation scenario, where it is fitted to reproduce
  PWBM's revenue loss. (Tests assert that scenario's value and the docs discuss
  it; those reference the same constant rather than adding uses of it.) The document now says which multiplier each
  published result was produced with, and records that the 5.3× is a known
  answer key (`run_loo.py --donor-matrix`), not a parameter.
- **Distributional claim replaced.** The two-line "vs. TPC TCJA analysis"
  summary is now the seven published CBO/JCT tables at 0.00-5.86pp, with the two
  circular ones (CBO 54796, CBO 60007) named as circular.
- **IRS SOI vintage.** METHODOLOGY contradicted itself on the tax-year basis; it
  now states that tax years 2021-2023 ship and production scoring runs on **tax
  year 2023**, and that tax-year (calendar) aggregates are carried into a
  fiscal-year window without conversion.
- `planning/MODELING_IMPROVEMENT.md` §2 error budget and §5 sequencing
  re-derived against the post-Phase-D/E battery; `planning/NEXT_STEPS.md` lost
  its "25+ policies validated within 15%" line.


### Ask assistant (May 2026)

- New **💬 Ask** tab (now the second top-level tab) and matching
  `POST /ask` + `POST /ask/stream` (Server-Sent Events) endpoints expose
  a citation-grounded Q&A assistant. Streams answers from Claude
  Sonnet 4.6 with tool access to the app's scoring engine, CBO baseline,
  validation scorecard, 49 preset policies, and 19 hand-curated
  authoritative snapshots covering CBO baseline, SSA Trustees, TCJA,
  capital gains, international tax, retirement-account taxation, IRA
  clean-energy credits, tariff scoring, JCT distributional methodology,
  fiscal multipliers, ETI literature, state/local fiscal interaction,
  debt sustainability, dynamic-scoring concepts, JCT tax expenditures,
  TPC TCJA distribution, PWBM TCJA dynamic, Yale Budget Lab tariffs,
  CBO long-term outlook, and a common-confusion FAQ.
- **Citation discipline is structural, not aspirational.** The model is
  required to emit `[^N]` footnote markers on every substantive claim.
  A post-processor cross-references each marker against the per-turn
  tool-call provenance log; unsupported markers are stripped and
  replaced with `[citation needed]`, surfacing as a defect to the
  reader.
- **Hard usage caps protect the deployer's API spend.** A sqlite-backed
  `assistant_events` ledger (also serves as the telemetry log)
  enforces a daily cost cap (`$5/day` default), per-session message
  cap (20), cool-down between messages (3s), and an
  `ASSISTANT_DISABLED` env-var kill switch. The same ledger is shared
  by the Streamlit tab and the FastAPI endpoints so a busy API caller
  cannot drain the UI budget.
- **Token-gated admin dashboard** (`💼 Admin` tab) shows today's spend
  vs. cap, KPIs (cache-hit ratio, error rate, avg cost/turn), the
  30-day daily-cost series, tool-usage frequency, and the recent-turn
  table — visible only when the URL has `?admin=<token>` matching
  `ASSISTANT_ADMIN_TOKEN`. Non-admins do not see the tab label.
- **Share-this-answer button.** Each assistant turn includes a 🔗 Share
  affordance that builds a URL containing the full Q+A+provenance as
  a gzip+base64 payload (no backend state). Recipients land on the Ask
  tab with the exact pair pre-rendered. SHARE_SCHEMA_VERSION makes
  future evolution graceful; MAX_DECODED_BYTES guards against
  decompression bombs.
- **Health/readiness wiring.** `/health` now carries an `assistant`
  component with three sub-signals (API key, knowledge corpus size,
  usage db reachability). The assistant is marked `required=False` in
  `/readiness` so a missing key on a CI runner or dev box reports as
  "degraded / warn" without blocking deploy. Older synthetic health
  payloads stay backward-compatible — the new check is skipped when
  the `assistant` key is absent.
- **Streamlit-Cloud secrets are auto-promoted to env vars** on first
  render. A Levenshtein-based typo detector surfaces near-miss key
  names (e.g., `ANTHROPHIC_API_KEY`) inline in the unavailable-key
  diagnostic. End users are never asked to enter an API key.
- **Latency tuning.** `DEFAULT_MAX_TOKENS` reduced from 1600 to 800.
  Follow-up question generation moved to a separate Streamlit rerun so
  it doesn't block answer finalization. Prompt cache pre-warms on a
  daemon thread at app boot so the first real turn skips the
  cache-creation tax. Typical turn: 5-7s, $0.01-$0.02.
- **Anti-spiral safeguards.** The agentic loop is capped at 4 tool
  iterations; on cap, a final tools-disabled call forces the model to
  write a real answer using whatever it has gathered. The system
  prompt explicitly budgets 2-3 tool calls per answer.
- **Dollar-sign KaTeX safety.** A post-processor escapes any unescaped
  `$` before a digit in rendered markdown so currency amounts never
  render as LaTeX math. The system prompt also instructs the model to
  emit `\$` directly.
- **Knowledge refresh script.** `scripts/refresh_knowledge.py` fetches
  any allowlisted authoritative URL through the same pipeline the
  runtime `fetch_url` tool uses (with `pdfplumber` for PDFs) and dumps
  a frontmatter'd stub for hand-summarization. Fails gracefully on
  bot-blocked domains (CBO, SSA) with a clear pointer to manual paste
  or live `web_search`.
- **Live smoke test.** `scripts/smoke_ask_assistant.py` runs three
  short questions through the real Anthropic API to verify the
  streaming tool-use loop, knowledge search, and citation discipline.
  ≈$0.04 per full run; supports `--only N` for single-scenario runs.
- 105 new tests across `tests/test_fiscal_assistant.py`,
  `tests/test_ask_api.py`, `tests/test_assistant_rate_limit.py`,
  `tests/test_assistant_admin.py`, `tests/test_assistant_share.py`,
  `tests/test_assistant_health.py`. All use mocked Anthropic clients;
  no API credit spent in CI.

### Operational readiness and CI telemetry

- `/health`, `/benchmarks`, `/summary`, and validation artifacts now expose
  flattened `issues` arrays with a shared status-issue shape for monitoring
  clients: `surface`, `severity`, `name`, `message`, and `details`.
- The Results Summary tab now renders a validation-evidence card beside each
  headline score, including calibrated category, benchmark count, observed
  error range, holdout status, and known caveats.
- CI smoke coverage now includes `scripts/check_streamlit_boot.py`, which
  starts the Streamlit app locally and verifies the calculator and
  classroom-mode routes serve the app shell.
- The FRED data layer now has a tracked bundled seed path between runtime cache
  and hardcoded fallback, so offline CI/deployments can build the baseline from
  a deterministic GDP seed instead of the IRS-ratio proxy.
- Bundled FRED seed data now carries a 120-day freshness contract, surfaces its
  age/max-age in health payloads, and degrades readiness when the seed ages out.
- Added `scripts/refresh_fred_seed.py` and a monthly `fred-seed-refresh`
  workflow so the tracked FRED seed is refreshed from live FRED with provenance
  and reviewed through a pull request before the 120-day window expires.
- The feasibility audit now emits a structured `model_pilot_assessment` with
  blockers/warnings and supports `--strict`, so implausible multi-model gaps
  stop the feasibility phase before UI expansion. The multi-model tab reuses
  the same assessment to flag pilot-quality blockers in the UI.
- PWBM-OLG is now excluded from the default multi-model pilot and kept behind
  `--include-experimental-pwbm` until its adapter clears the feasibility sanity
  bounds; the user-facing pilot defaults to the comparable CBO/TPC paths.
- The TPC microsim pilot now maps income-tax rate changes with thresholds to a
  taxable-income-above-threshold adjustment instead of collapsing every rate
  policy into a generic top-rate change.
- The model-pilot feasibility audit now uses the IRS-backed CBO-style scorer by
  default, with `--use-synthetic-cbo` retained for isolated diagnostics.
- The default TPC microsim pilot now applies SOI top-tail augmentation with
  metadata, reducing high-income threshold undercoverage while keeping
  `--no-top-tail-augmentation` available for CPS-only diagnostics.
- The experimental PWBM-OLG pilot now nets reform transitions against a
  no-reform OLG reference path and returns zero macro feedback when a policy
  does not map to an OLG parameter override, avoiding baseline transition drift
  being counted as a policy effect.
- The CPS microsim builder now emits explicit `investment_income` as interest,
  dividends, and capital gains, and the tracked `tax_microdata_2024.csv`
  artifact has been regenerated with that column.
- The release-readiness CLI now distinguishes real release blockers from
  expected offline data-environment warnings. `scripts/check_readiness.py
  --strict` still fails `not_ready` and non-environmental warnings, but it no
  longer blocks isolated CI runners solely because live FRED data or a warm
  FRED cache is unavailable.
- Validation and public-health scripts avoid `datetime.UTC` so the supported
  Python `3.10`-`3.13` matrix imports them consistently.

### API hardening

- Added opt-in API key auth via `X-API-Key` header, configured through the
  `FISCAL_API_KEYS` env var. Auth stays off by default so local launches and
  existing callers continue to work unchanged.
- Added a sliding-window rate limiter
  (`FISCAL_API_RATE_LIMIT_PER_MINUTE`, default 60; burst 20) keyed on API
  key label when auth is on and client IP otherwise. Returns `429` with
  `Retry-After: 60`.
- Every request now emits one structured JSON log line via the
  `fiscal_model.api_security` logger (path, method, status, duration,
  caller, key label).
- Wiring is in `fiscal_model/api_security.py`; tests in
  `tests/test_api_security.py`.

### Validation transparency

- New `docs/VALIDATION_NOTES.md` provides root-cause analysis for the three
  biggest validation outliers (SS donut hole 12.2%, Biden CTC 8.9%, Biden
  estate reform 10.1%). Each case documents the mechanical, data, and
  methodological causes with quantified fix paths.

### Test coverage

- New `tests/test_input_validation.py` (38 cases) covering invalid and
  malformed inputs distinct from the existing edge-case suite: structural
  invariants, parameter bounds, non-finite inputs, extreme-but-valid
  numerical robustness, and phase-in/sunset exact-boundary behavior.

### Dollar-escape + scoring unit fixes (April 2026)

- Converted remaining non-raw `"""..."""` tables in `methodology.py` to
  raw strings so bare `\$` no longer triggers `SyntaxWarning` under
  Python 3.12+.
- Removed the `/1e9` and sign-flip heuristic in the bill tracker's
  auto-scorer. `final_deficit_effect` is already in billions with the
  positive=deficit-increase convention used by `cbo_manual_scores.json`,
  so the heuristic was producing inconsistent signs and magnitudes.
- Added `_escape_dollars` helper in `classroom_app.py` to prevent
  Streamlit from rendering dollar amounts as LaTeX in assignment and
  exercise text.

## April 2026 — UI reorganization

### Progressive tab disclosure

The UI now separates primary analysis from advanced features. Previously a
single `st.tabs()` row of five tabs (one of which was a container with a
radio sub-selector) carried everything.

**Primary tabs** (always visible):

- 📊 Results Summary
- 👥 Distribution
- 🌍 Dynamic Scoring
- 📋 Detailed Results

**Advanced** (collapsible `st.expander("🔬 Advanced Analysis")`):

- 📈 Long-Run Growth
- ⚖️ Policy Comparison
- 📦 Package Builder
- 📖 Methodology

All eight tabs are mapped to a unified dictionary for
`render_result_tabs()`; there was no API change for callers.

### Export enhancements

The bottom of Results Summary now offers three export paths:

| Option          | Format           | Use case                                |
|-----------------|------------------|-----------------------------------------|
| CSV download    | Spreadsheet      | Excel, further processing               |
| Text download   | Plain text file  | Email, sharing as attachment            |
| Copy-paste block| Code block       | Direct paste into Word, Google Docs     |

The text summary includes the policy name, deficit impact, year-by-year
breakdown, assumptions, and data sources.

### Uncertainty bands + CBO comparison

Sensitivity bands (default: ETI ± 0.1) are rendered alongside the central
estimate on the Results Summary tab, with an in-line comparison against
the nearest published CBO/JCT score from the validation database.
`fiscal_model/ui/tabs/results_summary.py` is the entry point for this
rendering. The validation comparator is in
`fiscal_model/validation/cbo_scores.py`.

### Backwards compatibility

100% backwards compatible — no public-API change. Tests in
`tests/test_ui_controller_smoke.py` exercise both the old and new tab
paths.

## Earlier milestones

- **State-level modeling**: top 10 states with SALT cap interaction,
  combined federal + state effective rates.
- **OLG model**: 30-period Auerbach-Kotlikoff-style generational
  accounting for Social Security and Medicare reform
  (`fiscal_model/models/olg/`).
- **Classroom mode**: 7 interactive assignments, Laffer curve explorer,
  PDF export; launched with `streamlit run classroom_app.py`.
- **Real-time bill tracker**: pulls from congress.gov, extracts
  provisions via LLM, stores in SQLite (`bill_tracker/`).
- **Tariff scoring**: 5 presets (universal 10%, China 60%, autos 25%,
  reciprocal), consumer price impact by income quintile.
- **25+ validated policies** against CBO/JCT/Treasury scores; see
  `docs/VALIDATION.md` for the full matrix and
  `docs/VALIDATION_NOTES.md` for diagnostics on outliers.
