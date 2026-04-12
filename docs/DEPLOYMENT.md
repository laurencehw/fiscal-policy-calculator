# Deployment and Operations

This project now treats runtime selection as an explicit deployment concern rather than an implicit default.

## Supported Python Versions

- Package support: `>=3.10,<3.14` in [pyproject.toml](../pyproject.toml)
- Local default: `.python-version` pins `3.12`
- CI matrix: `3.10`, `3.11`, `3.12`, `3.13`
- Recommended production target: `3.12`

## Streamlit Community Cloud

Streamlit Community Cloud does not honor a repo-side `runtime.txt` for Python selection.
Set the deployed Python version in the app's **Advanced settings**.

Recommended setting:

1. Open the deployed app in Streamlit Cloud.
2. Open **Settings** or **Manage app**.
3. Set **Python version** to `3.12`.
4. Redeploy after changing the runtime.

Use the same target when reproducing production issues locally.

## CI and Smoke Checks

The GitHub Actions workflow now enforces the same coverage floor as local development and includes a dedicated smoke job for the Streamlit boot path.

Smoke coverage currently includes:

- `tests/test_app_entrypoints.py`
- `tests/test_ui_controller_smoke.py`

These tests are meant to fail fast on:

- top-level import regressions
- broken Streamlit bootstrap wiring
- session-state/widget ordering bugs
- classroom routing regressions

The full `test` job runs on Python `3.10`, `3.11`, `3.12`, and `3.13` and is expected to match the local dependency set.

## Dependency Parity

The deployment and CI paths both install from `requirements.txt`, while package metadata lives in `pyproject.toml`.
Keep these files aligned when adding runtime dependencies.

Important current examples:

- `openpyxl` is required for Excel export paths exercised by the test suite
- `requirements-lock-ci.txt` artifacts are emitted from CI to make dependency drift reproducible

## Runtime Logging

Both `app.py` and `classroom_app.py` now emit structured startup logs through `fiscal_model.ui.runtime_logging`.

Expected events:

- `app_boot`
- `app_route`

Fields include:

- `entrypoint`
- `mode`
- `python_version`

On Streamlit Cloud, inspect these in the app logs. Locally, they appear in the standard process output.

## Deployment Checklist

1. Verify `.python-version` is still aligned with the intended deploy target.
2. Confirm Streamlit Cloud advanced settings are set to Python `3.12`.
3. Wait for GitHub Actions `smoke` and `test` jobs to pass.
4. Confirm the public health workflow is green.
5. Load the calculator root and classroom mode once after deploy.
6. If dependencies changed, compare the new CI lock artifact to the prior successful run.

## Incident Checklist

If the app is reachable but user flows are broken:

1. Check the latest `app_boot` log for the deployed Python version.
2. Confirm the failure reproduces on the same Python version locally.
3. Run `pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q`.
4. Check for session-state mutations after widget creation.
5. If only one deployed mode is failing, isolate whether the break is in `app.py` routing or in the downstream controller.
