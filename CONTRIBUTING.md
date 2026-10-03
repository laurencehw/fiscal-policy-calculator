# Contributing to Fiscal Policy Calculator

Thanks for your interest in contributing! This project aims to make fiscal policy analysis more transparent and accessible.

## Getting started

```bash
git clone https://github.com/laurencehw/fiscal-policy-calculator.git
cd fiscal-policy-calculator
pip install -r requirements.txt
pip install pytest pytest-cov 'ruff==0.15.8' mypy
ANTHROPIC_API_KEY= python -m pytest tests/ -q
streamlit run app.py      # Launch the app locally
```

Local development targets Python `3.12` via `.python-version`. The supported package range is `3.10`-`3.13`, and GitHub Actions verifies the full matrix.

### Reproducible installs via `requirements-lock.txt`

`requirements.txt` lists direct dependencies with loose bounds (e.g. `numpy>=1.24,<3.0`) for library-style flexibility. For reproducible production installs — including the Streamlit Cloud deployment — we also commit `requirements-lock.txt`, a fully-pinned transitive closure.

Regenerate the lockfile with [`uv`](https://github.com/astral-sh/uv) from Python 3.12 (matching `.python-version` and the Streamlit Cloud runtime). We moved off `pip-tools` because it reaches into pip's private API and broke across consecutive `setup-python@v6` bumps; `uv`'s Rust resolver is pip-tools-format-compatible and API-stable.

```bash
# Install the exact versions CI + prod use
pip install -r requirements-lock.txt

# Refresh the lock file after editing requirements.txt.
# Must be Python 3.12 — verify with `python3.12 --version`.
python3.12 -m venv .lockvenv
.lockvenv/bin/pip install uv
.lockvenv/bin/uv pip compile --strip-extras --no-header \
    --output-file=requirements-lock.txt requirements.txt
git add requirements.txt requirements-lock.txt
```

The `lockfile` CI job verifies the committed lockfile is resolvable and that every `requirements.txt` entry is pinned. It no longer regenerates the lockfile on every PR (that check kept breaking on pip/pip-tools API drift); a best-effort `uv` regeneration runs as an advisory informational step.

The 3.12 `smoke` job installs from `requirements-lock.txt`, so production-style dependency breakage is caught in CI. The broader 3.10-3.13 matrix still installs from `requirements.txt` to verify the supported version range.

## High-impact areas

The ranked list is [`planning/ROUTE_TO_9.md`](planning/ROUTE_TO_9.md); [`planning/ROADMAP.md`](planning/ROADMAP.md) says which planning document answers which question. In short:

- **Correctness and security** of the shared scoring core and the API
- **One authoritative source for current evidence**, so the README, the pages and the API cannot disagree
- **The shared modelling core** — filing populations, upper incomes, and one tax-unit engine for revenue and distribution
- **Explicit policy interactions** — ordinary rates, SALT, AMT and credits scored jointly rather than summed
- **Fresh, locked benchmarks** across policy families, rate cuts and vintages

## How to contribute

1. **Open an issue first** to discuss significant changes before starting work
2. **Fork the repo** and create a feature branch from `main`
3. **Write tests** for new functionality — the project enforces an 85% coverage floor in `pyproject.toml`
4. **Run every blocking CI step** before submitting — each of these has failed a PR that skipped it:
   ```bash
   # With the Anthropic key UNSET: CI never sets it, and with it exported parts of
   # tests/ make live API calls, so a green run with the key present is not CI's run.
   ANTHROPIC_API_KEY= python -m pytest tests/ --cov=fiscal_model

   # Lint scope matches CI, including the Streamlit surface outside fiscal_model/
   ruff check fiscal_model/ tests/ app.py api.py app_pages/ components/ classroom_app.py

   # The blocking type-check gate, exactly as CI runs it
   mypy $(grep -v '^#' mypy.gate.txt | grep -v '^[[:space:]]*$')

   # If the change touches scoring: the two out-of-sample accuracy gates. Take the
   # thresholds from .github/workflows/validation-dashboard.yml, never from memory.
   python scripts/cold_holdout.py --max-mean-error <ceiling> --min-within-25pct <floor>
   python scripts/cold_holdout.py --max-class-mean-error <class=ceiling ...>

   # If the change moves a validation tier: regenerate the figures the pages,
   # the Ask assistant and the docs quote, then update the live headline
   # sentences tests/test_current_evidence.py names.
   python scripts/build_current_evidence.py
   ```
5. **Refresh the runtime lockfile** with `uv` as described above if you changed dependencies
6. **Submit a pull request** with a clear description of what changed and why

For Streamlit controller or session-state changes, also run:

```bash
python -m pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q
```

### Browser journeys (opt-in)

`tests/e2e/` drives the real app in Chromium (deep links, share-link round trips, CSV export,
keyboard focus, mobile nav, latency budgets). The default `pytest tests/` run **excludes** them
(`-m "not e2e"` in `pyproject.toml`), so the main CI job never needs a browser; CI runs them in
its own `e2e` job. Locally:

```bash
pip install playwright          # then `playwright install chromium`, or point at a binary:
export E2E_CHROMIUM=/path/to/chrome   # optional
ANTHROPIC_API_KEY= python -m pytest -m e2e tests/e2e -q
```

They skip cleanly without Playwright or a browser (and fail under `CI`, so the job cannot pass
by skipping). `E2E_BASE_URL` tests an already-running app instead of booting one, and
`E2E_LATENCY_SCALE=3` loosens every latency budget for a remote or loaded machine. A run prints
measured latency against budget at the end.

## Code style

- Python 3.10-3.13 supported, with `3.12` as the local default
- Linting via [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`)
- Type hints on public APIs
- Docstrings for public classes and methods

## Validation

If your change affects scoring logic, run the validation reports and read the tiers separately — never collapse them into one "validated within X%" figure:

```bash
python scripts/cold_holdout.py              # out-of-sample tier, the only skill claim
python scripts/run_validation_dashboard.py  # health, calibration, calibrated tiers
python scripts/run_loo.py                   # leave-one-out on the calibrated modules
python -c "from fiscal_model.validation import run_validation_suite; run_validation_suite()"
```

New policy modules should include at least one validation case from a published source (CBO, JCT, Treasury, SSA, TPC, PWBM, the Tax Foundation, CRFB or RAND), with the page it was read from. A new out-of-sample case is pre-registered in `fiscal_model/validation/preregistered.py` in a commit **before** the one that first scores it, and no constant may be tuned toward a held-out target.

## Questions?

Open an issue or start a discussion on the repository.
