"""
Contract tests for GitHub Actions workflow gates.
"""

from pathlib import Path

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"
TESTS_WORKFLOW_PATH = WORKFLOWS_DIR / "tests.yml"
PUBLIC_HEALTH_WORKFLOW_PATH = WORKFLOWS_DIR / "public-app-health.yml"
VALIDATION_DASHBOARD_WORKFLOW_PATH = WORKFLOWS_DIR / "validation-dashboard.yml"


def test_readiness_ci_job_uses_strict_release_gate():
    workflow = TESTS_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python scripts/check_readiness.py --strict" in workflow
    assert "python scripts/check_readiness.py\n" not in workflow
    assert "python scripts/check_readiness.py --json > readiness-report.json" in workflow


def test_smoke_job_runs_local_streamlit_boot_flow():
    workflow = TESTS_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q" in workflow
    assert "python scripts/check_streamlit_boot.py --timeout 45" in workflow


def test_public_app_health_workflow_uses_configurable_url_and_timeout():
    workflow = PUBLIC_HEALTH_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'cron: "0 */6 * * *"' in workflow
    assert "FISCAL_POLICY_APP_URL:" in workflow
    assert "vars.FISCAL_POLICY_APP_URL" in workflow
    assert "python scripts/check_public_app.py --timeout 20" in workflow
    assert "python scripts/check_public_app.py --timeout 20 --json > public-app-health.json" in workflow
    assert "public-app-health-report" in workflow


def test_validation_dashboard_workflow_uploads_json_artifact():
    workflow = VALIDATION_DASHBOARD_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python scripts/run_validation_dashboard.py --json > validation-dashboard.json" in workflow
    assert (
        "python scripts/run_validation_dashboard.py --augment-top-tail --json "
        "> validation-dashboard-augmented.json"
    ) in workflow
    assert "name: validation-dashboard" in workflow
    assert "path: |" in workflow
    assert "validation-dashboard-augmented.json" in workflow
