"""
The API, the Ask assistant and every in-app surface report the app's dynamic view.

Until 2026-09-29 ``POST /score`` and ``/score/preset`` with ``"dynamic": true``,
Ask's ``score_hypothetical_policy`` and the Ask page's scoring context reported
the scoring engine's ``EconomicModel`` feedback, while the result page showed
FRB/US-Lite. For +2.6pp above $400,000 that was -$86.1B against -$338.9B. So
did the Scoring Methods tab (under an "FRB/US-Lite" label), the side-by-side
compare, the state tab, three captions under the headline, the cumulative
chart's band and the CSV export's GDP columns.

Every test here compares a surface with the app's own completion step
(``calculation_controller.build_scored_result``, the function that builds what
the result page renders) run on the same policy, or asserts that
``EconomicModel`` is never consulted.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.baseline import APP_DEFAULT_START_YEAR
from fiscal_model.dynamic_view import (
    DEFAULT_MACRO_MODEL_SETTING,
    FRBUS_LITE_MODEL_LABEL,
    SIMPLE_MULTIPLIER_MODEL_LABEL,
    SIMPLE_MULTIPLIER_SETTING,
    conventional_path,
    conventional_total,
    macro_setting_for_label,
    policy_is_spending,
    run_dynamic_view,
)
from fiscal_model.economics import EconomicModel
from fiscal_model.models.macro_adapter import FRBUSAdapterLite
from fiscal_model.policies import CapitalGainsPolicy, PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.scoring import FiscalPolicyScorer

#: The policy the finding was measured on.
REFERENCE_REQUEST = {
    "name": "+2.6pp above $400K",
    "description": "Dynamic routing reference",
    "rate_change": 0.026,
    "income_threshold": 400_000,
}
CORPORATE_PRESET = "🏢 Biden Corporate 28% (CBO: -$1.35T)"
SALT_PRESET = "📋 Repeal SALT Cap ($1.17T)"


@pytest.fixture(scope="module")
def app_deps():
    from fiscal_model.ui.dependencies import build_app_dependencies

    return build_app_dependencies(pd_module=pd)


@pytest.fixture(autouse=True)
def _fixed_baseline_vintage(monkeypatch):
    """The vintage label is not under test, and resolving it runs every health check."""
    monkeypatch.setattr("components.results.resolve_baseline_vintage", lambda: "CBO Feb 2026")


def _reference_policy() -> TaxPolicy:
    return TaxPolicy(
        name=REFERENCE_REQUEST["name"],
        description=REFERENCE_REQUEST["description"],
        policy_type=PolicyType.INCOME_TAX,
        rate_change=REFERENCE_REQUEST["rate_change"],
        affected_income_threshold=REFERENCE_REQUEST["income_threshold"],
        start_year=APP_DEFAULT_START_YEAR,
    )


def _recording_scorer_cls():
    calls: list[tuple[object, bool]] = []

    class _Recording(FiscalPolicyScorer):
        def score_policy(self, policy, dynamic=False, include_uncertainty=True):
            calls.append((policy, dynamic))
            return super().score_policy(
                policy, dynamic=dynamic, include_uncertainty=include_uncertainty
            )

    return _Recording, calls


def _app_run(policy, *, use_real_data: bool, start_year: int = APP_DEFAULT_START_YEAR,
             is_spending: bool = False) -> dict:
    """A run as the app's calculation paths produce one with dynamic scoring on.

    The app scores with the toggle's value, so ``EconomicModel`` runs here and
    its figures sit on the result. That is the point: no surface may show them.
    """
    scorer = FiscalPolicyScorer(baseline=None, start_year=start_year, use_real_data=use_real_data)
    return {
        "policy": policy,
        "result": scorer.score_policy(policy, dynamic=True),
        "scorer": scorer,
        "is_spending": is_spending,
        "policy_name": policy.name,
    }


def _app_scored_result(result_data: dict, deps, *, macro_model: str = DEFAULT_MACRO_MODEL_SETTING):
    """What the result page renders for this run: the app's own completion step."""
    from fiscal_model.ui.calculation_controller import build_scored_result

    st = SimpleNamespace(session_state={"results": result_data})
    scored = build_scored_result(
        st, deps, {"run_id": "routing"}, {"dynamic_scoring": True, "macro_model": macro_model}
    )
    assert scored is not None and scored.mode == "dynamic"
    return scored


def _assistant_tools(scorer):
    from fiscal_model.assistant.tools import AssistantTools

    return AssistantTools(
        scorer=scorer,
        baseline=scorer.baseline,
        cbo_score_map=CBO_SCORE_MAP,
        presets=PRESET_POLICIES,
        policy_types=PolicyType,
        tax_policy_cls=TaxPolicy,
        spending_policy_cls=SpendingPolicy,
    )


def _boom(self, scenario):
    raise RuntimeError("macro model down")


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------


def test_api_score_returns_the_dynamic_view_the_app_shows(monkeypatch, app_deps):
    scorer_cls, calls = _recording_scorer_cls()
    monkeypatch.setattr(api_module, "FiscalPolicyScorer", scorer_cls)

    response = TestClient(api_module.app).post("/score", json={**REFERENCE_REQUEST, "dynamic": True})
    assert response.status_code == 200, response.text
    payload = response.json()

    ((policy, engine_dynamic),) = calls
    assert engine_dynamic is False
    result_data = _app_run(policy, use_real_data=True)
    scored = _app_scored_result(result_data, app_deps)

    assert payload["ten_year_deficit_impact"] == pytest.approx(scored.headline)
    assert payload["revenue_feedback"] == pytest.approx(scored.feedback)
    assert payload["debt_service"] == pytest.approx(scored.debt_service)
    assert payload["dynamic_adjusted_impact"] == pytest.approx(scored.dynamic_total)
    assert payload["dynamic_model"] == scored.macro_model == FRBUS_LITE_MODEL_LABEL
    # The same run carries EconomicModel's figure, which is far from the view.
    engine_total = float(result_data["result"].total_10_year_cost)
    assert abs(engine_total - payload["dynamic_adjusted_impact"]) > 100.0


def test_api_score_preset_returns_the_dynamic_view_the_app_shows(app_deps):
    from fiscal_model.ui.policy_execution import calculate_tax_policy_result

    response = TestClient(api_module.app).post(
        "/score/preset", json={"preset_name": CORPORATE_PRESET, "dynamic": True}
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    # The app's own preset path, exactly as the Explore page runs it.
    result_data = calculate_tax_policy_result(
        preset_policies=PRESET_POLICIES,
        preset_choice=CORPORATE_PRESET,
        create_policy_from_preset_fn=create_policy_from_preset,
        dynamic_scoring=True,
        use_real_data=True,
        fiscal_policy_scorer_cls=FiscalPolicyScorer,
        tax_policy_cls=TaxPolicy,
        capital_gains_policy_cls=CapitalGainsPolicy,
        policy_type_cls=PolicyType,
        policy_type="Income Tax Rate",
        policy_name=CORPORATE_PRESET,
        rate_change_pct=0.0,
        rate_change=0.0,
        threshold=0,
        data_year=2023,
        duration=10,
        phase_in=1,
        eti=0.25,
        ordinary_income_base=True,
        manual_taxpayers=0.0,
        manual_avg_income=0.0,
        cg_base_year=2023,
        baseline_cg_rate=0.2,
        baseline_realizations=0.0,
        realization_elasticity=0.5,
        persistent_elasticity=0.72,
        transitory_elasticity=1.2,
        use_time_varying=False,
        eliminate_step_up=False,
        step_up_exemption=0.0,
    )
    scored = _app_scored_result(result_data, app_deps)

    assert payload["ten_year_deficit_impact"] == pytest.approx(scored.headline)
    assert payload["revenue_feedback"] == pytest.approx(scored.feedback)
    assert payload["debt_service"] == pytest.approx(scored.debt_service)
    assert payload["dynamic_adjusted_impact"] == pytest.approx(scored.dynamic_total)
    assert payload["dynamic_model"] == scored.macro_model


def test_economic_model_is_never_consulted_by_the_api_or_ask(monkeypatch):
    def _forbidden(self, *args, **kwargs):
        raise AssertionError("EconomicModel ran for a surface that reports the app's view")

    monkeypatch.setattr(EconomicModel, "calculate_effects", _forbidden)

    client = TestClient(api_module.app)
    for path, body in (
        ("/score", {**REFERENCE_REQUEST, "dynamic": True}),
        ("/score/preset", {"preset_name": CORPORATE_PRESET, "dynamic": True}),
    ):
        response = client.post(path, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["dynamic_adjusted_impact"] is not None

    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=True)
    out = _assistant_tools(scorer).tool_score_hypothetical_policy(
        name="ref",
        policy_type="income_tax",
        rate_change=REFERENCE_REQUEST["rate_change"],
        affected_income_threshold=REFERENCE_REQUEST["income_threshold"],
        dynamic=True,
    )
    assert "error" not in out, out
    assert out["is_dynamic"] is True


def test_no_preset_is_an_outlay_impulse_so_every_path_agrees_on_the_scenario():
    """The app's preset path hard-codes ``is_spending: False``; the shared rule
    reads the policy. They agree on every preset, and this fails if a preset
    ever builds a ``SpendingPolicy`` and the two would diverge."""
    for label, data in PRESET_POLICIES.items():
        policy = create_policy_from_preset(data)
        if policy is not None:
            assert not policy_is_spending(policy), label
    assert policy_is_spending(
        SpendingPolicy(
            name="x",
            description="x",
            policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
            annual_spending_change_billions=1.0,
        )
    )


# ---------------------------------------------------------------------------
# The shared runner
# ---------------------------------------------------------------------------


def test_run_dynamic_view_defaults_to_frbus_lite_and_degrades_to_none(monkeypatch):
    policy = _reference_policy()
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    view, macro = run_dynamic_view(policy, result)
    assert view is not None and macro is not None
    assert view.model_name == FRBUS_LITE_MODEL_LABEL
    assert view.conventional == pytest.approx(conventional_total(result))
    assert view.dynamic_total == pytest.approx(view.conventional - view.feedback + view.debt_service)
    # The view reads only the conventional path, so how the engine ran does
    # not move it.
    assert run_dynamic_view(policy, scorer.score_policy(policy, dynamic=True))[0] == view

    simple, _ = run_dynamic_view(policy, result, macro_model_name=SIMPLE_MULTIPLIER_SETTING)
    assert simple is not None
    assert simple.model_name == SIMPLE_MULTIPLIER_MODEL_LABEL
    assert simple.dynamic_total != pytest.approx(view.dynamic_total)
    assert macro_setting_for_label(SIMPLE_MULTIPLIER_MODEL_LABEL) == SIMPLE_MULTIPLIER_SETTING
    assert macro_setting_for_label(FRBUS_LITE_MODEL_LABEL) == DEFAULT_MACRO_MODEL_SETTING
    assert macro_setting_for_label(None) == DEFAULT_MACRO_MODEL_SETTING

    monkeypatch.setattr(FRBUSAdapterLite, "run", _boom)
    assert run_dynamic_view(policy, result) == (None, None)


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------


def test_ask_hypothetical_returns_the_dynamic_view_the_app_shows(app_deps):
    scorer_cls, calls = _recording_scorer_cls()
    scorer = scorer_cls(start_year=APP_DEFAULT_START_YEAR, use_real_data=True)
    tools = _assistant_tools(scorer)
    kwargs = {
        "name": REFERENCE_REQUEST["name"],
        "policy_type": "income_tax",
        "rate_change": REFERENCE_REQUEST["rate_change"],
        "affected_income_threshold": REFERENCE_REQUEST["income_threshold"],
    }
    out = tools.tool_score_hypothetical_policy(**kwargs, dynamic=True)

    ((policy, engine_dynamic),) = calls
    assert engine_dynamic is False
    scored = _app_scored_result(_app_run(policy, use_real_data=True), app_deps)

    assert out["is_dynamic"] is True
    assert out["raw_engine_estimate_billions"] == pytest.approx(scored.headline)
    assert out["revenue_feedback_10yr_billions"] == pytest.approx(scored.feedback)
    assert out["debt_service_10yr_billions"] == pytest.approx(scored.debt_service)
    assert out["dynamic_total_10yr_billions"] == pytest.approx(scored.dynamic_total)
    assert out["dynamic_model"] == scored.macro_model
    assert "never as the headline" in out["dynamic_note"]

    # Asking for the dynamic view does not move the gate's headline.
    static = tools.tool_score_hypothetical_policy(**kwargs, dynamic=False)
    assert static["is_dynamic"] is False
    assert static["revenue_feedback_10yr_billions"] == 0.0
    assert "dynamic_total_10yr_billions" not in static
    assert out["ten_year_deficit_impact_billions"] == static["ten_year_deficit_impact_billions"]
    assert out["raw_engine_estimate_billions"] == pytest.approx(static["raw_engine_estimate_billions"])


def test_a_macro_failure_leaves_ask_with_the_conventional_score_and_says_so(monkeypatch):
    monkeypatch.setattr(FRBUSAdapterLite, "run", _boom)
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=False)
    out = _assistant_tools(scorer).tool_score_hypothetical_policy(
        name="ref", policy_type="income_tax", rate_change=0.01, dynamic=True
    )
    assert "error" not in out, out
    assert out["is_dynamic"] is False
    assert "dynamic_view_error" in out
    assert "dynamic_total_10yr_billions" not in out
    assert out["revenue_feedback_10yr_billions"] == 0.0


@pytest.mark.parametrize(
    ("policy_type", "category"),
    [
        ("discretionary_nondefense", "nondefense"),
        ("discretionary_defense", "defense"),
        ("mandatory_spending", "mandatory"),
    ],
)
def test_ask_spending_hypotheticals_score_as_the_requested_category(policy_type, category):
    """Every spending hypothetical used to fail to construct.

    The tool passed ``spending_change_billions``, which ``SpendingPolicy``
    rejects, and, had it constructed, the dataclass would have re-derived
    ``policy_type`` from its default ``nondefense`` category.
    """
    scorer_cls, calls = _recording_scorer_cls()
    scorer = scorer_cls(start_year=APP_DEFAULT_START_YEAR, use_real_data=False)
    out = _assistant_tools(scorer).tool_score_hypothetical_policy(
        name="+$50B a year", policy_type=policy_type, spending_change_billions=50.0, dynamic=True
    )
    assert "error" not in out, out

    ((policy, _),) = calls
    assert isinstance(policy, SpendingPolicy)
    assert policy.category == category
    assert policy.policy_type.value == policy_type
    assert policy.annual_spending_change_billions == 50.0
    assert out["raw_engine_estimate_billions"] > 0.0

    # An outlay impulse, as the app's spending form scores one.
    result = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=False).score_policy(policy)
    as_outlays, _ = run_dynamic_view(policy, result, is_spending=True)
    as_receipts, _ = run_dynamic_view(policy, result, is_spending=False)
    assert as_outlays is not None and as_receipts is not None
    assert out["dynamic_total_10yr_billions"] == pytest.approx(as_outlays.dynamic_total)
    assert out["dynamic_total_10yr_billions"] != pytest.approx(as_receipts.dynamic_total)


def test_the_ask_page_reports_the_figures_the_result_page_shows(app_deps):
    from fiscal_model.ui.tabs.ask_assistant import _scoring_context, _scoring_summary

    result_data = _app_run(_reference_policy(), use_real_data=True)
    scored = _app_scored_result(result_data, app_deps)
    engine = result_data["result"]

    ctx = _scoring_context(result_data, scored=scored)
    assert ctx is not None
    assert ctx["ten_year_deficit_impact_billions"] == pytest.approx(scored.headline)
    assert ctx["is_dynamic"] is True
    assert ctx["dynamic_model"] == scored.macro_model
    assert ctx["revenue_feedback_10yr_billions"] == pytest.approx(scored.feedback)
    assert ctx["debt_service_10yr_billions"] == pytest.approx(scored.debt_service)
    assert ctx["dynamic_total_10yr_billions"] == pytest.approx(scored.dynamic_total)
    # Not the engine's EconomicModel figures, which this run also carries.
    assert abs(ctx["ten_year_deficit_impact_billions"] - float(engine.total_10_year_cost)) > 100.0
    assert abs(ctx["revenue_feedback_10yr_billions"] - float(engine.revenue_feedback_10yr)) > 100.0
    assert f"{abs(scored.headline):,.0f}B" in _scoring_summary(result_data)

    # Without the page's object, or with one from another run, Ask reports no
    # dynamic view rather than EconomicModel's.
    bare = _scoring_context(result_data)
    assert bare is not None
    assert bare["is_dynamic"] is False
    assert bare["revenue_feedback_10yr_billions"] == 0.0
    assert "dynamic_total_10yr_billions" not in bare
    assert bare["ten_year_deficit_impact_billions"] == pytest.approx(scored.headline)
    stale = dataclasses.replace(scored, headline=scored.headline + 100.0)
    assert _scoring_context(result_data, scored=stale)["is_dynamic"] is False


# ---------------------------------------------------------------------------
# In-app surfaces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("macro_model", "label"),
    [
        (DEFAULT_MACRO_MODEL_SETTING, "FRB/US-Lite (Dynamic)"),
        (SIMPLE_MULTIPLIER_SETTING, "Simple Multiplier (Dynamic)"),
    ],
)
def test_the_scoring_methods_dynamic_column_is_the_apps_dynamic_total(app_deps, macro_model, label):
    from fiscal_model.ui.tabs.policy_comparison import _score_model, dynamic_model_label

    assert dynamic_model_label(macro_model) == label
    policy = create_policy_from_preset(PRESET_POLICIES[CORPORATE_PRESET])
    scorer = FiscalPolicyScorer(
        start_year=max(int(policy.start_year), APP_DEFAULT_START_YEAR), use_real_data=False
    )
    dynamic_row = _score_model(
        policy_name=CORPORATE_PRESET,
        model_name=label,
        policy=policy,
        scorer=scorer,
        dynamic=True,
        macro_model_name=macro_model,
    )
    static_row = _score_model(
        policy_name=CORPORATE_PRESET,
        model_name="CBO-Style (Static + ETI)",
        policy=policy,
        scorer=scorer,
        dynamic=False,
    )
    result_data = {
        "policy": policy,
        "result": scorer.score_policy(policy, dynamic=True),
        "is_spending": False,
        "policy_name": CORPORATE_PRESET,
    }
    scored = _app_scored_result(result_data, app_deps, macro_model=macro_model)

    assert dynamic_row["ten_year_cost"] == pytest.approx(scored.dynamic_total)
    assert static_row["ten_year_cost"] == pytest.approx(scored.headline)
    assert float(np.sum(dynamic_row["annual_effects"])) == pytest.approx(scored.dynamic_total)


def test_side_by_side_keeps_conventional_totals_and_adds_the_dynamic_view(app_deps):
    from fiscal_model.ui.tabs.side_by_side import _score

    policy = create_policy_from_preset(PRESET_POLICIES[CORPORATE_PRESET])
    scorer = FiscalPolicyScorer(baseline=None, start_year=APP_DEFAULT_START_YEAR, use_real_data=False)
    dynamic = _score(policy, scorer, True)
    static = _score(policy, scorer, False)
    scored = _app_scored_result(
        {
            "policy": policy,
            "result": scorer.score_policy(policy, dynamic=True),
            "is_spending": False,
            "policy_name": CORPORATE_PRESET,
        },
        app_deps,
    )

    assert dynamic["ten_year"] == pytest.approx(scored.headline)
    assert static["ten_year"] == pytest.approx(scored.headline)
    assert dynamic["dynamic_total"] == pytest.approx(scored.dynamic_total)
    assert dynamic["dynamic_model"] == scored.macro_model
    assert static["dynamic_total"] is None


def test_the_state_tab_prices_the_conventional_path():
    from fiscal_model.ui.tabs.state_analysis import _render_policy_impact, _state_revenue_share

    policy = _reference_policy()
    result = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=True).score_policy(
        policy, dynamic=True
    )
    metrics: list[tuple[str, str]] = []

    class _Streamlit:
        def markdown(self, *args, **kwargs):
            pass

        def caption(self, *args, **kwargs):
            pass

        def columns(self, n):
            return [contextlib.nullcontext() for _ in range(n)]

        def metric(self, label, value, **kwargs):
            metrics.append((label, value))

    _render_policy_impact(
        _Streamlit(),
        "CA",
        "California",
        {"policy": policy, "result": result},
        SimpleNamespace(top_rate=0.133, has_local_tax_caveat=False),
    )
    share = _state_revenue_share("CA")
    expected = conventional_total(result) / len(result.years) * share
    engine = float(np.sum(result.final_deficit_effect)) / len(result.years) * share
    assert metrics[0][1] == f"${expected:.1f}B / yr"
    assert f"{engine:.1f}" != f"{expected:.1f}"


def test_captions_under_the_headline_quote_the_conventional_score_on_a_dynamic_run():
    from fiscal_model.composer.composer import _build_preset_policy, _scorer_for
    from fiscal_model.ui.tabs.results_summary import (
        agi_income_column_caption,
        salt_current_law_caption,
    )

    salt_policy = create_policy_from_preset(PRESET_POLICIES[SALT_PRESET])
    salt_scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=False)
    warren, use_real = _build_preset_policy(
        "Warren Ultra-Millionaire Surtax", PRESET_POLICIES["Warren Ultra-Millionaire Surtax"]
    )
    cases = (
        (salt_current_law_caption, salt_policy, salt_scorer),
        (agi_income_column_caption, warren, _scorer_for(warren, use_real)),
    )
    for caption, policy, scorer in cases:
        static = scorer.score_policy(policy, dynamic=False)
        dynamic = scorer.score_policy(policy, dynamic=True)
        # The premise: EconomicModel moves ``final_deficit_effect`` here.
        assert float(np.sum(dynamic.final_deficit_effect)) != pytest.approx(
            conventional_total(dynamic), abs=1.0
        ), caption.__name__
        static_text = caption(policy, static)
        assert static_text, caption.__name__
        assert caption(policy, dynamic) == static_text, caption.__name__


def test_the_band_and_the_csv_are_centred_on_the_conventional_path(app_deps):
    from fiscal_model.ui.tabs.results_summary import build_csv_export, conventional_bounds

    policy = _reference_policy()
    static_result = FiscalPolicyScorer(
        baseline=None, start_year=APP_DEFAULT_START_YEAR, use_real_data=True
    ).score_policy(policy, dynamic=False)
    result_data = _app_run(policy, use_real_data=True)
    scored = _app_scored_result(result_data, app_deps)
    dynamic_result = result_data["result"]

    low, high = conventional_bounds(dynamic_result)
    path = conventional_path(dynamic_result)
    assert np.all(low <= path) and np.all(path <= high)
    # The band a dynamic run draws is the band a conventional run draws; the
    # engine's own arrays on the dynamic run are centred on EconomicModel's path.
    np.testing.assert_allclose(low, static_result.low_estimate)
    np.testing.assert_allclose(high, static_result.high_estimate)
    assert not np.allclose(dynamic_result.low_estimate, static_result.low_estimate)
    static_low, static_high = conventional_bounds(static_result)
    np.testing.assert_array_equal(static_low, static_result.low_estimate)
    np.testing.assert_array_equal(static_high, static_result.high_estimate)

    frame = pd.read_csv(io.StringIO(build_csv_export(scored, result_data)), comment="#")
    assert frame["Conventional Deficit Effect ($B)"].sum() == pytest.approx(scored.headline)
    assert frame["Revenue Feedback ($B)"].sum() == pytest.approx(scored.feedback)
    assert frame["Debt Service ($B)"].sum() == pytest.approx(scored.debt_service)
    assert frame["Dynamic Deficit Effect ($B)"].sum() == pytest.approx(scored.dynamic_total)
    np.testing.assert_allclose(frame["Low Estimate ($B)"], low)
    # EconomicModel's dollar GDP path has no counterpart in the adapter.
    assert "GDP Effect ($B)" not in frame.columns
    _view, macro = run_dynamic_view(policy, dynamic_result)
    assert macro is not None
    np.testing.assert_allclose(frame["GDP Effect (%)"], macro.gdp_level_pct)
    np.testing.assert_allclose(
        frame["Employment (thousands)"], np.asarray(macro.employment_change_millions) * 1000.0
    )
