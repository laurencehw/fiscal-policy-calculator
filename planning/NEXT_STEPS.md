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
| Out-of-sample, pre-registered | prediction | 25 | **31.3%** | 14.1% |
| Calibrated, fitted | bookkeeping (low by construction) | 30 | **2.2%** | 0.2% |
| Unfitted module reconstructions | modules vs targets never fitted to | 24 | **72.1%** | 40.0% |
| Calibrated, leave-one-out | how much of the calibration is structure | 17 | **32.3%** | 19.2% |

**The fitted tier has lost four rows, and both reasons must be quoted with the
number.** One left when a target it was fitted to was corrected:
`ScorecardSummary.revised_target_entries` is **2**, a constant fitted to a
superseded figure is not fitted to its replacement, and the revised row therefore
reports among the reconstructions. Held in place instead the fitted tier reads
**31 at 4.2%, 30/31 within 15%** — quote either, never one alone. Three more
left in Wave 2, when deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural
tuples removed the only constants ever fitted to the capital-gains scenarios; the
fitted mean *fell* 2.8% → 2.2% because those rows were what it had been
carrying, which is **composition, not accuracy**. The reconstruction tier is
itself four populations — 12 sectoral presets at 104.8%, 8 P.L. 119-21 line
items at 35.8%, 3 capital-gains scenarios at 39.6% and that revised row at 66.8%
— and must not be quoted as one number. The leave-one-out tier likewise dropped
from 18 derivable cases to 17: `eliminate_salt` is now caught by the leakage
guard. Distributional accuracy is separate again: 7 published CBO/JCT tables at
0.00-5.86pp, two of which are circular. See
[`docs/VALIDATION.md`](../docs/VALIDATION.md).

*Re-derived 2026-09-02, after Wave 2 (PRs #93–#95). Tier 1 moved 52.6% → 34.4%
on the eight spending rows in Wave 1 and 34.4% → **31.3%** on the four
capital-gains rows in Wave 2 — gains at death alone went 84.4% → 8.4%.
Leave-one-out rose 59.3% → 61.7% on the two AMT rows (the AMT module becoming
more structural rather than less accurate), fell to 58.7% when the AMT
extension's target was corrected, and then fell to **32.3%** in Wave 2 on three
rebuilt modules — the first of those moves that is a model change rather than a
target one, and the only one carrying a case-count caveat (31.7% like-for-like
over 18). The reconstruction tier went 250.8% → 82.6% on two pharma rows, then
to 21 rows at 76.7% on two target corrections, then to **24 rows at 72.1%** when
the capital-gains scenarios arrived from the fitted tier. See
[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) §§5.1 and 5.2.*

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

## Modelling plan: Waves 1 and 2 done, Wave 3 next

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
**58.7% → 32.3%**. Every module keeps `reported` as its app default under
Decision 1, so **no shipped preset moved**. §5.2 of
[`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) has the outturn, the four
findings and the three missed bands; §6.1 has the six open owner decisions.

Next, in order:

1. **Wave 3** — the last wave in the plan, three lanes on disjoint files:
   - **L3 credits / microsim** (45.1% of the LOO tier and the largest module
     left). Per owner **Decision 4** the raw CPS ASEC extract is *fetched by
     script at build time and never vendored*, which is what unblocks dependent
     ages for the ARP under-6/6–16 split; per **Decision 5** the three
     tautological credit benchmarks — whose annuals are their targets divided by
     ten — move to documented-exclusion status, like `repeal_corporate_amt`,
     with the LOO number carrying the honesty meanwhile.
   - **L8 tariffs** (gross customs revenue → net of pass-through, retaliation
     and the income/payroll offset). Per **Decision 6** the shipped preset
     numbers move by 40–50%, so the **UI note lands in the same PR**.
   - **L9 international** (a base-overlap term, so a per-country GILTI and
     Pillar Two's UTPR stop double-counting the same undertaxed profits).
2. **Carry-overs from Waves 1 and 2**, none of them a whole lane:
   - **L7's Part D channels** — the incidence bugs are fixed but no utilisation,
     launch-delay or availability response is modelled on either pharma row.
   - **L5's phase-out thresholds** — the AMT exemption phase-out is still a
     fixed schedule.
   - **L1's death-channel behavioural response** — no spousal or charitable
     carve-out, no §121 residence exclusion, no tangible-personal-property
     exclusion, no family-business deferral. This is the entire residual on the
     two Treasury Tier-1 rows (135% and 218%) and the single largest thing left
     undone in the capital-gains module.
   - **Promote CBO Option 56** once L6's excess share is indexed by year. It
     scores **+2.5%** in the option's own first year today and −32.6% over the
     window, because the share is evaluated once at `start_year`; recomputed
     annually it is −12.8%.
3. **`repeal_individual_amt` — the one target the provenance lane could not
   close.** It keeps an unsourced $450B that is internally incoherent with the
   transcribed $1,357.1B (a full repeal cannot cost less than extending the
   exemption on the same baseline). No published post-2025 repeal score exists at
   JCT, CBO or TPC, and TPC T25-0049's $948.9B is deliberately not adopted: it is
   a baseline projection rather than a scored repeal, *and* it is `amt.py`'s own
   input, so adopting it would manufacture a 0% row out of the leakage `loo.py`
   guards against. Closing it needs either a published score or an **owner
   decision** to re-register `holdout.py`'s locked
   `revenue-scorecard-post-lock-2026-05-02` protocol, which has no
   re-registration path and is a gate no lane may edit.
4. **Still open from L2**: CBO's account-level spendout rates (publications
   61913 and 62256) as the external cross-check on the outlay profiles — needs
   an environment that can reach cbo.gov.
5. **The other five open owner decisions**, all listed in one place at
   [`MODELING_IMPROVEMENT.md`](MODELING_IMPROVEMENT.md) §6.1: whether to re-lock
   the holdout protocol or keep the documented-miss warning convention that now
   covers `pwbm_39_with_stepup`; the SALT constants (the unsourced $120.0B
   no-cap level against SOI's derived $89.6B, a joint decision about
   `eliminate_salt` and `repeal_salt_cap`); whether Treasury's FY2022 −$322.0B
   is the combined or the rate-only row; the estate growth rate (SOI-fitted
   6.81% against the shipped nominal-GDP 3.82%); and the Option 56 promotion.

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
