"""The four-case regression: every surface must quote the same numbers.

``planning/redesign/NOTES.md`` §4.4 documented a three-way disagreement — the
headline and Key Metrics used the engine's internal ``EconomicModel``, the
Economic Effects tab ran an independent macro adapter, only one of them charged
debt service, and Copy Summary printed the static *deficit* effect under the
label "Static Revenue Effect". Flipping the dynamic-scoring toggle also moved a
calibrated preset off its own benchmark.

Phase 4's rule, pinned here:

* the headline is the conventional score (static + behavioral) in **every**
  mode, so the TCJA preset keeps matching CBO with dynamic on or off;
* revenue feedback comes from **one** function
  (``dynamic_scoring.compute_dynamic_view``) and is identical in Key Metrics,
  on the Economic Effects tab, and in Copy Summary;
* debt service is netted in **both** dynamic surfaces or neither.

Four cases: {TCJA calibrated preset, generic custom run} × {dynamic on, off}.
"""

from __future__ import annotations

import re

import pytest

from components.results import ScoredResult
from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.models.macro_adapter import (
    FRBUSAdapterLite,
    MacroScenario,
    SimpleMultiplierAdapter,
)
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.helpers import build_macro_scenario
from fiscal_model.ui.policy_execution import run_dynamic_view
from fiscal_model.ui.tabs.dynamic_scoring import render_dynamic_scoring_tab
from fiscal_model.ui.tabs.results_summary import (
    build_csv_export,
    build_text_summary,
    render_metrics_block,
)

TCJA_PRESET = next(name for name in PRESET_POLICIES if "TCJA Full Extension" in name)
TCJA_OFFICIAL = CBO_SCORE_MAP[TCJA_PRESET]["official_score"]


# ---------------------------------------------------------------------------
# A Streamlit stand-in that records what each surface printed
# ---------------------------------------------------------------------------


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _RecordingStreamlit:
    """Captures ``metric`` labels/values and every markdown/caption string."""

    def __init__(self) -> None:
        self.session_state = _SessionState()
        self.metrics: dict[str, str] = {}
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.errors: list[str] = []

    def metric(self, label, value, *args, **kwargs):
        self.metrics[str(label)] = str(value)

    def markdown(self, body="", *args, **kwargs):
        self.markdowns.append(str(body))

    def caption(self, body="", *args, **kwargs):
        self.captions.append(str(body))

    def subheader(self, *args, **kwargs):
        return None

    def header(self, *args, **kwargs):
        return None

    def code(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, message="", *args, **kwargs):
        self.errors.append(str(message))

    def dataframe(self, *args, **kwargs):
        return None

    def download_button(self, *args, **kwargs):
        return None

    def plotly_chart(self, *args, **kwargs):
        return None

    def selectbox(self, *args, **kwargs):
        return "(none)"

    def spinner(self, *args, **kwargs):
        return _Ctx()

    def expander(self, *args, **kwargs):
        return _Ctx()

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Ctx() for _ in range(count)]


# ---------------------------------------------------------------------------
# Fixtures: the four runs
# ---------------------------------------------------------------------------


def _dollars(text: str) -> float:
    """Parse ``$+4,581.9B`` / ``$-305B`` into a float."""
    match = re.search(r"\$\s*([+-]?[\d,]+(?:\.\d+)?)", text)
    assert match, f"no dollar figure in {text!r}"
    return float(match.group(1).replace(",", ""))


def _score(policy, *, dynamic: bool, policy_name: str, start_year: int = 2025):
    scorer = FiscalPolicyScorer(start_year=start_year, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=dynamic)
    return {
        "policy": policy,
        "result": result,
        "scorer": scorer,
        "is_spending": False,
        "policy_name": policy_name,
    }


def _build(result_data, *, dynamic: bool, spec_hash: str = "hash-1"):
    view = None
    if dynamic:
        view, _macro = run_dynamic_view(
            policy=result_data["policy"],
            result=result_data["result"],
            is_spending=False,
            macro_model_name="FRB/US-Lite (recommended)",
            macro_scenario_cls=MacroScenario,
            frbus_adapter_lite_cls=FRBUSAdapterLite,
            simple_multiplier_adapter_cls=SimpleMultiplierAdapter,
            build_macro_scenario_fn=build_macro_scenario,
        )
        assert view is not None, "the macro adapter must produce a dynamic view"
    return ScoredResult.from_pipeline(
        result_data=result_data,
        policy_spec_hash=spec_hash,
        dynamic_scoring=dynamic,
        dynamic_view=view,
        cbo_score_map=CBO_SCORE_MAP,
        baseline_vintage="CBO Feb 2026",
    )


def _tcja_run(dynamic: bool):
    policy = create_policy_from_preset(PRESET_POLICIES[TCJA_PRESET])
    data = _score(
        policy,
        dynamic=dynamic,
        policy_name=TCJA_PRESET,
        start_year=getattr(policy, "start_year", 2025),
    )
    return data, _build(data, dynamic=dynamic)


def _generic_run(dynamic: bool):
    policy = TaxPolicy(
        name="Custom top-rate surcharge",
        description="+2.0pp for AGI >= $400,000",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
        duration_years=10,
        phase_in_years=1,
    )
    data = _score(policy, dynamic=dynamic, policy_name="Custom Policy")
    return data, _build(data, dynamic=dynamic)


CASES = {
    "tcja_conventional": (_tcja_run, False),
    "tcja_dynamic": (_tcja_run, True),
    "generic_conventional": (_generic_run, False),
    "generic_dynamic": (_generic_run, True),
}


@pytest.fixture(scope="module")
def runs():
    return {name: builder(dynamic) for name, (builder, dynamic) in CASES.items()}


# ---------------------------------------------------------------------------
# Surface readers
# ---------------------------------------------------------------------------


def _key_metrics(result_data, scored) -> _RecordingStreamlit:
    st = _RecordingStreamlit()
    render_metrics_block(st, scored, result_data)
    return st


def _economic_effects(result_data, scored) -> _RecordingStreamlit:
    st = _RecordingStreamlit()
    render_dynamic_scoring_tab(
        st_module=st,
        dynamic_scoring=scored.is_dynamic,
        result_data=result_data,
        macro_model_name="FRB/US-Lite (recommended)",
        macro_scenario_cls=MacroScenario,
        frbus_adapter_lite_cls=FRBUSAdapterLite,
        simple_multiplier_adapter_cls=SimpleMultiplierAdapter,
        build_macro_scenario_fn=build_macro_scenario,
        run_id=None,
    )
    assert not st.errors, st.errors
    return st


# ---------------------------------------------------------------------------
# The four cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", sorted(CASES))
def test_headline_key_metrics_and_copy_summary_agree(runs, case):
    result_data, scored = runs[case]

    metrics = _key_metrics(result_data, scored)
    assert _dollars(metrics.metrics["Static Deficit Effect (10Y)"]) == pytest.approx(
        scored.static, abs=0.15
    )
    assert _dollars(metrics.metrics["Behavioral Response (10Y)"]) == pytest.approx(
        scored.behavioral, abs=0.15
    )

    text = build_text_summary(scored, result_data)
    assert _dollars(text.splitlines()[
        next(i for i, line in enumerate(text.splitlines()) if "Deficit Impact (conventional)" in line)
    ]) == pytest.approx(scored.headline, abs=0.15)
    assert f"Static Deficit Effect: ${scored.static:+,.1f}B" in text
    assert f"Behavioral Offset: ${scored.behavioral:+,.1f}B" in text


@pytest.mark.parametrize("case", sorted(CASES))
def test_copy_summary_no_longer_mislabels_the_static_deficit_term(runs, case):
    """NOTES §4.4 item 5 / §11 item 20: the label was the opposite sign."""
    result_data, scored = runs[case]
    text = build_text_summary(scored, result_data)
    assert "Static Revenue Effect" not in text
    assert "Static Deficit Effect" in text


@pytest.mark.parametrize("case", ["tcja_dynamic", "generic_dynamic"])
def test_key_metrics_feedback_equals_economic_effects_feedback(runs, case):
    """One feedback number, one model, two surfaces."""
    result_data, scored = runs[case]

    metrics = _key_metrics(result_data, scored)
    economic = _economic_effects(result_data, scored)

    km_feedback = _dollars(metrics.metrics["Revenue Feedback (10Y)"])
    ee_feedback = _dollars(economic.metrics["Revenue Feedback"])
    assert km_feedback == pytest.approx(ee_feedback, abs=1.0)
    assert km_feedback == pytest.approx(scored.feedback, abs=1.0)


@pytest.mark.parametrize("case", ["tcja_dynamic", "generic_dynamic"])
def test_debt_service_is_netted_on_both_dynamic_surfaces(runs, case):
    result_data, scored = runs[case]

    metrics = _key_metrics(result_data, scored)
    economic = _economic_effects(result_data, scored)

    assert _dollars(metrics.metrics["Debt Service (10Y)"]) == pytest.approx(
        _dollars(economic.metrics["Debt Service"]), abs=1.0
    )
    assert _dollars(metrics.metrics["Dynamic Total (10Y)"]) == pytest.approx(
        _dollars(economic.metrics["Dynamic Score"]), abs=1.0
    )
    # The arithmetic the two surfaces print must actually hold.
    assert scored.dynamic_total == pytest.approx(
        scored.headline - scored.feedback + scored.debt_service, abs=1e-6
    )


@pytest.mark.parametrize("case", ["tcja_conventional", "generic_conventional"])
def test_conventional_runs_say_not_included_rather_than_zero(runs, case):
    """A static run must not assert $0.0B feedback while another tab shows one."""
    result_data, scored = runs[case]
    metrics = _key_metrics(result_data, scored)
    assert metrics.metrics["Revenue Feedback (10Y)"] == "Not included"
    assert "Debt Service (10Y)" not in metrics.metrics
    assert scored.feedback == 0.0
    assert "Revenue Feedback: not included" in build_text_summary(scored, result_data)


@pytest.mark.parametrize("case", ["tcja_dynamic", "generic_dynamic"])
def test_economic_effects_conventional_score_is_the_headline(runs, case):
    result_data, scored = runs[case]
    economic = _economic_effects(result_data, scored)
    assert _dollars(economic.metrics["Conventional Score"]) == pytest.approx(
        scored.headline, abs=1.0
    )


# ---------------------------------------------------------------------------
# The calibrated preset must not drift off its benchmark when the toggle flips
# ---------------------------------------------------------------------------


def test_tcja_headline_is_identical_with_dynamic_on_and_off(runs):
    _, static_scored = runs["tcja_conventional"]
    _, dynamic_scored = runs["tcja_dynamic"]
    assert static_scored.headline == pytest.approx(dynamic_scored.headline, abs=1e-6)


@pytest.mark.parametrize("case", ["tcja_conventional", "tcja_dynamic"])
def test_tcja_headline_still_matches_the_official_benchmark(runs, case):
    """The whole point of the rule: a toggle must not change the error %."""
    _, scored = runs[case]
    error_pct = abs(scored.headline - TCJA_OFFICIAL) / abs(TCJA_OFFICIAL) * 100
    assert error_pct < 1.0, f"{case} drifted to {error_pct:.1f}% off CBO"
    assert scored.tier == "calibrated"
    assert scored.benchmark is not None and scored.benchmark["is_exact"] is True


def test_dynamic_view_is_reported_separately_not_folded_into_the_headline(runs):
    """The engine still nets feedback internally; the UI headline must not."""
    result_data, scored = runs["tcja_dynamic"]
    engine_final = float(result_data["result"].final_deficit_effect.sum())
    assert engine_final != pytest.approx(scored.headline, abs=1.0)
    assert scored.feedback > 0
    assert scored.dynamic_total != pytest.approx(scored.headline, abs=1.0)


# ---------------------------------------------------------------------------
# Exports carry the provenance every artifact must carry (plan §9.10)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", sorted(CASES))
def test_every_export_carries_name_status_vintage_window_tier_and_mode(runs, case):
    result_data, scored = runs[case]
    csv_text = build_csv_export(scored, result_data, "https://example.com/share")
    summary = build_text_summary(scored, result_data, "https://example.com/share")

    for artifact in (csv_text, summary):
        assert scored.display_name in artifact
        assert scored.policy_status in artifact
        assert scored.baseline_vintage in artifact
        assert scored.window in artifact
        assert scored.tier in artifact
        assert scored.mode in artifact
        assert "https://example.com/share" in artifact

    assert "positive = increases the deficit" in csv_text
    assert "Sign convention: positive = increases the deficit." in summary


@pytest.mark.parametrize("case", sorted(CASES))
def test_detailed_breakdown_uses_the_same_sign_convention_as_the_headline(runs, case):
    """It summed a revenue-convention static term with a deficit-convention one."""
    from fiscal_model.ui.tabs.detailed_results import render_detailed_results_tab

    result_data, scored = runs[case]

    captured: list = []

    class _Capture(_RecordingStreamlit):
        def table(self, frame, *args, **kwargs):
            captured.append(("table", frame))

        def dataframe(self, frame, *args, **kwargs):
            captured.append(("frame", frame))

        def download_button(self, *, label, data, **kwargs):
            captured.append((label, data))

    st = _Capture()
    render_detailed_results_tab(st, result_data, scored=scored)
    assert not st.errors, st.errors

    frame = next(obj for kind, obj in captured if kind == "frame")
    per_year = [
        float(cell.replace("$", "").replace(",", ""))
        for cell in frame["Conventional Deficit Effect ($B)"]
    ]
    assert sum(per_year) == pytest.approx(scored.headline, abs=0.5)
    assert "Static Revenue Effect ($B)" not in frame.columns

    import json

    payload = json.loads(next(data for label, data in captured if label.endswith("JSON")))
    provenance = payload["provenance"]
    assert provenance["baseline_vintage"] == scored.baseline_vintage
    assert provenance["window"] == scored.window
    assert provenance["tier"] == scored.tier
    assert provenance["mode"] == scored.mode
    assert payload["policy"]["status"] == scored.policy_status
    assert payload["results"]["conventional_deficit_10yr"] == pytest.approx(
        scored.headline, abs=1e-6
    )


@pytest.mark.parametrize("case", sorted(CASES))
def test_headline_copy_line_matches_the_headline(runs, case):
    from fiscal_model.ui.tabs.results_summary import build_headline_copy

    _, scored = runs[case]
    line = build_headline_copy(scored)
    assert _dollars(line) == pytest.approx(scored.headline, abs=0.15)
    assert scored.baseline_vintage in line
    assert scored.window in line
