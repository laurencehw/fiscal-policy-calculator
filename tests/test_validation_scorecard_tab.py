"""
Smoke tests for the Streamlit Validation tab renderer.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fiscal_model.ui.tabs.validation_scorecard import (
    _entry_to_row,
    render_validation_scorecard_tab,
)
from fiscal_model.validation.scorecard import ScorecardEntry


def _make_entry(**overrides) -> ScorecardEntry:
    base = dict(
        category="TCJA",
        policy_id="x",
        policy_name="Stub",
        official_10yr_billions=100.0,
        official_source="Stub",
        benchmark_kind="Test",
        benchmark_date="2025",
        benchmark_url="https://example.test",
        model_10yr_billions=104.0,
        difference_billions=4.0,
        percent_difference=4.0,
        abs_percent_difference=4.0,
        rating="Excellent",
        direction_match=True,
        known_limitations=[],
        notes="",
    )
    base.update(overrides)
    return ScorecardEntry(**base)


def test_entry_to_row_renders_signed_diff():
    row = _entry_to_row(_make_entry(percent_difference=-12.5, rating="Acceptable"))
    assert row["Δ%"] == "-12.5%"
    assert row["Rating"] == "Acceptable"
    assert "🟡" in row["Status"]


def test_entry_to_row_rates_poor_red():
    row = _entry_to_row(_make_entry(rating="Poor", percent_difference=-50.0))
    assert "🔴" in row["Status"]
    assert row["Δ%"] == "-50.0%"


def test_render_validation_scorecard_tab_runs_without_streamlit():
    """The renderer must work against a fully-mocked Streamlit module so it
    can be imported and exercised in CI without a Streamlit runtime."""
    st_mock = MagicMock()
    st_mock.columns.return_value = [MagicMock() for _ in range(4)]
    st_mock.radio.return_value = "By |Δ%| (worst first)"
    # Streamlit context managers: __enter__ takes no args (the protocol
    # passes no arguments since the descriptor is bound). Use MagicMocks
    # so the lambda-with-`self` mistake can't sneak back in.
    expander_mock = st_mock.expander.return_value
    expander_mock.__enter__ = MagicMock(return_value=expander_mock)
    expander_mock.__exit__ = MagicMock(return_value=None)

    render_validation_scorecard_tab(st_mock)

    # Header + summary metrics + at least one section header should render.
    assert st_mock.header.called
    assert st_mock.markdown.called
    assert st_mock.subheader.called
    assert st_mock.dataframe.called


def test_render_validation_scorecard_tab_handles_compute_failure(monkeypatch):
    """If the cached scorecard raises, the tab shows an error rather than 500ing."""
    from fiscal_model.ui.tabs import validation_scorecard as module

    def _boom(*_a, **_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "cached_default_scorecard", _boom)
    st_mock = MagicMock()
    render_validation_scorecard_tab(st_mock)
    assert st_mock.error.called


def test_unsourced_entries_get_their_own_table():
    """An entry whose provenance was never established is in neither the
    published table nor the illustrations table. It must still be rendered,
    or a future sourcing gap would silently vanish from the tab."""
    from fiscal_model.ui.tabs.validation_scorecard import (
        _render_unsourced_table,
        unsourced_entries,
    )
    from fiscal_model.validation.scorecard import ScorecardSummary

    entry = _make_entry(policy_id="mystery", provenance="unclassified")
    summary = ScorecardSummary(
        total_entries=1,
        within_5pct=1,
        within_10pct=1,
        within_15pct=1,
        within_20pct=1,
        direction_match=1,
        poor=0,
        mean_abs_percent_difference=4.0,
        median_abs_percent_difference=4.0,
        ratings_breakdown={"Excellent": 1},
        by_category={},
        entries=[entry],
    )

    assert [e.policy_id for e in unsourced_entries(summary)] == ["mystery"]

    st_mock = MagicMock()
    _render_unsourced_table(st_mock, summary)
    assert st_mock.subheader.called
    assert st_mock.dataframe.called


def test_unsourced_table_is_skipped_when_the_bucket_is_empty():
    from fiscal_model.ui.tabs.validation_scorecard import _render_unsourced_table
    from fiscal_model.validation.scorecard import ScorecardSummary

    summary = ScorecardSummary(
        total_entries=0,
        within_5pct=0,
        within_10pct=0,
        within_15pct=0,
        within_20pct=0,
        direction_match=0,
        poor=0,
        mean_abs_percent_difference=0.0,
        median_abs_percent_difference=0.0,
        ratings_breakdown={},
        by_category={},
        entries=[_make_entry(provenance="line_item")],
    )
    st_mock = MagicMock()
    _render_unsourced_table(st_mock, summary)
    assert not st_mock.subheader.called
