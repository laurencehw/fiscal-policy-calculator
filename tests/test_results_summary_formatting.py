from __future__ import annotations

from types import SimpleNamespace

from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.tabs.results_summary import (
    _build_credibility_html,
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
    # Bare "$" is correct here: the caller wraps this in <p>…</p> and renders it
    # with unsafe_allow_html, and an HTML block is opaque to remark-math — so
    # neither KaTeX nor markdown escaping applies (tests/test_dollar_rendering.py).
    assert "<strong>add approximately $4,582 billion</strong>" in html
    assert "<strong>$458B per year</strong>" in html
    assert "<strong>1.4% of GDP annually</strong>" in html


def test_build_credibility_html_keeps_the_band_and_the_row_apart():
    """Two facts, two places. Collapsing them is the claim CLAUDE.md forbids.

    The card H4 replaced printed one category mean — blended across fitted
    bookkeeping and unfitted reconstructions — under a single rating word. What
    prints now is the policy class's out-of-sample distribution *and*, beside
    it, this policy's own scorecard row with the tier that row sits in.
    """
    html = _build_credibility_html(
        SimpleNamespace(
            uncertainty_low=-1040.0,
            uncertainty_high=-960.0,
            outer_low=-1200.0,
            outer_high=-800.0,
            evidence_type="out_of_sample_class_distribution",
            category="Payroll",
            policy_class="payroll",
            class_label="payroll",
            n_tier1_rows=2,
            mean_abs_pct_error=7.8,
            median_abs_pct_error=7.8,
            max_abs_pct_error=8.1,
            rows_inside_mean_band=1,
            no_band_reason="",
            own_row_policy_id="ss_donut_250k",
            own_row_tier="reconstruction",
            own_row_tier_label="Unfitted reconstruction",
            own_row_abs_pct_error=89.2,
            own_row_caption="Unfitted reconstruction, 89.2% from -$1.43T (CBO).",
            holdout_status="post_lock_holdout",
            caption="Out-of-sample accuracy, payroll: 2 pre-registered rows.",
            limitations=["Known limitation <must escape>"],
        )
    )

    assert "Accuracy evidence" in html
    assert "Policy class: <strong>payroll</strong>" in html
    assert "Out-of-sample rows: <strong>2</strong>" in html
    assert "Mean error: <strong>±7.8%</strong>" in html
    assert "Typical: <strong>$-1,040B to $-960B</strong>" in html
    assert "Worst row: <strong>$-1,200B to $-800B</strong>" in html
    assert "<strong>1 of 2</strong> inside the mean" in html
    assert "Unfitted reconstruction" in html
    assert "89.2% from -$1.43T" in html
    assert "not an official CBO/JCT score" in html
    assert "Known limitation &lt;must escape&gt;" in html
    assert "Known limitation <must escape>" not in html
    # A single blended accuracy word is exactly what this replaced.
    assert "confidence</span>" not in html


def test_build_credibility_html_says_when_there_is_no_band():
    html = _build_credibility_html(
        SimpleNamespace(
            uncertainty_low=None,
            uncertainty_high=None,
            outer_low=None,
            outer_high=None,
            evidence_type="no_out_of_sample_benchmark",
            category="TCJA",
            policy_class=None,
            class_label=None,
            n_tier1_rows=0,
            mean_abs_pct_error=None,
            median_abs_pct_error=None,
            max_abs_pct_error=None,
            rows_inside_mean_band=None,
            no_band_reason="no pre-registered row scores a bundle",
            own_row_policy_id="tcja_full_extension",
            own_row_tier="fitted",
            own_row_tier_label="Calibrated reference",
            own_row_abs_pct_error=0.4,
            own_row_caption="Calibrated to reproduce $4.60T (CBO).",
            holdout_status="not_applicable_calibrated",
            caption="No out-of-sample band: no pre-registered row scores a bundle.",
            limitations=[],
        )
    )

    assert "<strong>No out-of-sample band</strong> for this policy class" in html
    assert "Calibrated reference" in html
    assert "Calibrated to reproduce $4.60T" in html
    assert "Mean error" not in html


def test_build_credibility_html_says_when_there_is_no_row_either():
    html = _build_credibility_html(
        SimpleNamespace(
            uncertainty_low=-1148.0,
            uncertainty_high=-852.0,
            outer_low=-1245.0,
            outer_high=-755.0,
            evidence_type="out_of_sample_class_distribution",
            category="Generic",
            policy_class="ordinary_rate_change",
            class_label="ordinary rate change",
            n_tier1_rows=4,
            mean_abs_pct_error=14.8,
            median_abs_pct_error=16.4,
            max_abs_pct_error=24.5,
            rows_inside_mean_band=1,
            no_band_reason="",
            own_row_policy_id=None,
            own_row_tier=None,
            own_row_tier_label=None,
            own_row_abs_pct_error=None,
            own_row_caption="",
            holdout_status="not_applicable_generic",
            caption="Out-of-sample accuracy, ordinary rate change.",
            limitations=[],
        )
    )

    assert "No scorecard row scores this exact policy." in html
    assert "Policy class: <strong>ordinary rate change</strong>" in html


def test_build_credibility_html_returns_empty_for_missing_metadata():
    assert _build_credibility_html(None) == ""


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
    # HTML bold, not markdown bold. Currency stays unescaped on purpose: an
    # HTML block is opaque to both markdown escapes and KaTeX.
    assert "<strong>$" in body
    assert "**" not in body
