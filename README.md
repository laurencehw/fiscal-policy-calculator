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

**Frozen assignment links (classroom).** Adding `&engine=<macro model>&frozen=1`
to those stamps turns them from a record of a past run into a lock on the next
one, so a class hands in one set of numbers rather than one per student:

```
/explore?preset=tcja-full-extension&dynamic=0&run=1
        &baseline=february2026&engine=frbus_lite&spec=506d91e321f8
        &mode=conventional&frozen=1
```

The baseline vintage, the macro model, dynamic scoring **and** the policy are
applied from the URL and their controls render disabled under "🔒 Frozen for
this assignment" — in the form, beside the Score button and in the ⚙ popover —
with a provenance line under the number. A link naming a baseline vintage this
deployment is not serving is **refused**: the page says which vintage the
assignment wants and scores nothing, rather than quietly answering with
different numbers. To make one, open a result surface with `?classroom=1`
(`/classroom` links there) and copy the **🔒 Assignment link** from Export
Results.

**Build** freezes the same way, over a *package* rather than one score:

```
/build?policies=ss-donut-250k,corporate-28pct&target=3.0&metric=pct_gdp
      &baseline=february2026&engine=frbus_lite&spec=424a0fef5bce
      &mode=conventional&frozen=1
```

The checklist, the deficit-target slider, the metric toggle and the search box
render disabled with the link's package ticked; `spec=` hashes the ids, the
target and the metric, so a hand-edited `policies=` is reported rather than
silently scored. The exports still work — a student has to be able to hand
something in. A `?values=<archetype>` or `?vector=` package can be frozen too,
because selection is deterministic: the model only ever translates free text
into values, and a link carries the values, never the text.

### Additional features

- **💬 Ask assistant** — Citation-grounded Q&A about public finance and this model's outputs. Streams answers from Claude Sonnet 4.6 with tool access to the app's scoring engine, CBO baseline, validation scorecard, and 23 curated authoritative snapshots (CBO, JCT, PWBM, Yale Budget Lab, TPC, PGPF, BEA, BLS, SSA Trustees, FRED). Every substantive claim carries a `[^N]` footnote cross-referenced against the tool-call provenance; unsupported markers are auto-stripped. Hard daily cost cap ($5/day default across all visitors), per-session message cap, cool-down, and kill-switch protect the deployer's API budget. Available as a Streamlit tab, a non-streaming `POST /ask` endpoint, and an SSE `POST /ask/stream` endpoint.
- **Tariff scoring** — 5 presets (universal 10%, China 60%, autos 25%, steel and aluminium 25%, reciprocal), consumer price impact by income quintile. Since Wave 3 the headline is **net**, not gross customs duty: it subtracts duty avoidance and the income-and-payroll offset CBO, JCT and Treasury apply to any indirect tax, and since Wave C retaliation is reported beside the score rather than inside it, because every target it is measured against is a conventional estimate. Since Wave F that offset is **JCT's own published year path** — 0.244 in 2025 falling to 0.241 in 2035, from CBO's `conventional-tariff-analysis-model` — rather than a round 25% cited secondhand, and the two Section 232 bases are read at **HS-10 off CBO's own annex lists** rather than from whole HS chapters: steel \$108.4B → **\$219.4B**, autos \$198.5B → **\$555.0B**. The declared bracket around the old base was wrong at both ends — 558 of the 1,180 primary article lines sit in HS-73, which the "floor" excluded, while the derivative annex lives in chapters 82-95, which HS-73 does not contain at all — so the measured base is **2.04× what had been called a ceiling**. A caption computed from the scored result says so under the number.
- **Behavioural-offset sign contract** — The scoring engine adds the behavioural offset to the static deficit effect, so an offset must carry the **same sign as the static revenue effect** to erode it. A 2026-09 sweep found 7 of the 15 implementations against that contract — three inverted (AMT, estate, PTC) and four `abs()`-ed (corporate in `reported` mode, the credits fallback, enforcement, international) — and signed six of them; `TaxExpenditurePolicy` is kept opposite-signed as a **sourced convention**, cited to CBO Option 56's own text, where both channels raise revenue. Two shipped presets moved by about 20% and each carries a caption computed from its own scored result: **Trump Corporate 15% +\$1,690.6B → +\$1,314.9B** and **Repeal ACA Premium Credits -\$966.2B → -\$790.5B**. Their validation badges dropped with them (Excellent → Poor and Excellent → Acceptable), which is the correct reading: those badges were partly bought by the defect. A follow-up provenance pass then re-sourced the corporate one to a published range and its badge is now a distance from a document rather than from the model's own answer (Poor, 121.6%); the PTC one is still measured against an untraceable secondhand figure.
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
| **🟢 Core — validated** | Revenue scoring (static + behavioral), distributional analysis (return-level CPS microsim, on CBO's household universe where the source ranks households), dynamic scoring (FRB/US-calibrated) | Benchmarked against published scores from CBO, JCT, Treasury and SSA, plus TPC, PWBM, the Tax Foundation, CRFB, Penn Wharton and RAND where no agency scored the policy. **Honest accuracy is published, not just the flattering cases:** fitted calibrated reference models reproduce official decompositions (**1.6% over 15 benchmarks**, or **12.4% over 26** with the six rows a *target revision* moved out held in place — the reading `python scripts/run_validation_dashboard.py` prints; the 7 published distributional tables span 0.00-5.86pp, two of them circular), while **38 *unfitted* module reconstructions miss by 42.3% mean** — **a figure that must never be quoted on its own line**, because two targets were *withdrawn* in Wave D and the same tier with them held in place at the error they carried on the day they were withdrawn is **60.0% over 40**, printed on the line beneath for exactly that reason; genuine *out-of-sample* predictions across **22** pre-registered cases run **11.8% mean error, 8.9% median, 17/22 within 15%, 19/22 within 25%** (`python scripts/cold_holdout.py`), and that tier is itself **eight policy classes running 4.6% to 44.5%**, each gated separately in CI. **Never read a falling mean as a better model until you know which rows left.** The out-of-sample battery shrank from 26 rows to 22 in Wave E because four targets turned out to be in no publication; the **share** within 25% rose 84.6% → 86.4% while the **count** fell 22 → 19, and a smaller battery is a weaker test however well it scores. |
| **🟡 Specialized — calibrated, narrower** | The 14 policy-area modules (TCJA, corporate, international, estate, payroll, AMT, PTC, tax expenditures, enforcement, pharma, trade/tariff, climate), state-level modeling (top-10 states), OLG generational model | Each is parameterized to reproduce a published score. Trustworthy as transparent reconstructions and for directional comparison; not independent confirmation. State and OLG use a representative taxpayer / reduced form. |
| **🔵 Exploratory — interfaces & pipelines** | Ask assistant, Real-Time Bill Tracker, Classroom Mode, multi-model pilot platform, admin dashboard, share links | Reading, teaching, and data-plumbing layers *over* the model — useful and guard-railed (e.g. the assistant is citation-disciplined and cost-capped), but **not themselves validated estimates**. The bill tracker's LLM provision extraction in particular is demo-grade. |

The dividing line is deliberate: investment goes into the green core's correctness and honest validation first; the blue tier exists to make the core usable and explorable, and is held to a UX/safety bar rather than an accuracy bar.

### Validation

Revenue validation comes in **two epistemically different kinds**, and we report them separately because conflating them overstates the model's predictive power. (Reproduce both tables live: `python scripts/cold_holdout.py`.)

#### 1. Out-of-sample predictions — the genuine test

These policies are scored **bottom-up from IRS SOI** filer counts and incomes via raw rate/threshold auto-population, with **no fitting to the official target**. This is the only tier that measures real predictive accuracy.

Fifteen of the 22 cases are the [CBO *Options for Reducing the Deficit: 2025-2034*](https://www.cbo.gov/publication/60557) battery — **15 alternatives across 12 of that report's 76 options** are expressible by the uncalibrated path; the other **64 options** carry a one-line exclusion reason. Option 56 joined in Wave 3: it had been excluded for **leakage**, because the only path that could score a cap on the employer-health exclusion ran through a module annual fitted to that same reform, and lane L6 removed that dependency — a percentile cap is now the published expenditure level times a share read off a premium distribution. Two leakage exclusions remain (Options 53 and 62). Selected rows (full table and per-case error causes in [`docs/VALIDATION.md`](docs/VALIDATION.md)):

All 22, sorted by error. Nothing is omitted: a battery that showed only its good rows would not be a validation, and the four cases Wave E withdrew are named underneath rather than quietly dropped.

| Policy | Official | Model | Error | Source |
|--------|---------:|------:|------:|--------|
| Cut international affairs 25% | -\$187B | -\$187B | 0% | CBO Options #37 |
| IIJA 2021 (discretionary component) | +\$415B | +\$414B | 0% | CBO, S.Amdt. 2137 (scored FY2022-2031) |
| All ordinary rates +1pp | -\$1,185B | -\$1,201B | 1% | CBO Options #45 |
| Cut selected nondefense discretionary | -\$339B | -\$333B | 2% | CBO Options #42 |
| Treasury 39.6% + step-up repeal | -\$322B | -\$316B | 2% | Treasury (Green Book FY2022 row, scored FY2022-2031) |
| AGI surtax 2pp (>\$100K single) | -\$1,051B | -\$1,076B | 2% | CBO Options #46 |
| End national community service | -\$10B | -\$11B | 3% | CBO Options #38 |
| New 1% payroll tax (all earnings) | -\$1,282B | -\$1,378B | 8% | CBO Options #61 |
| AGI surtax 1pp (>\$20K single) | -\$1,440B | -\$1,326B | 8% | CBO Options #46 |
| Tighten Pell grant eligibility | -\$22B | -\$20B | 8% | CBO Options #39 |
| New 2% payroll tax (all earnings) | -\$2,540B | -\$2,745B | 8% | CBO Options #61 |
| Social Security Fairness Act (WEP/GPO repeal) | +\$196B | +\$215B | 10% | CBO, H.R. 82 |
| LTCG + qualified dividends +2pp | -\$103B | -\$92B | 10% | CBO Options #47 |
| Cut certain state and local grants | -\$67B | -\$74B | 11% | CBO Options #43 |
| Fiscal Responsibility Act (discretionary caps) | -\$1,332B | -\$1,170B | 12% | CBO, H.R. 3746 |
| Limit the income-tax employer-health exclusion | -\$697B | -\$608B | 13% | CBO Options #56 |
| 1pp all brackets | -\$1,081B | -\$1,236B | 14% | CBO Options 2023-2032 #13 alt 1 (JCT estimate) |
| Top four brackets +2pp | -\$570B | -\$671B | 18% | CBO Options #45 |
| Biden top rate 39.6% (\$400K+) | -\$246B | -\$300B | 22% | Treasury (Green Book FY2025 row) |
| Biden capital income at ordinary rates | -\$289B | -\$366B | 27% | Treasury (Green Book FY2025 row) |
| Tax accrued gains at death | -\$536B | -\$346B | 36% | CBO Options #51 |
| Corporate rate +1pp (21%→22%) | -\$136B | -\$196B | 44% | CBO Options #64 (JCT estimate) |

**Every row above is a `line_item` — a figure read off a published table.** That is new: until Wave E, five rows carried targets nobody had published, and the provenance lane took each to the documents. One was **superseded** — `1pp all brackets` moved from a -\$960B "JCT rule of thumb" onto CBO publication 58164's Option 13 alternative 1, **-\$1,081B** over FY2023-2032 (report p. 72), and fell 25% → 14%. Four were **retired**, and are listed in the next paragraph rather than hidden. Note that `1pp all brackets` and `All ordinary rates +1pp` still score the **same reform**, but now against two figures CBO itself published two years apart — -\$1,081B and -\$1,185B, **9.6% apart** — where the model answers **1.0% apart**. The pair therefore measures the model's *insensitivity to the decade*, not two independent predictions.

**Four cases were withdrawn in Wave E, and a withdrawn case is never deleted.** The Warren ultra-millionaire surtax 3pp, the Medicare surcharge 2pp, the 5pp top rate above \$1M and the 2pp cut above \$500K keep their rows in `fiscal_model/validation/preregistered.py` with `retired=True`, their model figures, their withdrawn targets and the full record of the search that failed. **All four were withdrawn for absence of a document, none for the size of its error**, and the rule runs both ways: the corporate row at 44% is the battery's worst and is not at risk, because its target exists. The Medicare surcharge is the proof — it scored **1.2% from the figure Treasury actually prints**, and was withdrawn anyway because Treasury prints that figure for a **1.2 percentage-point** reform where this row applies 2pp; restated on the document's own rate it reads **39% under**, so the retirement *raised* this battery's honest error while lowering its mean. Two costs are recorded rather than absorbed: the withdrawn 2pp cut was the battery's **only rate cut and only positive target**, so it no longer tests the direction a Tailor user most often asks about, and the AGI-inclusive class is down to **two rows**.

**22 out-of-sample cases, mean abs error 11.8%, 17/22 within 15%, 19/22 within 25%** (median 8.9%; `python scripts/cold_holdout.py`). **Read that fall from 26 cases at 14.5% as a smaller battery before reading it as a better model**: four rows were withdrawn for want of a published target, the **share** within 25% rose 84.6% → 86.4% while the **count** fell 22 → 19, and a smaller battery is a weaker test however well it scores. There is deliberately no single "validated within X%" figure: the distribution has a tight core and a long tail, and it is **eight policy classes** rather than one — capital gains 18.7% (n=4), ordinary rate change 13.8% (4), corporate 44.5% (1), discretionary spending 4.6% (5), enacted-law spending 7.4% (3), payroll 7.8% (2), tax-expenditure cap 12.8% (1), AGI-inclusive surtax 5.2% (2). **Two of those class means fell by composition rather than accuracy**: AGI-inclusive surtax lost four of its six rows to the retirements, and what is left is the two CBO Option 46 rows. **Ordinary rate change then rose 12.9% → 13.8% in Wave F**, on one row and by design: Wave F gave `Top four brackets +2pp` CBO's own year-indexed statutory bracket schedule — including the 2026 revert, which moves joint floors down 3.5% while head-of-household floors rise 65.5% — and the row went 14% → **18%**, a regression registered before the file was opened. Its CI ceiling was **not** raised with it. **Each class now carries its own CI ceiling** (`--max-class-mean-error`), because a pooled mean cannot see one class regressing while the others carry it — which is what happened to the Medicare surcharge in Wave 7 and to the Warren surtax in Wave B. The model predicts ordinary and AGI-inclusive *rate* changes at conventional thresholds well (1.5-22%) and discretionary funding changes — now scored through a budget-authority-to-outlay spend-out model — well too (CBO Options spending rows 0-11%, the three enacted-law components 10-18%). The one **tax-expenditure cap** in the tier, CBO Option 56, lands at **13%** since Wave 4 gave its excess share CBO's own chained-CPI indexation instead of evaluating it once at the start year; what is left is named rather than tuned — about half of it is a **base omission** (CBO caps premiums *and* FSA/HRA/HSA contributions, and the repository's premium distribution has no account dimension) and about a fifth a **behavioural offset whose direction is now sourced and whose magnitude is not** (Wave 7 read the direction off CBO 60557 Option 56's own text; the elasticity's size remains unsourced, here and on the module's other four reforms).

**Payroll left the tail in Wave 5, and the fix was arithmetic rather than incidence.** The plan had scoped the two CBO Option 61 rows as an employer-share-and-income-tax-offset problem; CBO's own option text says the new tax "would be paid entirely by employees", so that offset does not exist. The real defect was a base built as Medicare receipts divided by 2.9% — a rate that does not raise all of them, because the 0.9% Additional Medicare Tax sits on a far smaller base. Pricing the base as CBO's own wage path times the Trustees' covered-earnings ratio took the two rows **54-56% → 7.5% / 8.1%**, the largest single move of the wave.

**Gains at death left the tail in two steps, and Wave 5 put part of it back on purpose.** Wave 2 replaced a flat \$54B/yr constant with decedent wealth × an unrealized-gain share by estate size, taking CBO Option 51 from 84% to 8%. Wave 4 then gave the death channel the six carve-outs a realization-at-death proposal does not tax — spousal, charitable, the §121 residence exclusion, tangible personal property, a family-business deferral and the per-donor exclusion, applied *after* the others — plus a rate response at death: the Green Book FY2025 row fell 135% → 17%, the FY2022 row 218% → 0.2%, and Option 51 rose 8% → **19%, worse, and pre-registered as a regression** because its 8% had been bought by taxing charitable bequests and small decedents' housing gains that no such regime reaches. **That 0.2% was never accuracy**: its own lane recorded it as two errors cancelling, one of which was a tax-year-2023 realizations base priced unchanged in every year of the window. Wave 5 removed that error — the realizations base is now grown with the accrued-gains stock it is a flow off — so the FY2022 row reads **43%** and the FY2025 row **31%**, both over-predicting and both pre-registered as regressions. **28.7 of the FY2022 row's 43.3 points turned out to be the window it was scored on** — not the "about 17" this file used to say, because the old figure discounted only the rate channel — and PR #126 moved it onto the ten fiscal years its own document covers, taking it to 18%. **Wave C then fixed the decedent headcount and the channel moved a fourth time, in both directions at once.** `estate_flow_rate` was Poterba & Weisbenner's *dollar* flow of estates used as a *headcount* rate — 408,532 decedents against roughly 3.09 million NCHS deaths — while the same module has priced the lock-in wedge off a **2.647%/yr** mortality-weighted rate since Wave 2, so it carried two death rates 8.3× apart. On the second of those the count is **3,384,194**, the $196.2B level is untouched, and a fixed per-donor exclusion bites 8.3× harder: **Option 51 20% → 35%, a registered regression**, the FY2025 Green Book row **33% → 27%**, the FY2022 row **18% → 2%**. That 2% is not accuracy — the count and the level come from the same ratio and only the count was authorised to move, and held against the module's own death-exit rate the level is 7.1× low, which points the other way. The plan's instruction to grade the rate by estate size was **refuted in sign before any code changed**: the wealthy are older, so a size-graded rate is *higher* at the top (2.84% against 2.65%) and takes the implied top count further from SOI's, not nearer.

**Waves A and B rewrote the tail, and the two rows that had been at the top of it left it entirely.** The four largest rows are now **corporate margins at 44.5%**, **CBO Option 51's gains at death at 35.5%** (20.3% before Wave C's decedent headcount landed as a registered regression), the **Medicare surcharge at 31.8%** and the FY2025 Green Book capital-gains row at **27.0%** — and the two CBO Option 46 rows that were the tier's first and third read **7.4%** and **-2.9%**. Getting them there took the two steps Wave 7 had *measured* and neither of which it built. First (PR #144) the generic base stopped being flat for ten years: every generic run had returned the same tax-year-2023 annual ten times, and it now carries the scored vintage's own nominal-GDP path, which took the two rows 49.8% → 34.1% and 37.4% → 17.9%. Then (PR #146) the AGI-stated rows started reading SOI's **AGI column** — the defect was a **unit mismatch**, selecting returns by an AGI class boundary and then subtracting the threshold from an average of *taxable* income — which took them to 7.4% and -2.9%. **The plan's own 9.1% / 1.0% endpoints were unreachable as written**: they had been attributed to a *preset* flag that cannot move a validation row, and the missing third step was the column.

**Neither lane took the flattering option, and both said so in advance.** PR #144 raised the tier mean 15.0% → **15.6%**, firing the plan's own falsification condition, because six rows had been under-predicting by *less* than a decade of the baseline's own growth is worth; the lane reported it and tuned nothing, and PR #146 then took the tier to **14.7%**, below where PR #144 found it. PR #146's column rule is likewise not the flattering one: it makes the AGI class's best-scoring row **five times worse** (Warren 5.2% → 24.8%, a registered regression) and it leaves three rows on the taxable column because their own sources say so — `medicare_surcharge_2pp`'s statutory base, wages plus net investment income, is **neither SOI column**. Moving those three anyway would read **17.8%** for the tier against the measured 14.7%, so holding them is also the lower number, and the *reason* is on the record where a document can overturn it.

**Corporate stopped being the largest in PR #121** and fell from 62%: the derived path had priced a percentage point on IRS SOI Table 11's published statutory base but aged it at a flat 4%/yr, so the base started right and grew wrong; it is now projected off CBO's own February 2024 corporate receipts path with a §6655 convolution, which took the row to 44.5% and the window-average marginal share from 90.8% of the vintage's own average base to **80.8%** — a point of rate can no longer be scored against more base than the baseline implies exists. What is left of that residual is not a defect the module can close from a published source: PR #120's memo transcribed 18 published corporate-rate estimates and found the spread is an **estimator** difference (JCT, not CBO, produces every *Options* corporate row) times a **scope** difference (Treasury's 28% row bundles a GILTI step), and on the comparable metric the record reads Tax Foundation 55.1%, JCT 55.9%, PWBM 64.4%, Treasury 79.5% — with this model above every published estimator. **Wave B ships that record on the app's own corporate surfaces** (PR #143): a headline corporate run now prints the four houses' scores converted to its own rate step and says where it sits among them. That surface also produced a measurement worth having — in `derived` mode the model lands **inside** the published span at the +7pp step every shipped preset uses and outside it at +1pp, where `reported` is outside at every step. **Wave F acted on it: `CORPORATE_APP_MODE` is now `derived`.** The decision rule was fixed before the lane implemented anything and required *both* metrics to favour `derived` — mean error over the three published corporate targets (**61.43%** against **62.75%**) and the +7pp estimator-span position (inside, against $47.27B outside and larger than all four houses) — with no tie-break and no re-weighting. Three things belong beside that default and the module docstring carries all three: `derived` wins the mean while **losing two rows of three**, and the row it wins is the only one whose *scope* matches what the factory builds; **neither mean is small**, so this is a choice between two wrong answers taken on a rule set in advance; and **nothing was retuned**, the fitted constant reading 1900.0 before and after. The lane's own headline mechanism — CBO's published loss-firm haircut — was **sourced and then refused on the merits**, because it adjusts a *rate* inside a user-cost expression while this module multiplies a base that already nets those losses; CBO itself divides the factor back out where the other input carries it, "to avoid double-counting". Two shipped corporate presets moved with the flip: **Biden Corporate 28% -\$1,397.2B → -\$1,310.9B** and **Trump Corporate 15% +\$1,491.8B → +\$1,562.8B**.

**The FY2022 Green Book capital-gains row is now scored on the ten fiscal years its own document covers** (PR #126): the target does not move, the *shape input* does, under the same supersede rule IIJA's `.v2` row used — and the offset turned out to be **28.7 of the row's 43.3 points, not the "about 17" this repository had been quoting**, because the old figure discounted only the rate channel and the death channel both grows and does not grow proportionally. Its control is the FY2025 row, same shape and module on its own window, whose offset is exactly zero. The same mechanism would take IIJA 18.2% → 0.3%; that number is published in the memo precisely so the decision not to take it is a visible choice rather than a silent one. Misses are kept, not tuned away, and each carries a documented structural cause. Three of the cases replicate laws that actually passed — the Social Security Fairness Act, the Fiscal Responsibility Act's discretionary caps and IIJA — always as *components* whose annual level or authorization schedule the CBO estimate itself states, never as a bill total no single shape can construct. Every case is **pre-registered** ([`fiscal_model/validation/preregistered.py`](fiscal_model/validation/preregistered.py)) *before* the commit that first scores it, and the tier is **CI-gated** (`--max-mean-error 15 --min-within-25pct 19`, set by Wave E's provenance lane when the battery shrank and re-derived after Wave F by the workflow's own rule and **downward only**: ceiling `ceil(11.8 × 1.25) = 15`, which rounds to 15 and re-derives to itself; the floor would derive to `19 - 1 = 18`, which **loosens** a gate the battery meets with no slack, so it stays at 19. Read `20 / 22 → 15 / 19` as a smaller battery rather than a relaxed gate — the comparable figure across a battery that changes size is the *share* within 25%, and it rose). **A second, per-class gate runs beside it**, one ceiling for each of the eight classes above, derived from each case's own benchmark record rather than a hand-kept list — and it fails if the battery ever contains a class nobody gated. Wave C tightened exactly one of its eight ceilings, **capital gains 26 → 24**; Wave F tightened none and held `ordinary_rate_change` at **15**, where its own re-derivation would now allow 18. Treat uncalibrated custom rate policies as **directional, ±15-25%**.

One case left the battery in the provenance pass and two changed target. **Top rate to 45% was retired**: its -\$420B is in no TPC, CBO or JCT publication (TPC's full sitemap contains no 45%-ordinary-rate table at any date), so it is withdrawn rather than scored against a number nobody published — and the figure is gone from the app's score map too. **Biden capital gains was re-sourced** from an unsupported -\$456B to the FY2025 Green Book's actual combined row, -\$288.6B, with the shape corrected to that document's own definition (taxable income over \$1M; a \$5M per-donor exclusion for gains at death, not \$1M) — which moved its error from 79% to 142% before Wave 4's carve-outs brought it to 17% under and Wave 5's realizations projection to **31% over**. **Biden's top rate moved in Wave 4** from a rounded -\$252B to the Green Book's own printed row, **-\$245.9B** (\$245,924M, report p. 242), through the manifest's new-row supersede rule; nothing in the model reads the target, the prediction is the same -\$216.5B it was, and only the error column moved (14% → **12%**).

#### 2. Calibrated reference models — transparent reconstructions, not independent confirmation

The specialized modules (TCJA, Corporate, Estate, Credits, AMT, Payroll, PTC, Capital Gains, Tax Expenditures) are parameterized so their components **reproduce a published decomposition** — usually CBO's, JCT's or Treasury's, but the fitted benchmarks also include the Social Security Trustees, PWBM and the Tax Foundation where no agency scored the policy. Across the **16** benchmarks a module is actually fitted to, the mean absolute error is **1.5%**, 16 of 16 within 15% — but that low error is **expected by construction**. These are useful as auditable, source-linked reconstructions of official scores, *not* as evidence the model would have predicted them cold.

**Never quote the 15 without saying which rows left.** **Five** mechanisms move rows out of this tier now and all are live. First, `ScorecardSummary.revised_target_entries` is **22**: twenty-two calibrated targets have been corrected through the Tier-2 revision ledger ([`fiscal_model/validation/target_revisions.py`](fiscal_model/validation/target_revisions.py)), and a constant fitted to a superseded figure is not fitted to its replacement — so those rows move out of the fitted tier and into the reconstructions below. **Wave 4's provenance pass alone moved five that way (28 → 23)**: `biden_eitc_childless`, `eliminate_salt`, `extend_enhanced_ptc`, `ira_enforcement` and `repeal_salt_cap`, each mechanically, none retuned to close the new gap. Held in place *at the time*, the tier read **28 benchmarks at 3.0%, 27 of 28 within 15%** (the live held-in-place reading is below, and it is now 27 at 11.9%, because Wave B moved five more targets onto documents). Second, **Wave 2 moved the three capital-gains scenarios out (33 → 30)**: deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural tuples removed the only constants ever fitted to those three targets, so `calibrated_to_target` is now simply `False` for them and they report as reconstructions. Third, **Wave 3's L8 lane moved the two Trump tariff rows out (30 → 28)**: `universal_coverage_rate` and `china_effective_coverage` were fitted to those two benchmarks, and once the first became a Census measurement and the second was deleted outright, no `TRADE_BASELINE` constant is fitted to anything. Fourth — and this one is not the ledger's — **the offset-sign sweep moved two more out (23 → 21)**: `trump_corporate_15` and `repeal_ptc` were reclassified `calibrated_to_target=False` in PR #119, because each annual had been fitted so that `static × (1 + offset share)` hit the target and signing the offset took the score to `static × (1 − offset share)`. **A constant that reproduced its target only through a defect is not a calibration to that target**, so neither was retuned and neither got a readiness exemption. **Wave B's provenance pass then moved five more out (21 → 16)** — `ss_donut_250k`, `tcja_rates_only`, `trump_china_60`, `eliminate_estate_tax` and `eliminate_mortgage`, each when its target found a document, none retuned. Held in place, the tier reads **27 at 11.9%, 22 of 27 within 15%**, where the same line read 27 at 5.6% before Wave B; **the whole of that 6.3pp is five untraceable targets finding their documents**, with `ss_donut_250k` at 89.2% and `tcja_rates_only` at 44.3% most of it. The fitted mean *fell* 2.8% → 2.2% → 2.0% → 1.6% → 1.7% → **1.5%** across every one of those moves while nothing ever improved, because each row that left was one this tier had been carrying — the five Wave B moved out averaged **2.42%**, above the tier's own mean. That is a change of **composition, not of accuracy** — read it next to the reconstruction tier below or not at all. **And the reading that is not composition at all**: the 21 rows this tier held before Wave B, scored on the targets Wave B leaves behind, read **9.82%, 18 of 21 within 15%** — which is what five untraceable targets had been worth to its headline.

The calibrated tier also carries **38 module reconstructions nothing was fitted to** — the international, trade, pharma, IRS-enforcement and climate presets wired in during Phase E (now including the two reclassified tariff rows), the eight P.L. 119-21 JCT line items added in Phase D, the rows the revision ledger moved out of the fitted tier, the three capital-gains scenarios Wave 2 unfitted, the two the offset-sign sweep reclassified, and the second corporate benchmark PR #122 registered. Those miss by **42.3% mean / 30.1% median**, 11 of 38 within 15% — **and that figure must never be quoted on its own line.** Wave D *withdrew* two targets from this tier, a 93.3% row and a 701.0% row, which on its own arithmetic buys **18 points of "improvement" for nothing**; `python scripts/run_validation_dashboard.py` therefore prints the same tier with both rows folded back at the error they carried on the day they were withdrawn — **60.0% over 40** — on the line beneath, so quoting the smaller number requires skipping a line. It also prints **fifteen** finer sub-populations, which is why the tier must never be quoted as one number either way. What the withdrawal genuinely changed is that this tier's `model_estimate` target count went **2 → 0**, so no row it reports is now scored against this model's own output. **Wave C's 1.2pp rise is accuracy and the constant-population reading says so**: the same 39 rows sit in the tier either side, and all of the movement is the `Trade` sub-population going **34.2% → 43.6%** when PR #150 took retaliation out of a score measured against conventional targets. That was registered as worse in advance, `steel_tariff_25` carries the whole of the net (11.89% → **75.28%**, against a target that is untraceable and has been examined-and-left twice), and on the **four trade rows that have a document the mean improves 39.72% → 35.66%**. **Wave F then moved the tier again, on accuracy, by more than any wave before it**: the same 38 rows sit in it either side, so **37.5% → 42.3% is like-for-like**, the median and both within-counts are unchanged, and three quarters of the movement is `steel_tariff_25` alone going 75.3% → **258.1%** when its base moved from two whole HS chapters to CBO's own HS-10 Section 232 annex — against the same untraceable target, so **that number measures the base becoming the one the statute reaches and measures nothing about the score**, while the four documented trade rows move 35.66% → **36.16%**. The rest is the corporate default flipping to `derived`, which takes the FY2022 rate-only row 62.9% → **50.7%** and gives up `trump_corporate_15` 121.6% → 129.6%. **Wave B's 2.4pp fall, by contrast, was composition and its constant-population reading says so**: on the same 34 rows the new targets read **58.26%**, *worse*, and the whole 0.38pp of that is `trump_china_60`; the tier's mean fell only because the five arrivals average **36.42%**. The single honest number for what the new targets did to the model's measured error is that 0.38pp, against 2.42pp of composition. **Wave 7 is the first round in which this tier's mean moved on accuracy rather than composition, and the difference is worth stating.** The same 34 rows sit in it before and after, so **57.6% → 57.9% is like-for-like**, and all of the 0.33pp is `repeal_ptc` going 18.5% → **29.6%** when PR #131 replaced a fitted $83.0B/yr — which was the carried target run backwards through the engine's growth factor — with CBO/JCT publication 51298's own annual credit path, net of publication 60437's published 19.28% of offsetting effects. It is a registered regression, and the whole $326B of it decomposes into three published steps rather than a residual. The composition readings still stand behind that: on the **33 rows the tier held before PR #122** the mean is **57.4% / 29.9%**, and on the **31 it held before PR #119** it is **56.6% / 29.9%**. The whole of that 56.6% → 57.4% step is `trump_corporate_15` going 22.3% → **121.6%** when its target stopped being the model's own output and became the published PWBM/Tax Foundation range; the remaining 0.2pp is the new FY2022 corporate row arriving at 62.9%. Behind those, the Wave 4 readings still stand: on the **26 rows the tier held before Wave 4** the mean is **65.7% / 40.5% median**, *worse* than the 61.8% / 38.0% it read before; on the **14 sectoral rows the subset already held** it is **88.2%**, not 82.6%. The reason is named rather than smoothed: Wave 4's pharma rebuild (three federal Part D channels, a negotiation ladder fitted to all three published CMS cycles, a RAND coverage base) **took two rows further from their targets** — expanded negotiation 25.7% → **93.3%** and international reference pricing 646.2% → **701.0%** — because the lane's own ladder condemned an unsourced \$220B Part D gross-spending constant that the reference-pricing leg also reads, and the lane took the sourced \$281B and reported the miss rather than keeping a number that flattered it. The insulin row is unchanged at 39.0%. Each row carries a `known_limitations` note; none was retuned. The universal insulin cap scores **+\$7.0B** against CBO's own **+\$11.4B** (publication 57957) — a deficit *increase* on both sides — where the repository used to carry a -\$15B saving that pointed the other way and made the row read 146%. The P.L. 119-21 block is the sharpest of these: the TCJA module reproduces CBO's \$4.6T aggregate to **0.4%** and JCT's own provision rows to **35.8%**, because its single calibration factor is fitted to the aggregate and to no individual row. **Wave 5 moved neither calibrated tier**: its three lanes all worked at the out-of-sample margin, no target was moved and no constant was retuned, so 0 of the 23 fitted rows and 0 of these 31 changed — a falsification test each lane registered in advance and passed. **PR #121 did the same at the corporate margin**, moving one out-of-sample row and 0 of the 21 fitted and 0 of the 33 reconstructions the tier then held.

**Where the targets come from.** The provenance pass opened the primary documents rather than inspecting the citations, and **Wave 4 finished the job it started**. By provenance the **55** calibrated targets are now **36 `line_item` / 8 `line_item_differs` / 7 `secondhand` / 4 `model_estimate`**, where before Wave 4 they were 19 / 13 / 15 / 7 and before Wave B 30 / 7 / 12 / 6. **Wave B met one of the plan's two provenance criteria and came one row short of the other**: `model_estimate` 6 → 4 (target ≤ 4) and `secondhand` 12 → **7** (target ≤ 6), the seventh being a locked-holdout id with nothing to move to. **Thirteen targets moved onto their documents in Wave 4 and none of the seven rows that still disagree is an open question**: three are range revisions carrying an in-range anchor (Pillar Two, reciprocal tariffs, Trump corporate 15%), three are explicit **examined-and-left** verdicts (`EXAMINED_NOT_REVISED`, **fourteen** entries after Wave B) and one is a **scope** verdict, where the figures agree to 0.2% and the reforms do not. **Twenty-two targets have been moved** — not edited, but superseded through the Tier-2 revision ledger, which keeps the old figure on the record as a `superseded_by` row. The first three: the universal insulin cap from -\$15B to CBO 57957's **+\$11.4B** (a \$35 cost-sharing cap *adds* to the deficit), TCJA AMT relief from \$450B to CRS R48286's **\$1,357.1B** (a five-year cost sitting in a ten-year column), and Pillar Two adoption from a -\$80B point to JCT JCX-22-23's **published range [-\$102.6B, +\$56.5B]**, inside which the model's -\$61.2B sits at distance \$0.0B — so its 23.5% against -\$80B is a distance from an editorial midpoint, not a measurement of accuracy. Wave 4 moved twelve more, ten of them a rounded headline standing in for a printed row (the SALT deduction to CBO Option 49's **-\$1,621.0B**, the SALT cap to PWBM Table 3's **+\$1,169.0B**, GILTI reform to **-\$373.9B**, FDII repeal to the Green Book's gross **-\$158.0B**, the international package to **-\$632.2B**, childless EITC to **+\$162.6B**, IRA enforcement to CBO 58390's **-\$180.4B** in place of a figure CBO had *withdrawn*, EV credits to **-\$182.3B**, enhanced PTC to **+\$335.0B**, the universal tariff to Tax Foundation FF861's **-\$2,171.1B**), and two that were a different kind of error: the auto tariff's -\$100B was a **per-year** claim in a ten-year column (now Tax Foundation's -\$386.2B), and the reciprocal-tariff target was **Tax Foundation's dynamic score sitting in a conventional column** — a *tier* error no rescaling would have found, now the range **[-\$1,800B, -\$1,400B]** on which CRFB, Tax Foundation and Yale disagree by 29%. **Six of the thirteen got worse**, which is the shape a correct provenance pass has: if every revision improved its row, the documents would look chosen to fit. **Wave B (PR #145) moved the six most recent and five of the six make their row worse**, which is the shape a correct provenance pass has: the \$250,000 Social Security donut from -\$2,700B to CBO Option 62 alternative 2's **-\$1,426.8B** (same design, this repository's own window, 47% below the carried figure — 0.0% → **89.2%**, and the 0.0% it replaced was `payroll.py`'s own comment, `2_177.0  # 270 / 0.124`); TCJA rates-only from \$3,185B to CRS R48286's **\$2,158.7B** (2.2% → **44.3%**, out of a table this repository already reads another target from); the 60% China tariff to CRFB's **-\$650B**; estate repeal to Tax Foundation *Options 3.0*'s **+\$407.2B**; the mortgage deduction to the **range [-\$495.0B, -\$367.9B]**; and IRA credit repeal to **-\$851B**, whose old 0.0% was arithmetic — the module's annual *was* the target. **The sharpest result of that pass is a refusal the mechanism made rather than the author**: a Tax Foundation figure for cap elimination is -\$3,200.0B *to the digit the carried target states*, so the ledger rejected it — "a revision that restates the old target is noise" — and rightly, since the module's constant is documented as a window-average of that very figure.

**Seven rows still could not be traced at all**, down from twelve, and **the five that left did so by finding a document, never by deciding a model estimate was good enough**. Three of the findings are worth carrying: the claim that *"OCACT publishes no ten-year dollar amount for any payroll provision"* was **too strong and this repository had been making it** (an OCACT letter of July 2023 prints \$3,035.1B — for a \$400,000 donut, so not a line item for either row, but the claim needed narrowing); `eliminate_mortgage`'s two-and-a-half-fold spread was **the standard deduction, not the simulator** (Yale's \$1.2T is scored pre-P.L. 119-21, where the itemising population roughly doubles); and `cap_employer_health`'s -\$450B is most likely **a real published figure for a cap a third the size, a decade early** — CBO's 2008 *Budget Options* Option 9, JCT-scored at \$452.1B for a \$17,280/yr cap against this benchmark's stated \$50,000 — with the difference that there is nothing to move it *to*. The remaining **4 are illustrations with no official score at all** and are excluded from every count: the honest published-benchmark count across both tiers is **73 of 77**. **Both halves of that pair fell by four in Wave E and it is the same four rows** — the out-of-sample retirements — so 77/81 → 73/77 is a battery losing four unsourced cases, not four documents going missing. The whole of the `secondhand` reduction from 12 to 7 is the out-of-sample tier's own count going **5 → 0**; every remaining `secondhand` row is in the calibrated tier and each still needs the same per-target judgement.

**The `retire` state was applied for the first time in Wave D, and the arithmetic it was built around is why it is safe.** Withdrawing the two pharma rows takes 93.3% and 701.0% out of the reconstruction tier and buys **18 points of "improvement" by deletion**, which the plan forbids — so a retired row keeps its scorecard entry and its model figure, and can leave the tier mean **only alongside a second reading** with the withdrawn rows folded back at the error they carried, printed by both reports on adjacent lines. The two withdrawn are `expand_drug_negotiation` (-\$500B, the repository's own extrapolation from a figure that was never a negotiation score but CBO's total for a whole title) and `international_reference_pricing` (-\$100B, derived from a **RAND price index**, which is a price statistic and not a budget score). `test_nothing_is_retired_yet` was inverted into a test that pins the retired set in both directions. Two further candidates are named and not acted on: `carbon_tax_50` and `eliminate_step_up`. See [`docs/VALIDATION_NOTES.md`](docs/VALIDATION_NOTES.md) §7 and §8.

| Policy (calibrated) | Official | Model | Error | Tier |
|--------|---------:|------:|------:|------|
| TCJA Full Extension | \$4,600B | \$4,582B | 0.4% | fitted |
| Biden Corporate 28% | -\$1,347B | -\$1,293B | 4.0% | fitted |
| Repeal Corporate AMT | \$220B | \$220B | 0.0% | fitted |
| Cap Employer Health | -\$450B | -\$450B | 0.1% | fitted |
| SS Donut Hole \$250K | **-\$1,427B** | -\$2,700B | **89.2%** | reconstruction |
| TCJA Rates Only | **\$2,159B** | \$3,115B | **44.3%** | reconstruction |

**The last two rows are the point, and they belong beside the first four.** Both printed 0.0% and 2.2% until Wave B, against targets nobody had published; both now carry a document, neither constant was retuned, and the miss is a finding rather than a regression. A fitted 0.0% anywhere above them is bookkeeping.

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
- **CBO Baseline** — 10-year revenue, spending, and deficit projections, **transcribed from CBO's own tables** in the [`US-CBO/cbo-data`](https://github.com/US-CBO/cbo-data) repository, pinned by commit and verified by SHA-256 per file. The default February 2026 vintage is [publication 61882](https://www.cbo.gov/publication/61882), *The Budget and Economic Outlook: 2026 to 2036*, through CBO's 51118 data release; it reproduces that report's own headlines (FY2026 -\$1,852.7B, FY2027-2036 -\$24,406.0B, FY2036 -\$3,115.4B). The app quotes **-\$23,143.3B** because it sums the same table over its own **FY2026-2035** window — CBO's headline ten-year window is FY2027-2036, so the two are different decades of one table rather than a disagreement. `VINTAGE_SOURCING` grades every vintage **per line**: February 2024's economic path is transcribed but CBO publishes no `ten_year_budget` file for that edition, so its budget levels remain a reconstruction and **its debt/GDP ratio is a mixture that should not be quoted**.
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

23 hand-maintained Markdown files live in `fiscal_model/assistant/knowledge/` — 22 topic snapshots plus the corpus README, all of them indexed. Each carries a frontmatter `source:` URL the assistant uses for citation. To add or refresh a snapshot, use the helper:

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
| CBO Baseline | February 2026 (publication 61882, transcribed from `US-CBO/cbo-data`) | Quarterly with CBO publications |
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
