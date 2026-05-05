# Next Steps — Fiscal Policy Calculator

> Updated April 2026. This file tracks roadmap items beyond the current shipped branch.

For a manuscript-focused path to citation-grade quality, see [MANUSCRIPT_95_PLUS.md](MANUSCRIPT_95_PLUS.md). For repo-grounded go/no-go gates on the two biggest upgrades, see [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md).

---

## Current state (April 2026)

**Large automated test suite, 85% enforced coverage gate, 25+ policies validated within 15% of CBO/JCT**

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

### CPS microsimulation feasibility sprint
- [ ] Audit current `fiscal_model/microsim/` inputs, tax-unit construction, and weighting assumptions
- [ ] Confirm whether `tax_microdata_2024.csv` is reproducible from source CPS files
- [ ] Wire one interaction-heavy benchmark through the microsim path
- [ ] Decide whether the current stack is strong enough for a full CPS migration

### Multi-model feasibility sprint
- [ ] Audit the current `BaseScoringModel` / `ModelResult` abstractions
- [ ] Wrap one microsim-style engine and one PWBM-style path behind a common comparison contract
- [ ] Run one preset policy through 2-3 engines outside the current static-vs-dynamic UI
- [ ] Resolve any `model_pilot_assessment.blockers` from `scripts/run_feasibility_audit.py --include-model-pilot --json`
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
- IRS SOI 2023 data (available ~2025, currently using 2022)
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
| IRS SOI 2023 | Medium | Low | Easy warm-up task |
| Docker/lock file | Medium | Low | Interleave with above |
