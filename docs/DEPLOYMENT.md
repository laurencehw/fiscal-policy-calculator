# Deployment and Operations

This project now treats runtime selection as an explicit deployment concern rather than an implicit default.

## Supported Python Versions

- Package support: `>=3.10,<3.14` in [pyproject.toml](../pyproject.toml)
- Local default: `.python-version` pins `3.12`
- CI matrix: `3.10`, `3.11`, `3.12`, `3.13`
- Recommended production target: `3.12`
- Runtime health: `/health` includes a `runtime` component and reports `degraded` if the deployed interpreter is outside `>=3.10,<3.14`.
- Release readiness: `/readiness` combines runtime, health, distribution benchmark, and revenue scorecard gates into one `ready` / `ready_with_warnings` / `not_ready` verdict.

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

The GitHub Actions workflow now enforces the same coverage floor as local development, includes a dedicated smoke job for the Streamlit boot path, and runs a production-runtime readiness gate.

Smoke coverage currently includes:

- `tests/test_app_entrypoints.py`
- `tests/test_ui_controller_smoke.py`

These tests are meant to fail fast on:

- top-level import regressions
- broken Streamlit bootstrap wiring
- session-state/widget ordering bugs
- classroom routing regressions

The full `test` job runs on Python `3.10`, `3.11`, `3.12`, and `3.13` and is expected to match the local dependency set.

The `readiness` job runs on Python `3.12`, installs `requirements-lock.txt`, and executes:

```bash
python scripts/check_readiness.py --strict
```

It fails on `not_ready` and on non-environmental warnings. CI runners may lack live FRED access or a warm FRED cache, so documented baseline GDP-proxy and FRED fallback warnings remain visible in the report but do not block the job.
Each run also uploads `readiness-report.json` as a workflow artifact for audit/debugging. The readiness payload includes full `checks` plus a flattened `issues` array for non-passing checks, so release blockers can be surfaced without parsing every check detail.

Strict exit behavior:

- `0`: ready, or ready with only documented external-data fallback warnings.
- `1`: `not_ready`; at least one required readiness check failed.
- `2`: ready with release-blocking warnings, such as model validation warnings that are not explained by the CI data environment.

The `public-app-health` workflow runs every six hours and on manual dispatch. It checks the public Streamlit root and classroom-mode URL using `scripts/check_public_app.py --timeout 20`. By default it targets `https://fiscal-policy-calculator.streamlit.app`; set the repository variable `FISCAL_POLICY_APP_URL` to point the check at another deployment. Each run uploads `public-app-health.json` with per-URL status, latency, and a flattened `issues` array for failed URL checks.

The `validation-dashboard` workflow uploads `validation-dashboard.json` and `validation-dashboard-augmented.json` on push, pull request, and manual dispatch. The default artifact shows the raw CPS calibration state; the augmented artifact runs with `--augment-top-tail` so high-income SOI correction is visible separately. Each artifact includes `generated_at`, aggregate `overall`, per-surface gate booleans for health, calibration, and distributional benchmarks, plus an `issues` array that names the failing component, bracket, or benchmark. The calibration payload also records `augmentation` and `filter` metadata when those optional microdata operations are used.

## Dependency Parity

The deployment path is intentionally split:

- The Python `3.12` `smoke` job installs from `requirements-lock.txt` so the production-style runtime lock is exercised in CI.
- The broader `3.10`-`3.13` matrix installs from `requirements.txt` to verify the supported version range.
- Package metadata still lives in `pyproject.toml`.

Keep all three aligned when adding runtime dependencies.

Important current examples:

- `openpyxl` is required for Excel export paths exercised by the test suite
- `requirements-lock.txt` must be regenerated with `pip-compile` from Python `3.12` when `requirements.txt` changes

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
3. If dependencies changed, regenerate `requirements-lock.txt` with `pip-compile` on Python `3.12`.
4. Run `python scripts/run_validation_dashboard.py` in the deployment runtime; confirm the runtime line is `[ok]`.
5. Run `python scripts/check_readiness.py --strict` or check `/readiness`. Production should ship with `verdict == "ready"` unless the only warnings are documented external-data fallback warnings.
6. Check `/health` after deploy and confirm `components.runtime.status == "ok"`.
7. Wait for GitHub Actions `smoke`, `readiness`, `test`, and `lockfile` jobs to pass.
8. Confirm the public health workflow is green.
9. Load the calculator root and classroom mode once after deploy.

## Incident Checklist

If the app is reachable but user flows are broken:

1. Check the latest `app_boot` log for the deployed Python version.
2. Confirm the failure reproduces on the same Python version locally.
3. Run `pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q`.
4. Check for session-state mutations after widget creation.
5. If only one deployed mode is failing, isolate whether the break is in `app.py` routing or in the downstream controller.
