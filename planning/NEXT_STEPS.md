# Next Steps — Fiscal Policy Calculator

> Updated April 2026. All sprints and horizon features completed.

---

## Current state (April 2026)

**973 tests passing, 73% coverage, 25+ policies validated within 15% of CBO/JCT**

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

### Estimated rating: ~9.5/10

---

## Genuine next priorities

### Multi-model comparison platform
Run the same policy through CBO-style, TPC-style (microsim), and FRB/US dynamic models side by side. Show divergences and explain why. This is the architecture vision in `docs/ARCHITECTURE.md` and is the most impactful remaining feature.

### CPS microsimulation
Replace IRS bracket-level data with CPS ASEC microdata for distributional analysis. Would fix the #1 accuracy limitation and enable precise incidence modeling for complex provision interactions (AMT + SALT + CTC phase-outs).

### Additional policy modules
- **Climate/energy** — IRA clean energy credits, carbon pricing, EV incentives
- **Immigration** — Workforce effects on payroll tax base and GDP
- **Housing** — Mortgage deduction reform, first-time buyer credits

### Data freshness
- IRS SOI 2023 data (available ~2025, currently using 2022)
- CBO baseline auto-loader from `cbo.gov` instead of hardcoded values

### Production hardening
- Docker containerization
- `requirements-lock.txt` with pinned versions
- Structured logging, data freshness monitoring

---

## Priority matrix

| Feature | Impact | Effort | Recommended |
|---------|--------|--------|-------------|
| Multi-model comparison | High | High | Next major feature |
| CPS microsimulation | High | High | Parallel with above |
| Climate module | Med-High | Medium | Good standalone sprint |
| IRS SOI 2023 | Medium | Low | Easy warm-up task |
| Docker/lock file | Medium | Low | Interleave with above |
