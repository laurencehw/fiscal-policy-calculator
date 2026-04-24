"""
Tests for the multi-model comparison tab.

The tab orchestrates the existing ``compare_policy_models`` pipeline, so
these tests focus on the UI contract: the tab renders all model results
when they succeed, surfaces errors per-model when a backend fails, and
degrades cleanly when no results come back.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fiscal_model.models.base import ModelResult
from fiscal_model.models.comparison import ComparisonBundle


class _StubStreamlit:
    """Minimal Streamlit double that records what the tab emits."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.selectbox_value = None

    def header(self, text):
        self.calls.append(("header", text))

    def subheader(self, text):
        self.calls.append(("subheader", text))

    def markdown(self, text, **kwargs):
        del kwargs
        self.calls.append(("markdown", text))

    def info(self, text):
        self.calls.append(("info", text))

    def warning(self, text):
        self.calls.append(("warning", text))

    def error(self, text):
        self.calls.append(("error", text))

    def caption(self, text):
        self.calls.append(("caption", text))

    def metric(self, label, value, **kwargs):
        del kwargs
        self.calls.append(("metric", label, value))

    def selectbox(self, label, options, **kwargs):
        del label, kwargs
        return self.selectbox_value or options[0]

    def dataframe(self, df, **kwargs):
        del kwargs
        self.calls.append(("dataframe", df.to_dict(orient="records")))

    def line_chart(self, data):
        self.calls.append(("line_chart", data.shape if hasattr(data, "shape") else None))

    class _Spinner:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def spinner(self, _text):
        return self._Spinner()

    class _Expander:
        def __init__(self, outer):
            self.outer = outer

        def __enter__(self):
            return self.outer

        def __exit__(self, *exc):
            return False

    def expander(self, _text):
        return self._Expander(self)


def _make_bundle(*, include_error: bool = False) -> ComparisonBundle:
    bundle = ComparisonBundle(policy_name="Demo Top Rate")
    bundle.results.append(
        ModelResult(
            model_name="CBO-Style",
            policy_name="Demo Top Rate",
            ten_year_cost=-250.0,
            annual_effects=[-25.0] * 10,
            metadata={"methodology": "Static + ETI"},
        )
    )
    bundle.results.append(
        ModelResult(
            model_name="TPC-Microsim Pilot",
            policy_name="Demo Top Rate",
            ten_year_cost=-240.0,
            annual_effects=[-24.0] * 10,
            metadata={"methodology": "CPS microsim"},
        )
    )
    bundle.results.append(
        ModelResult(
            model_name="PWBM-OLG Pilot",
            policy_name="Demo Top Rate",
            ten_year_cost=-230.0,
            annual_effects=[-23.0] * 10,
            metadata={
                "methodology": "OLG + fiscal adapter",
                "confidence_label": "low",
            },
        )
    )
    if include_error:
        bundle.errors["Experimental Model"] = "Missing microdata"
    return bundle


@pytest.fixture
def stub_deps(monkeypatch):
    """Wire stubs for compare_policy_models and the policy builder."""
    from fiscal_model.ui.tabs import multi_model

    monkeypatch.setattr(
        multi_model,
        "build_default_comparison_models",
        lambda *args, **kwargs: [],
    )
    return multi_model


def test_tab_renders_all_results(stub_deps, monkeypatch):
    bundle = _make_bundle()
    monkeypatch.setattr(stub_deps, "compare_policy_models", lambda *a, **k: bundle)

    st = _StubStreamlit()
    stub_deps.render_multi_model_tab(
        st,
        is_spending=False,
        preset_policies={"Demo Top Rate": {"rate_change": 2.6}},
        tax_policy_cls=lambda **kwargs: SimpleNamespace(name=kwargs["name"]),
        policy_type_income_tax="income_tax",
        fiscal_policy_scorer_cls=lambda **kwargs: None,
        data_year=2022,
        use_real_data=False,
    )

    # Header + summary dataframe must be emitted.
    assert any(call[0] == "header" for call in st.calls)
    df_calls = [call for call in st.calls if call[0] == "dataframe"]
    assert len(df_calls) == 1
    rows = df_calls[0][1]
    model_names = {row["Model"] for row in rows}
    assert model_names == {"CBO-Style", "TPC-Microsim Pilot", "PWBM-OLG Pilot"}

    # Max spread metric is emitted with correct sign (|−250 − (−230)| = 20).
    metric_calls = [call for call in st.calls if call[0] == "metric"]
    assert len(metric_calls) == 1
    assert "$20.0B" in metric_calls[0][2] or "$20B" in metric_calls[0][2]

    # Line chart present with one column per model.
    line_calls = [call for call in st.calls if call[0] == "line_chart"]
    assert len(line_calls) == 1
    shape = line_calls[0][1]
    assert shape is not None and shape[1] == 3  # 3 model columns


def test_tab_surfaces_backend_errors(stub_deps, monkeypatch):
    bundle = _make_bundle(include_error=True)
    monkeypatch.setattr(stub_deps, "compare_policy_models", lambda *a, **k: bundle)

    st = _StubStreamlit()
    stub_deps.render_multi_model_tab(
        st,
        is_spending=False,
        preset_policies={"Demo Top Rate": {"rate_change": 2.6}},
        tax_policy_cls=lambda **kwargs: SimpleNamespace(name=kwargs["name"]),
        policy_type_income_tax="income_tax",
        fiscal_policy_scorer_cls=lambda **kwargs: None,
        data_year=2022,
        use_real_data=False,
    )

    backend_error_markers = [
        call for call in st.calls
        if call[0] == "markdown" and "Experimental Model" in call[1]
    ]
    assert backend_error_markers, "Expected backend error to be rendered"


def test_tab_handles_empty_bundle(stub_deps, monkeypatch):
    empty = ComparisonBundle(policy_name="Demo Top Rate")
    monkeypatch.setattr(stub_deps, "compare_policy_models", lambda *a, **k: empty)

    st = _StubStreamlit()
    stub_deps.render_multi_model_tab(
        st,
        is_spending=False,
        preset_policies={"Demo Top Rate": {"rate_change": 2.6}},
        tax_policy_cls=lambda **kwargs: SimpleNamespace(name=kwargs["name"]),
        policy_type_income_tax="income_tax",
        fiscal_policy_scorer_cls=lambda **kwargs: None,
        data_year=2022,
        use_real_data=False,
    )

    assert any(
        call[0] == "warning" and "No backend" in call[1]
        for call in st.calls
    )


def test_tab_skips_spending_policies(stub_deps):
    st = _StubStreamlit()
    stub_deps.render_multi_model_tab(
        st,
        is_spending=True,
        preset_policies={"Demo Top Rate": {}},
        tax_policy_cls=lambda **kwargs: SimpleNamespace(),
        policy_type_income_tax="income_tax",
        fiscal_policy_scorer_cls=lambda **kwargs: None,
        data_year=2022,
        use_real_data=False,
    )
    assert any(call[0] == "info" for call in st.calls)


def test_tab_skips_empty_preset_dict(stub_deps):
    st = _StubStreamlit()
    stub_deps.render_multi_model_tab(
        st,
        is_spending=False,
        preset_policies={},
        tax_policy_cls=lambda **kwargs: SimpleNamespace(),
        policy_type_income_tax="income_tax",
        fiscal_policy_scorer_cls=lambda **kwargs: None,
        data_year=2022,
        use_real_data=False,
    )
    assert any(call[0] == "info" for call in st.calls)
