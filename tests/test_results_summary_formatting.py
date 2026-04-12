from __future__ import annotations

from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.tabs.results_summary import (
    _build_interpretation_html,
    render_results_summary_tab,
)


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _DummyStreamlit:
    def __init__(self) -> None:
        self.markdown_calls: list[tuple[str, dict[str, object]]] = []

    def header(self, *args, **kwargs):
        del args, kwargs
        return None

    def markdown(self, body, **kwargs):
        self.markdown_calls.append((body, kwargs))
        return None

    def code(self, *args, **kwargs):
        del args, kwargs
        return None

    def metric(self, *args, **kwargs):
        del args, kwargs
        return None

    def caption(self, *args, **kwargs):
        del args, kwargs
        return None

    def subheader(self, *args, **kwargs):
        del args, kwargs
        return None

    def info(self, *args, **kwargs):
        del args, kwargs
        return None

    def plotly_chart(self, *args, **kwargs):
        del args, kwargs
        return None

    def download_button(self, *args, **kwargs):
        del args, kwargs
        return None

    def dataframe(self, *args, **kwargs):
        del args, kwargs
        return None

    def button(self, *args, **kwargs):
        del args, kwargs
        return False

    def selectbox(self, *args, **kwargs):
        del args, kwargs
        return "(none)"

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_DummyContext() for _ in range(count)]

    def expander(self, *args, **kwargs):
        del args, kwargs
        return _DummyContext()


def _build_result_data():
    policy = TaxPolicy(
        name="TCJA-style extension",
        description="Extend expiring individual tax provisions",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-0.01,
        affected_income_threshold=0,
    )
    scorer = FiscalPolicyScorer(use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    return {
        "policy": policy,
        "policy_name": policy.name,
        "result": result,
        "is_spending": False,
    }


def test_build_interpretation_html_avoids_markdown_currency_markup():
    html = _build_interpretation_html(
        final_deficit_total=4582.0,
        n_years=10,
        annual_avg=458.2,
        pct_of_gdp=1.4,
    )

    assert "**" not in html
    assert "<strong>add approximately $4,582 billion</strong>" in html
    assert "<strong>$458B per year</strong>" in html
    assert "<strong>1.4% of GDP annually</strong>" in html


def test_render_results_summary_uses_html_for_interpretation():
    st_module = _DummyStreamlit()
    result_data = _build_result_data()

    render_results_summary_tab(
        st_module=st_module,
        result_data=result_data,
        cbo_score_map={},
    )

    interpretation_calls = [
        (body, kwargs)
        for body, kwargs in st_module.markdown_calls
        if "This policy would" in body or "negligible fiscal impact" in body
    ]
    assert interpretation_calls

    body, kwargs = interpretation_calls[0]
    assert kwargs.get("unsafe_allow_html") is True
    assert "<strong>$" in body
    assert "**" not in body
