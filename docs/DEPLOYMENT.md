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
- `scripts/check_streamlit_boot.py --timeout 45`, which starts `app.py` through Streamlit and checks both `/` and `/?mode=classroom` return the app shell

These tests are meant to fail fast on:

- top-level import regressions
- broken Streamlit bootstrap wiring
- session-state/widget ordering bugs
- classroom routing regressions
- Streamlit server boot or route-shell regressions that import-only tests cannot catch

The full `test` job runs on Python `3.10`, `3.11`, `3.12`, and `3.13` and is expected to match the local dependency set.

The `readiness` job runs on Python `3.12`, installs `requirements-lock.txt`, and executes:

```bash
python scripts/check_readiness.py --strict
```

It fails on `not_ready` and on non-environmental warnings. CI runners may lack live FRED access or a warm FRED cache, so the data layer ships a tracked `fiscal_model/data_files/fred_seed.json` seed before falling back to hardcoded GDP. The bundled seed is treated as fresh for 120 days; after that, readiness warns so the seed is intentionally refreshed. If cache and seed are both unavailable, documented baseline GDP-proxy and FRED fallback warnings remain visible in the report but do not block the job.
Each run also uploads `readiness-report.json` as a workflow artifact for audit/debugging. The readiness payload includes full `checks` plus a flattened `issues` array for non-passing checks, so release blockers can be surfaced without parsing every check detail.

Strict exit behavior:

- `0`: ready, or ready with only documented external-data fallback warnings.
- `1`: `not_ready`; at least one required readiness check failed.
- `2`: ready with release-blocking warnings, such as model validation warnings that are not explained by the CI data environment.

The `public-app-health` workflow runs every six hours and on manual dispatch. It checks the public Streamlit root and classroom-mode URL using `scripts/check_public_app.py --timeout 20`. By default it targets `https://fiscal-policy-calculator.streamlit.app`; set the repository variable `FISCAL_POLICY_APP_URL` to point the check at another deployment. Each run uploads `public-app-health.json` with per-URL status, latency, and a flattened `issues` array for failed URL checks.

The `validation-dashboard` workflow uploads `validation-dashboard.json` and `validation-dashboard-augmented.json` on push, pull request, and manual dispatch. The default artifact shows the raw CPS calibration state; the augmented artifact runs with `--augment-top-tail` so high-income SOI correction is visible separately. Each artifact includes `generated_at`, aggregate `overall`, per-surface gate booleans for health, calibration, and distributional benchmarks, plus an `issues` array that names the failing component, bracket, or benchmark. The calibration payload also records `augmentation` and `filter` metadata when those optional microdata operations are used.

The `fred-seed-refresh` workflow runs monthly and on manual dispatch. It
requires the repository secret `FRED_API_KEY`, refreshes
`fiscal_model/data_files/fred_seed.json` with `scripts/refresh_fred_seed.py`,
runs the strict readiness gate plus targeted FRED seed regressions, and opens a
pull request only when the committed seed changes.

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

## Ask Assistant Configuration

The 💬 Ask tab and `/ask` + `/ask/stream` endpoints require an Anthropic API key. The rest of the app works without one — the Ask tab degrades to a friendly "not configured" message that no end user can mistake for a working chat.

### Secrets

On **Streamlit Cloud**, set in **Settings → Secrets** (TOML):

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

The tab promotes `st.secrets["ANTHROPIC_API_KEY"]` to `os.environ` on first render, so the same code path works with both Streamlit secrets and a regular env var. A typo-detecting diagnostic (Levenshtein distance) catches common mistakes like `ANTHROPHIC_API_KEY` inline.

### Cost controls (recommended secrets)

| Variable | Default | Purpose |
|---|---|---|
| `ASSISTANT_DAILY_COST_CAP_USD` | `5.00` | Hard daily cap across all visitors. Past this, new requests get a friendly "budget exhausted" message until UTC midnight. |
| `ASSISTANT_SESSION_MESSAGE_CAP` | `20` | Per-session turn cap. |
| `ASSISTANT_COOLDOWN_SECONDS` | `3` | Minimum spacing between turns from the same session. |
| `ASSISTANT_DISABLED` | unset | Set to `1` to disable the assistant entirely (kill switch). |
| `ASSISTANT_USAGE_DB` | (auto) | Sqlite path for the `assistant_events` ledger; falls back to `:memory:` on read-only filesystems. |

### Admin dashboard

Set `ASSISTANT_ADMIN_TOKEN = "your-rotated-secret"` (TOML). The 💼 Admin tab will then appear only when the URL has `?admin=your-rotated-secret`. Non-admins never see the tab title in the top tab bar.

### Smoke testing the Ask stack

Before deploy, run the live smoke test against the same API key the deployment will use:

```bash
ANTHROPIC_API_KEY=sk-ant-... python scripts/smoke_ask_assistant.py
```

Costs roughly $0.04 and verifies the streaming tool loop, citation discipline, three of the nine tools, and the cost meter end-to-end.

## Deployment Checklist

1. Verify `.python-version` is still aligned with the intended deploy target.
2. Confirm Streamlit Cloud advanced settings are set to Python `3.12`.
3. If dependencies changed, regenerate `requirements-lock.txt` with `pip-compile` on Python `3.12`.
4. Run `python scripts/run_validation_dashboard.py` in the deployment runtime; confirm the runtime line is `[ok]`.
5. Run `python scripts/check_readiness.py --strict` or check `/readiness`. Production should ship with `verdict == "ready"`; live FRED or a warm cache is preferred, with a fresh bundled FRED seed as the deterministic offline path.
6. Check `/health` after deploy and confirm `components.runtime.status == "ok"`. The `components.assistant` block reports `status: "ok"` when `ANTHROPIC_API_KEY` is configured and the knowledge corpus is present; "degraded" is non-blocking.
7. Wait for GitHub Actions `smoke`, `readiness`, `test`, and `lockfile` jobs to pass.
8. Confirm the public health workflow is green.
9. Confirm the monthly FRED seed refresh workflow has `FRED_API_KEY` configured.
10. Load the calculator root and classroom mode once after deploy.
11. If the Ask assistant is enabled on this deployment: confirm `ANTHROPIC_API_KEY` is set (Streamlit secret or env var), then open the 💬 Ask tab and submit a starter prompt to verify the streaming loop, citation rendering, and dollar-sign escaping all work end-to-end.

## Incident Checklist

If the app is reachable but user flows are broken:

1. Check the latest `app_boot` log for the deployed Python version.
2. Confirm the failure reproduces on the same Python version locally.
3. Run `pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q`.
4. Check for session-state mutations after widget creation.
5. If only one deployed mode is failing, isolate whether the break is in `app.py` routing or in the downstream controller.
