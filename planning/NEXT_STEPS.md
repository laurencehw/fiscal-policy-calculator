# Next Steps — Fiscal Policy Calculator

> Roadmap last reviewed April 2026; the validation scorecard below was re-derived 2026-09-01. This file tracks roadmap items beyond the current shipped branch.

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
| Out-of-sample, pre-registered | prediction | 25 | **52.6%** | 21.1% |
| Calibrated, fitted | bookkeeping (low by construction) | 34 | **2.7%** | 0.2% |
| Unfitted module reconstructions | modules vs targets never fitted to | 20 | **250.8%** | 43.1% |
| Calibrated, leave-one-out | how much of the calibration is structure | 18 | **59.3%** | 35.6% |

The reconstruction tier is itself two populations — 12 sectoral presets at 394.1%
and 8 P.L. 119-21 line items at 35.8% — and must not be quoted as one number.
Distributional accuracy is separate again: 7 published CBO/JCT tables at
0.00-5.86pp, two of which are circular. See [`docs/VALIDATION.md`](../docs/VALIDATION.md).

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
