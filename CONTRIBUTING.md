# Contributing to Fiscal Policy Calculator

Thanks for your interest in contributing! This project aims to make fiscal policy analysis more transparent and accessible.

## Getting started

```bash
git clone https://github.com/laurencehw/fiscal-policy-calculator.git
cd fiscal-policy-calculator
pip install -r requirements.txt
pip install pytest pytest-cov ruff
pytest tests/ -v          # Run the test suite (1070 tests)
streamlit run app.py      # Launch the app locally
```

Local development targets Python `3.12` via `.python-version`. The supported package range is `3.10`-`3.13`, and GitHub Actions verifies the full matrix.

## High-impact areas

These are the areas where contributions would be most valuable:

- **Multi-model comparison** — CBO-style, TPC microsim, and dynamic scoring side-by-side
- **CPS microsimulation** — Individual-level tax calculation using CPS ASEC data
- **New policy modules** — Climate/energy, immigration, housing, wealth tax
- **Data updates** — IRS SOI 2023 tables, CBO baseline auto-loader

## How to contribute

1. **Open an issue first** to discuss significant changes before starting work
2. **Fork the repo** and create a feature branch from `main`
3. **Write tests** for new functionality — the project maintains 1070 tests at 78%+ coverage with a 78% enforced floor
4. **Run the full suite** before submitting:
   ```bash
   pytest tests/ -v
   pytest tests/ --cov=fiscal_model
   ruff check fiscal_model/ tests/
   ```
5. **Submit a pull request** with a clear description of what changed and why

For Streamlit controller or session-state changes, also run:

```bash
pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q
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
