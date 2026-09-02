"""The single result object: fields, ``from_pipeline``, and hash stability.

``ScoredResult`` is what every result surface renders (chip ⑩). These tests pin
its field set, the derivation of each field from a completed run, and the
policy-spec hash that drives invalidation — a hash that moved for a cosmetic
reason would blank the panel on every theme change; a hash that failed to move
would show one policy's numbers under another policy's inputs.
"""

from __future__ import annotations

import dataclasses

import pytest

from components.results import (
    SCORED_RESULT_KEY,
    SCORING_SETTING_KEYS,
    Benchmark,
    ScoredResult,
    compute_policy_spec_hash,
    get_scored_result,
    resolve_baseline_vintage,
    store_scored_result,
)
from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.session_state import ALL_KEYS, KEY_SCORED_RESULT
from fiscal_model.ui.tabs.dynamic_scoring import DynamicView

# The width the *UI* requires before it will draw a range, read from the
# production constant with the production comparison so the two cannot drift
# apart (Copilot review, 2026-09-01).
from fiscal_model.ui.tabs.results_summary import (
    _MIN_BAND_WIDTH_BILLIONS as MIN_BAND_WIDTH,
)

TCJA_PRESET = next(name for name in PRESET_POLICIES if "TCJA Full Extension" in name)

#: Every field the redesign plan §6.3 requires on the result object.
REQUIRED_FIELDS = {
    "policy_spec_hash",
    "policy_name",
    "mode",
    "window",
    "headline",
    "static",
    "behavioral",
    "feedback",
    "per_year",
    "tier",
    "benchmark",
    "baseline_vintage",
    "policy_status",
    "created_at",
    "sensitivity",
}


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _Session:
    def __init__(self):
        self.session_state = _SessionState()


def _generic_result_data(*, rate_change: float = 0.02, dynamic: bool = False):
    policy = TaxPolicy(
        name="Custom top-rate surcharge",
        description=f"{rate_change * 100:+.1f}pp for AGI >= $400,000",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=rate_change,
        affected_income_threshold=400_000,
    )
    scorer = FiscalPolicyScorer(use_real_data=False)
    return {
        "policy": policy,
        "result": scorer.score_policy(policy, dynamic=dynamic),
        "scorer": scorer,
        "is_spending": False,
        "policy_name": "Custom Policy",
    }


def _preset_result_data(dynamic: bool = False):
    policy = create_policy_from_preset(PRESET_POLICIES[TCJA_PRESET])
    scorer = FiscalPolicyScorer(
        start_year=getattr(policy, "start_year", 2025), use_real_data=False
    )
    return {
        "policy": policy,
        "result": scorer.score_policy(policy, dynamic=dynamic),
        "scorer": scorer,
        "is_spending": False,
        "policy_name": TCJA_PRESET,
    }


def _build(result_data, **kwargs):
    kwargs.setdefault("policy_spec_hash", "abc123")
    kwargs.setdefault("dynamic_scoring", False)
    kwargs.setdefault("cbo_score_map", CBO_SCORE_MAP)
    kwargs.setdefault("baseline_vintage", "CBO Feb 2026")
    return ScoredResult.from_pipeline(result_data=result_data, **kwargs)


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_scored_result_declares_every_required_field():
    names = {field.name for field in dataclasses.fields(ScoredResult)}
    assert REQUIRED_FIELDS <= names, REQUIRED_FIELDS - names


def test_scored_result_is_immutable():
    scored = _build(_generic_result_data())
    with pytest.raises(dataclasses.FrozenInstanceError):
        scored.headline = 0.0


def test_session_key_is_registered_in_the_schema():
    assert SCORED_RESULT_KEY == KEY_SCORED_RESULT
    assert SCORED_RESULT_KEY in ALL_KEYS


def test_store_and_get_round_trip():
    st = _Session()
    scored = _build(_generic_result_data())
    store_scored_result(st, scored)
    assert st.session_state[SCORED_RESULT_KEY] is scored
    assert get_scored_result(st) is scored


def test_as_dict_is_serialisable_and_drops_the_live_credibility_object():
    import json

    payload = _build(_generic_result_data()).as_dict()
    assert "credibility" not in payload
    json.dumps(payload)  # must not raise


# ---------------------------------------------------------------------------
# from_pipeline
# ---------------------------------------------------------------------------


def test_headline_is_the_conventional_score_not_the_engine_final():
    result_data = _generic_result_data(dynamic=True)
    scored = _build(result_data, dynamic_scoring=True)
    result = result_data["result"]

    conventional = float((result.static_deficit_effect + result.behavioral_offset).sum())
    assert scored.headline == pytest.approx(conventional, abs=1e-6)
    assert scored.headline == pytest.approx(scored.static + scored.behavioral, abs=1e-6)
    # The engine still nets its own internal feedback into final_deficit_effect;
    # the UI headline deliberately does not read it.
    assert float(result.final_deficit_effect.sum()) != pytest.approx(
        scored.headline, abs=1.0
    )


def test_mode_and_feedback_follow_the_dynamic_flag():
    conventional = _build(_generic_result_data())
    assert conventional.mode == "conventional"
    assert conventional.feedback == 0.0
    assert conventional.debt_service == 0.0
    assert conventional.dynamic_total == pytest.approx(conventional.headline)
    assert conventional.macro_model is None

    view = DynamicView(
        model_name="FRB/US-Lite (Federal Reserve calibrated)",
        conventional=100.0,
        feedback=20.0,
        debt_service=5.0,
        dynamic_total=85.0,
    )
    dynamic = _build(
        _generic_result_data(dynamic=True), dynamic_scoring=True, dynamic_view=view
    )
    assert dynamic.mode == "dynamic"
    assert dynamic.feedback == 20.0
    assert dynamic.debt_service == 5.0
    assert dynamic.dynamic_total == 85.0
    assert dynamic.macro_model == "FRB/US-Lite (Federal Reserve calibrated)"


def test_per_year_sums_to_the_headline():
    scored = _build(_generic_result_data())
    assert sum(scored.per_year) == pytest.approx(scored.headline, abs=1e-6)
    assert len(scored.per_year) == scored.n_years


def test_window_is_a_fiscal_year_range_drawn_from_the_baseline():
    result_data = _generic_result_data()
    scored = _build(result_data)
    start = int(result_data["result"].baseline.start_year)
    end = start + len(result_data["result"].baseline.years) - 1
    assert scored.window == f"FY{start}–FY{end}"
    assert (scored.window_start, scored.window_end) == (start, end)


def test_calibrated_preset_gets_its_exact_benchmark_and_tier():
    scored = _build(_preset_result_data())
    assert scored.tier == "calibrated"
    assert scored.benchmark["is_exact"] is True
    assert scored.benchmark["name"] == TCJA_PRESET
    assert scored.benchmark["official_billions"] == CBO_SCORE_MAP[TCJA_PRESET][
        "official_score"
    ]
    assert scored.policy_status  # curated status, not the hypothetical fallback


def test_generic_run_gets_the_nearest_same_signed_benchmark():
    """The wireframe's 'no official score exists ... nearest validated' line."""
    scored = _build(_generic_result_data(rate_change=0.02))
    assert scored.tier == "generic"
    assert scored.benchmark is not None
    assert scored.benchmark["is_exact"] is False
    # A deficit-reducing policy must be anchored to a deficit-reducing score.
    assert scored.headline < 0
    assert scored.benchmark["official_billions"] < 0
    assert "Hypothetical" in scored.policy_status


def test_benchmark_obj_round_trips_the_dict():
    scored = _build(_preset_result_data())
    benchmark = scored.benchmark_obj
    assert isinstance(benchmark, Benchmark)
    assert benchmark.as_dict() == scored.benchmark


def test_sensitivity_band_brackets_the_headline_for_an_eti_policy():
    scored = _build(_generic_result_data())
    assert scored.sensitivity is not None
    low, high = scored.sensitivity
    assert low <= scored.headline <= high
    assert high - low >= MIN_BAND_WIDTH, "an ETI band must have width, not just brackets"
    assert "ETI" in scored.sensitivity_note


# ---------------------------------------------------------------------------
# Sensitivity band width (external UI review, 2026-09-01)
# ---------------------------------------------------------------------------
#
# Explore printed "Sensitivity range: $+4,581.9B to $+4,581.9B (ETI
# 0.15-0.35)" for every calibrated preset whose module zeroes the behavioural
# *offset* while leaving TaxPolicy's default 0.25 elasticity in place: flexing
# an elasticity that multiplies zero moves neither end of the band.


@pytest.mark.parametrize(
    "preset_name",
    [
        name
        for name in (
            TCJA_PRESET,
            next((n for n in PRESET_POLICIES if "Estate" in n), None),
            next((n for n in PRESET_POLICIES if "Donut" in n), None),
            next((n for n in PRESET_POLICIES if "Corporate AMT" in n), None),
        )
        if name is not None
    ],
)
def test_calibrated_presets_never_report_a_zero_width_band(preset_name):
    policy = create_policy_from_preset(PRESET_POLICIES[preset_name])
    scorer = FiscalPolicyScorer(
        start_year=getattr(policy, "start_year", 2025), use_real_data=False
    )
    scored = _build(
        {
            "policy": policy,
            "result": scorer.score_policy(policy, dynamic=False),
            "scorer": scorer,
            "is_spending": False,
            "policy_name": preset_name,
        }
    )
    if scored.sensitivity is None:
        # Acceptable, but only when the surface says why instead of drawing a
        # range with no width.
        assert "No sensitivity range" in scored.sensitivity_note
        return
    low, high = scored.sensitivity
    assert high - low >= MIN_BAND_WIDTH, (
        f"{preset_name} reports a degenerate band {low:+,.1f} to {high:+,.1f}; "
        "a calibrated preset has no ETI channel to flex, so it must fall "
        "through to the engine's uncertainty band or say it has no range"
    )
    assert "ETI" not in scored.sensitivity_note, (
        "a calibrated preset's behavioural response is inside its "
        "calibration; the band must not be labelled as an ETI sweep"
    )


def test_a_zero_behavioral_offset_never_takes_the_eti_branch():
    """The precise condition, unit-tested away from any particular preset."""
    from fiscal_model.ui.tabs.results_summary import _sensitivity_band

    policy = TaxPolicy(
        name="Calibrated stand-in",
        description="behavioural response already inside the calibration",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
    )
    assert policy.taxable_income_elasticity > 0  # inherited default, the trap

    class _Result:
        low_estimate = [90.0] * 10
        high_estimate = [110.0] * 10

    band, note = _sensitivity_band(
        _Result(),
        policy,
        static_total=1000.0,
        behavioral_total=0.0,
        is_spending=False,
    )
    assert band == (900.0, 1100.0)
    assert note == "model uncertainty band"


def test_no_band_at_all_is_reported_as_a_reason_not_a_range():
    from fiscal_model.ui.tabs.results_summary import _sensitivity_band

    policy = TaxPolicy(
        name="Calibrated stand-in",
        description="no uncertainty path either",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
    )

    class _Result:
        low_estimate = [100.0] * 10
        high_estimate = [100.0] * 10

    band, note = _sensitivity_band(
        _Result(),
        policy,
        static_total=1000.0,
        behavioral_total=0.0,
        is_spending=False,
    )
    assert band is None
    assert "No sensitivity range" in note


def test_spending_policy_is_flagged_and_scored_on_the_outlay_path():
    policy = SpendingPolicy(
        name="Infrastructure Investment",
        description="+$100B annual spending",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=100.0,
    )
    scorer = FiscalPolicyScorer(use_real_data=False)
    scored = _build(
        {
            "policy": policy,
            "result": scorer.score_policy(policy, dynamic=False),
            "scorer": scorer,
            "is_spending": True,
            "policy_name": "Infrastructure Investment",
        }
    )
    assert scored.is_spending is True
    assert scored.headline > 0  # spending increases the deficit


def test_baseline_vintage_resolves_to_a_cbo_string():
    vintage = resolve_baseline_vintage()
    assert vintage.startswith("CBO")


# ---------------------------------------------------------------------------
# Hash stability (chip ⑩ invalidation)
# ---------------------------------------------------------------------------


def _context(**tax_inputs):
    base = {"rate_change_pct": 2.0, "threshold": 400_000, "eti": 0.25}
    base.update(tax_inputs)
    return {
        "mode": "📊 Single Policy",
        "is_spending": False,
        "tax_inputs": base,
        "spending_inputs": {},
    }


_SETTINGS = {
    "use_real_data": True,
    "dynamic_scoring": False,
    "macro_model": None,
    "use_microsim": False,
    "use_microsim_distribution": True,
    "data_year": 2022,
    "dark_mode": False,
}


def test_hash_is_stable_for_identical_inputs():
    first = compute_policy_spec_hash(_context(), dict(_SETTINGS))
    second = compute_policy_spec_hash(_context(), dict(_SETTINGS))
    assert first == second


def test_hash_changes_when_a_form_input_changes():
    baseline = compute_policy_spec_hash(_context(), dict(_SETTINGS))
    assert compute_policy_spec_hash(_context(rate_change_pct=3.0), dict(_SETTINGS)) != baseline
    assert compute_policy_spec_hash(_context(threshold=1_000_000), dict(_SETTINGS)) != baseline


def test_hash_changes_when_the_dynamic_toggle_changes():
    """Explore invalidates on a toggle change too, not just a preset change."""
    off = compute_policy_spec_hash(_context(), dict(_SETTINGS))
    on = compute_policy_spec_hash(_context(), {**_SETTINGS, "dynamic_scoring": True})
    assert off != on


def test_hash_ignores_presentation_only_settings():
    """Flipping dark mode must not blank a valid result panel."""
    light = compute_policy_spec_hash(_context(), dict(_SETTINGS))
    dark = compute_policy_spec_hash(_context(), {**_SETTINGS, "dark_mode": True})
    assert light == dark
    assert "dark_mode" not in SCORING_SETTING_KEYS


def test_hash_is_insensitive_to_key_order():
    reordered = {key: _SETTINGS[key] for key in reversed(list(_SETTINGS))}
    assert compute_policy_spec_hash(_context(), reordered) == compute_policy_spec_hash(
        _context(), dict(_SETTINGS)
    )


def test_scored_result_carries_the_hash_it_was_built_with():
    scored = _build(_generic_result_data(), policy_spec_hash="deadbeef")
    assert scored.policy_spec_hash == "deadbeef"


def test_detailed_results_download_names_use_the_shared_sanitizer():
    """Copilot review (PR #66): CSV/JSON download names must go through
    results_summary._file_stem, not a bare space replacement of policy.name."""
    import pathlib
    import re
    from types import SimpleNamespace

    from fiscal_model.ui.tabs.results_summary import _file_stem

    stem = _file_stem(SimpleNamespace(display_name="My/Policy: 💥 v2"))
    assert re.fullmatch(r"[a-z0-9_\-]+", stem), stem
    assert _file_stem(SimpleNamespace(display_name="///")) == "policy"

    src = pathlib.Path("fiscal_model/ui/tabs/detailed_results.py").read_text(encoding="utf-8")
    names = re.findall(r"file_name=f\"([^\"]+)\"", src)
    assert len(names) == 2, names
    assert all("_file_stem(scored)" in n for n in names), names
