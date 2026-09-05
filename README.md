# Fiscal Policy Impact Calculator

[![Tests](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml/badge.svg)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)
[![Coverage Gate](https://img.shields.io/badge/coverage_gate-85%25-brightgreen)](https://github.com/laurencehw/fiscal-policy-calculator/actions/workflows/tests.yml)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fiscal-policy-calculator.streamlit.app)
![Python 3.10-3.13](https://img.shields.io/badge/Python-3.10--3.13-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Estimate the 10-year budgetary and economic effects of U.S. tax and spending proposals using CBO methodology, IRS data, and FRB/US-calibrated dynamic scoring.

**[Launch the app](https://fiscal-policy-calculator.streamlit.app)**

---

## What it does

The calculator scores fiscal policy proposals through a three-stage pipeline:

1. **Static scoring** — Direct revenue effect of rate/policy changes using IRS Statistics of Income data
2. **Behavioral adjustment** — Taxpayer response via the Elasticity of Taxable Income (ETI = 0.25, [Saez et al. 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf))
3. **Dynamic feedback** *(optional)* — GDP, employment, and interest rate effects using FRB/US-calibrated multipliers

### 49 pre-built proposals across 14 policy areas

| Category | Examples | Count |
|----------|----------|-------|
| TCJA / Individual | Full extension (+\$4.6T), rates only, no SALT cap | 4 |
| Income Tax | Progressive millionaire tax, middle-class tax cut, flat tax reform | 3 |
| Corporate | Biden 28% (-\$1.35T), Trump 15% | 2 |
| International Tax | GILTI reform, FDII repeal, Pillar Two, Biden package | 4 |
| Tax Credits | Biden CTC (\$1.6T), EITC expansion | 3 |
| Estate Tax | TCJA extension, Biden reform, full repeal | 3 |
| Payroll / SS | Donut hole, eliminate cap, expand NIIT | 4 |
| AMT | Extend TCJA relief, repeal individual/corporate | 3 |
| ACA / Healthcare | Extend enhanced PTCs, repeal all PTCs | 2 |
| Tax Expenditures | SALT cap, employer health, step-up basis, charitable | 4 |
| IRS Enforcement | IRA funding, double enforcement, high-income targeting | 3 |
| Drug Pricing | Expanded negotiation, insulin cap, reference pricing | 4 |
| Trade / Tariffs | Universal 10%, China 60%, autos 25%, steel and aluminium 25%, reciprocal tariffs | 5 |
| Climate / Energy | IRA repeal, carbon tax paths, methane fee repeal | 5 |

Plus fully custom policy design with adjustable parameters.

### Navigation and URLs

The app is verb-first and multipage — **Ask · Build · Tailor · Explore · More ▾**
in a top nav, with no global sidebar. Every page is addressable, so any view can
be linked, bookmarked, or pasted into a document:

| Page | URL | What it does |
|------|-----|--------------|
| **Ask** | `/` · `/?q=<question>` | landing page: ask a public-finance question, or step through to a doorway |
| **Build** | `/build?values=<archetype>` · `?vector=<b64>` · `?policies=<ids>` | start from your values (5 archetypes or free text) or straight from the policy checklist |
| **Tailor** | `/tailor?type=income&rate=2&who=top400k&phase=1&run=1` | set the parameters yourself; `who` takes an enum or a bare amount |
| **Explore** | `/explore?preset=<id>&dynamic=1&run=1` | score a catalog proposal |
| **More ▾** | `/tracker` · `/methodology` · `/classroom` · `/about` | bill tracker, methodology, classroom mode, and who made this and how to read it |

Share links additionally stamp `baseline=<vintage>`, `spec=<policy hash>` and
`mode=conventional|dynamic`, so a link says which baseline and which run
produced its numbers. Older links — including the pre-redesign
`?analysis=preset&preset=<label>&run=1` form — are rewritten transparently.
Data Status and Model settings live in popovers in the shared page chrome; on
phones the top nav collapses into a sidebar toggle.

### Additional features

- **💬 Ask assistant** — Citation-grounded Q&A about public finance and this model's outputs. Streams answers from Claude Sonnet 4.6 with tool access to the app's scoring engine, CBO baseline, validation scorecard, and 23 curated authoritative snapshots (CBO, JCT, PWBM, Yale Budget Lab, TPC, PGPF, BEA, BLS, SSA Trustees, FRED). Every substantive claim carries a `[^N]` footnote cross-referenced against the tool-call provenance; unsupported markers are auto-stripped. Hard daily cost cap ($5/day default across all visitors), per-session message cap, cool-down, and kill-switch protect the deployer's API budget. Available as a Streamlit tab, a non-streaming `POST /ask` endpoint, and an SSE `POST /ask/stream` endpoint.
- **Tariff scoring** — 5 presets (universal 10%, China 60%, autos 25%, steel and aluminium 25%, reciprocal), consumer price impact by income quintile. Since Wave 3 the headline is **net**, not gross customs duty: it subtracts duty avoidance, the ~25% income-and-payroll offset CBO, JCT and Treasury apply to any indirect tax, and the receipts lost to retaliation. Net/gross runs 0.60-0.66 across the five presets, every one of them moved 28-49%, and a caption computed from the scored result says so under the number.
- **State-level modeling** — Combined federal + state effective rates for top 10 states, with SALT cap interaction
- **OLG model** — 30-period Auerbach-Kotlikoff-style generational accounting for Social Security and Medicare reform
- **Classroom Mode** — 7 interactive assignments (intro → advanced), Laffer curve explorer, PDF export; accessible at `streamlit run classroom_app.py`
- **Real-Time Bill Tracker** — Pulls active bills from congress.gov, extracts fiscal provisions via LLM, stores in SQLite
- **Shareable preset links** — Generate deep links for supported preset tax proposals and preset spending programs directly from the results tab; custom policies still fall back to export-only
- **Shareable Ask answers** — Each assistant turn has a 🔗 Share button that generates a self-contained URL (gzip+base64 encoded payload, no backend state required) so recipients see the exact Q+A on open
- **Admin dashboard for Ask usage** — Token-gated `💼 Admin` tab (URL `?admin=<token>` matching `ASSISTANT_ADMIN_TOKEN`) surfaces today's spend, 30-day cost/turn series, tool-usage frequency, cache-hit ratio, and recent-turns table read live from the `assistant_events` sqlite ledger
- **Result-level validation evidence** — Each standard result summary surfaces the calibrated category, benchmark count, observed error band, holdout status, and known caveats before users interpret the headline score

### Model maturity

This project is a **validated scoring core with experimental interfaces around it**, not a flat pile of equally-trusted features. Read each tier accordingly:

| Tier | What it covers | Trust level |
|------|----------------|-------------|
| **🟢 Core — validated** | Revenue scoring (static + behavioral), distributional analysis (return-level CPS microsim, on CBO's household universe where the source ranks households), dynamic scoring (FRB/US-calibrated) | Benchmarked against published scores from CBO, JCT, Treasury and SSA, plus TPC, PWBM, the Tax Foundation, CRFB, Penn Wharton and RAND where no agency scored the policy. **Honest accuracy is published, not just the flattering cases:** fitted calibrated reference models reproduce official decompositions (1.6% revenue over 23 benchmarks, or 3.0% over 28 with Wave 4's five revised rows held in place; the 7 published distributional tables span 0.00-5.86pp, two of them circular, run `python scripts/cold_holdout.py`), while 31 *unfitted* module reconstructions miss by 56.6% mean and are reported as such — **65.7% on the 26 rows that tier already held, which is the like-for-like reading and it got worse**; genuine *out-of-sample* predictions across 26 pre-registered cases run 18.0% mean error, 14/26 within 15%, 21/26 within 25% (`python scripts/cold_holdout.py`). |
| **🟡 Specialized — calibrated, narrower** | The 14 policy-area modules (TCJA, corporate, international, estate, payroll, AMT, PTC, tax expenditures, enforcement, pharma, trade/tariff, climate), state-level modeling (top-10 states), OLG generational model | Each is parameterized to reproduce a published score. Trustworthy as transparent reconstructions and for directional comparison; not independent confirmation. State and OLG use a representative taxpayer / reduced form. |
| **🔵 Exploratory — interfaces & pipelines** | Ask assistant, Real-Time Bill Tracker, Classroom Mode, multi-model pilot platform, admin dashboard, share links | Reading, teaching, and data-plumbing layers *over* the model — useful and guard-railed (e.g. the assistant is citation-disciplined and cost-capped), but **not themselves validated estimates**. The bill tracker's LLM provision extraction in particular is demo-grade. |

The dividing line is deliberate: investment goes into the green core's correctness and honest validation first; the blue tier exists to make the core usable and explorable, and is held to a UX/safety bar rather than an accuracy bar.

### Validation

Revenue validation comes in **two epistemically different kinds**, and we report them separately because conflating them overstates the model's predictive power. (Reproduce both tables live: `python scripts/cold_holdout.py`.)

#### 1. Out-of-sample predictions — the genuine test

These policies are scored **bottom-up from IRS SOI** filer counts and incomes via raw rate/threshold auto-population, with **no fitting to the official target**. This is the only tier that measures real predictive accuracy.

Fifteen of the 26 cases are the [CBO *Options for Reducing the Deficit: 2025-2034*](https://www.cbo.gov/publication/60557) battery — **15 alternatives across 12 of that report's 76 options** are expressible by the uncalibrated path; the other **64 options** carry a one-line exclusion reason. Option 56 joined in Wave 3: it had been excluded for **leakage**, because the only path that could score a cap on the employer-health exclusion ran through a module annual fitted to that same reform, and lane L6 removed that dependency — a percentile cap is now the published expenditure level times a share read off a premium distribution. Two leakage exclusions remain (Options 53 and 62). Selected rows (full table and per-case error causes in [`docs/VALIDATION.md`](docs/VALIDATION.md)):

| Policy | Official | Model | Error | Source |
|--------|---------:|------:|------:|--------|
| Cut international affairs 25% | -\$187B | -\$187B | 0% | CBO Options #37 |
| Treasury 39.6% + step-up repeal | -\$322B | -\$323B | 0.2% | Treasury (Green Book FY2022 row) |
| Medicare surcharge 2pp (>\$400K) | -\$310B | -\$315B | 2% | Treasury |
| Cut selected nondefense discretionary | -\$339B | -\$333B | 2% | CBO Options #42 |
| 1pp all brackets | -\$960B | -\$920B | 4% | JCT |
| 5pp top rate (\$1M+) | -\$700B | -\$648B | 7% | TPC |
| Tighten Pell grant eligibility | -\$22B | -\$20B | 8% | CBO Options #39 |
| Social Security Fairness Act (WEP/GPO repeal) | +\$196B | +\$215B | 10% | CBO, H.R. 82 |
| Cut certain state and local grants | -\$67B | -\$74B | 11% | CBO Options #43 |
| Biden top rate 39.6% (\$400K+) | -\$246B | -\$217B | 12% | Treasury |
| Fiscal Responsibility Act (discretionary caps) | -\$1,332B | -\$1,170B | 12% | CBO, H.R. 3746 |
| Limit the income-tax employer-health exclusion | -\$697B | -\$606B | 13% | CBO Options #56 |
| Biden capital income at ordinary rates | -\$289B | -\$240B | 17% | Treasury (Green Book FY2025 row) |
| IIJA 2021 (discretionary component) | +\$415B | +\$340B | 18% | CBO, S.Amdt. 2137 |
| Tax accrued gains at death | -\$536B | -\$433B | 19% | CBO Options #51 |
| All ordinary rates +1pp | -\$1,185B | -\$920B | 22% | CBO Options #45 |
| AGI surtax 1pp (>\$20K single) | -\$1,440B | -\$797B | 45% | CBO Options #46 |
| LTCG + qualified dividends +2pp | -\$103B | -\$57B | 45% | CBO Options #47 |
| Corporate rate +1pp (21%→22%) | -\$136B | -\$200B | 47% | CBO Options #64 |
| New 1% payroll tax (all earnings) | -\$1,282B | -\$1,975B | 54% | CBO Options #61 |

**26 out-of-sample cases, mean abs error 18.0%, 14/26 within 15%, 21/26 within 25%** (median 12.6%; `python scripts/cold_holdout.py`). There is deliberately no single "validated within X%" figure: the distribution has a tight core and a long tail. The model predicts ordinary and AGI-inclusive *rate* changes at conventional thresholds well (2-22%) and discretionary funding changes — now scored through a budget-authority-to-outlay spend-out model — well too (CBO Options spending rows 0-11%, the three enacted-law components 10-18%). The one **tax-expenditure cap** in the tier, CBO Option 56, lands at **13%** since Wave 4 gave its excess share CBO's own chained-CPI indexation instead of evaluating it once at the start year; what is left is named rather than tuned — about half of it is a **base omission** (CBO caps premiums *and* FSA/HRA/HSA contributions, and the repository's premium distribution has no account dimension) and about a fifth an **unsourced behavioural offset** whose sign convention is the reverse of `TaxPolicy`'s.

**Gains at death left the tail in two steps.** Wave 2 replaced a flat \$54B/yr constant with decedent wealth × an unrealized-gain share by estate size, taking CBO Option 51 from 84% to 8%. Wave 4 then gave the death channel the six carve-outs a realization-at-death proposal does not tax — spousal, charitable, the §121 residence exclusion, tangible personal property, a family-business deferral and the per-donor exclusion, applied *after* the others — plus a rate response at death: the Green Book FY2025 row fell 135% → **17%**, the FY2022 row 218% → **0.2%**, and Option 51 rose 8% → **19%, worse, and pre-registered as a regression** because its 8% had been bought by taxing charitable bequests and small decedents' housing gains that no such regime reaches. **Read that 0.2% with the caveat its own lane attaches: it is two errors cancelling, not a measurement of accuracy** — the mechanism removes 87.2% of that row's death channel where the pre-registered hand path said 92.8%. The two Green Book rows land on opposite sides of their targets, which the lane diagnoses as the five-class decedent ladder having no within-group dispersion rather than any mis-ordering of the exclusion.

What remains of the behavioural tail is narrower and better named — a 2pp preferential-rate change at 45%, corporate margins at 47% and payroll incidence at 54-56%, which is now the tier's largest single error mass. Two rate cases sit between the core and the tail at 18% and 45%, both because the source states a filing-status-specific boundary the generic path cannot express. Misses are kept, not tuned away, and each carries a documented structural cause. Three of the cases replicate laws that actually passed — the Social Security Fairness Act, the Fiscal Responsibility Act's discretionary caps and IIJA — always as *components* whose annual level or authorization schedule the CBO estimate itself states, never as a bill total no single shape can construct. Every case is **pre-registered** ([`fiscal_model/validation/preregistered.py`](fiscal_model/validation/preregistered.py)) *before* the commit that first scores it, and the tier is **CI-gated** (`--max-mean-error 25 --min-within-25pct 20`, re-derived from this battery by the workflow's own rule after the death channel halved the tier — ceiling `ceil(18.0 × 1.25) = 23` rounded up to 25, floor `21 - 1 = 20`). Treat uncalibrated custom rate policies as **directional, ±15-25%**, and uncalibrated payroll policies as not yet predictive.

One case left the battery in the provenance pass and two changed target. **Top rate to 45% was retired**: its -\$420B is in no TPC, CBO or JCT publication (TPC's full sitemap contains no 45%-ordinary-rate table at any date), so it is withdrawn rather than scored against a number nobody published — and the figure is gone from the app's score map too. **Biden capital gains was re-sourced** from an unsupported -\$456B to the FY2025 Green Book's actual combined row, -\$288.6B, with the shape corrected to that document's own definition (taxable income over \$1M; a \$5M per-donor exclusion for gains at death, not \$1M) — which moved its error from 79% to 142% before Wave 4's carve-outs brought it to **17%**. **Biden's top rate moved in Wave 4** from a rounded -\$252B to the Green Book's own printed row, **-\$245.9B** (\$245,924M, report p. 242), through the manifest's new-row supersede rule; nothing in the model reads the target, the prediction is the same -\$216.5B it was, and only the error column moved (14% → **12%**).

#### 2. Calibrated reference models — transparent reconstructions, not independent confirmation

The specialized modules (TCJA, Corporate, Estate, Credits, AMT, Payroll, PTC, Capital Gains, Tax Expenditures) are parameterized so their components **reproduce a published decomposition** — usually CBO's, JCT's or Treasury's, but the fitted benchmarks also include the Social Security Trustees, PWBM and the Tax Foundation where no agency scored the policy. Across the **23** benchmarks a module is actually fitted to, the mean absolute error is **1.6%**, 23 of 23 within 15% — but that low error is **expected by construction**. These are useful as auditable, source-linked reconstructions of official scores, *not* as evidence the model would have predicted them cold.

**Never quote the 23 without saying which rows left.** Three mechanisms move rows out of this tier and all are live. First, `ScorecardSummary.revised_target_entries` is **15**: fifteen calibrated targets have been corrected through the Tier-2 revision ledger ([`fiscal_model/validation/target_revisions.py`](fiscal_model/validation/target_revisions.py)), and a constant fitted to a superseded figure is not fitted to its replacement — so those rows move out of the fitted tier and into the reconstructions below. **Wave 4's provenance pass alone moved five that way (28 → 23)**: `biden_eitc_childless`, `eliminate_salt`, `extend_enhanced_ptc`, `ira_enforcement` and `repeal_salt_cap`, each mechanically, none retuned to close the new gap. Held in place instead, the fitted tier reads **28 benchmarks at 3.0%, 27 of 28 within 15%**, the one miss being `eliminate_salt` at 22.3% (or 29 at 5.2% with the revised TCJA-AMT row also held in — the reading earlier versions of this README quoted as 4.3%). Second, **Wave 2 moved the three capital-gains scenarios out (33 → 30)**: deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural tuples removed the only constants ever fitted to those three targets, so `calibrated_to_target` is now simply `False` for them and they report as reconstructions. Third, **Wave 3's L8 lane moved the two Trump tariff rows out (30 → 28)**: `universal_coverage_rate` and `china_effective_coverage` were fitted to those two benchmarks, and once the first became a Census measurement and the second was deleted outright, no `TRADE_BASELINE` constant is fitted to anything. The fitted mean *fell* 2.8% → 2.2% → 2.0% → **1.6%** across those moves while nothing regressed, because every row that left was one this tier had been carrying. That is a change of **composition, not of accuracy** — read it next to the reconstruction tier below or not at all. The worst fitted row is still TCJA-without-the-SALT-cap at 13.9%.

The calibrated tier also carries **31 module reconstructions nothing was fitted to** — the international, trade, pharma, IRS-enforcement and climate presets wired in during Phase E (now including the two reclassified tariff rows), the eight P.L. 119-21 JCT line items added in Phase D, the rows the revision ledger moved out of the fitted tier, and the three capital-gains scenarios Wave 2 unfitted. Those miss by **56.6% mean / 29.9% median**, 9 of 31 within 15% (15 sectoral presets at 82.6%, 8 P.L. 119-21 line items at 35.8%, 3 capital-gains scenarios at 39.6%, TCJA AMT relief at 66.8%, and the 5 rows Wave 4's provenance pass moved in at 9.4%). **Both of those figures fell for composition reasons and neither is an improvement — quote the constant-population reading beside them.** On the **26 rows this tier already held** the mean is **65.7% / 40.5% median**, *worse* than the 61.8% / 38.0% it read before Wave 4; on the **14 sectoral rows the subset already held** it is **88.2%**, not 82.6%. The reason is named rather than smoothed: Wave 4's pharma rebuild (three federal Part D channels, a negotiation ladder fitted to all three published CMS cycles, a RAND coverage base) **took two rows further from their targets** — expanded negotiation 25.7% → **93.3%** and international reference pricing 646.2% → **701.0%** — because the lane's own ladder condemned an unsourced \$220B Part D gross-spending constant that the reference-pricing leg also reads, and the lane took the sourced \$281B and reported the miss rather than keeping a number that flattered it. The insulin row is unchanged at 39.0%. Each row carries a `known_limitations` note; none was retuned. The universal insulin cap scores **+\$7.0B** against CBO's own **+\$11.4B** (publication 57957) — a deficit *increase* on both sides — where the repository used to carry a -\$15B saving that pointed the other way and made the row read 146%. The P.L. 119-21 block is the sharpest of these: the TCJA module reproduces CBO's \$4.6T aggregate to **0.4%** and JCT's own provision rows to **35.8%**, because its single calibration factor is fitted to the aggregate and to no individual row.

**Where the targets come from.** The provenance pass opened the primary documents rather than inspecting the citations, and **Wave 4 finished the job it started**. By provenance the 54 calibrated targets are now **30 `line_item` / 5 `line_item_differs` / 12 `secondhand` / 7 `model_estimate`**, where before Wave 4 they were 19 / 13 / 15 / 7. **Thirteen targets moved onto their documents, and none of the five rows that still disagree is an open question**: two are range revisions carrying an in-range anchor (Pillar Two, reciprocal tariffs) and three are explicit **examined-and-left** verdicts (`EXAMINED_NOT_REVISED`, now five entries in all). **Fifteen targets have been moved** — not edited, but superseded through the Tier-2 revision ledger, which keeps the old figure on the record as a `superseded_by` row. The first three: the universal insulin cap from -\$15B to CBO 57957's **+\$11.4B** (a \$35 cost-sharing cap *adds* to the deficit), TCJA AMT relief from \$450B to CRS R48286's **\$1,357.1B** (a five-year cost sitting in a ten-year column), and Pillar Two adoption from a -\$80B point to JCT JCX-22-23's **published range [-\$102.6B, +\$56.5B]**, inside which the model's -\$61.2B sits at distance \$0.0B — so its 23.5% against -\$80B is a distance from an editorial midpoint, not a measurement of accuracy. Wave 4 moved twelve more, ten of them a rounded headline standing in for a printed row (the SALT deduction to CBO Option 49's **-\$1,621.0B**, the SALT cap to PWBM Table 3's **+\$1,169.0B**, GILTI reform to **-\$373.9B**, FDII repeal to the Green Book's gross **-\$158.0B**, the international package to **-\$632.2B**, childless EITC to **+\$162.6B**, IRA enforcement to CBO 58390's **-\$180.4B** in place of a figure CBO had *withdrawn*, EV credits to **-\$182.3B**, enhanced PTC to **+\$335.0B**, the universal tariff to Tax Foundation FF861's **-\$2,171.1B**), and two that were a different kind of error: the auto tariff's -\$100B was a **per-year** claim in a ten-year column (now Tax Foundation's -\$386.2B), and the reciprocal-tariff target was **Tax Foundation's dynamic score sitting in a conventional column** — a *tier* error no rescaling would have found, now the range **[-\$1,800B, -\$1,400B]** on which CRFB, Tax Foundation and Yale disagree by 29%. **Six of the thirteen got worse**, which is the shape a correct provenance pass has: if every revision improved its row, the documents would look chosen to fit. **Twelve rows still could not be traced at all**, including both Social Security payroll targets, for which OCACT publishes only percent-of-payroll and no dollar figure in any year. The remaining **7 are illustrations with no official score at all** and are excluded from every count: the honest published-benchmark count across both tiers is **73**, not 80, unchanged by Wave 4 because no row changed to or from `model_estimate`. See [`docs/VALIDATION_NOTES.md`](docs/VALIDATION_NOTES.md) §7 and §8.

| Policy (calibrated) | Official | Model | Error |
|--------|---------:|------:|------:|
| TCJA Full Extension | \$4,600B | \$4,582B | 0.4% |
| Biden Corporate 28% | -\$1,347B | -\$1,397B | 3.7% |
| Repeal Corporate AMT | \$220B | \$220B | 0.0% |
| Cap Employer Health | -\$450B | -\$450B | 0.1% |
| SS Donut Hole \$250K | -\$2,700B | -\$2,700B | 0.0% |

See [`docs/VALIDATION.md`](docs/VALIDATION.md) for the full matrix and [`fiscal_model/validation/holdout.py`](fiscal_model/validation/holdout.py) for the locked regression protocol.

**Distributional accuracy** — 7 benchmarks wired end-to-end against the distributional engine. Accuracy is the mean absolute share error across each benchmark's income groups; live numbers are exposed via `GET /benchmarks` and `scripts/run_validation_dashboard.py`.

The default distributional engine is now the **return-level microsimulation** (correct ordinary/preferential rate treatment, real SALT modeling, refundable credits). The Streamlit **Distribution** setting defaults on and maps to `prefer_microsim`; uncheck it to force the synthetic bracket path. Where a policy isn't yet microsim-representable the engine falls back automatically. The `Engine` column / result `engine` field says which path produced each number.

| Benchmark | Source | Engine | Universe (scored) | Rating | Err (pp) |
|-----------|--------|--------|-------------------|--------|---------:|
| TCJA 2018, deciles | CBO 54796 | synthetic | household→tax_unit | **excellent** | 0.00 |
| TCJA 2019, AGI class | JCT JCX-68-17 | synthetic | tax_unit | good | 2.10 |
| ARP 2021, quintiles | CBO 56952 | microsim | **household** | good | 3.72 |
| SALT cap repeal 2024, AGI class | JCT JCX-4-24 | microsim | tax_unit | good | 5.86 |
| Corporate 28% 2022, AGI class | JCT JCX-32-21 | synthetic | tax_unit | good | 2.51 |
| TCJA ext 2026, deciles | CBO 60007 | synthetic | household→tax_unit | **excellent** | 0.74 |
| P.L. 119-21, 2026-2034 avg, deciles | CBO 61367 | synthetic | household→tax_unit | good | 3.96 |

`≤ 2pp = excellent`, `≤ 5pp = good`, `≤ 10pp = acceptable`. The SALT number is **higher than before by design**: it used to read 0.00 from a table *calibrated to JCX-4-24*; it now reads 5.86 from a genuine return-level computation (the synthetic calibrated reference still matches near-exactly if forced). **The ARP number fell 7.77 → 3.72 in Wave 4**, when the engine gained CBO's own **household** universe — size-adjusted household income before transfers and taxes, quintiles containing equal numbers of *people* — and each benchmark was registered on the universe *its source ranks*. Before that the model was ranking 38.2M tax units against CBO's ~26M households; scored on CBO's population the bottom quintile's share goes 53.4% → 28.6% against CBO's 34.0%. The same PR also fixed a per-household **dollar** column that was low by a factor of three and invisible to every gate in the repository, because the error metric scores shares and the shares were computed from a correctly weighted merge.

**The `Universe (scored)` column is the point of the exercise, not decoration.** Three of the four CBO tables are registered on `household` but scored on `tax_unit`, shown as `household→tax_unit`: `TCJAExtensionPolicy` and the corporate policy have no microsim reform mapping, so those rows take the synthetic bracket path, which aggregates IRS *return* counts and has no household layer to rank. Two of the three are also the tables whose 0.00pp and 0.74pp are **circular** — they read CBO's own published shares back. Giving `TCJAExtensionPolicy` a microsim path would move all three at once and is the obvious next lane. See [`docs/VALIDATION_NOTES.md`](docs/VALIDATION_NOTES.md) for the ARP residual analysis.

---

## Quick start

### Use the web app

Visit **[fiscal-policy-calculator.streamlit.app](https://fiscal-policy-calculator.streamlit.app)** — no installation needed.

### Run locally

```bash
git clone https://github.com/laurencehw/fiscal-policy-calculator.git
cd fiscal-policy-calculator
pip install -r requirements.txt
streamlit run app.py          # Main policy calculator
streamlit run classroom_app.py  # Classroom mode
```

The repository pins Python `3.12` for local development via `.python-version`. CI verifies `3.10` through `3.13`, the `smoke` job exercises the Streamlit boot path before the full matrix, and the recommended Streamlit Cloud runtime is also `3.12`.

### Use the REST API

```bash
uvicorn api:app --reload
```

Key routes:

- `GET /presets` lists the full preset library with official-score metadata where available.
- `POST /score` supports generic `income_tax`, `corporate_tax`, and `payroll_tax` custom policies.
- `POST /score/preset` routes preset scoring through the same preset factory used by the Streamlit UI, including specialized policy modules such as TCJA, credits, payroll, PTC, trade, and climate presets.
- `POST /score/tariff` uses the tariff policy model instead of a standalone rough formula.
- `POST /ask` poses a public-finance question to the Ask assistant and returns the full citation-grounded answer plus tool-call provenance, usage, and session id. Honors the same `X-API-Key` auth, daily-cost cap, and per-session limits as the Streamlit tab — they share one sqlite ledger.
- `POST /ask/stream` streams the same response as Server-Sent Events: `event: token` frames carry the answer chunks and a terminal `event: done` frame carries the metadata payload.
- Score responses include a `credibility` block with benchmark category, calibrated-vs-generic evidence type, implied uncertainty range, known limitations, and a `holdout_status` field backed by the locked post-change holdout protocol.
- `GET /validation/scorecard` exposes the consolidated revenue benchmark table, calibrated/generic/holdout counts, and a flattened `issues` list for material revenue benchmark problems.
- `GET /benchmarks` lists distributional benchmark accuracy and includes a flattened `issues` list if any benchmark needs improvement.
- `GET /summary` combines health, distributional benchmarks, microdata coverage, auth status, and a flattened `issues` list for dashboards.
- `GET /readiness` combines runtime, health, distribution benchmark, and revenue scorecard checks into one machine-readable verdict: `ready`, `ready_with_warnings`, or `not_ready`.
- `GET /health` exposes Python runtime compatibility, baseline vintage, IRS/FRED freshness, microdata coverage, fallback status, and a flattened health `issues` list.

Status-oriented endpoints use the same issue shape so dashboards can consume them without endpoint-specific parsing: `surface`, `severity`, `name`, `message`, and `details`.

### Use as a Python library

```python
from fiscal_model import FiscalPolicyScorer, TaxPolicy, PolicyType

# Score a custom policy
policy = TaxPolicy(
    name="Top Rate Increase",
    description="Restore 39.6% rate for income above $400K",
    policy_type=PolicyType.INCOME_TAX,
    rate_change=0.026,
    affected_income_threshold=400_000,
)

scorer = FiscalPolicyScorer()
result = scorer.score_policy(policy, dynamic=True)

print(f"10-year cost: ${result.total_10_year_cost:,.0f}B")
print(f"Revenue feedback: ${result.revenue_feedback_10yr:,.0f}B")
```

```python
# Score a pre-built proposal
from fiscal_model import create_tcja_extension

policy = create_tcja_extension(extend_all=True)
result = FiscalPolicyScorer().score_policy(policy)
print(f"TCJA extension: ${result.total_10_year_cost:,.0f}B")
```

```python
# OLG model for long-run analysis (55-cohort Auerbach-Kotlikoff)
from fiscal_model.models.olg import OLGModel, OLGParameters
model = OLGModel(OLGParameters())
result = model.analyze_policy(
    reform_overrides={"tau_k": 0.35},   # +5pp capital tax
    policy_name="Capital tax +5pp",
    compute_gen_accounts=True,
    start_year=2026,
)
print(result.summary())
```

---

## Architecture

```
Policy Definition → Static Scoring → Behavioral Offset (ETI) → Dynamic Feedback (FRB/US)
                         ↓                    ↓                        ↓
                   ΔRate × Base         -ETI × 0.5 × static      GDP × marginal rate
```

### Module structure

| Module | Purpose |
|--------|---------|
| `scoring.py` | Public scoring facade re-exporting `scoring_engine.py` and `scoring_result.py` |
| `policies.py` | Public policy facade re-exporting `policies_core.py` and `policies_factory.py` |
| `baseline.py` | CBO 10-year budget projections |
| `economics.py` | Dynamic effects, multipliers, GDP feedback |
| `distribution.py` | Public distribution facade over core, grouping, effects, engine, and reporting modules |
| `trade.py` | Tariff scoring, consumer price impact, retaliation |
| `international.py` | GILTI, FDII, Pillar Two, UTPR |
| `enforcement.py` | IRS enforcement revenue ROI |
| `pharma.py` | Drug pricing, Medicare negotiation |
| `corporate.py` | Corporate rate, pass-through, book minimum |
| `tcja.py` | TCJA extension with component breakdown |
| `credits.py` | CTC, EITC with phase-in/out |
| `estate.py` | Estate tax with exemption modeling |
| `payroll.py` | SS cap, donut hole, NIIT |
| `amt.py` | Individual and corporate AMT |
| `ptc.py` | ACA premium tax credits |
| `tax_expenditures.py` | Public tax-expenditure facade over core tables and policy factories |
| `models/macro_adapter.py` | Public macro adapter facade over FRB/US, simple multiplier, and scenario-conversion modules |
| `models/olg.py` | Overlapping generations model (Auerbach-Kotlikoff) |
| `microsim/` | Vectorized individual-level tax calculator |
| `long_run/` | Solow growth model, generational accounting |
| `models/state/` | Combined federal + state tax calculator (top 10 states) |
| `validation/compare.py` | Compatibility facade over the refactored validation core, scenarios, reporting, and specialized suites |
| `ui/` | Controller-based Streamlit UI with decomposed input, settings, runtime logging, and share-link helpers |
| `constants.py` | All parameters with source citations |
| `classroom/` | Assignment engine, feedback, PDF export |
| `bill_tracker/` | congress.gov pipeline, LLM extraction, SQLite |
| `assistant/` | Ask assistant — system prompt, tool schemas, BM25 knowledge search over `assistant/knowledge/*.md`, citation post-processor, cost meter, sqlite rate limiter, admin dashboard queries, share-link encoding |

### Data sources

- **IRS Statistics of Income** — Taxpayer counts and income by bracket (Tables 1.1, 3.3)
- **FRED** — GDP and macroeconomic indicators (St. Louis Fed)
- **CBO Baseline** — 10-year revenue, spending, and deficit projections (Feb 2026)
- **congress.gov API** — Active bill text and status (Bill Tracker)
- **Anthropic Claude API** — Powers the Ask assistant (Sonnet 4.6 for answers, Haiku for follow-up suggestions). Optional — the rest of the app works without it.

---

## Ask assistant

The 💬 Ask tab is a citation-disciplined Q&A interface over this model and 23 curated authoritative snapshots. Tool-grounded; every numerical claim must trace to either an app tool call (scoring engine, baseline, validation scorecard, knowledge search, FRED query) or an authoritative URL from `web_search` / `fetch_url`. Unsupported `[^N]` markers are stripped automatically and surfaced as a defect.

### Configuration (env vars or Streamlit secrets)

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required to enable the Ask tab. Set via env var or Streamlit Cloud Secrets (the tab promotes `st.secrets["ANTHROPIC_API_KEY"]` to `os.environ` on first render). Without it, the tab shows a friendly "not configured" message with a typo-detecting diagnostic — no API-key input is ever shown to end users. |
| `ASSISTANT_DAILY_COST_CAP_USD` | `5.00` | Hard cap across all visitors per UTC day; new requests return a friendly "budget exhausted" message once exceeded. |
| `ASSISTANT_SESSION_MESSAGE_CAP` | `20` | Per-session turn cap. |
| `ASSISTANT_COOLDOWN_SECONDS` | `3` | Minimum spacing between turns from the same session. |
| `ASSISTANT_DISABLED` | unset | Set to `1` to disable the assistant entirely (kill switch). |
| `ASSISTANT_USAGE_DB` | (auto) | Path to the sqlite `assistant_events` ledger. Defaults to a writable location under the repo or the user home; falls back to `:memory:`. |
| `ASSISTANT_ADMIN_TOKEN` | — | Optional. When set, visiting `?admin=<token>` reveals a 💼 Admin tab with usage analytics. |
| `ASSISTANT_MODEL` | `claude-sonnet-4-6` | Override the Anthropic model id (e.g., for local Opus testing — not surfaced as a toggle in the UI to avoid runaway cost). |
| `ASSISTANT_SHOW_TOOLS` | unset | Set to `1` to surface a developer expander listing every tool call per turn. Off by default — readers see only the answer and citation footnotes. |

### Curated knowledge corpus

19 hand-maintained Markdown snapshots live in `fiscal_model/assistant/knowledge/`. Each carries a frontmatter `source:` URL the assistant uses for citation. To add or refresh a snapshot, use the helper:

```bash
python scripts/refresh_knowledge.py \
    --url https://www.taxpolicycenter.org/publications/<slug> \
    --slug tpc_<topic>_<year> \
    --title "Full title from the page" \
    --org TPC --year 2026 \
    --keywords "tpc, distribution, tcja, decile"
```

It fetches the page (or PDF, via `pdfplumber`) through the same allowlist-enforced pipeline the runtime `fetch_url` tool uses, then dumps a frontmatter'd stub for you to summarize by hand. CBO and SSA hard-block bots regardless of UA — the script tells you when to fall back to manual paste or trust the assistant's server-side `web_search`.

### Smoke testing

A 3-scenario live smoke test costs ≈$0.04 and verifies the streaming tool-use loop, citation discipline, and cost meter against real Anthropic:

```bash
python scripts/smoke_ask_assistant.py        # all 3 scenarios
python scripts/smoke_ask_assistant.py --only 1   # one scenario
```

### Health / readiness integration

The `/health` response carries an `assistant` component reporting three sub-signals (API key, knowledge corpus size, usage db reachability). It is *not required* — a missing API key on a CI runner or dev box reports as "degraded" without dragging overall health or readiness to `not_ready`. The `/readiness` payload includes the same component with `required=False`.

---

## Methodology

The full methodology is documented in the app's **Methodology** tab and in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md). Key parameters:

| Parameter | Default | Source |
|-----------|---------|--------|
| Elasticity of Taxable Income | 0.25 | Saez, Slemrod & Giertz (2012) |
| Capital gains elasticity | 0.8 short / 0.4 long | CBO (2012), Dowd et al. (2015) |
| Spending multiplier (normal times) | 1.0 | CBO-conventional; Auerbach & Gorodnichenko (2012) |
| Tax multiplier (normal times) | 0.5 | CBO-conventional |
| Multiplier decay | 0.7/year | Multiplier-decay literature |
| Okun's Law coefficient | 0.5 | Ball, Leigh & Loungani (2017) |
| Marginal revenue rate | 0.25 | CBO |
| Corporate tax incidence | 75% capital / 25% labor | CBO/TPC |

The default dynamic-scoring engine is the state-dependent `EconomicModel`, which uses CBO-conventional normal-times multipliers (spending 1.0, tax 0.5) and raises them in recessions / at the zero lower bound (see [Spending Multipliers](docs/METHODOLOGY.md#spending-multipliers)). A separate FRB/US-calibrated reduced-form model (`FRBUSAdapterLite`, spending 1.4 / tax 0.7, decay 0.75) is offered as a *comparison engine* in the multi-model **Scoring Models** tab — it is not what the default "Dynamic scoring" toggle uses.

The **Multi-Model Comparison** pilot (Scoring Models tab) runs the same preset through **CBO-Style** and **TPC-Microsim** when the policy maps to microsim reforms (income-tax rates, CTC, EITC, SALT, AMT exemption). Specialized families such as corporate, OASDI payroll, and estate still score on CBO-Style; TPC reports **not representable** instead of inventing agreement. See `fiscal_model.models.capabilities`.

### Parameter sensitivity

Revenue estimates are sensitive to key behavioral parameters. The table below shows how a ±50% change in each parameter shifts the 10-year estimate for a representative income tax reform:

| Parameter | Range tested | Revenue impact |
|-----------|-------------|----------------|
| Elasticity of Taxable Income (ETI) | 0.12 – 0.40 | ±12% |
| Capital gains elasticity (long-run) | 0.20 – 0.60 | ±18% |
| Spending multiplier | 0.7 – 2.0 | ±8% (dynamic only) |
| Corporate tax elasticity | 0.12 – 0.40 | ±10% |

The app includes interactive sensitivity sliders to explore these ranges.

### When to use this model

- **Directional policy analysis** — Order-of-magnitude estimates for comparing proposals
- **Teaching fiscal policy** — Classroom mode with 7 structured assignments
- **Rapid prototyping** — Quickly score new proposals before detailed CBO/JCT analysis

### When NOT to use this model

- **Official scoring** — Use CBO/JCT for legislative budget estimates
- **Precise distributional analysis** — Bracket-level aggregates, not individual-level microsimulation
- **State-level precision** — Top 10 states only; representative taxpayer, not microsim
- **Complex dynamic effects** — Reduced-form FRB/US multipliers, not structural general equilibrium

### Known limitations

1. **CPS-based microsim, with known top-income undercount** — Distributional analysis now defaults to a return-level CPS ASEC microsimulation (ordinary/preferential rates, real SALT modeling, refundable credits). CPS ASEC undercounts top incomes and capital gains, so the very top of the distribution is approximate; SALT and itemized deductions are imputed from state aggregates rather than reported
2. **Simplified corporate pass-through** — Pass-through income not fully modeled
3. **State modeling approximate** — Top 10 states only; uses representative taxpayer, not microsim
4. **Reduced-form dynamic scoring** — Calibrated FRB/US multipliers, not structural GE model
5. **Aging source data** — IRS SOI data currently tops out at 2022; updated annually following IRS release (typically Q3)
6. **Distributional benchmarks are still narrow** — Current distributional validation is benchmarked mainly to published TPC tables, not a broader CBO distributional set

### Data freshness

| Source | Vintage | Update cadence |
|--------|---------|----------------|
| IRS Statistics of Income | 2022 | Annual (~Q3 following tax season) |
| CBO Baseline | February 2026 | Quarterly with CBO publications |
| FRED macro data | Live / cached / bundled seed | Daily when API key is set; bundled seed covers offline smoke/readiness paths and warns after 120 days |
| congress.gov bills | Live | On-demand via `scripts/update_bills.py` |

### Manuscript readiness

For a citation-grade roadmap focused on manuscript quality rather than just app polish, see [planning/MANUSCRIPT_95_PLUS.md](planning/MANUSCRIPT_95_PLUS.md).

---

## Development

### Runtime contract

- Supported package range: Python `3.10` to `3.13`
- Local default: `.python-version` -> `3.12`
- Recommended Streamlit Cloud runtime: `3.12`
- Current CI contract: passing `smoke` job plus full `3.10`-`3.13` matrix on `main`
- The `/health` response includes a `runtime` component and marks unsupported Python versions, such as `3.14`, as `degraded`.
- Deployment checklist and incident guide: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

### Run tests

```bash
pip install -r requirements.txt pytest pytest-cov
python -m pytest tests/ -v
python -m pytest tests/ --cov=fiscal_model
```

### Verify against CBO/JCT scores

```bash
python -c "from fiscal_model.validation import run_validation_suite; run_validation_suite()"
```

### Verify release readiness

```bash
python scripts/check_readiness.py
python scripts/check_readiness.py --strict
python scripts/check_readiness.py --json > readiness-report.json
```

Default mode exits non-zero only when the verdict is `not_ready`. Strict mode is the CI release gate: it still reports every warning, but only blocks on actual failures or non-environmental warnings. A tracked FRED seed keeps isolated CI runners off the hardcoded GDP fallback; if the seed and cache are both unavailable, offline FRED/cache fallback warnings remain visible without failing strict CI.

### Refresh bundled FRED seed

The tracked FRED seed is refreshed from live FRED only; it never writes cache or
fallback values into the committed snapshot.

```bash
export FRED_API_KEY="..."
python scripts/refresh_fred_seed.py --observations 8
python scripts/check_readiness.py --strict
```

A scheduled GitHub Actions workflow runs monthly and opens a pull request when
`fiscal_model/data_files/fred_seed.json` changes. Configure the repository
secret `FRED_API_KEY` so the workflow can refresh the seed before the 120-day
freshness window expires.

### Verify public app availability

```bash
# Optional: override default URL used by the check
export FISCAL_POLICY_APP_URL="https://your-app.streamlit.app"

python scripts/check_public_app.py
```

The scheduled GitHub Actions public-health workflow runs the same check every six hours. Override the target deployment with the repository variable `FISCAL_POLICY_APP_URL`.
For an artifact-friendly report, run `python scripts/check_public_app.py --json`.

### Lint

```bash
pip install ruff
ruff check fiscal_model/ tests/
```

### Reproducibility (dependency lock strategy)

- `requirements-lock.txt` is the committed `pip-compile` lock for the Python `3.12` production/runtime path.
- The `smoke` CI job installs from `requirements-lock.txt`, so lockfile breakage is exercised before the full matrix suite runs.
- The broader `3.10`-`3.13` matrix still installs from `requirements.txt` to verify the supported version range.
- Refresh the lock intentionally from Python `3.12`:

```bash
python3.12 -m venv .lockvenv
.lockvenv/bin/pip install pip-tools
.lockvenv/bin/pip-compile --strip-extras --output-file=requirements-lock.txt requirements.txt
```

### Deployment smoke tests

- GitHub Actions now runs a dedicated `smoke` job for `app.py` and the core Streamlit controller path before the full matrix suite.
- The smoke suite is `tests/test_app_entrypoints.py` plus `tests/test_ui_controller_smoke.py`.
- The `readiness` job runs `python scripts/check_readiness.py --strict` on Python `3.12` and uploads `readiness-report.json`.
- The `smoke` job also runs `python scripts/check_streamlit_boot.py --timeout 45`, which starts Streamlit locally and checks the calculator and classroom-mode URLs return the app shell.
- The `validation-dashboard` and `public-app-health` workflows upload JSON artifacts with flattened `issues` arrays for monitoring and release triage.

### Project structure

```
fiscal-policy-calculator/
├── app.py                    # Router: st.navigation(position="top") + legacy-URL shim
├── app_pages/                # One module per page (ask, build, tailor, explore, …)
├── components/               # Shared frame: chrome.py, cards.py, results.py
├── classroom_app.py          # Classroom mode Streamlit app
├── api.py                    # FastAPI endpoints
├── fiscal_model/             # Core scoring engine
│   ├── ui/                   # Streamlit UI components
│   │   └── tabs/             # Page bodies + result sub-views
│   ├── composer/             # Values vector, archetypes, deterministic selector
│   ├── preset_ids.py         # Stable preset ids, exclusive groups, values tags
│   ├── models/               # Macro adapters (FRB/US)
│   ├── long_run/             # OLG model, Solow growth
│   ├── state/                # State-level rate modeling
│   ├── data/                 # IRS SOI, FRED, capital gains loaders
│   ├── validation/           # CBO score comparison framework
│   └── constants.py          # All parameters with citations
├── classroom/                # Assignment engine, feedback, PDF export
├── bill_tracker/             # congress.gov pipeline, LLM extraction
├── tests/                    # Automated test suite
├── docs/                     # Methodology, architecture docs
├── planning/                 # Roadmap, session notes
└── pyproject.toml            # Project config, ruff, pytest
```

---

## REST API

The project includes a FastAPI REST API for programmatic access:

```bash
uvicorn api:app --reload        # Start API server
# Visit http://localhost:8000/docs for interactive Swagger documentation
```

Endpoints include `/score` (custom policies), `/presets` (list pre-built proposals), and `/score/tariff` (tariff scoring).

For production deployments, set `FISCAL_API_KEYS=label1:secret1,label2:secret2` to require an `X-API-Key` header on scoring endpoints. Rate limiting is always on (defaults: 60/min with burst 20, per-key when auth is on, per-IP otherwise). See [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for the full API-hardening reference.

---

## Documentation

- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — three-stage scoring, parameter citations, behavioral and dynamic assumptions
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — module layout, dependency graph, extensibility patterns
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — full benchmark matrix against published agency and think-tank scores
- [`docs/VALIDATION_NOTES.md`](docs/VALIDATION_NOTES.md) — root-cause analysis for high-error outliers
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Streamlit Cloud + custom deployment notes
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — material changes to features and the API

---

## Contributing

Contributions welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup instructions and guidelines.

The most impactful areas:

- **Multi-model comparison platform** — Planned CBO/TPC/PWBM-style side-by-side scoring
- **CPS microsimulation upgrade** — Planned move from synthetic tax units to CPS ASEC-based microdata
- **New policy modules** — Climate/energy, immigration, housing, wealth tax
- **Data updates** — IRS SOI 2023, CBO auto-loader

Please open an issue first to discuss significant changes.

---

## References

1. Saez, Slemrod & Giertz (2012). "The Elasticity of Taxable Income." *JEL*, 50(1).
2. Auerbach & Gorodnichenko (2012). "Measuring Output Responses to Fiscal Policy." *AEJ: EP*, 4(2).
3. Christiano, Eichenbaum & Rebelo (2011). "When Is the Spending Multiplier Large?" *JPE*, 119(1).
4. CBO (2026). "The Budget and Economic Outlook: 2026 to 2036."
5. Treasury (2024). "General Explanations of the Administration's FY2025 Revenue Proposals."
6. Yale Budget Lab. [Dynamic Scoring Using FRB/US](https://budgetlab.yale.edu/research/dynamic-scoring-using-frbus-macroeconomic-model).
7. Auerbach & Kotlikoff (1987). *Dynamic Fiscal Policy*. Cambridge University Press.

---

## License

[MIT](LICENSE)
