# Changelog

Material changes to the Fiscal Policy Calculator. Trivial fixes are captured
in git history, not here.

## 2026 — ongoing

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
