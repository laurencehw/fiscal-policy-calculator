"""
Tests for the TPC-style winners/losers narrative on the Distribution tab.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fiscal_model.ui.distribution_callouts import (
    GroupSummary,
    build_winners_losers,
    headline_sentence,
    render_winners_losers_callout,
)


def _result(name: str, *, avg: float, pct: float, share: float, floor: float = 0.0):
    """Stand-in for ``DistributionalResult`` carrying just the fields the
    narrative helpers read. ``floor`` lets tests pin the income-group
    ordering used to pick top/bottom."""
    return SimpleNamespace(
        income_group=SimpleNamespace(name=name, floor=floor),
        tax_change_avg=avg,
        tax_change_pct_income=pct,
        share_of_total_change=share,
    )


def _analysis(*results, total: float = 0.0):
    return SimpleNamespace(results=list(results), total_tax_change=total)


def test_build_winners_losers_partitions_groups():
    analysis = _analysis(
        _result("Bottom Quintile", avg=+50, pct=+0.10, share=+0.01, floor=0),
        _result("Middle Quintile", avg=-100, pct=-0.20, share=-0.05, floor=50_000),
        _result("Top Quintile", avg=-4500, pct=-1.20, share=-0.94, floor=200_000),
        total=-200.0,
    )
    summary = build_winners_losers(analysis)

    assert [g.name for g in summary.winners] == ["Top Quintile", "Middle Quintile"]
    assert [g.name for g in summary.losers] == ["Bottom Quintile"]
    # Top group is the last result (assumed sorted low-to-high in the engine).
    assert summary.top_group.name == "Top Quintile"
    assert summary.bottom_group.name == "Bottom Quintile"
    assert summary.total_change_billions == pytest.approx(-200.0)


def test_winners_sorted_most_negative_first():
    analysis = _analysis(
        _result("A", avg=-50, pct=-0.1, share=-0.01),
        _result("B", avg=-1000, pct=-2.5, share=-0.5),
        _result("C", avg=-200, pct=-0.4, share=-0.04),
    )
    summary = build_winners_losers(analysis)
    assert [g.name for g in summary.winners] == ["B", "C", "A"]


def test_headline_direction_progressive_when_top_pays_more():
    analysis = _analysis(
        _result("Bottom", avg=10, pct=0.05, share=0.001, floor=0),
        _result("Top", avg=20000, pct=4.5, share=0.99, floor=500_000),
    )
    summary = build_winners_losers(analysis)
    assert summary.headline_direction == "progressive"


def test_headline_direction_regressive_when_bottom_hit_harder():
    analysis = _analysis(
        _result("Bottom", avg=200, pct=2.0, share=0.4, floor=0),
        _result("Top", avg=2500, pct=0.3, share=0.6, floor=500_000),
    )
    summary = build_winners_losers(analysis)
    assert summary.headline_direction == "regressive"


def test_headline_direction_flat_when_pct_of_income_matches():
    analysis = _analysis(
        _result("Bottom", avg=100, pct=0.50, share=0.25, floor=0),
        _result("Top", avg=5000, pct=0.50, share=0.75, floor=500_000),
    )
    summary = build_winners_losers(analysis)
    assert summary.headline_direction == "flat"


def test_headline_direction_handles_empty_analysis():
    summary = build_winners_losers(_analysis())
    assert summary.headline_direction == "flat"
    assert summary.top_group is None
    assert summary.bottom_group is None


def test_top_and_bottom_picked_after_explicit_income_sort():
    """If the engine returns groups in an unexpected order, the narrative
    must still pick top/bottom by income — not by list position."""
    analysis = _analysis(
        # Pass them out of income order on purpose.
        _result("Top Quintile", avg=-4500, pct=-1.20, share=-0.94, floor=200_000),
        _result("Bottom Quintile", avg=+50, pct=+0.10, share=+0.01, floor=0),
        _result("Middle Quintile", avg=-100, pct=-0.20, share=-0.05, floor=50_000),
    )
    summary = build_winners_losers(analysis)
    assert summary.top_group is not None and summary.top_group.name == "Top Quintile"
    assert summary.bottom_group is not None and summary.bottom_group.name == "Bottom Quintile"


def test_headline_sentence_phrases_top_and_bottom():
    analysis = _analysis(
        _result("Bottom Quintile", avg=+30, pct=+0.10, share=+0.01, floor=0),
        _result("Top Quintile", avg=-4250, pct=-1.20, share=-0.95, floor=500_000),
    )
    sentence = headline_sentence(build_winners_losers(analysis))
    assert "top quintile" in sentence.lower()
    assert "bottom quintile" in sentence.lower()
    assert "tax cut" in sentence
    assert "tax increase" in sentence
    # Signed-dollar formatting uses unicode minus to match TPC reports.
    assert "−$4,250" in sentence
    assert "+$30" in sentence


def test_headline_sentence_handles_empty_analysis():
    sentence = headline_sentence(build_winners_losers(_analysis()))
    assert "no distributional impact" in sentence.lower()


def test_render_winners_losers_callout_with_mocked_streamlit():
    analysis = _analysis(
        _result("Bottom", avg=+30, pct=+0.10, share=+0.01, floor=0),
        _result("Middle", avg=-100, pct=-0.20, share=-0.05, floor=50_000),
        _result("Top", avg=-4500, pct=-1.20, share=-0.94, floor=200_000),
        total=-200.0,
    )

    st = MagicMock()
    win_col = MagicMock()
    lose_col = MagicMock()
    st.columns.return_value = [win_col, lose_col]

    render_winners_losers_callout(st, analysis)

    # Headline + direction caption + winner/loser cards all render.
    assert st.markdown.called
    assert st.caption.called
    assert st.columns.called


def test_render_handles_no_winners_no_losers():
    """A zero-impact policy should not crash the renderer."""
    analysis = _analysis(
        _result("Bottom", avg=0, pct=0, share=0, floor=0),
        _result("Top", avg=0, pct=0, share=0, floor=500_000),
    )
    st = MagicMock()
    st.columns.return_value = [MagicMock(), MagicMock()]
    render_winners_losers_callout(st, analysis)
    # Should still call markdown to render headers and the no-winners /
    # no-losers caption.
    assert st.markdown.called


def test_group_summary_is_immutable():
    """Frozen dataclass is intentional so the summary can't be mutated mid-render."""
    g = GroupSummary(name="Top", avg_tax_change=-100.0, pct_of_income=-0.5, share_of_total=-0.9)
    with pytest.raises(FrozenInstanceError):
        g.avg_tax_change = 0  # type: ignore[misc]
