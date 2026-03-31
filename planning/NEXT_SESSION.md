# Next Session Priorities

**Current Phase**: Phase 7 — Advanced Modeling & Production Readiness
**Last Updated**: March 31, 2026

## Recent Accomplishments (March 2026)

### App Review & Roadmap (Phase 6 completion)
- Comprehensive app review scored 7.2/10 with detailed roadmap to 9.5
- Centralized constants module (`fiscal_model/constants.py`) with 50+ cited parameters
- Input validation on all policy dataclasses
- `pyproject.toml` with project metadata, ruff, pytest, coverage config

### Test Coverage (86 → 302+ tests)
- Core model tests: scoring, baseline, economics, policies
- Policy module smoke tests for all 8 modules
- CBO regression tests against official score ranges
- Performance benchmarks for scoring speed
- Ruff linting in CI pipeline

### UI/UX Overhaul
- Redesigned sidebar with two clear paths: "Analyze a known proposal" vs "Design a custom policy"
- Comprehensive in-app Methodology tab with citations, validation table, and limitations
- Plain-English result interpretation below headline numbers
- Uncertainty band on cumulative deficit chart
- Assumptions panel showing ETI, data sources, methodology
- Side-by-side policy comparison on results page
- Sensitivity analysis widget (ETI impact table)
- CSV export for all result tables
- Onboarding welcome screen with example policies
- Friendly error messages with expandable technical details

### Code Quality
- 947 lint issues auto-fixed with ruff
- Hardcoded Windows paths replaced with environment variables
- Fixed lint issues in source code instead of suppressing rules
- Structured logging at key scoring entry points

## Next Priorities

### Phase 7: Advanced Policy Modules
1. **International tax**: GILTI reform, FDII repeal, Pillar Two minimum tax
2. **IRS enforcement**: Revenue from increased enforcement spending
3. **Pharmaceutical**: Drug pricing provisions, Medicare negotiation
4. **Trade policy**: Tariff revenue scoring, consumer price effects

### Phase 8: Production Hardening
1. Increase test coverage threshold to 70%+
2. Add Docker containerization
3. Add security scanning (bandit) to CI
4. Pin exact dependency versions

### Phase 9: Multi-Model Platform
1. Side-by-side model comparison (CBO vs TPC vs PWBM methodology)
2. API endpoint (FastAPI) for programmatic access
3. OLG (Overlapping Generations) model for 30+ year projections
