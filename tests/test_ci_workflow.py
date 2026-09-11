"""
Contract tests for GitHub Actions workflow gates.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"
TESTS_WORKFLOW_PATH = WORKFLOWS_DIR / "tests.yml"
PUBLIC_HEALTH_WORKFLOW_PATH = WORKFLOWS_DIR / "public-app-health.yml"
VALIDATION_DASHBOARD_WORKFLOW_PATH = WORKFLOWS_DIR / "validation-dashboard.yml"
FRED_SEED_REFRESH_WORKFLOW_PATH = WORKFLOWS_DIR / "fred-seed-refresh.yml"


def test_readiness_ci_job_uses_strict_release_gate():
    workflow = TESTS_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python scripts/check_readiness.py --strict" in workflow
    assert "python scripts/check_readiness.py\n" not in workflow
    assert "python scripts/check_readiness.py --json > readiness-report.json" in workflow


def test_smoke_job_runs_local_streamlit_boot_flow():
    workflow = TESTS_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pytest tests/test_app_entrypoints.py tests/test_ui_controller_smoke.py -q" in workflow
    assert "python scripts/check_streamlit_boot.py --timeout 45" in workflow


def test_ruff_lint_step_covers_the_streamlit_app_surface():
    """The redesign moved the UI into ``app.py`` / ``app_pages/`` /
    ``components/``. Linting only ``fiscal_model/ tests/`` left the entire
    router and every page module unchecked in CI.
    """
    workflow = TESTS_WORKFLOW_PATH.read_text(encoding="utf-8")

    lint_lines = [line for line in workflow.splitlines() if "ruff check" in line]
    assert len(lint_lines) == 1, "expected exactly one ruff check invocation"
    lint = lint_lines[0]
    for target in (
        "fiscal_model/",
        "tests/",
        "app.py",
        "app_pages/",
        "components/",
        "classroom_app.py",
    ):
        assert target in lint, f"ruff scope is missing {target}"

    # Pinned, not floating: an unpinned linter turns CI red on untouched code.
    assert "pip install 'ruff==0.15.8'" in workflow


def test_type_check_gate_is_blocking_and_full_pass_is_advisory():
    workflow = TESTS_WORKFLOW_PATH.read_text(encoding="utf-8")

    # The curated gate runs the allowlist and is NOT marked continue-on-error,
    # so it blocks the build on type regressions in the green core.
    assert "mypy $(grep -v '^#' mypy.gate.txt" in workflow
    # The full pass is advisory only.
    assert "mypy fiscal_model" in workflow
    assert "Type-check full pass (non-blocking)" in workflow


def test_mypy_gate_file_lists_only_existing_modules():
    gate_path = Path(__file__).resolve().parents[1] / "mypy.gate.txt"
    repo_root = gate_path.parent
    entries = [
        line.strip()
        for line in gate_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert entries, "mypy gate allowlist should not be empty"
    for rel in entries:
        assert (repo_root / rel).is_file(), f"gate lists missing module: {rel}"


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


def _cold_holdout_gate_lines(workflow: str) -> tuple[str, str]:
    """Return the (pooled, per-class) cold-holdout gate invocation lines."""
    # Invocations only: the step bodies start with ``python``. A comment that
    # names the script is documentation, not a gate.
    lines = [
        line
        for line in workflow.splitlines()
        if "cold_holdout.py" in line and line.strip().startswith("python ")
    ]
    assert len(lines) == 2, (
        "expected exactly two cold-holdout gate invocations: the pooled tier gate "
        f"and the per-class floor, got {lines}"
    )
    pooled = [line for line in lines if "--max-mean-error" in line]
    per_class = [line for line in lines if "--max-class-mean-error" in line]
    assert len(pooled) == 1 and len(per_class) == 1
    return pooled[0], per_class[0]


def test_validation_dashboard_workflow_gates_the_out_of_sample_tier():
    """The Generic tier is the only one that claims predictive skill; before
    Phase A it was the only one with no numeric ceiling in CI."""
    workflow = VALIDATION_DASHBOARD_WORKFLOW_PATH.read_text(encoding="utf-8")

    pooled, per_class = _cold_holdout_gate_lines(workflow)
    assert "--max-mean-error" in pooled
    assert "--min-within-25pct" in pooled
    # Both gates must be blocking: no `|| true`, no continue-on-error.
    assert "|| true" not in pooled
    assert "|| true" not in per_class


def test_cold_holdout_gate_thresholds_match_the_live_battery():
    """Thresholds are derived from the widened battery, not hand-set. If the
    battery moves enough to invalidate them, this test says so."""
    import re

    from scripts.cold_holdout import build_report

    workflow = VALIDATION_DASHBOARD_WORKFLOW_PATH.read_text(encoding="utf-8")
    gate, _ = _cold_holdout_gate_lines(workflow)
    max_mean = float(re.search(r"--max-mean-error\s+([\d.]+)", gate).group(1))
    min_within = int(re.search(r"--min-within-25pct\s+(\d+)", gate).group(1))

    summary = build_report()["out_of_sample"]["summary"]
    assert summary["mean_abs_error"] <= max_mean
    assert summary["within_25pct"] >= min_within
    # The ceiling should stay meaningful: no more than ~2x the live mean.
    assert max_mean <= summary["mean_abs_error"] * 2


def test_the_per_class_floor_gates_every_class_the_battery_contains():
    """``HIGH_STAKES_ACCURACY.md`` section 3, process rule 4.

    The pooled gate above cannot see one class regressing while the others carry
    the mean. This asserts three things the workflow must keep true: the eight
    classes of the plan's section 2 are all named, each ceiling is at or above
    that class's live mean, and none of them is loose enough to have stopped
    meaning anything (the same ~2x rule the pooled ceiling carries).
    """
    import re

    from scripts.cold_holdout import POLICY_CLASS_LABELS, build_report

    workflow = VALIDATION_DASHBOARD_WORKFLOW_PATH.read_text(encoding="utf-8")
    _, per_class_line = _cold_holdout_gate_lines(workflow)
    # The invocation continues across lines; read the whole step body.
    step = workflow.split("--max-class-mean-error", 1)[1].split("\n\n", 1)[0]
    ceilings = {
        slug: float(value)
        for slug, value in re.findall(r"\b([a-z_]+)=(\d+(?:\.\d+)?)\b", step)
        if slug in POLICY_CLASS_LABELS
    }
    assert per_class_line  # the flag is on its own step, not appended to the pooled one
    assert set(ceilings) == set(POLICY_CLASS_LABELS), (
        "every policy class must carry a ceiling, or a newly-registered row can "
        "land in an un-gated class"
    )

    classes = build_report()["out_of_sample"]["classes"]
    assert set(classes) <= set(ceilings)
    for slug, stats in classes.items():
        mean_err = stats["mean_abs_error"]
        assert mean_err <= ceilings[slug], f"{slug} is over its own CI ceiling"
        assert ceilings[slug] <= max(mean_err * 2, 2.0), (
            f"{slug}'s ceiling {ceilings[slug]} is more than twice its live mean "
            f"{mean_err} and has stopped meaning anything"
        )


def test_fred_seed_refresh_workflow_opens_seed_refresh_pr():
    workflow = FRED_SEED_REFRESH_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'cron: "0 10 1 * *"' in workflow
    assert "FRED_API_KEY: ${{ secrets.FRED_API_KEY }}" in workflow
    assert "python scripts/refresh_fred_seed.py --observations 8" in workflow
    assert "python scripts/check_readiness.py --strict" in workflow
    assert "tests/test_refresh_fred_seed_script.py" in workflow
    assert "peter-evans/create-pull-request" in workflow
    assert "fiscal_model/data_files/fred_seed.json" in workflow
