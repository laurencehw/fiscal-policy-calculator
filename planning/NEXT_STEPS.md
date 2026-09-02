# Next Steps — Fiscal Policy Calculator

> Roadmap last reviewed April 2026; the validation scorecard below was re-derived 2026-09-02. This file tracks roadmap items beyond the current shipped branch.

For a manuscript-focused path to citation-grade quality, see [MANUSCRIPT_95_PLUS.md](MANUSCRIPT_95_PLUS.md). For repo-grounded go/no-go gates on the two biggest upgrades, see [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md).

For the ranked plan to close the errors the validation expansion exposed - by modelling the mechanism, never by tuning to the held-out targets - see [MODELING_IMPROVEMENT.md](MODELING_IMPROVEMENT.md).

---

## Current state (April 2026)

**Large automated test suite, 85% enforced coverage gate, and a four-tier
validation scorecard.** There is no single "validated within 15%" figure — that
phrasing was on this line until 2026-09-01 and was wrong. Live numbers from
`python scripts/cold_holdout.py`, `python scripts/run_loo.py` and
`python scripts/run_validation_dashboard.py`:

| Tier | What it measures | n | Mean | Median |
|---|---|--:|--:|--:|
| Out-of-sample, pre-registered | prediction | 26 | **31.0%** | 15.1% |
| Calibrated, fitted | bookkeeping (low by construction) | 28 | **2.0%** | 0.1% |
| Unfitted module reconstructions | modules vs targets never fitted to | 26 | **61.8%** | 38.0% |
| Calibrated, leave-one-out | how much of the calibration is structure | 18 | **28.4%** | 16.5% |

**Three of those four changed population in Wave 3, so the like-for-like
readings belong beside them**: the reconstruction tier is **63.6%** over the 24
rows it held before L8, its sectoral subset **87.8%** over the 12 it held, and
leave-one-out would read **29.5%** over 17 had `eliminate_salt` not been
readmitted. A mean that moves because the population moved has not improved.

**The fitted tier has lost six rows, and every reason must be quoted with the
number.** One left when a target it was fitted to was corrected:
`ScorecardSummary.revised_target_entries` is **3**, a constant fitted to a
superseded figure is not fitted to its replacement, and the revised TCJA-AMT row
therefore reports among the reconstructions. Held in place instead the fitted
tier reads **29 at 4.3%, 28/29 within 15%** — quote either, never one alone.
Three more left in Wave 2, when deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural
tuples removed the only constants ever fitted to the capital-gains scenarios.
Two more left in Wave 3, when L8 turned `universal_coverage_rate` into a Census
measurement and deleted `china_effective_coverage` outright, so the two Trump
tariff rows stopped reading 1.1% and 6.2% off constants fitted to them and now
read 37.1% and 44.3%. The fitted mean *fell* 2.8% → 2.2% → **2.0%** because every
row that left was one it had been carrying, which is **composition, not
accuracy**. The reconstruction tier is itself four populations — 14 sectoral
presets at 81.0%, 8 P.L. 119-21 line items at 35.8%, 3 capital-gains scenarios at
39.6% and that revised row at 66.8% — and must not be quoted as one number. The
leave-one-out tier went 18 derivable → 17 in Wave 2 when `eliminate_salt` tripped
the leakage guard, and **back to 18 in Wave 3** when PR #100 replaced the leaked
constant with its SOI computation. Distributional accuracy is separate again: 7
published CBO/JCT tables at **0.00-7.77pp**, two of which are circular, with the
ARP row rising 4.76 → 7.77 because the Recovery Rebate moved onto the same
universe as the other two components. See
[`docs/VALIDATION.md`](../docs/VALIDATION.md).

*Re-derived 2026-09-02, after Wave 3 (PRs #98–#102). Tier 1 moved 52.6% → 34.4%
on the eight spending rows in Wave 1, 34.4% → 31.3% on the four capital-gains
rows in Wave 2 — gains at death alone went 84.4% → 8.4% — and 31.3% → **31.0%**
in Wave 3 by *adding* a case rather than moving one: CBO Option 56 stopped being
a leakage exclusion and entered at 24.0%, taking within-25 to 19/26 and the CI
gate to `--max-mean-error 40 --min-within-25pct 18`. Leave-one-out rose
59.3% → 61.7% on the two AMT rows (the AMT module becoming more structural rather
than less accurate), fell to 58.7% when the AMT extension's target was corrected,
fell to 32.3% in Wave 2 on three rebuilt modules, and fell to **28.4%** in Wave 3
on one more rebuilt module pulling against one provenance fix — credits
45.1% → 20.5%, expenditures 28.8% → 30.2% with a case readmitted. The
reconstruction tier went 250.8% → 82.6% on two pharma rows, then to 21 rows at
76.7% on two target corrections, then to 24 rows at 72.1% when the capital-gains
scenarios arrived from the fitted tier, and then to **26 rows at 61.8%** on L8's
gross→net tariff change, L9's FDII identity and the two reclassified tariff rows.
See [`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) §§5.1, 5.2 and 5.3.*

### Completed work

**Foundation + Sprints 1–5 (March–April 2026)**
- CBO February 2026 baseline with vintage selector (Feb 2024 / Jan 2025 / Feb 2026)
- Sprint 1: Tariff scoring — 5 presets, consumer price impact display, 45 tests
- Sprint 2: Microsimulation hardening — MFJ brackets, SALT, AMT, EITC, NIIT
- Sprint 3: FastAPI endpoints (`/health`, `/presets`, `/score`, `/score/preset`, `/score/tariff`)
- Sprint 4: Test coverage 57% → 72% (131 new tests)
- Sprint 5: `scripts/update_data.py`, `scripts/batch_score.py`

**Horizon features (April 2026)**
- Feature 1: OLG model — 30-period Auerbach-Kotlikoff-style, SS/Medicare reform, generational accounting
- Feature 2: Classroom Mode — 7 assignments (intro → advanced), OLG exercises, PDF export, relative validation
- Feature 3: State-Level Modeling — top 10 states, SALT interaction, combined rate curves
- Feature 4: Real-Time Bill Tracker — congress.gov pipeline, LLM provision extraction, SQLite storage, Streamlit UI

## Modelling plan: Waves 1-3 complete (2026-09-02)

[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) Wave 1 landed 2026-09-01/02
(PRs #83, #85, #86, #87, #88): the budget-authority-to-outlay spend-out model
(L2), the AMT live exemption branch and published year-indexed path (L5), pharma
federal incidence (L7), IIJA's superseding authorization-path row, and spend-out
for the app's own spending presets. §5.1 of that file has the outturn and the
three findings.

**The AMT / insulin target provenance lane closed two of its three targets**
(PR #90, 2026-09-02). `extend_tcja_amt` moved $450B → **$1,357.1B** (CRS R48286
Table 1, transcribing CBO 60114/60271) and `universal_insulin_cap` −$15B →
**+$11.4B** (CBO pub. 57957), both through a new Tier-2 supersede ledger,
`fiscal_model/validation/target_revisions.py`, which mirrors `preregistered.py`'s
rule: ledger entry in one commit, first scoring in the next, old figure kept as a
`superseded_by` row. **No constant was retuned and no threshold moved.**
`KNOWN_TARGET_SIGN_INVERSIONS` is now empty, and the emptiness is the assertion.
`AMT_APP_MODE` and `AMT_SCORECARD_MODE` both stay `reported` — 22.3% reported
against 54.2% derived across the three AMT benchmarks, which is Decision 1's own
rule — so nothing a user sees changed.

**Wave 2 landed 2026-09-02** (PRs #93, #94, #95): L4 estate replaced a
two-point taxable-estate blend that was *exactly invariant* in the exemption with
a SOI-fitted Pareto size distribution; L6 tax expenditures made every cap declare
its unit and gave each expenditure a transcribed benefit distribution; L1 capital
gains rebuilt the realizations base (IRS SOI Table 3.5), the elasticity (the
semi-log **tax-rate** form CRS R48562 defines — the frozen 0.8 had been applied
as a net-of-tax elasticity and was an effective 0.25), lock-in (a derived 1.44×
price wedge in place of the 5.3× multiplier) and gains at death (a
decedent-wealth stock in place of a flat $54B/yr). Tier 1 **34.4% → 31.3%**, LOO
**58.7% → 32.3%**. §5.2 of that file has the outturn, the four findings and the
three missed bands.

**Wave 3 landed 2026-09-02** (PRs #98, #99, #100, #101, #102) and completes the
plan.

- **L9 international** (PR #98) added a jurisdiction-level base-overlap term and
  gave FDII repeal the same base × rate identity the module's rate branch already
  used. **Two rows got worse on purpose and the lane registered both before
  opening a file**: `fdii_repeal` 15.0% → **44.65%** and the package
  41.0% → **49.47%**, because the identity is built on Treasury OTA's published
  $130,230M cost and the carried −$200B is 54% above it. The double count the
  plan named turned out not to exist — the UTPR reads foreign-parented profits
  and GILTI reads US-parented CFC income, so the overlap term nets exactly zero
  for every shipped factory — and the package's real residual is a **level**: a
  $15B UTPR against Treasury's own $136,313M row and JCT's implied $133.9B.
- **L8 tariffs** (PR #99) took the score **gross → net**: duty avoidance, the 25%
  income-and-payroll offset CBO/JCT/Treasury apply to any indirect tax, and the
  receipts lost to retaliation, on Census 2024 levels and a tax-inclusive rate.
  The three unfitted rows fell from a summed 353.5 points of error to **110.5**
  (auto 152.3% → 82.2%, steel 73.2% → 11.9%, reciprocal 128.0% → 16.4%), the two
  *fitted* coverage constants were re-derived or deleted so both Trump rows left
  the fitted tier and now read 37.1% and 44.3%, and the lane found and fixed a
  **sign defect** that made a tariff *cut* raise the deficit. Per **Decision 6**
  every shipped preset moved 28–49% and the user-facing caption shipped in the
  same PR.
- **L3 credits / microsim** (PR #101) replaced `Δcredit × units × participation`
  with two statutory parameter sets run through `MicroTaxCalculator` over CPS
  ASEC tax units and differenced on final liability: module LOO
  **45.1% → 20.5%**. Per **Decision 4** the raw 148 MB ASEC archive is fetched by
  script (`scripts/fetch_cps_asec.py`, SHA-256 verified) into a cache outside the
  repository and never vendored, with five dependent age bands added and every
  pre-existing column byte-identical; per **Decision 5** the three tautological
  credit benchmarks now carry a per-case declaration. The **ARP distributional
  benchmark got worse, 4.76pp → 7.77pp**, and that is the finding: the old figure
  was ranking one of three components by IRS return counts and the other two by
  CPS tax units, and the two universes were partly cancelling.
- **PR #100** (target provenance) moved five targets onto their documents:
  **CBO Option 56 promoted into Tier 1** at 24.0% now that L6 removed the leakage
  its only path ran through; **Pillar Two re-benchmarked as JCT's published
  range** [−$102.6B, +$56.5B], which the model sits inside; the leaked
  `annual_cost_no_cap = 120.0` replaced by **$89.55B** computed from SOI Table
  2.1; the **estate** target examined and deliberately left, with both errors
  recorded under a new `EXAMINED_NOT_REVISED` state; and the **Treasury FY2022**
  combined-row reading confirmed.
- **PR #102** re-derived the Tier 1 CI gate by the workflow's own rule after the
  battery grew: `--max-mean-error 40 --min-within-25pct **18**`.

**Every Wave 3 module keeps `reported` as its app default under Decision 1.**
The only shipped numbers that moved are the five tariff presets, and they moved
because the *score* changed rather than because a default did.

### Next: the carry-over list, sequenced by the owner

There is no Wave 4 in the plan. What is left is a single list of open items at
[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) **§6.2**, which supersedes
§6.1 and covers: the holdout-protocol re-lock; `repeal_individual_amt`'s
unsourced $450B; `repeal_salt_cap`'s unsourced $1,100B (now −29.4%) and the
contradictory baselines the two SALT benchmarks are scored against; the mortgage
record's unsourced `annual_cost_no_limit = 100.0`; `ctc_extension` against JCT's
+$816.8B line item; the 12 remaining `line_item_differs` rows; Option 56's
year-indexed excess share and its two payroll alternatives; re-basing the UTPR on
OECD CbCR aggregates (blocked by 403s) and GILTI's two calibration constants; a
GDP-feedback channel for tariffs; L7's Part D channels; L5's phase-out
thresholds; L1's death-channel behavioural response; the estate growth lever; the
tax-unit-versus-household distributional universe; CBO's account-level spendout
rates as the L2 cross-check; the alternatives CSV's revenue sub-row sign
artifact; the dead `PHARMA_VALIDATION_SCENARIOS` registry; and the four
capital-gains `known_limitations` notes that still describe the pre-Wave-2
mechanism. **Sequencing is an owner call**, which is why they are one list rather
than a wave.

## Immediate next moves (next 2-3 weeks)

Before committing to the full CPS microsimulation build or the full multi-model platform, run the feasibility gates first.

Starter commands:
- `python scripts/run_feasibility_audit.py --json`
- `python scripts/run_feasibility_audit.py --include-model-pilot`
- `python scripts/run_feasibility_audit.py --include-model-pilot --strict`
- `python scripts/run_feasibility_audit.py --include-model-pilot --use-synthetic-cbo`
- `python scripts/run_feasibility_audit.py --include-model-pilot --no-top-tail-augmentation`
- `python scripts/run_feasibility_audit.py --include-model-pilot --include-experimental-pwbm --strict`

### CPS microsimulation feasibility sprint
- [ ] Audit current `fiscal_model/microsim/` inputs, tax-unit construction, and weighting assumptions
- [ ] Confirm whether `tax_microdata_2024.csv` is reproducible from source CPS files
- [ ] Wire one interaction-heavy benchmark through the microsim path
- [ ] Decide whether the current stack is strong enough for a full CPS migration

### Multi-model feasibility sprint
- [ ] Audit the current `BaseScoringModel` / `ModelResult` abstractions
- [ ] Wrap one microsim-style engine and one PWBM-style path behind a common comparison contract
- [ ] Run one preset policy through 2-3 engines outside the current static-vs-dynamic UI
- [ ] Resolve any PWBM blockers from `scripts/run_feasibility_audit.py --include-model-pilot --include-experimental-pwbm --json`
- [ ] Decide whether the repo is ready for a true side-by-side comparison feature

### Go/no-go memo
- [ ] Write a short memo covering risks, effort, reproducibility, and recommended sequencing
- [ ] Use that memo to choose whether CPS or multi-model work starts first

## Genuine next priorities

### Multi-model comparison platform
Run the same policy through distinct CBO-style, TPC-style (microsim), and FRB/US/PWBM-inspired engines side by side. This remains a roadmap item; the current UI only compares the existing conventional and dynamic scoring paths.

### CPS microsimulation
Replace IRS bracket-level aggregates and synthetic tax units with CPS ASEC microdata for distributional analysis. This remains the highest-leverage methodological upgrade for AMT + SALT + CTC interaction accuracy.

### Additional policy modules
- **Climate/energy** — IRA clean energy credits, carbon pricing, EV incentives
- **Immigration** — Workforce effects on payroll tax base and GDP
- **Housing** — Mortgage deduction reform, first-time buyer credits

### Data freshness
- ~~IRS SOI 2023 data~~ — **done.** Tables 1.1 and 3.3 for tax years 2021, 2022
  and 2023 ship in `fiscal_model/data_files/irs_soi/`, and auto-population takes
  the latest available year, so production scoring runs on **tax year 2023**.
- CBO baseline auto-loader from `cbo.gov` instead of hardcoded values

### Production hardening
- Docker containerization
- `requirements-lock.txt` with `pip-compile`-managed pinned transitive runtime versions
- Structured logging, data freshness monitoring

---

## Priority matrix

| Feature | Impact | Effort | Recommended |
|---------|--------|--------|-------------|
| CPS microsimulation feasibility sprint | High | Medium | Do now |
| Multi-model feasibility sprint | High | Medium | Do now |
| Full multi-model comparison | High | High | Start after feasibility gate |
| Full CPS microsimulation | High | High | Start after feasibility gate |
| Climate module | Med-High | Medium | Good standalone sprint |
| ~~IRS SOI 2023~~ | Medium | Low | **Done** — shipped and in use |
| Docker/lock file | Medium | Low | Interleave with above |

---

## Bill Tracker: committee filter + JCX crosswalk (pipeline work, from the 2026-08 UI review)

Both need new data before any UI ships — a filter or crosswalk built on
what the database holds today would be silently wrong:

- **Committee filter**: the ingestor does not fetch committee referrals;
  committee names appear only incidentally inside `latest_action` text for
  ~20% of bills (and vanish once a bill moves past referral). Requires the
  congress.gov `/bill/{congress}/{type}/{number}/committees` endpoint in
  `bill_tracker/ingestor.py`, a `committees` column, and a pipeline run
  (CONGRESS_API_KEY).
- **JCX crosswalk**: no JCT publication data exists in the pipeline.
  Requires scraping/curating jct.gov publication listings (JCX number,
  title, bill reference) into a small table keyed by bill_id, refreshed by
  the update pipeline; render beside the CBO score for revenue titles.
