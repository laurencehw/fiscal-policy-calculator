"""
The app's spending presets spend out, and say so.

Validation switched to the budget-authority -> outlay spend-out model in lane
L2; the app kept booking authority as outlays. These tests pin the follow-up:

1. **Every shipped spending program is classified**, in the preset's own
   definition, by the account type it funds - never by a benchmark id and
   never by the number the class produces.
2. **``immediate`` is still reachable**, as an explicit choice under Advanced
   parameters, but is the default for nothing.
3. **The number change ships with its explanation.** A spending score renders
   a line naming the profile and the 10-year outlay/authority ratio.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from components.results import ScoredResult
from fiscal_model.app_data import CBO_SCORE_MAP
from fiscal_model.composer.composer import (
    _CATEGORY_TO_OUTLAY_CLASS as _GOAL_TO_OUTLAY_CLASS,
)
from fiscal_model.composer.composer import _build_spending_policy
from fiscal_model.composer.goal_spec import SpendingGoal
from fiscal_model.policies import PolicyType, SpendingPolicy
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.spending_outlays import (
    ACCOUNT_CLASS_LABELS,
    IMMEDIATE,
    account_class_label,
    account_classes,
)
from fiscal_model.ui.policy_input_spending import (
    OUTLAY_CLASS_ORDER,
    SPENDING_PRESETS,
    calculate_spending_policy_result,
    outlay_class_for,
    render_spending_policy_inputs,
)
from fiscal_model.ui.tabs.results_summary import render_headline_block, spend_out_caption

_SPEND_OUT_CLASSES = tuple(name for name in account_classes() if name != IMMEDIATE)


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:  # pragma: no cover - mirrors Streamlit
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _FakeStreamlit:
    """Enough Streamlit to render the spending form and the headline block."""

    def __init__(self):
        self.session_state = _SessionState()
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.codes: list[str] = []

    def markdown(self, body="", *args, **kwargs):
        self.markdowns.append(body)

    def caption(self, body="", *args, **kwargs):
        self.captions.append(body)

    def code(self, body="", *args, **kwargs):
        self.codes.append(body)

    def expander(self, *args, **kwargs):
        return _Ctx()

    def _resolve(self, key, fallback):
        if key is None:
            return fallback
        if key in self.session_state:
            return self.session_state[key]
        self.session_state[key] = fallback
        return fallback

    def selectbox(self, label, options=None, index=0, key=None, **kwargs):
        opts = list(options or [])
        if key is not None and key in self.session_state:
            current = self.session_state[key]
            assert current in opts, f"session_state[{key!r}] = {current!r} not in {opts!r}"
            return current
        return self._resolve(key, opts[index or 0])

    def text_input(self, label, value="", key=None, **kwargs):
        return self._resolve(key, value)

    def checkbox(self, label, value=False, key=None, **kwargs):
        return self._resolve(key, bool(value))

    def number_input(self, label, value=None, min_value=None, key=None, **kwargs):
        return self._resolve(key, value if value is not None else min_value)

    def slider(self, label, min_value=None, max_value=None, value=None, key=None, **kwargs):
        return self._resolve(key, value if value is not None else min_value)


# ── 1. Every shipped program is classified ─────────────────────────────────


def test_every_spending_preset_declares_a_spend_out_class():
    for name, preset in SPENDING_PRESETS.items():
        declared = preset.get("outlay_account_class")
        assert declared, f"{name} ships without an account class"
        assert declared in _SPEND_OUT_CLASSES, (
            f"{name} declares {declared!r}, which is not a fitted spend-out "
            f"profile. Classify it from the account type it funds."
        )


def test_a_preset_keeps_its_own_class_and_a_changed_category_re_derives_one():
    preset = SPENDING_PRESETS["Universal Childcare ($100B/yr)"]
    # The preset's own classification wins over what its category implies:
    # childcare subsidies are assistance awards, not federal operations.
    assert preset["category"] == "Non-Defense Discretionary"
    assert outlay_class_for(preset, "Non-Defense Discretionary") == "grants_and_procurement"
    # Change the category and the classification follows the new account type.
    assert outlay_class_for(preset, "Social Security") == "mandatory_benefit"
    assert outlay_class_for(preset, "Infrastructure") == "construction_and_capital"


def test_tailor_form_returns_the_programs_class():
    st = _FakeStreamlit()
    out = render_spending_policy_inputs(st, default_preset="Infrastructure Investment ($100B/yr)")
    assert out["outlay_account_class"] == "construction_and_capital"


def test_the_form_scores_on_that_class():
    st = _FakeStreamlit()
    inputs = render_spending_policy_inputs(
        st, default_preset="Infrastructure Investment ($100B/yr)"
    )
    data = calculate_spending_policy_result(
        spending_inputs=inputs,
        spending_policy_cls=SpendingPolicy,
        policy_type_discretionary_nondefense=PolicyType.DISCRETIONARY_NONDEFENSE,
        fiscal_policy_scorer_cls=FiscalPolicyScorer,
        use_real_data=False,
        dynamic_scoring=False,
    )
    assert data["policy"].outlay_account_class == "construction_and_capital"
    result = data["result"]
    # Outlays are strictly below authority: the construction tail runs past the
    # window. The identity would make the two equal.
    assert result.outlay_rate_in_window < 0.75
    assert abs(sum(result.static_spending_effect)) < abs(result.total_budget_authority)


def test_a_caller_that_omits_the_key_still_spends_out():
    """A stale share link or an older caller must not silently fall back to the
    identity - that is the behaviour this lane is removing."""
    data = calculate_spending_policy_result(
        spending_inputs={
            "program_name": "legacy caller",
            "annual_spending": 100.0,
            "spending_category": "Infrastructure",
            "growth_rate": 0.02,
            "multiplier": 1.0,
            "is_one_time": False,
            "duration": 10,
        },
        spending_policy_cls=SpendingPolicy,
        policy_type_discretionary_nondefense=PolicyType.DISCRETIONARY_NONDEFENSE,
        fiscal_policy_scorer_cls=FiscalPolicyScorer,
        use_real_data=False,
        dynamic_scoring=False,
    )
    assert data["policy"].outlay_account_class == "construction_and_capital"


# ── 2. ``immediate`` is a choice, not a default ────────────────────────────


def test_immediate_is_offered_but_defaults_nowhere():
    assert IMMEDIATE in OUTLAY_CLASS_ORDER, (
        "the identity must stay reachable as an explicit advanced choice"
    )
    assert set(OUTLAY_CLASS_ORDER) == set(account_classes())
    for name, preset in SPENDING_PRESETS.items():
        assert outlay_class_for(preset, preset["category"]) != IMMEDIATE, name


def test_every_offered_class_has_a_label():
    for name in OUTLAY_CLASS_ORDER:
        assert ACCOUNT_CLASS_LABELS[name]
        assert account_class_label(name) == ACCOUNT_CLASS_LABELS[name]


# ── 3. Build's spending picks spend out too ────────────────────────────────


def test_every_spending_goal_category_spends_out():
    from fiscal_model.composer.composer import _CATEGORY_TO_BUDGET_CATEGORY

    assert set(_GOAL_TO_OUTLAY_CLASS) == set(_CATEGORY_TO_BUDGET_CATEGORY), (
        "every goal category the composer can build needs a classification"
    )
    for category, account_class in _GOAL_TO_OUTLAY_CLASS.items():
        assert account_class in _SPEND_OUT_CLASSES, category


def test_a_built_spending_goal_carries_its_class():
    goal = SpendingGoal(label="Rebuild bridges", category="infrastructure", annual_billions=50.0)
    policy = _build_spending_policy(goal, 2026)
    assert policy.outlay_account_class == "construction_and_capital"

    benefit = SpendingGoal(label="Expand Medicaid", category="healthcare", annual_billions=50.0)
    assert _build_spending_policy(benefit, 2026).outlay_account_class == "mandatory_benefit"


# ── 4. The number change ships with its explanation ────────────────────────


def _spending_run(account_class: str):
    policy = SpendingPolicy(
        name="Infrastructure Investment",
        description="$100B/yr",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=100.0,
        category="nondefense",
        outlay_account_class=account_class,
        start_year=2025,
        duration_years=10,
    )
    scorer = FiscalPolicyScorer(use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    return {
        "policy": policy,
        "result": result,
        "scorer": scorer,
        "is_spending": True,
        "policy_name": "Infrastructure Investment ($100B/yr)",
    }


def test_the_note_names_the_profile_and_the_ratio():
    data = _spending_run("construction_and_capital")
    note = spend_out_caption(data["policy"], data["result"])
    assert "construction and capital" in note
    assert "outlay/authority ratio" in note
    ratio = data["result"].outlay_rate_in_window
    assert f"{ratio:.2f}" in note


def test_no_note_when_nothing_spends_out():
    data = _spending_run(IMMEDIATE)
    assert spend_out_caption(data["policy"], data["result"]) == ""
    assert spend_out_caption(SimpleNamespace(), data["result"]) == ""


def test_the_headline_block_renders_the_note():
    data = _spending_run("construction_and_capital")
    scored = ScoredResult.from_pipeline(
        result_data=data,
        policy_spec_hash="spend-out-note",
        dynamic_scoring=False,
        dynamic_view=None,
        cbo_score_map=CBO_SCORE_MAP,
        baseline_vintage="CBO Feb 2026",
    )
    st = _FakeStreamlit()
    render_headline_block(st, scored, data)
    assert any("Spend-out:" in caption for caption in st.captions), st.captions


def test_a_tax_score_renders_no_spend_out_note():
    from fiscal_model.policies import TaxPolicy

    policy = TaxPolicy(
        name="Custom rate",
        description="+2pp above $400,000",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
    )
    scorer = FiscalPolicyScorer(use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    assert spend_out_caption(policy, result) == ""


@pytest.mark.parametrize("name", sorted(SPENDING_PRESETS))
def test_every_preset_scores_and_explains_itself(name):
    """End to end, for all eleven shipped programs."""
    preset = SPENDING_PRESETS[name]
    policy = SpendingPolicy(
        name=name,
        description=name,
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=preset["annual_spending"],
        annual_growth_rate=preset["growth_rate"],
        gdp_multiplier=preset["multiplier"],
        is_one_time=preset["is_one_time"],
        category="nondefense",
        outlay_account_class=preset["outlay_account_class"],
        duration_years=preset["duration"],
    )
    result = FiscalPolicyScorer(use_real_data=False).score_policy(policy, dynamic=False)
    assert 0.0 < result.outlay_rate_in_window <= 1.0
    assert spend_out_caption(policy, result)
