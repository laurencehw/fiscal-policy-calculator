"""
Tests for multi-model pilot capability matrix and specialized preset wiring.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fiscal_model.corporate import create_biden_corporate_rate_only
from fiscal_model.credits import create_biden_ctc_2021, create_biden_eitc_childless
from fiscal_model.distribution_effects import policy_to_microsim_reforms
from fiscal_model.models.capabilities import (
    CBO_ENGINE,
    TPC_ENGINE,
    comparable_across_default_pilots,
    engine_support_matrix,
    policy_family,
    support_label,
    tpc_support,
)
from fiscal_model.models.comparison import (
    UnsupportedModelPolicyError,
    compare_policy_models,
)
from fiscal_model.payroll import create_ss_donut_hole
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.ui.tabs import multi_model


def test_income_tax_is_comparable_across_default_pilots():
    policy = TaxPolicy(
        name="Top rate +1pp",
        description="",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=400_000,
    )
    assert policy_family(policy) == "income_tax"
    assert support_label(policy) == "CBO+TPC"
    assert comparable_across_default_pilots(policy) is True


def test_corporate_is_cbo_only_with_explicit_tpc_reason():
    policy = create_biden_corporate_rate_only()
    assert policy_family(policy) == "corporate"
    assert support_label(policy) == "CBO only"
    support = tpc_support(policy)
    assert support.supported is False
    assert "corporate" in support.reason.lower() or "firm-level" in support.reason.lower()


def test_payroll_donut_is_cbo_only():
    policy = create_ss_donut_hole()
    assert policy_family(policy) == "payroll"
    assert support_label(policy) == "CBO only"
    assert tpc_support(policy).supported is False


def test_ctc_and_eitc_map_to_microsim_reforms():
    ctc = create_biden_ctc_2021()
    eitc = create_biden_eitc_childless()
    assert "ctc_amount" in policy_to_microsim_reforms(ctc)
    # A childless expansion moves the childless schedule only; it used to be
    # mapped to a single multiplier over all four child counts.
    assert "eitc_childless_max_credit" in policy_to_microsim_reforms(eitc)
    assert support_label(ctc) == "CBO+TPC"
    assert support_label(eitc) == "CBO+TPC"


def test_engine_support_matrix_default_engines():
    policy = create_biden_corporate_rate_only()
    rows = engine_support_matrix(policy)
    by_name = {row.engine: row for row in rows}
    assert by_name[CBO_ENGINE].supported is True
    assert by_name[TPC_ENGINE].supported is False


def test_compare_corporate_collects_tpc_as_not_representable():
    class CBOStub:
        name = CBO_ENGINE

        def score(self, policy):
            return SimpleNamespace(
                model_name=self.name,
                policy_name=policy.name,
                ten_year_cost=-1350.0,
                annual_effects=[-135.0] * 10,
                metadata={"methodology": "stub", "confidence_label": "calibrated"},
            )

    class TPCStub:
        name = TPC_ENGINE

        def score(self, policy):
            support = tpc_support(policy)
            assert support.supported is False
            raise UnsupportedModelPolicyError(support.reason)

    policy = create_biden_corporate_rate_only()
    bundle = compare_policy_models(policy, [CBOStub(), TPCStub()], continue_on_error=True)
    assert len(bundle.results) == 1
    assert bundle.results[0].model_name == CBO_ENGINE
    assert TPC_ENGINE in bundle.errors
    assert "firm-level" in bundle.errors[TPC_ENGINE].lower() or "corporate" in bundle.errors[
        TPC_ENGINE
    ].lower()


@pytest.mark.parametrize(
    "preset,family",
    [
        ({"is_corporate": True, "corporate_type": "biden_28"}, "corporate"),
        ({"is_credit": True, "credit_type": "biden_ctc_2021"}, "credit"),
        ({"is_payroll": True, "payroll_type": "donut_250k"}, "payroll"),
    ],
)
def test_create_policy_from_preset_builds_specialized_families(preset, family):
    policy = create_policy_from_preset(preset)
    assert policy is not None
    assert policy_family(policy) == family


def test_multi_model_tab_labels_corporate_as_cbo_only(monkeypatch):
    st = MagicMock()
    st.selectbox.side_effect = lambda label, options, **kwargs: options[0]
    st.spinner.return_value.__enter__ = lambda *a, **k: None
    st.spinner.return_value.__exit__ = lambda *a, **k: False
    st.expander.return_value.__enter__ = lambda *a, **k: st
    st.expander.return_value.__exit__ = lambda *a, **k: False

    corporate = create_biden_corporate_rate_only()

    monkeypatch.setattr(
        multi_model,
        "_build_policy",
        lambda **kwargs: corporate,
    )
    monkeypatch.setattr(
        multi_model,
        "build_default_comparison_models",
        lambda *a, **k: [],
    )

    def fake_compare(policy, models, continue_on_error=True):
        del models, continue_on_error
        from fiscal_model.models.base import ModelResult
        from fiscal_model.models.comparison import ComparisonBundle

        bundle = ComparisonBundle(policy_name=policy.name)
        bundle.results.append(
            ModelResult(
                model_name=CBO_ENGINE,
                policy_name=policy.name,
                ten_year_cost=-1350.0,
                annual_effects=[-135.0] * 10,
                metadata={"methodology": "stub", "confidence_label": "calibrated"},
            )
        )
        bundle.errors[TPC_ENGINE] = tpc_support(policy).reason
        return bundle

    monkeypatch.setattr(multi_model, "compare_policy_models", fake_compare)

    multi_model.render_multi_model_tab(
        st,
        is_spending=False,
        preset_policies={
            "Biden Corporate 21%→28% (CBO: -$1.35T)": {
                "is_corporate": True,
                "corporate_type": "biden_rate",
            }
        },
        tax_policy_cls=TaxPolicy,
        policy_type_income_tax=PolicyType.INCOME_TAX,
        fiscal_policy_scorer_cls=lambda **kwargs: None,
        data_year=2022,
        use_real_data=False,
    )

    select_calls = [c for c in st.selectbox.call_args_list]
    assert select_calls
    options = select_calls[0].kwargs.get("options") or select_calls[0].args[1]
    assert any("CBO only" in opt for opt in options)

    info_texts = [str(c.args[0]) for c in st.info.call_args_list]
    assert any("Only one default pilot" in text for text in info_texts)

    markdown_texts = [str(c.args[0]) for c in st.markdown.call_args_list]
    assert any("Not representable" in text for text in markdown_texts)
