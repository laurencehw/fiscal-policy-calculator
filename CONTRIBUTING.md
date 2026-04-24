# Contributing to Fiscal Policy Calculator

Thanks for your interest in contributing! This project aims to make fiscal policy analysis more transparent and accessible.

## Getting started

```bash
git clone https://github.com/laurencehw/fiscal-policy-calculator.git
cd fiscal-policy-calculator
pip install -r requirements.txt
pip install pytest pytest-cov ruff
python -m pytest tests/ -v
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

These are the areas where contributions would be most valuable:

- **Multi-model comparison platform** — Planned CBO/TPC/PWBM-style side-by-side scoring
- **CPS microsimulation upgrade** — Planned move from synthetic tax units to CPS ASEC data
- **New policy modules** — Climate/energy, immigration, housing, wealth tax
- **Data updates** — IRS SOI 2023 tables, CBO baseline auto-loader

## How to contribute

1. **Open an issue first** to discuss significant changes before starting work
2. **Fork the repo** and create a feature branch from `main`
3. **Write tests** for new functionality — the project enforces an 85% coverage floor in `pyproject.toml`
4. **Run the full suite** before submitting:
   ```bash
   python -m pytest tests/ -v
   python -m pytest tests/ --cov=fiscal_model
   ruff check fiscal_model/ tests/
   ```
5. **Refresh the runtime lockfile** if you changed dependencies:
   ```bash
   python3.12 -m venv .lockvenv
   .lockvenv/bin/pip install pip-tools
   .lockvenv/bin/pip-compile --strip-extras --output-file=requirements-lock.txt requirements.txt
   ```
6. **Submit a pull request** with a clear description of what changed and why

For Streamlit controller or session-state changes, also run:

```bash
python -m pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q
```

## Code style

- Python 3.10-3.13 supported, with `3.12` as the local default
- Linting via [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`)
- Type hints on public APIs
- Docstrings for public classes and methods

## Validation

If your change affects scoring logic, verify against CBO/JCT benchmarks:

```bash
python -c "from fiscal_model.validation import run_validation_suite; run_validation_suite()"
```

New policy modules should include at least one validation case from an official source (CBO, JCT, Treasury, TPC, or PWBM).

## Questions?

Open an issue or start a discussion on the repository.
