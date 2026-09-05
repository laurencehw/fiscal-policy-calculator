"""The app's budget window is FY2026-FY2035 on every surface, and only the app's.

``planning/redesign/FOLLOWUPS.md`` carried two open items saying the same thing
twice: Explore showed FY2026-FY2035 for a calibrated preset while Tailor showed
FY2025-FY2034 for a generic run, and Build rendered FY2025-2034 against
wireframes that say FY2026-2035. Both came from the same place — the window was
whatever ``Policy.start_year`` happened to be, and calibrated presets name a
year while generic runs do not.

The decision was to make the app's default explicit
(:data:`fiscal_model.baseline.APP_DEFAULT_START_YEAR`) rather than to move the
library default, because the validation suite reaches the same policy factories
the app does and its targets are quoted on the windows their documents used.
So there are two halves to test and they pull in opposite directions:

1. **Rendered** — through ``AppTest`` on the real router, so a page that stops
   routing through the constant fails here rather than in a screenshot.
2. **Pinned** — the validation window is *not* the app window, and must not
   follow it. A future edit that "tidies up" by pointing
   ``DEFAULT_VALIDATION_START_YEAR`` at ``APP_DEFAULT_START_YEAR`` would move
   published benchmarks by a year of growth; that is a target revision, and
   target revisions go through ``target_revisions.py``, not through here.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.baseline import APP_DEFAULT_START_YEAR  # noqa: E402
from fiscal_model.ui import cache as ui_cache  # noqa: E402

#: What the result panel and Explore print.
EXPECTED_WINDOW = f"FY{APP_DEFAULT_START_YEAR}–FY{APP_DEFAULT_START_YEAR + 9}"
#: What Build prints (same window, its own shorter form).
EXPECTED_BUILD_WINDOW = f"FY{APP_DEFAULT_START_YEAR}–{APP_DEFAULT_START_YEAR + 9}"

TAILOR = "app_pages/tailor.py"
BUILD = "app_pages/build.py"
EXPLORE = "app_pages/explore.py"
SCORE_BUTTON = "score_policy_button"
SCORED_RESULT_KEY = "scored_result"

HEALTHY_HEALTH: dict = {
    "runtime": {"status": "ok", "python_version": "3.12.0"},
    "baseline": {
        "status": "ok",
        "vintage": "February 2026",
        "vintage_key": "cbo_feb_2026",
        "start_year": APP_DEFAULT_START_YEAR,
        "freshness": {"level": "fresh", "is_stale": False, "message": "current"},
    },
    "fred": {"status": "ok", "source": "live", "cache_is_expired": False},
    "irs_soi": {
        "status": "ok",
        "latest_year": 2023,
        "freshness": {"level": "ok", "is_stale": False, "message": "lag 3y"},
    },
    "model": {"status": "ok"},
    "microdata": {"status": "ok"},
    "assistant": {"status": "ok"},
    "overall": "ok",
}


@pytest.fixture(autouse=True)
def _offline_and_healthy(monkeypatch):
    """Seed the health cache and keep the run off the network (see
    ``tests/test_dollar_rendering.py``, which uses the same fixture)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ui_cache.clear_health_snapshot()
    ui_cache._health_snapshot["value"] = HEALTHY_HEALTH
    ui_cache._health_snapshot["at"] = time.monotonic()
    yield
    ui_cache.clear_health_snapshot()


def _run(page: str, *, query: dict[str, str] | None = None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=300)
    at.run()
    at.switch_page(page)
    for key, value in (query or {}).items():
        at.query_params[key] = value
    at.run()
    assert not at.exception, at.exception
    return at


def _rendered_text(at) -> str:
    parts = []
    for name in ("markdown", "caption", "info", "success", "metric", "code"):
        for element in getattr(at, name, []):
            for attribute in ("value", "label", "body"):
                value = getattr(element, attribute, None)
                if isinstance(value, str):
                    parts.append(value)
    return " ".join(parts)


# ── Rendered: the three scoring surfaces ─────────────────────────────────


def test_tailor_scores_a_generic_run_on_the_app_window():
    """The first FOLLOWUPS item: a generic Tailor run used to say FY2025-FY2034
    because ``FiscalPolicyScorer`` defaults ``start_year=2025``."""
    at = _run(TAILOR)
    at.button(key=SCORE_BUTTON).click()
    at.run()
    assert not at.exception, at.exception

    scored = at.session_state[SCORED_RESULT_KEY]
    assert scored is not None, "the default configuration did not score"
    assert scored.window == EXPECTED_WINDOW, scored.window
    assert scored.window_start == APP_DEFAULT_START_YEAR
    assert scored.window_end == APP_DEFAULT_START_YEAR + 9
    assert scored.n_years == 10


def test_explore_scores_a_calibrated_preset_on_the_same_window():
    """Explore already showed FY2026-FY2035 for this preset — because the TCJA
    factory names 2026, not because anything chose the window. It has to keep
    doing so now that the choice is explicit."""
    at = _run(EXPLORE, query={"preset": "tcja-full-extension", "run": "1"})

    scored = at.session_state[SCORED_RESULT_KEY]
    assert scored is not None, "the auto-run did not score"
    assert scored.window == EXPECTED_WINDOW, scored.window


def test_explore_scores_a_2025_preset_on_the_app_window_too():
    """The presets whose factories name 2025 are the ones that used to disagree
    with Explore's calibrated headline. ``create_policy_from_preset`` moves them
    onto the window, so the whole page speaks one window."""
    at = _run(EXPLORE, query={"preset": "corporate-28pct", "run": "1"})

    scored = at.session_state[SCORED_RESULT_KEY]
    assert scored is not None, "the auto-run did not score"
    assert scored.window == EXPECTED_WINDOW, scored.window


def test_build_renders_the_app_window():
    """The second FOLLOWUPS item: Build took the scorer's default baseline, so
    its scoreboard divided ten-year totals by a FY2025-2034 window.

    Build states the window in the provenance header its exports carry — the
    copy summary and the CSV — which is where a reader of a shared package
    finds out what ten years the per-year figures are averages over.
    """
    at = _run(BUILD, query={"policies": "ss-cap-90pct"})

    text = _rendered_text(at)
    assert f"Window: {EXPECTED_BUILD_WINDOW}" in text, (
        f"Build's export provenance does not say {EXPECTED_BUILD_WINDOW!r}; "
        f"rendered text was: {text[-600:]!r}"
    )
    assert f"Window: FY{APP_DEFAULT_START_YEAR - 1}" not in text


# ── Pinned: validation keeps its own window ──────────────────────────────


def test_validation_window_does_not_follow_the_app_window():
    """``DEFAULT_VALIDATION_START_YEAR`` is 2025 and stays 2025.

    Every calibrated and out-of-sample target in this repository is quoted for
    a window its own document chose. Moving this to track the app would shift
    published benchmarks by a year of growth without a single document having
    changed — which is a target revision, and target revisions are made in
    ``fiscal_model/validation/target_revisions.py`` (Tier 2) or by a superseding
    row in ``preregistered.py`` (Tier 1), never by a constant drifting.
    """
    from fiscal_model.validation.core import DEFAULT_VALIDATION_START_YEAR
    from fiscal_model.validation.specialized_sectoral import _SCORER_START_YEAR

    assert DEFAULT_VALIDATION_START_YEAR == 2025
    assert _SCORER_START_YEAR == 2025
    assert DEFAULT_VALIDATION_START_YEAR != APP_DEFAULT_START_YEAR


def test_library_defaults_stay_where_validation_expects_them():
    """The app's window is app-side wiring, not a moved library default.

    ``validate_sectoral_policy`` pins its policies precisely because the
    factories it shares with the app would otherwise inherit these; the pin
    makes the scorecard safe either way, and this records that the decision
    taken was to leave them alone.
    """
    import inspect

    from fiscal_model.baseline import BaselineProjection
    from fiscal_model.policies import Policy
    from fiscal_model.scoring import FiscalPolicyScorer

    assert Policy.start_year == 2025
    assert BaselineProjection().start_year == 2025
    signature = inspect.signature(FiscalPolicyScorer.__init__)
    assert signature.parameters["start_year"].default == 2025


# ── The one seam every app surface goes through ──────────────────────────


def test_preset_policies_all_open_on_the_app_window():
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.preset_handler import create_policy_from_preset

    early = []
    for name, preset in PRESET_POLICIES.items():
        if name == "Custom Policy":
            continue
        policy = create_policy_from_preset(preset)
        if policy is None:
            continue  # a simple rate-and-threshold preset; the caller builds it
        if int(policy.start_year) < APP_DEFAULT_START_YEAR:
            early.append((name, policy.start_year))

    assert not early, (
        "these presets open before the app's window and would be scored over "
        f"fewer than ten years of their own effect: {early}"
    )


def test_a_later_stated_start_year_survives_the_app_window():
    """``max``, not assignment: a policy that states a mid-decade effective
    year is stating a fact, and the window must not overwrite it."""
    from fiscal_model.policies import PolicyType, TaxPolicy
    from fiscal_model.preset_handler import _open_no_earlier_than

    late = TaxPolicy(
        name="late",
        description="starts after the window opens",
        policy_type=PolicyType.INCOME_TAX,
        start_year=APP_DEFAULT_START_YEAR + 3,
    )
    assert _open_no_earlier_than(late, None).start_year == APP_DEFAULT_START_YEAR + 3

    early = TaxPolicy(
        name="early",
        description="states the library default",
        policy_type=PolicyType.INCOME_TAX,
        start_year=2025,
    )
    assert _open_no_earlier_than(early, None).start_year == APP_DEFAULT_START_YEAR
